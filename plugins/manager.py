#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
插件管理器模块

负责插件的加载、卸载、安装和管理
"""

import os
import sys
import json
import importlib
import inspect
import logging
import shutil
import time
import threading
import zipfile
from pathlib import Path
from datetime import datetime

from core.exceptions import PluginError, PluginLoadError, PluginDependencyError, PluginInstallError
from core.utils import ensure_dir, compute_file_hash, extract_zip, create_unique_id

# 设置日志
logger = logging.getLogger('plugins.manager')

class PluginManager:
    """插件管理器类
    
    管理应用程序的所有插件，提供插件的加载、卸载、安装和管理功能
    """
    
    def __init__(self, app_core):
        """初始化插件管理器
        
        Args:
            app_core: 应用核心实例
        """
        self.app_core = app_core
        self.config = app_core.config
        self.event_system = app_core.event_system
        self.thread_manager = app_core.thread_manager
        self.logger = logging.getLogger('plugins.manager')
        
        # 获取或初始化repository
        if hasattr(app_core, 'repository'):
            self.repository = app_core.repository
        else:
            # 初始化repository
            from data.repository import Repository
            self.repository = Repository(app_core)
            # 初始化数据库
            self.repository.initialize()
            # 将repository添加到app_core中，以便其他组件使用
            app_core.repository = self.repository
        
        # 插件相关路径
        self.base_plugins_dir = self.config.get("plugins_directory")
        if not self.base_plugins_dir:
            # 默认插件目录
            user_home = os.path.expanduser("~")
            app_dir = os.path.join(user_home, ".edgeplughub")
            self.base_plugins_dir = os.path.join(app_dir, "plugins")
        
        # 确保插件目录存在
        ensure_dir(self.base_plugins_dir)
        
        # 内置插件目录
        self.builtin_plugins_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            'builtin_plugins'
        )
        
        # 已加载的插件
        self.loaded_plugins = {}  # 插件ID -> 插件实例
        self.plugin_modules = {}  # 插件ID -> 插件模块
        
        # 插件依赖项
        self.plugin_dependencies = {}  # 插件ID -> [依赖的插件ID列表]
        self.dependent_plugins = {}    # 插件ID -> [依赖于该插件的插件ID列表]
        
        # 插件加载顺序
        self.plugin_load_order = []
        
        # 线程锁，用于线程安全
        self.lock = threading.RLock()
        
        # 注册事件处理器
        self.event_system.subscribe('app.stopping', self._on_app_stopping)
    
    def initialize(self):
        """初始化插件管理器
        
        Returns:
            bool: 是否成功初始化
        """
        try:
            self.logger.info("正在初始化插件管理器")
            
            # 确保插件目录结构
            self._ensure_plugin_directories()
            
            # 扫描并注册内置插件
            self._scan_builtin_plugins()
            
            self.logger.info("插件管理器初始化成功")
            return True
        except Exception as e:
            self.logger.error(f"插件管理器初始化失败: {str(e)}", exc_info=True)
            return False
    
    def _ensure_plugin_directories(self):
        """确保插件相关目录结构存在"""
        # 插件目录
        ensure_dir(self.base_plugins_dir)
        
        # 临时目录，用于插件安装
        temp_dir = os.path.join(self.base_plugins_dir, 'temp')
        ensure_dir(temp_dir)
    
    def _scan_builtin_plugins(self):
        """扫描并注册内置插件"""
        if not os.path.exists(self.builtin_plugins_dir):
            self.logger.info("内置插件目录不存在")
            return
        
        self.logger.info(f"扫描内置插件目录: {self.builtin_plugins_dir}")
        
        # 遍历内置插件目录
        for plugin_dir in [d for d in os.listdir(self.builtin_plugins_dir) if os.path.isdir(os.path.join(self.builtin_plugins_dir, d))]:
            try:
                plugin_path = os.path.join(self.builtin_plugins_dir, plugin_dir)
                manifest_path = os.path.join(plugin_path, 'manifest.json')
                
                if not os.path.exists(manifest_path):
                    self.logger.warning(f"内置插件 {plugin_dir} 缺少manifest.json文件，跳过")
                    continue
                
                # 加载插件清单
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                
                plugin_id = manifest.get('id')
                if not plugin_id:
                    self.logger.warning(f"内置插件 {plugin_dir} 清单中缺少ID，跳过")
                    continue
                
                # 更新清单为内置插件
                manifest['builtin'] = True
                
                # 将内置插件注册到数据库
                plugin_data = {
                    'id': plugin_id,
                    'name': manifest.get('name', plugin_id),
                    'version': manifest.get('version', '0.1.0'),
                    'author': manifest.get('author', 'Unknown'),
                    'description': manifest.get('description', ''),
                    'install_date': datetime.now().isoformat(),
                    'enabled': True,
                    'metadata': manifest
                }
                
                self.repository.save_plugin(plugin_data)
                self.logger.info(f"注册内置插件: {plugin_id} - {plugin_data['name']} v{plugin_data['version']}")
                
            except Exception as e:
                self.logger.error(f"注册内置插件 {plugin_dir} 失败: {str(e)}", exc_info=True)
    
    def load_installed_plugins(self):
        """加载所有已安装的插件
        
        Returns:
            dict: 已加载的插件，插件ID -> 插件实例
        """
        with self.lock:
            try:
                self.logger.info("开始加载已安装的插件")
                
                # 获取已启用的插件列表
                enabled_plugins = self.repository.get_all_plugins(enabled_only=True)
                
                if not enabled_plugins:
                    self.logger.info("没有已启用的插件")
                    return {}
                
                # 分析插件依赖关系
                self._analyze_plugin_dependencies(enabled_plugins)
                
                # 按照依赖关系顺序加载插件
                loaded_count = 0
                for plugin_id in self.plugin_load_order:
                    try:
                        plugin_data = next((p for p in enabled_plugins if p['id'] == plugin_id), None)
                        if not plugin_data:
                            continue
                        
                        # 加载插件
                        if self.load_plugin(plugin_id):
                            loaded_count += 1
                    except Exception as e:
                        self.logger.error(f"加载插件 {plugin_id} 失败: {str(e)}", exc_info=True)
                
                self.logger.info(f"已成功加载 {loaded_count}/{len(enabled_plugins)} 个插件")
                
                # 触发插件加载完成事件
                self.event_system.publish('plugins.all_loaded', self.loaded_plugins)
                
                return self.loaded_plugins
            
            except Exception as e:
                self.logger.error(f"加载插件失败: {str(e)}", exc_info=True)
                return {}
    
    def _analyze_plugin_dependencies(self, plugins):
        """分析插件依赖关系
        
        Args:
            plugins: 插件信息列表
        """
        # 清空依赖关系
        self.plugin_dependencies.clear()
        self.dependent_plugins.clear()
        self.plugin_load_order.clear()
        
        # 构建依赖图
        for plugin_data in plugins:
            plugin_id = plugin_data['id']
            metadata = plugin_data.get('metadata', {})
            
            # 获取依赖项
            dependencies = metadata.get('dependencies', [])
            self.plugin_dependencies[plugin_id] = dependencies
            
            # 更新依赖于该插件的插件列表
            for dep_id in dependencies:
                if dep_id not in self.dependent_plugins:
                    self.dependent_plugins[dep_id] = []
                self.dependent_plugins[dep_id].append(plugin_id)
        
        # 使用拓扑排序确定加载顺序
        self._determine_load_order()
    
    def _determine_load_order(self):
        """使用拓扑排序确定插件加载顺序"""
        # 入度表（每个插件依赖的插件数量）
        in_degree = {plugin_id: len(deps) for plugin_id, deps in self.plugin_dependencies.items()}
        
        # 零入度队列（不依赖其他插件的插件）
        queue = [plugin_id for plugin_id, degree in in_degree.items() if degree == 0]
        
        # 拓扑排序
        while queue:
            current_id = queue.pop(0)
            self.plugin_load_order.append(current_id)
            
            # 减少依赖于当前插件的插件的入度
            if current_id in self.dependent_plugins:
                for dependent_id in self.dependent_plugins[current_id]:
                    in_degree[dependent_id] -= 1
                    if in_degree[dependent_id] == 0:
                        queue.append(dependent_id)
        
        # 检查循环依赖
        if len(self.plugin_load_order) < len(in_degree):
            self.logger.warning("检测到插件循环依赖，某些插件可能无法加载")
            # 将剩余的插件添加到加载顺序中
            for plugin_id in self.plugin_dependencies:
                if plugin_id not in self.plugin_load_order:
                    self.plugin_load_order.append(plugin_id)
    
    def load_plugin(self, plugin_id):
        """加载指定的插件
        
        Args:
            plugin_id: 插件ID
            
        Returns:
            bool: 是否成功加载
        """
        with self.lock:
            # 检查插件是否已加载
            if plugin_id in self.loaded_plugins:
                self.logger.debug(f"插件 {plugin_id} 已经加载")
                return True
            
            try:
                # 从数据库获取插件信息
                plugin_data = self.repository.get_plugin(plugin_id)
                if not plugin_data:
                    raise PluginLoadError(f"找不到插件 {plugin_id} 的信息", plugin_id=plugin_id)
                
                # 检查插件是否启用
                if not plugin_data.get('enabled', False):
                    self.logger.info(f"插件 {plugin_id} 已禁用，跳过加载")
                    return False
                
                metadata = plugin_data.get('metadata', {})
                
                # 检查依赖项
                dependencies = metadata.get('dependencies', [])
                for dep_id in dependencies:
                    # 检查依赖插件是否已加载
                    if dep_id not in self.loaded_plugins:
                        # 尝试加载依赖插件
                        if not self.load_plugin(dep_id):
                            raise PluginDependencyError(
                                f"无法加载依赖插件 {dep_id}", 
                                plugin_id=plugin_id,
                                dependency=dep_id
                            )
                
                # 获取插件路径
                plugin_path = self._get_plugin_path(plugin_id, metadata)
                
                if not plugin_path or not os.path.exists(plugin_path):
                    raise PluginLoadError(f"插件路径 {plugin_path} 不存在", plugin_id=plugin_id)
                
                # 添加插件目录到Python路径
                if plugin_path not in sys.path:
                    sys.path.insert(0, plugin_path)
                
                # 导入插件模块
                module_name = f"{plugin_id}_plugin"
                if module_name in sys.modules:
                    # 如果模块已存在，重新加载
                    plugin_module = importlib.reload(sys.modules[module_name])
                else:
                    # 查找主模块文件
                    main_module = metadata.get('main', 'plugin.py')
                    main_module_path = os.path.join(plugin_path, main_module)
                    
                    if not os.path.exists(main_module_path):
                        raise PluginLoadError(
                            f"插件主模块 {main_module} 不存在",
                            plugin_id=plugin_id
                        )
                    
                    # 加载主模块
                    spec = importlib.util.spec_from_file_location(module_name, main_module_path)
                    plugin_module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = plugin_module
                    spec.loader.exec_module(plugin_module)
                
                # 存储插件模块
                self.plugin_modules[plugin_id] = plugin_module
                
                # 查找并实例化插件类
                plugin_class = None
                for name, obj in inspect.getmembers(plugin_module):
                    # 查找名为Plugin的类
                    if inspect.isclass(obj) and name == "Plugin":
                        plugin_class = obj
                        break
                
                if not plugin_class:
                    raise PluginLoadError(
                        f"插件 {plugin_id} 中找不到Plugin类",
                        plugin_id=plugin_id
                    )
                
                # 创建插件实例
                plugin_instance = plugin_class(
                    self.config,
                    self.event_system,
                    self.repository,
                    plugin_id
                )
                
                # 存储插件实例
                self.loaded_plugins[plugin_id] = plugin_instance
                
                # 初始化并启动插件
                plugin_instance.initialize()
                plugin_instance.start()
                
                self.logger.info(f"插件 {plugin_id} ({plugin_data['name']} v{plugin_data['version']}) 加载成功")
                
                # 触发插件加载事件
                self.event_system.publish('plugin.loaded', {
                    'plugin_id': plugin_id,
                    'name': plugin_data['name'],
                    'version': plugin_data['version']
                })
                
                return True
                
            except Exception as e:
                if isinstance(e, PluginError):
                    self.logger.error(str(e))
                else:
                    self.logger.error(f"加载插件 {plugin_id} 失败: {str(e)}", exc_info=True)
                return False
    
    def _get_plugin_path(self, plugin_id, metadata):
        """获取插件路径
        
        Args:
            plugin_id: 插件ID
            metadata: 插件元数据
            
        Returns:
            str: 插件路径
        """
        # 检查是否为内置插件
        if metadata.get('builtin', False):
            return os.path.join(self.builtin_plugins_dir, plugin_id)
        else:
            # 用户安装的插件
            return os.path.join(self.base_plugins_dir, plugin_id)
    
    def unload_plugin(self, plugin_id):
        """卸载插件
        
        Args:
            plugin_id: 插件ID
            
        Returns:
            bool: 是否成功卸载
        """
        with self.lock:
            # 检查插件是否已加载
            if plugin_id not in self.loaded_plugins:
                self.logger.debug(f"插件 {plugin_id} 未加载，无需卸载")
                return True
            
            try:
                # 检查是否有其他插件依赖于该插件
                dependent_ids = self.dependent_plugins.get(plugin_id, [])
                dependent_ids = [pid for pid in dependent_ids if pid in self.loaded_plugins]
                
                if dependent_ids:
                    # 有其他已加载的插件依赖于此插件
                    raise PluginError(
                        f"无法卸载插件 {plugin_id}，以下插件依赖于它: {', '.join(dependent_ids)}",
                        plugin_id=plugin_id
                    )
                
                # 获取插件实例
                plugin_instance = self.loaded_plugins[plugin_id]
                
                # 停止插件
                plugin_instance.stop()
                
                # 清理插件
                plugin_instance.cleanup()
                
                # 从已加载插件中移除
                del self.loaded_plugins[plugin_id]
                
                if plugin_id in self.plugin_modules:
                    # 从模块缓存中移除
                    module_name = f"{plugin_id}_plugin"
                    if module_name in sys.modules:
                        del sys.modules[module_name]
                    del self.plugin_modules[plugin_id]
                
                self.logger.info(f"插件 {plugin_id} 已卸载")
                
                # 触发插件卸载事件
                self.event_system.publish('plugin.unloaded', {'plugin_id': plugin_id})
                
                return True
                
            except Exception as e:
                if isinstance(e, PluginError):
                    self.logger.error(str(e))
                else:
                    self.logger.error(f"卸载插件 {plugin_id} 失败: {str(e)}", exc_info=True)
                return False
    
    def install_plugin(self, plugin_path, enable=True, force=False):
        """安装插件
        
        Args:
            plugin_path: 插件文件或目录路径
            enable: 安装后是否启用插件
            force: 是否强制安装（覆盖已有版本）
            
        Returns:
            dict: 包含安装结果的字典，例如:
                {'success': True, 'plugin_id': 'plugin_id', 'name': '插件名称'}
        """
        try:
            self.logger.info(f"开始安装插件: {plugin_path}")
            
            temp_dir = os.path.join(self.base_plugins_dir, 'temp')
            
            # 判断插件路径是目录还是文件
            if os.path.isdir(plugin_path):
                # 直接使用目录
                plugin_dir = plugin_path
                is_temp = False
            else:
                # 检查文件扩展名，目前仅支持.zip
                if not plugin_path.lower().endswith('.zip'):
                    raise PluginInstallError(f"不支持的插件文件格式: {plugin_path}")
                
                # 清理临时目录
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                
                # 创建临时目录
                os.makedirs(temp_dir)
                
                # 解压插件到临时目录
                if not extract_zip(plugin_path, temp_dir):
                    raise PluginInstallError(f"解压插件文件失败: {plugin_path}")
                
                # 找出主目录（包含manifest.json的目录）
                plugin_dir = None
                for root, dirs, files in os.walk(temp_dir):
                    if 'manifest.json' in files:
                        plugin_dir = root
                        break
                
                if not plugin_dir:
                    raise PluginInstallError("无效的插件包: 找不到manifest.json文件")
                
                is_temp = True
            
            # 读取清单文件
            manifest_path = os.path.join(plugin_dir, 'manifest.json')
            if not os.path.exists(manifest_path):
                raise PluginInstallError("无效的插件: 找不到manifest.json文件")
            
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            
            # 检查必要字段
            required_fields = ['id', 'name', 'version']
            for field in required_fields:
                if field not in manifest:
                    raise PluginInstallError(f"无效的manifest.json: 缺少必要字段 '{field}'")
            
            plugin_id = manifest['id']
            plugin_name = manifest['name']
            plugin_version = manifest['version']
            
            # 检查插件是否已安装
            existing_plugin = self.repository.get_plugin(plugin_id)
            if existing_plugin and not force:
                raise PluginInstallError(
                    f"插件 {plugin_name} ({plugin_id}) 已安装，版本为 {existing_plugin['version']}",
                    plugin_id=plugin_id
                )
            
            # 目标目录
            target_dir = os.path.join(self.base_plugins_dir, plugin_id)
            
            # 如果是更新现有插件，先卸载
            if existing_plugin and plugin_id in self.loaded_plugins:
                self.logger.info(f"卸载现有插件版本: {plugin_id} v{existing_plugin['version']}")
                self.unload_plugin(plugin_id)
            
            # 如果目标目录已存在，先删除
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
            
            # 移动插件文件到目标目录
            shutil.copytree(plugin_dir, target_dir)
            
            # 如果使用临时目录，清理
            if is_temp:
                shutil.rmtree(temp_dir)
            
            # 保存插件信息到数据库
            plugin_data = {
                'id': plugin_id,
                'name': plugin_name,
                'version': plugin_version,
                'author': manifest.get('author', 'Unknown'),
                'description': manifest.get('description', ''),
                'install_date': datetime.now().isoformat(),
                'enabled': enable,
                'metadata': manifest
            }
            
            self.repository.save_plugin(plugin_data)
            
            self.logger.info(f"插件 {plugin_name} v{plugin_version} ({plugin_id}) 安装成功")
            
            # 触发插件安装事件
            self.event_system.publish('plugin.installed', {
                'plugin_id': plugin_id,
                'name': plugin_name,
                'version': plugin_version,
                'enabled': enable
            })
            
            # 如果需要启用，加载插件
            if enable:
                self.load_plugin(plugin_id)
            
            return {
                'success': True,
                'plugin_id': plugin_id,
                'name': plugin_name,
                'version': plugin_version
            }
            
        except Exception as e:
            error_msg = str(e)
            if isinstance(e, PluginError):
                self.logger.error(error_msg)
            else:
                self.logger.error(f"安装插件失败: {error_msg}", exc_info=True)
            
            # 清理临时目录
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            
            return {
                'success': False,
                'error': error_msg
            }
    
    def uninstall_plugin(self, plugin_id, remove_data=False):
        """卸载插件
        
        Args:
            plugin_id: 插件ID
            remove_data: 是否同时删除插件数据
            
        Returns:
            bool: 是否成功卸载
        """
        try:
            self.logger.info(f"开始卸载插件: {plugin_id}")
            
            # 检查插件是否存在
            plugin_data = self.repository.get_plugin(plugin_id)
            if not plugin_data:
                self.logger.warning(f"找不到插件 {plugin_id}，无法卸载")
                return False
            
            # 获取插件名称
            plugin_name = plugin_data['name']
            
            # 如果插件已加载，先卸载
            if plugin_id in self.loaded_plugins:
                if not self.unload_plugin(plugin_id):
                    raise PluginError(f"无法卸载插件 {plugin_id}，请先解决依赖问题")
            
            # 删除插件文件
            plugin_path = self._get_plugin_path(plugin_id, plugin_data.get('metadata', {}))
            if os.path.exists(plugin_path) and not plugin_data.get('metadata', {}).get('builtin', False):
                # 只删除非内置插件的文件
                shutil.rmtree(plugin_path)
            
            # 从数据库中删除插件信息
            self.repository.delete_plugin(plugin_id)
            
            # 如果需要，删除插件数据
            if remove_data:
                self._remove_plugin_data(plugin_id)
            
            self.logger.info(f"插件 {plugin_name} ({plugin_id}) 卸载完成")
            
            # 触发插件卸载事件
            self.event_system.publish('plugin.uninstalled', {
                'plugin_id': plugin_id,
                'name': plugin_name,
                'remove_data': remove_data
            })
            
            return True
            
        except Exception as e:
            if isinstance(e, PluginError):
                self.logger.error(str(e))
            else:
                self.logger.error(f"卸载插件 {plugin_id} 失败: {str(e)}", exc_info=True)
            return False
    
    def _remove_plugin_data(self, plugin_id):
        """删除插件数据
        
        Args:
            plugin_id: 插件ID
        """
        # 删除插件配置
        self.repository.delete_plugin_config(plugin_id, None)
        
        # 删除插件数据文件夹
        plugin_data_dir = os.path.join(self.repository.data_dir, 'plugins', plugin_id)
        if os.path.exists(plugin_data_dir):
            shutil.rmtree(plugin_data_dir)
            self.logger.debug(f"已删除插件 {plugin_id} 的数据目录")
    
    def enable_plugin(self, plugin_id):
        """启用插件
        
        Args:
            plugin_id: 插件ID
            
        Returns:
            bool: 是否成功启用
        """
        try:
            self.logger.info(f"启用插件: {plugin_id}")
            
            # 检查插件是否存在
            plugin_data = self.repository.get_plugin(plugin_id)
            if not plugin_data:
                self.logger.warning(f"找不到插件 {plugin_id}，无法启用")
                return False
            
            # 如果已经启用，直接返回成功
            if plugin_data.get('enabled', False) and plugin_id in self.loaded_plugins:
                self.logger.debug(f"插件 {plugin_id} 已经启用")
                return True
            
            # 更新启用状态
            self.repository.set_plugin_enabled(plugin_id, True)
            
            # 加载插件
            success = self.load_plugin(plugin_id)
            
            if success:
                # 触发插件启用事件
                self.event_system.publish('plugin.enabled', {
                    'plugin_id': plugin_id,
                    'name': plugin_data['name']
                })
                
                self.logger.info(f"插件 {plugin_id} ({plugin_data['name']}) 启用成功")
            else:
                # 如果加载失败，更新状态为禁用
                self.repository.set_plugin_enabled(plugin_id, False)
                self.logger.error(f"插件 {plugin_id} 启用失败，已设置为禁用状态")
            
            return success
            
        except Exception as e:
            if isinstance(e, PluginError):
                self.logger.error(str(e))
            else:
                self.logger.error(f"启用插件 {plugin_id} 失败: {str(e)}", exc_info=True)
            return False
    
    def disable_plugin(self, plugin_id):
        """禁用插件
        
        Args:
            plugin_id: 插件ID
            
        Returns:
            bool: 是否成功禁用
        """
        try:
            self.logger.info(f"禁用插件: {plugin_id}")
            
            # 检查插件是否存在
            plugin_data = self.repository.get_plugin(plugin_id)
            if not plugin_data:
                self.logger.warning(f"找不到插件 {plugin_id}，无法禁用")
                return False
            
            # 如果已经禁用，直接返回成功
            if not plugin_data.get('enabled', True) and plugin_id not in self.loaded_plugins:
                self.logger.debug(f"插件 {plugin_id} 已经禁用")
                return True
            
            # 检查是否有其他插件依赖于该插件
            dependent_ids = self.dependent_plugins.get(plugin_id, [])
            dependent_ids = [pid for pid in dependent_ids if pid in self.loaded_plugins]
            
            if dependent_ids:
                # 有其他已加载的插件依赖于此插件
                raise PluginError(
                    f"无法禁用插件 {plugin_id}，以下插件依赖于它: {', '.join(dependent_ids)}",
                    plugin_id=plugin_id
                )
            
            # 卸载插件
            if plugin_id in self.loaded_plugins:
                if not self.unload_plugin(plugin_id):
                    raise PluginError(f"无法卸载插件 {plugin_id}，禁用失败")
            
            # 更新禁用状态
            self.repository.set_plugin_enabled(plugin_id, False)
            
            # 触发插件禁用事件
            self.event_system.publish('plugin.disabled', {
                'plugin_id': plugin_id,
                'name': plugin_data['name']
            })
            
            self.logger.info(f"插件 {plugin_id} ({plugin_data['name']}) 禁用成功")
            return True
            
        except Exception as e:
            if isinstance(e, PluginError):
                self.logger.error(str(e))
            else:
                self.logger.error(f"禁用插件 {plugin_id} 失败: {str(e)}", exc_info=True)
            return False
    
    def get_plugin_info(self, plugin_id):
        """获取插件信息
        
        Args:
            plugin_id: 插件ID
            
        Returns:
            dict: 插件信息，如果插件不存在则返回None
        """
        try:
            # 从数据库获取基本信息
            plugin_data = self.repository.get_plugin(plugin_id)
            if not plugin_data:
                return None
            
            # 补充运行时信息
            plugin_data['is_loaded'] = plugin_id in self.loaded_plugins
            
            if plugin_id in self.loaded_plugins:
                plugin_instance = self.loaded_plugins[plugin_id]
                plugin_data['status'] = plugin_instance.get_status()
                plugin_data['runtime_info'] = plugin_instance.get_info()
            else:
                plugin_data['status'] = 'stopped'
                plugin_data['runtime_info'] = {}
            
            # 获取插件配置
            plugin_data['config'] = self.repository.get_all_plugin_configs(plugin_id)
            
            return plugin_data
            
        except Exception as e:
            self.logger.error(f"获取插件 {plugin_id} 信息失败: {str(e)}", exc_info=True)
            return None
    
    def get_all_plugins_info(self):
        """获取所有插件的信息
        
        Returns:
            list: 插件信息列表
        """
        try:
            # 从数据库获取所有插件
            plugins = self.repository.get_all_plugins()
            
            # 补充运行时信息
            for plugin_data in plugins:
                plugin_id = plugin_data['id']
                plugin_data['is_loaded'] = plugin_id in self.loaded_plugins
                
                if plugin_id in self.loaded_plugins:
                    plugin_instance = self.loaded_plugins[plugin_id]
                    plugin_data['status'] = plugin_instance.get_status()
                    plugin_data['runtime_info'] = plugin_instance.get_info()
                else:
                    plugin_data['status'] = 'stopped'
                    plugin_data['runtime_info'] = {}
            
            return plugins
            
        except Exception as e:
            self.logger.error(f"获取所有插件信息失败: {str(e)}", exc_info=True)
            return []
    
    def stop_all_plugins(self):
        """停止所有插件
        
        Returns:
            bool: 是否所有插件都成功停止
        """
        self.logger.info("正在停止所有插件...")
        
        # 按照加载顺序的反序停止插件
        success = True
        reverse_order = list(reversed(self.plugin_load_order))
        
        for plugin_id in reverse_order:
            if plugin_id in self.loaded_plugins:
                try:
                    plugin_instance = self.loaded_plugins[plugin_id]
                    plugin_instance.stop()
                    self.logger.info(f"插件 {plugin_id} 已停止")
                except Exception as e:
                    self.logger.error(f"停止插件 {plugin_id} 失败: {str(e)}", exc_info=True)
                    success = False
        
        if success:
            self.logger.info("所有插件已停止")
        else:
            self.logger.warning("部分插件停止失败")
        
        return success
    
    def _on_app_stopping(self, _):
        """应用停止事件处理器"""
        self.logger.info("应用正在停止，停止所有插件")
        self.stop_all_plugins()
    
    def cleanup(self):
        """清理插件管理器"""
        # 停止所有插件
        self.stop_all_plugins()
        
        # 清理资源
        self.loaded_plugins.clear()
        self.plugin_modules.clear()
        self.plugin_dependencies.clear()
        self.dependent_plugins.clear()
        self.plugin_load_order.clear()
        
        self.logger.info("插件管理器已清理")

    def update_plugin(self, plugin_id, plugin_path=None, auto_restart=True):
        """更新插件
        
        支持在不重启应用程序的情况下更新插件
        
        Args:
            plugin_id: 要更新的插件ID
            plugin_path: 新版本插件的路径，如果为None则需要从服务器下载
            auto_restart: 是否自动重启插件
            
        Returns:
            dict: 包含更新结果的字典
        """
        try:
            self.logger.info(f"开始更新插件: {plugin_id}")
            
            # 检查插件是否存在
            plugin_data = self.repository.get_plugin(plugin_id)
            if not plugin_data:
                raise PluginError(f"插件 {plugin_id} 不存在，无法更新")
            
            # 获取当前版本
            current_version = plugin_data.get('version', '0.0.0')
            plugin_name = plugin_data.get('name', plugin_id)
            
            # 记录当前插件状态
            was_enabled = plugin_data.get('enabled', False)
            was_loaded = plugin_id in self.loaded_plugins
            
            # 如果插件是内置的且没有提供新路径，则无法更新
            if plugin_data.get('metadata', {}).get('builtin', False) and not plugin_path:
                raise PluginError(f"无法更新内置插件 {plugin_name}，请提供新版本路径")
            
            # 如果未提供路径，则需要从服务器下载
            if not plugin_path:
                self.logger.info(f"未提供插件路径，将通过下载更新插件 {plugin_id}")
                # 发布下载请求事件
                download_result = {"success": False, "error": "下载未完成"}
                
                def download_callback(result):
                    nonlocal download_result
                    download_result = result
                
                self.event_system.publish('plugin.download_request', {
                    'plugin_id': plugin_id,
                    'callback': download_callback,
                    'update': True
                })
                
                # 等待下载完成（实际应用中可能需要异步处理）
                # 简单起见，这里使用一个循环等待
                timeout = 60  # 最多等待60秒
                start_time = time.time()
                
                while not download_result.get('success') and time.time() - start_time < timeout:
                    time.sleep(0.5)
                
                if not download_result.get('success'):
                    error = download_result.get('error', '未知错误')
                    raise PluginError(f"下载插件 {plugin_id} 更新失败: {error}")
                
                # 下载成功，获取下载的插件路径
                plugin_path = download_result.get('path')
                if not plugin_path or not os.path.exists(plugin_path):
                    raise PluginError(f"下载的插件路径无效: {plugin_path}")
            
            # 先卸载当前插件（如果已加载）
            if was_loaded:
                self.logger.info(f"卸载当前版本插件: {plugin_id} v{current_version}")
                if not self.unload_plugin(plugin_id):
                    raise PluginError(f"无法卸载当前版本插件 {plugin_id}，更新失败")
            
            # 安装新版本插件
            install_result = self.install_plugin(plugin_path, enable=False, force=True)
            if not install_result.get('success'):
                error = install_result.get('error', '未知错误')
                raise PluginError(f"安装新版本插件失败: {error}")
            
            new_version = install_result.get('version', 'unknown')
            
            # 恢复插件状态
            if was_enabled or auto_restart:
                self.logger.info(f"启用更新后的插件: {plugin_id} v{new_version}")
                self.enable_plugin(plugin_id)
            
            self.logger.info(f"插件 {plugin_name} 已成功从 v{current_version} 更新到 v{new_version}")
            
            # 触发插件更新事件
            self.event_system.publish('plugin.updated', {
                'plugin_id': plugin_id,
                'name': plugin_name,
                'old_version': current_version,
                'new_version': new_version
            })
            
            return {
                'success': True,
                'plugin_id': plugin_id,
                'name': plugin_name,
                'old_version': current_version,
                'new_version': new_version
            }
            
        except Exception as e:
            error_msg = str(e)
            if isinstance(e, PluginError):
                self.logger.error(error_msg)
            else:
                self.logger.error(f"更新插件 {plugin_id} 失败: {error_msg}", exc_info=True)
            
            return {
                'success': False,
                'plugin_id': plugin_id,
                'error': error_msg
            } 