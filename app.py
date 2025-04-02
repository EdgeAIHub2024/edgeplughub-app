#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
EdgePlugHub 应用程序

一个插件管理平台，支持多种不同类型插件的管理、运行和更新
"""

import os
import sys
import time
import argparse
import threading
import logging
from typing import Dict, Any, Optional, List

# 导入核心模块
from core.app_core import AppCore
from core.utils import get_platform_info
from core.exceptions import EdgePlugHubException, ConfigError, PluginError

class EdgePlugHubApp:
    """EdgePlugHub应用程序主类"""
    
    def __init__(self, args=None):
        """初始化EdgePlugHub应用程序
        
        Args:
            args: 命令行参数，默认解析sys.argv
        """
        # 解析命令行参数
        self.args = self._parse_args(args)
        
        # 初始化路径
        self.app_dir = self.args.app_dir or os.path.dirname(os.path.abspath(__file__))
        
        # 初始化配置文件路径
        config_file = self.args.config_file
        if not config_file and os.path.isdir(self.app_dir):
            config_file = os.path.join(self.app_dir, "config.json")
        
        # 创建核心应用
        self.core = AppCore("EdgePlugHub", self.app_dir, config_file)
        
        # 设置日志级别
        if self.args.log_level:
            logging.getLogger().setLevel(getattr(logging, self.args.log_level))
        
        # 记录基本信息
        self.logger = self.core.logger
        self.config = self.core.config
        self.event_system = self.core.event_system
        self.thread_manager = self.core.thread_manager
        
        # 其他初始化工作
        self._init_modules()
        
        # 注册事件处理器
        self._register_event_handlers()
    
    def _parse_args(self, args=None):
        """解析命令行参数
        
        Args:
            args: 命令行参数列表，默认使用sys.argv
        
        Returns:
            解析后的参数对象
        """
        parser = argparse.ArgumentParser(description="EdgePlugHub - 插件管理平台")
        
        # 运行模式
        mode_group = parser.add_argument_group("运行模式")
        mode_group.add_argument("--version", action="store_true", help="显示版本信息并退出")
        mode_group.add_argument("--gui", action="store_true", help="启动图形用户界面")
        mode_group.add_argument("--plugin-manager", action="store_true", help="仅启动插件管理器界面")
        mode_group.add_argument("--list-plugins", action="store_true", help="列出可用的插件")
        
        # 插件操作
        plugin_group = parser.add_argument_group("插件操作")
        plugin_group.add_argument("--download-plugin", metavar="PLUGIN_ID", help="下载并安装插件")
        plugin_group.add_argument("--update-plugin", metavar="PLUGIN_ID", help="更新插件")
        plugin_group.add_argument("--remove-plugin", metavar="PLUGIN_ID", help="移除插件")
        plugin_group.add_argument("--enable-plugin", metavar="PLUGIN_ID", help="启用插件")
        plugin_group.add_argument("--disable-plugin", metavar="PLUGIN_ID", help="禁用插件")
        
        # 配置选项
        config_group = parser.add_argument_group("配置选项")
        config_group.add_argument("--log-level", default="INFO", 
                                 choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], 
                                 help="设置日志级别")
        config_group.add_argument("--app-dir", type=str, help="指定应用程序数据目录")
        config_group.add_argument("--config-file", type=str, help="指定配置文件路径")
        
        # 解析命令行参数
        return parser.parse_args(args)
    
    def _init_modules(self):
        """初始化模块"""
        # 这里将在后续阶段添加具体的初始化代码
        # 包括插件管理器、数据仓库等组件的创建
        pass
    
    def _register_event_handlers(self):
        """注册事件处理器"""
        # 注册基本事件处理
        self.event_system.subscribe("plugin.download_request", self._on_plugin_download_request)
        self.event_system.subscribe("plugin.update_request", self._on_plugin_update_request)
    
    def _on_plugin_download_request(self, data):
        """处理插件下载请求
        
        Args:
            data: 请求数据，包含plugin_id和callback
        """
        if not isinstance(data, dict):
            return
        
        plugin_id = data.get("plugin_id")
        callback = data.get("callback")
        
        if not plugin_id or not callable(callback):
            self.logger.error("插件下载请求无效，缺少plugin_id或callback")
            return
        
        self.logger.info(f"收到插件下载请求: {plugin_id}")
        
        # 在后续实现中，将通过线程管理器安全地执行下载
        # 这里是临时的实现
        def download_task():
            result = {
                "success": False,
                "plugin_id": plugin_id,
                "error": "功能尚未实现"
            }
            
            try:
                # 调用回调函数，确保在主线程中执行
                callback(result)
            except Exception as e:
                self.logger.error(f"调用下载回调函数时出错: {str(e)}")
        
        # 创建并启动下载线程
        self.thread_manager.run_task(download_task)
    
    def _on_plugin_update_request(self, data):
        """处理插件更新请求
        
        Args:
            data: 请求数据，包含plugin_id和callback
        """
        if not isinstance(data, dict):
            return
        
        plugin_id = data.get("plugin_id")
        callback = data.get("callback")
        
        if not plugin_id or not callable(callback):
            self.logger.error("插件更新请求无效，缺少plugin_id或callback")
            return
        
        self.logger.info(f"收到插件更新请求: {plugin_id}")
        
        # 在后续实现中，将通过线程管理器安全地执行更新
        # 这里是临时的实现
        def update_task():
            result = {
                "success": False,
                "plugin_id": plugin_id,
                "error": "功能尚未实现"
            }
            
            try:
                # 调用回调函数，确保在主线程中执行
                callback(result)
            except Exception as e:
                self.logger.error(f"调用更新回调函数时出错: {str(e)}")
        
        # 创建并启动更新线程
        self.thread_manager.run_task(update_task)
    
    def start(self):
        """启动应用程序
        
        Returns:
            bool: 是否成功启动
        """
        try:
            # 启动核心服务
            if not self.core.start():
                self.logger.error("核心服务启动失败")
                return False
            
            # 处理版本显示
            if self.args.version:
                self._show_version()
                return True
            
            # 处理插件列表
            if self.args.list_plugins:
                self._list_plugins()
                return True
            
            # 处理插件操作
            if self.args.download_plugin:
                self._download_plugin(self.args.download_plugin)
                return True
            
            if self.args.update_plugin:
                self._update_plugin(self.args.update_plugin)
                return True
                
            if self.args.remove_plugin:
                self._remove_plugin(self.args.remove_plugin)
                return True
                
            if self.args.enable_plugin:
                self._enable_plugin(self.args.enable_plugin)
                return True
                
            if self.args.disable_plugin:
                self._disable_plugin(self.args.disable_plugin)
                return True
            
            # 标记为运行中
            self.logger.info("EdgePlugHub应用程序已启动")
            
            # 选择运行模式
            if self.args.plugin_manager:
                # 仅启动插件管理器
                self._start_plugin_manager()
            elif self.args.gui:
                # 启动完整GUI
                self._start_gui()
            else:
                # 默认启动CLI模式
                self._start_cli()
            
            return True
            
        except Exception as e:
            self.logger.error(f"启动应用程序失败: {str(e)}", exc_info=True)
            return False
    
    def _show_version(self):
        """显示版本信息"""
        version = self.config.get("app.version", "0.1.0")
        build_date = self.config.get("app.build_date", "未知")
        
        print(f"EdgePlugHub v{version} (构建日期: {build_date})")
        print(f"运行平台: {get_platform_info()['os_name']} {get_platform_info()['os_version']}")
        print(f"Python版本: {get_platform_info()['python_version']}")
    
    def _list_plugins(self):
        """列出可用插件"""
        try:
            self.logger.info("列出可用插件")
            
            # 确保插件管理器已初始化
            if not hasattr(self.core, 'plugin_manager') or not self.core.plugin_manager:
                self.logger.error("插件管理器未初始化")
                print("错误: 插件管理器未初始化")
                return False
            
            # 获取已安装的插件
            installed_plugins = self.core.repository.get_all_plugins()
            
            if installed_plugins:
                print("\n已安装的插件:")
                print("-" * 60)
                print(f"{'ID':<20} {'名称':<20} {'版本':<10} {'状态':<10}")
                print("-" * 60)
                
                for plugin in installed_plugins:
                    plugin_id = plugin.get('id')
                    name = plugin.get('name', plugin_id)
                    version = plugin.get('version', 'unknown')
                    enabled = "启用" if plugin.get('enabled', False) else "禁用"
                    
                    print(f"{plugin_id:<20} {name:<20} {version:<10} {enabled:<10}")
            else:
                print("\n没有安装任何插件")
            
            # 尝试获取可用的插件列表
            try:
                from plugins.downloader import PluginDownloader
                downloader = PluginDownloader(self.core.config, self.core.repository)
                
                # 获取可用插件列表
                available_plugins = downloader.get_available_plugins()
                
                if available_plugins.get('success', False) and available_plugins.get('plugins', []):
                    print("\n可用于下载的插件:")
                    print("-" * 60)
                    print(f"{'ID':<20} {'名称':<20} {'版本':<10} {'类别':<10}")
                    print("-" * 60)
                    
                    for plugin in available_plugins.get('plugins', []):
                        plugin_id = plugin.get('id')
                        name = plugin.get('name', plugin_id)
                        version = plugin.get('version', 'unknown')
                        category = plugin.get('category', 'unknown')
                        
                        # 检查是否已安装
                        installed = any(p.get('id') == plugin_id for p in installed_plugins)
                        if not installed:
                            print(f"{plugin_id:<20} {name:<20} {version:<10} {category:<10}")
                else:
                    print("\n无法获取可用插件列表")
                    if not available_plugins.get('success', False):
                        print(f"错误: {available_plugins.get('error', '未知错误')}")
                
            except ImportError as e:
                self.logger.error(f"无法导入下载器模块: {str(e)}")
                print("\n无法获取可下载的插件列表")
            
            return True
            
        except Exception as e:
            self.logger.error(f"列出插件时出错: {str(e)}", exc_info=True)
            print(f"错误: {str(e)}")
            return False
    
    def _download_plugin(self, plugin_id):
        """下载并安装插件
        
        Args:
            plugin_id: 插件ID
            
        Returns:
            bool: 是否成功下载安装
        """
        self.logger.info(f"开始下载插件: {plugin_id}")
        
        try:
            # 确保插件管理器已初始化
            if not hasattr(self.core, 'plugin_manager') or not self.core.plugin_manager:
                self.logger.error("插件管理器未初始化")
                return False
            
            # 获取插件下载器
            try:
                from plugins.downloader import PluginDownloader
                downloader = PluginDownloader(self.core.config, self.core.repository)
            except ImportError as e:
                self.logger.error(f"无法导入下载器模块: {str(e)}")
                return False
            
            # 执行下载和安装
            result = downloader.download_and_install(plugin_id, self.core.plugin_manager)
            
            if result.get('success', False):
                plugin_path = result.get('file_path', '')
                plugin_version = result.get('version', 'unknown')
                plugin_name = result.get('name', plugin_id)
                
                self.logger.info(f"插件 {plugin_name} v{plugin_version} 下载并安装成功")
                return True
            else:
                error = result.get('error', '未知错误')
                self.logger.error(f"下载插件失败: {error}")
                return False
                
        except Exception as e:
            self.logger.error(f"下载插件 {plugin_id} 时出错: {str(e)}", exc_info=True)
            return False
    
    def _update_plugin(self, plugin_id):
        """更新插件
        
        Args:
            plugin_id: 插件ID
        """
        # 这将在后续阶段实现
        print(f"更新插件功能尚未实现: {plugin_id}")
    
    def _start_gui(self):
        """启动图形用户界面"""
        try:
            self.logger.info("正在启动图形用户界面...")
            
            # 导入UI模块
            from ui.plugin_manager_ui import launch_plugin_manager_ui
            
            # 发布应用程序启动事件
            self.event_system.publish("app.started", {
                "timestamp": time.time(),
                "mode": "gui"
            })
            
            # 启动UI
            exit_code = launch_plugin_manager_ui(self)
            
            # UI关闭后退出
            sys.exit(exit_code)
            
        except ImportError as e:
            self.logger.error(f"无法导入UI模块: {str(e)}", exc_info=True)
            print("错误: 无法导入UI模块，请确保已安装PyQt5")
            print("可以使用命令: pip install PyQt5")
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"启动图形界面失败: {str(e)}", exc_info=True)
            self.core.stop()
    
    def _start_cli(self):
        """启动命令行模式"""
        self.logger.info("启动命令行模式...")
        
        # 发布应用程序启动事件
        self.event_system.publish("app.started", {
            "timestamp": time.time(),
            "mode": "cli"
        })
        
        try:
            # 等待退出事件
            while self.core.running and not self.core.exit_event.is_set():
                # 处理定时任务或命令
                
                # 休眠一段时间，避免CPU占用过高
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            self.logger.info("接收到键盘中断")
        except Exception as e:
            self.logger.error(f"主循环异常: {str(e)}", exc_info=True)
        finally:
            self.stop()
    
    def stop(self):
        """停止应用程序"""
        # 停止核心
        self.core.stop()
    
    def restart(self):
        """重启应用程序"""
        self.stop()
        time.sleep(1)  # 等待资源释放
        return self.start()
    
    def _start_plugin_manager(self):
        """启动插件管理器GUI"""
        self.logger.info("正在启动插件管理器界面...")
        
        try:
            # 导入UI模块
            from ui.plugin_manager_ui import launch_plugin_manager_ui
            from PyQt5.QtWidgets import QApplication
            
            # 创建Qt应用程序
            qt_app = QApplication(sys.argv)
            qt_app.setStyle("Fusion")
            
            # 启动插件管理器UI
            ui = launch_plugin_manager_ui(self.core)
            
            # 启动Qt事件循环
            sys.exit(qt_app.exec_())
            
        except ImportError as e:
            self.logger.error(f"无法导入UI模块: {str(e)}", exc_info=True)
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"启动插件管理器界面失败: {str(e)}", exc_info=True)
            sys.exit(1)
            
    def _remove_plugin(self, plugin_id):
        """移除插件
        
        Args:
            plugin_id: 插件ID
        """
        self.logger.info(f"正在移除插件: {plugin_id}")
        
        try:
            # 确保插件管理器已初始化
            if not hasattr(self.core, 'plugin_manager') or not self.core.plugin_manager:
                self.logger.error("插件管理器未初始化")
                return False
                
            # 执行卸载
            result = self.core.plugin_manager.uninstall_plugin(plugin_id)
            
            if result:
                self.logger.info(f"插件 {plugin_id} 已成功移除")
            else:
                self.logger.error(f"移除插件 {plugin_id} 失败")
                
            return result
                
        except Exception as e:
            self.logger.error(f"移除插件 {plugin_id} 时出错: {str(e)}", exc_info=True)
            return False
            
    def _enable_plugin(self, plugin_id):
        """启用插件
        
        Args:
            plugin_id: 插件ID
        """
        self.logger.info(f"正在启用插件: {plugin_id}")
        
        try:
            # 确保插件管理器已初始化
            if not hasattr(self.core, 'plugin_manager') or not self.core.plugin_manager:
                self.logger.error("插件管理器未初始化")
                return False
                
            # 执行启用
            result = self.core.plugin_manager.enable_plugin(plugin_id)
            
            if result:
                self.logger.info(f"插件 {plugin_id} 已成功启用")
            else:
                self.logger.error(f"启用插件 {plugin_id} 失败")
                
            return result
                
        except Exception as e:
            self.logger.error(f"启用插件 {plugin_id} 时出错: {str(e)}", exc_info=True)
            return False
            
    def _disable_plugin(self, plugin_id):
        """禁用插件
        
        Args:
            plugin_id: 插件ID
        """
        self.logger.info(f"正在禁用插件: {plugin_id}")
        
        try:
            # 确保插件管理器已初始化
            if not hasattr(self.core, 'plugin_manager') or not self.core.plugin_manager:
                self.logger.error("插件管理器未初始化")
                return False
                
            # 执行禁用
            result = self.core.plugin_manager.disable_plugin(plugin_id)
            
            if result:
                self.logger.info(f"插件 {plugin_id} 已成功禁用")
            else:
                self.logger.error(f"禁用插件 {plugin_id} 失败")
                
            return result
                
        except Exception as e:
            self.logger.error(f"禁用插件 {plugin_id} 时出错: {str(e)}", exc_info=True)
            return False

# 用于直接运行的入口点
def main():
    app = EdgePlugHubApp()
    try:
        app.start()
    except Exception as e:
        logging.error(f"应用程序运行时出错: {str(e)}", exc_info=True)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main()) 