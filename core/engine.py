#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
EdgePlugHub 核心引擎

负责应用程序的整体生命周期管理和组件协调
"""

import os
import sys
import logging
from PyQt5.QtWidgets import QApplication

from .config import Config
from .events import EventSystem
from ..data.repository import Repository
from ..plugins.manager import PluginManager
from ..logging.logger import LogManager

class Engine:
    """应用程序核心引擎"""
    
    def __init__(self):
        """初始化应用引擎"""
        self.initialized = False
        self.running = False
        self.logger = logging.getLogger('core.engine')
        
        # 核心组件
        self.config = None
        self.event_system = None
        self.log_manager = None
        self.data_repository = None
        self.plugin_manager = None
        self.qt_app = None
        self.main_window = None
    
    def initialize(self):
        """初始化应用程序的所有组件"""
        if self.initialized:
            self.logger.warning("引擎已经初始化")
            return
        
        try:
            self.logger.info("开始初始化应用引擎")
            
            # 创建Qt应用程序
            self.qt_app = QApplication(sys.argv)
            self.qt_app.setApplicationName("EdgePlugHub")
            self.qt_app.setApplicationVersion("1.0.0")
            self.qt_app.setOrganizationName("EdgePlugHub")
            self.qt_app.setOrganizationDomain("edgeplughub.com")
            
            # 初始化事件系统
            self.event_system = EventSystem()
            self.logger.info("事件系统初始化完成")
            
            # 初始化配置系统
            self.config = Config()
            self.logger.info("配置系统初始化完成")
            
            # 初始化日志管理器
            self.log_manager = LogManager(self.config)
            self.logger.info("日志系统初始化完成")
            
            # 初始化数据仓库
            self.data_repository = Repository(self.config, self.event_system)
            self.logger.info("数据仓库初始化完成")
            
            # 初始化插件管理器
            self.plugin_manager = PluginManager(self.config, self.event_system, self.data_repository)
            self.logger.info("插件管理器初始化完成")
            
            # 所有后台组件初始化完成
            self.initialized = True
            self.logger.info("应用引擎初始化完成")
            
            # 触发初始化完成事件
            self.event_system.publish("engine.initialized")
            
            return True
        except Exception as e:
            self.logger.error(f"引擎初始化失败: {str(e)}", exc_info=True)
            return False
    
    def start(self):
        """启动应用程序"""
        if not self.initialized:
            if not self.initialize():
                self.logger.error("引擎未能成功初始化，无法启动")
                return False
        
        try:
            # 导入UI层，避免循环导入
            from ..ui.main_window import MainWindow
            
            # 创建并显示主窗口
            self.main_window = MainWindow(self.plugin_manager, self.event_system, self.config)
            self.main_window.show()
            
            # 标记应用为运行状态
            self.running = True
            self.logger.info("应用程序已启动")
            
            # 触发应用启动事件
            self.event_system.publish("engine.started")
            
            # 加载已安装的插件
            self.plugin_manager.load_installed_plugins()
            
            # 进入Qt事件循环
            return self.qt_app.exec_()
            
        except Exception as e:
            self.logger.error(f"应用启动失败: {str(e)}", exc_info=True)
            return False
    
    def shutdown(self):
        """关闭应用程序"""
        if not self.running:
            self.logger.warning("引擎未运行，无需关闭")
            return
        
        try:
            self.logger.info("正在关闭应用程序...")
            
            # 触发关闭事件
            self.event_system.publish("engine.shutting_down")
            
            # 停止所有插件
            if self.plugin_manager:
                self.plugin_manager.stop_all_plugins()
            
            # 保存配置
            if self.config:
                self.config.save()
            
            # 关闭主窗口
            if self.main_window:
                self.main_window.close()
            
            # 关闭所有组件
            self.running = False
            self.initialized = False
            
            self.logger.info("应用程序已正常关闭")
            return True
            
        except Exception as e:
            self.logger.error(f"应用关闭时出错: {str(e)}", exc_info=True)
            return False
    
    def get_resource_path(self, relative_path):
        """获取资源文件的绝对路径"""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, relative_path)
    
    def get_plugins_directory(self):
        """获取插件目录"""
        plugins_dir = self.config.get("plugins_directory")
        if not plugins_dir:
            plugins_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'plugins')
        
        # 确保目录存在
        os.makedirs(plugins_dir, exist_ok=True)
        return plugins_dir 