#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
应用程序核心类

提供应用程序的基本功能和服务，包括配置管理、事件系统和线程管理
"""

import os
import logging
import threading
import time
from typing import Dict, Any, Optional

from .config import ConfigManager
from .events import EventSystem
from .logging_manager import LoggingManager
from .threading import ThreadManager
from .exceptions import ConfigError

class AppCore:
    """应用程序核心类
    
    提供应用程序基础服务的集成点
    """
    
    def __init__(self, app_name: str, app_dir: str, config_file: str = None):
        """初始化应用程序核心
        
        Args:
            app_name: 应用程序名称
            app_dir: 应用程序目录
            config_file: 配置文件路径，默认为app_dir/config.json
        """
        self.app_name = app_name
        self.app_dir = app_dir
        
        # 创建必要的目录
        self.data_dir = os.path.join(app_dir, "data")
        self.logs_dir = os.path.join(app_dir, "logs")
        self.plugins_dir = os.path.join(app_dir, "plugins_data")
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.plugins_dir, exist_ok=True)
        
        # 配置日志
        self.logging_manager = LoggingManager(
            log_dir=self.logs_dir
        )
        self.logger = logging.getLogger(app_name)
        
        # 初始化配置
        config_file = config_file or os.path.join(app_dir, "config.json")
        self.config = ConfigManager(config_file)
        self.config.set_defaults({
            "app.name": app_name,
            "app.version": "0.1.0",
            "app.data_dir": self.data_dir,
            "app.logs_dir": self.logs_dir,
            "app.plugins_dir": self.plugins_dir,
            "plugins_directory": self.plugins_dir,
            "threading.max_threads": 4
        })
        
        # 初始化事件系统
        self.event_system = EventSystem()
        
        # 初始化线程管理器
        max_threads = self.config.get("threading.max_threads", 4)
        self.thread_manager = ThreadManager(max_threads)
        
        # 数据仓库和插件管理器会在启动过程中初始化
        self.repository = None
        self.plugin_manager = None
        
        # 应用程序状态
        self.running = False
        self.exit_event = threading.Event()
        
        self.logger.info(f"{app_name} 核心服务初始化完成")
    
    def start(self) -> bool:
        """启动应用程序核心服务
        
        Returns:
            bool: 是否成功启动
        """
        try:
            self.logger.info(f"正在启动 {self.app_name} 核心服务")
            
            # 加载配置
            if not self.config.load():
                self.logger.warning("无法加载配置文件，将使用默认配置")
            
            # 初始化数据仓库
            if self.repository is None:
                from data.repository import Repository
                self.repository = Repository(self)
                self.repository.initialize()
                self.logger.info("数据仓库初始化成功")
            
            # 初始化插件管理器
            if self.plugin_manager is None:
                from plugins.manager import PluginManager
                self.plugin_manager = PluginManager(self)
                self.plugin_manager.initialize()
                self.logger.info("插件管理器初始化成功")
            
            # 注册基本事件处理
            self.event_system.subscribe("app.exit", self._on_app_exit)
            
            # 标记为运行状态
            self.running = True
            self.exit_event.clear()
            
            # 发布应用启动事件
            self.event_system.publish("app.started", {
                "timestamp": time.time(),
                "app_name": self.app_name
            })
            
            self.logger.info(f"{self.app_name} 核心服务已启动")
            return True
            
        except Exception as e:
            self.logger.error(f"启动 {self.app_name} 核心服务失败: {str(e)}", exc_info=True)
            return False
    
    def stop(self):
        """停止应用程序核心服务"""
        if not self.running:
            return
            
        try:
            self.logger.info(f"正在停止 {self.app_name} 核心服务")
            
            # 标记为非运行状态
            self.running = False
            self.exit_event.set()
            
            # 发布应用停止事件
            self.event_system.publish("app.stopping", {
                "timestamp": time.time(),
                "app_name": self.app_name
            })
            
            # 停止插件管理器
            if self.plugin_manager:
                try:
                    self.logger.info("正在停止插件管理器")
                    self.plugin_manager.stop_all_plugins()
                    self.plugin_manager.cleanup()
                except Exception as e:
                    self.logger.error(f"停止插件管理器时出错: {str(e)}")
            
            # 等待线程池完成
            self.thread_manager.wait_for_finished(5000)  # 等待最多5秒
            
            # 关闭数据仓库
            if self.repository:
                try:
                    self.logger.info("正在关闭数据仓库")
                    self.repository.close()
                except Exception as e:
                    self.logger.error(f"关闭数据仓库时出错: {str(e)}")
            
            # 保存配置
            try:
                self.config.save()
            except ConfigError as e:
                self.logger.warning(f"保存配置时出错: {str(e)}")
            
            # 关闭事件系统
            self.event_system.flush()
            self.event_system.shutdown()
            
            self.logger.info(f"{self.app_name} 核心服务已停止")
            
        except Exception as e:
            self.logger.error(f"停止 {self.app_name} 核心服务失败: {str(e)}", exc_info=True)
    
    def restart(self):
        """重启应用程序核心服务"""
        self.logger.info(f"正在重启 {self.app_name} 核心服务")
        self.stop()
        time.sleep(1)  # 等待资源释放
        return self.start()
    
    def get_status(self) -> Dict[str, Any]:
        """获取应用程序状态
        
        Returns:
            Dict: 状态信息
        """
        return {
            "app_name": self.app_name,
            "running": self.running,
            "version": self.config.get("app.version", "0.1.0"),
            "uptime": time.time() - self.config.get("app.start_time", time.time()) if self.running else 0,
            "thread_count": self.thread_manager.thread_pool.activeThreadCount()
        }
    
    def _on_app_exit(self, data):
        """应用程序退出事件处理"""
        exit_code = data.get("exit_code", 0) if isinstance(data, dict) else 0
        self.logger.info(f"收到退出请求，退出码: {exit_code}")
        self.stop()
    
    def run_in_thread(self, task, *args, 
                    on_result=None, on_error=None, on_finished=None, 
                    **kwargs):
        """在线程池中运行任务
        
        Args:
            task: 要执行的函数
            *args: 函数参数
            on_result: 结果回调
            on_error: 错误回调
            on_finished: 完成回调
            **kwargs: 函数关键字参数
            
        Returns:
            Worker: 工作线程对象
        """
        return self.thread_manager.run_task(
            task, *args,
            on_result=on_result,
            on_error=on_error,
            on_finished=on_finished,
            **kwargs
        ) 