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
        self.app_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 创建核心应用
        self.core = AppCore("EdgePlugHub", self.app_dir)
        
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
        
        # 添加命令行参数
        parser.add_argument("--version", action="store_true", help="显示版本信息并退出")
        parser.add_argument("--gui", action="store_true", help="启动图形用户界面")
        parser.add_argument("--list-plugins", action="store_true", help="列出可用的插件")
        parser.add_argument("--download-plugin", metavar="PLUGIN_ID", help="下载并安装插件")
        parser.add_argument("--update-plugin", metavar="PLUGIN_ID", help="更新插件")
        parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="设置日志级别")
        
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
                return False
            
            # 处理插件列表
            if self.args.list_plugins:
                self._list_plugins()
                return False
            
            # 处理插件下载
            if self.args.download_plugin:
                self._download_plugin(self.args.download_plugin)
                return False
            
            # 处理插件更新
            if self.args.update_plugin:
                self._update_plugin(self.args.update_plugin)
                return False
            
            # 标记为运行中
            self.logger.info("EdgePlugHub应用程序已启动")
            
            # 启动GUI或CLI模式
            if self.args.gui:
                self._start_gui()
            else:
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
        # 这将在后续阶段实现
        print("插件列表功能尚未实现")
    
    def _download_plugin(self, plugin_id):
        """下载并安装插件
        
        Args:
            plugin_id: 插件ID
        """
        # 这将在后续阶段实现
        print(f"下载插件功能尚未实现: {plugin_id}")
    
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