#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
插件基类模块 - EdgePlugHub应用

此模块继承自edgeplughub-sdk中的插件基类，并拓展针对EdgePlugHub应用的特定功能
使用此类为中间层，避免直接依赖SDK的变化影响应用代码
"""

import os
import logging
import threading
from typing import Dict, Any, Optional, List, Callable, Union

# 导入SDK中的基类和数据类型
try:
    from edgeplughub_sdk.sdk.plugin_base import PluginBase as SDKPluginBase
    from edgeplughub_sdk.sdk.plugin_base import PluginInput, PluginOutput, DataType
except ImportError:
    # 如果没有安装SDK，使用相对路径导入
    # 这样可以在开发环境中工作，但生产环境应该安装SDK
    import sys
    import os.path
    sdk_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../edgeplughub-sdk'))
    if sdk_path not in sys.path:
        sys.path.append(sdk_path)
    from sdk.plugin_base import PluginBase as SDKPluginBase
    from sdk.plugin_base import PluginInput, PluginOutput, DataType

from ..core.exceptions import PluginError

logger = logging.getLogger('plugins.base')

class PluginBase(SDKPluginBase):
    """EdgePlugHub应用插件基类
    
    继承自SDK中的插件基类，并添加了应用特定的功能
    所有EdgePlugHub应用插件都应该继承此类
    """
    
    def __init__(self, config, event_system, repository, plugin_id):
        """初始化插件基类
        
        Args:
            config: 配置管理器实例
            event_system: 事件系统实例
            repository: 数据仓库实例
            plugin_id: 插件ID
        """
        super().__init__()
        
        # 应用系统组件
        self.config = config
        self.event_system = event_system
        self.repository = repository
        
        # 设置插件ID
        self.plugin_id = plugin_id
        
        # 插件状态
        self._status = "initialized"  # initialized, running, paused, stopped, error
        self._error = None
        
        # 线程锁，保证线程安全
        self._lock = threading.RLock()
        
        # 插件设置
        self._settings = {}
        self._load_settings()
        
        # 可以被其他插件调用的接口
        self.api = {}
        
        # 加载插件元数据
        self._load_metadata()
        
        logger.debug(f"插件 {plugin_id} 基类初始化完成")
    
    def _load_metadata(self):
        """从数据库加载插件元数据"""
        try:
            plugin_data = self.repository.get_plugin(self.plugin_id)
            if plugin_data and 'metadata' in plugin_data:
                metadata = plugin_data['metadata']
                # 使用元数据更新插件属性
                self.name = metadata.get('name', self.plugin_id)
                self.version = metadata.get('version', '0.1.0')
                self.description = metadata.get('description', '')
                self.category = metadata.get('category', '')
                self.author = metadata.get('author', 'Unknown')
                self.dependencies = metadata.get('dependencies', [])
                
                # 支持的数据类型
                input_types = metadata.get('supported_input_types', [])
                output_types = metadata.get('supported_output_types', [])
                
                # 转换为DataType枚举
                self.supported_input_types = [DataType(t) for t in input_types if t in [dt.value for dt in DataType]]
                self.supported_output_types = [DataType(t) for t in output_types if t in [dt.value for dt in DataType]]
                
                logger.debug(f"已加载插件 {self.plugin_id} 的元数据")
            else:
                logger.warning(f"插件 {self.plugin_id} 没有元数据")
        except Exception as e:
            logger.error(f"加载插件 {self.plugin_id} 元数据失败: {str(e)}")
    
    def _load_settings(self):
        """从仓库加载插件设置"""
        try:
            settings = self.repository.get_all_plugin_configs(self.plugin_id)
            if settings:
                self._settings = settings
                logger.debug(f"已加载插件 {self.plugin_id} 的设置")
            else:
                logger.debug(f"插件 {self.plugin_id} 没有保存的设置")
        except Exception as e:
            logger.error(f"加载插件 {self.plugin_id} 设置失败: {str(e)}")
    
    def _save_settings(self):
        """保存插件设置到仓库"""
        try:
            for key, value in self._settings.items():
                self.repository.save_plugin_config(self.plugin_id, key, value)
            logger.debug(f"已保存插件 {self.plugin_id} 的设置")
        except Exception as e:
            logger.error(f"保存插件 {self.plugin_id} 设置失败: {str(e)}")
    
    def get_setting(self, key, default=None):
        """获取插件设置
        
        Args:
            key: 设置键名
            default: 默认值
            
        Returns:
            设置值或默认值
        """
        return self._settings.get(key, default)
    
    def set_setting(self, key, value):
        """设置插件配置
        
        Args:
            key: 设置键名
            value: 设置值
            
        Returns:
            bool: 是否设置成功
        """
        try:
            self._settings[key] = value
            self.repository.save_plugin_config(self.plugin_id, key, value)
            return True
        except Exception as e:
            logger.error(f"保存插件 {self.plugin_id} 设置 {key} 失败: {str(e)}")
            return False
    
    # SDK方法的实现
    def initialize(self):
        """初始化插件
        
        在子类中应该重写此方法以执行具体的初始化操作
        
        Returns:
            bool: 是否初始化成功
        """
        return True
    
    def process(self, input_data: PluginInput) -> PluginOutput:
        """处理输入数据
        
        在子类中必须实现此方法
        
        Args:
            input_data: 插件输入数据
            
        Returns:
            插件输出数据
        """
        raise NotImplementedError("插件必须实现process方法")
    
    # EdgePlugHub应用特定的方法
    def start(self):
        """启动插件
        
        启动插件的运行，如启动线程、注册事件处理器等
        在子类中应该重写此方法
        
        Returns:
            bool: 是否启动成功
        """
        with self._lock:
            self._status = "running"
            logger.info(f"插件 {self.plugin_id} 已启动")
            return True
    
    def stop(self):
        """停止插件
        
        停止插件的运行，如停止线程、注销事件处理器等
        在子类中应该重写此方法
        
        Returns:
            bool: 是否停止成功
        """
        with self._lock:
            self._status = "stopped"
            logger.info(f"插件 {self.plugin_id} 已停止")
            return True
    
    def cleanup(self):
        """清理插件资源
        
        释放插件占用的资源，如关闭文件、释放内存等
        在子类中应该重写此方法
        
        Returns:
            bool: 是否清理成功
        """
        with self._lock:
            logger.info(f"插件 {self.plugin_id} 资源已清理")
            return True
    
    def pause(self):
        """暂停插件
        
        暂停插件的运行，但不释放资源
        可选实现
        
        Returns:
            bool: 是否暂停成功
        """
        with self._lock:
            if self._status == "running":
                self._status = "paused"
                logger.info(f"插件 {self.plugin_id} 已暂停")
                return True
            return False
    
    def resume(self):
        """恢复插件
        
        恢复暂停的插件
        可选实现
        
        Returns:
            bool: 是否恢复成功
        """
        with self._lock:
            if self._status == "paused":
                self._status = "running"
                logger.info(f"插件 {self.plugin_id} 已恢复")
                return True
            return False
    
    def get_status(self):
        """获取插件状态
        
        Returns:
            str: 插件状态
        """
        with self._lock:
            return self._status
    
    def set_status(self, status, error=None):
        """设置插件状态
        
        Args:
            status: 状态字符串
            error: 错误信息(可选)
            
        Returns:
            bool: 是否设置成功
        """
        with self._lock:
            self._status = status
            if error:
                self._error = error
            return True
    
    def get_error(self):
        """获取插件错误信息
        
        Returns:
            str: 错误信息
        """
        with self._lock:
            return self._error
    
    def get_info(self):
        """获取插件信息
        
        返回插件的运行时信息，如版本、状态等
        
        Returns:
            dict: 插件信息
        """
        with self._lock:
            info = self.get_manifest()
            info.update({
                "status": self._status,
                "error": self._error
            })
            return info
    
    def register_event_handlers(self):
        """注册事件处理器
        
        子类应该重写此方法以注册自定义事件处理器
        """
        pass
    
    def unregister_event_handlers(self):
        """注销事件处理器
        
        子类应该重写此方法以注销自定义事件处理器
        """
        pass
    
    def register_api(self, api_name, func):
        """注册API接口
        
        注册一个可供其他插件调用的API接口
        
        Args:
            api_name: API名称
            func: API函数
            
        Returns:
            bool: 是否注册成功
        """
        try:
            self.api[api_name] = func
            logger.debug(f"插件 {self.plugin_id} 注册API: {api_name}")
            return True
        except Exception as e:
            logger.error(f"注册API {api_name} 失败: {str(e)}")
            return False
    
    def unregister_api(self, api_name):
        """注销API接口
        
        Args:
            api_name: API名称
            
        Returns:
            bool: 是否注销成功
        """
        try:
            if api_name in self.api:
                del self.api[api_name]
                logger.debug(f"插件 {self.plugin_id} 注销API: {api_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"注销API {api_name} 失败: {str(e)}")
            return False
    
    def has_api(self, api_name):
        """检查API是否存在
        
        Args:
            api_name: API名称
            
        Returns:
            bool: API是否存在
        """
        return api_name in self.api
    
    def call_api(self, plugin_id, api_name, *args, **kwargs):
        """调用其他插件的API
        
        Args:
            plugin_id: 目标插件ID
            api_name: API名称
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            API调用结果
        """
        try:
            # 通过插件管理器获取目标插件
            target_plugin = None
            for plugin in self.repository.get_all_plugins():
                if plugin['id'] == plugin_id:
                    target_plugin = plugin
                    break
                    
            if not target_plugin:
                raise PluginError(f"插件 {plugin_id} 不存在")
            
            # 获取插件实例
            # 这里需要通过插件管理器获取已加载的插件实例
            # 由于我们没有直接访问插件管理器的引用，可以通过事件系统请求
            response = {}
            
            def callback(result):
                nonlocal response
                response = result
            
            self.event_system.publish('plugin.call_api', {
                'caller_id': self.plugin_id,
                'target_id': plugin_id,
                'api_name': api_name,
                'args': args,
                'kwargs': kwargs,
                'callback': callback
            })
            
            if not response:
                raise PluginError(f"调用插件 {plugin_id} 的API {api_name} 失败")
                
            return response.get('result')
            
        except Exception as e:
            logger.error(f"调用插件 {plugin_id} 的API {api_name} 失败: {str(e)}")
            raise
    
    def __str__(self):
        """字符串表示
        
        Returns:
            str: 插件的字符串表示
        """
        return f"插件[{self.plugin_id}]: {self.name} v{self.version} ({self.get_status()})" 