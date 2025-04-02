#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
插件运行器组件
负责处理插件运行请求和调用插件方法
"""

import os
import sys
import logging
import traceback
from threading import Thread, Lock

# 创建简单的数据结构，不依赖SDK
class PluginInput:
    def __init__(self, data_type, data, metadata=None):
        self.data_type = data_type
        self.data = data
        self.metadata = metadata or {}

class DataType:
    IMAGE = "image"
    TEXT = "text"
    JSON = "json"
    BINARY = "binary"

class PluginRunner:
    """插件运行器
    负责处理插件运行请求和执行插件
    """
    
    def __init__(self, plugin_manager, event_system, repository):
        """初始化插件运行器
        
        Args:
            plugin_manager: 插件管理器实例
            event_system: 事件系统实例
            repository: 数据仓库实例
        """
        self.plugin_manager = plugin_manager
        self.event_system = event_system
        self.repository = repository
        self.logger = logging.getLogger("plugins.runner")
        
        # 运行中的插件线程
        self.running_plugins = {}
        self.lock = Lock()
        
        # 注册事件处理器
        self._register_event_handlers()
        
        self.logger.info("插件运行器已初始化")
    
    def _register_event_handlers(self):
        """注册事件处理器"""
        # 注册插件运行请求事件处理器
        self.event_system.subscribe('plugin.run_request', self._on_plugin_run_request)
        
        # 注册应用停止事件处理器
        self.event_system.subscribe('app.stopping', self._on_app_stopping)
    
    def _on_plugin_run_request(self, data):
        """处理插件运行请求事件
        
        Args:
            data: 事件数据，包含plugin_id和name
        """
        plugin_id = data.get('plugin_id')
        plugin_name = data.get('name', plugin_id)
        
        if not plugin_id:
            self.logger.error("无效的插件运行请求：缺少plugin_id")
            return
        
        self.logger.info(f"收到运行插件请求: {plugin_name} ({plugin_id})")
        
        # 运行插件
        self.run_plugin(plugin_id)
    
    def run_plugin(self, plugin_id, input_data=None):
        """运行插件
        
        Args:
            plugin_id: 插件ID
            input_data: 输入数据（可选）
            
        Returns:
            bool: 是否成功启动插件
        """
        try:
            # 检查插件是否已加载
            if plugin_id not in self.plugin_manager.loaded_plugins:
                self.logger.warning(f"插件 {plugin_id} 未加载，尝试加载")
                if not self.plugin_manager.load_plugin(plugin_id):
                    self.logger.error(f"无法加载插件 {plugin_id}")
                    return False
            
            # 获取插件实例
            plugin_instance = self.plugin_manager.loaded_plugins.get(plugin_id)
            if not plugin_instance:
                self.logger.error(f"获取插件 {plugin_id} 实例失败")
                return False
            
            # 创建默认输入数据（如果未提供）
            if input_data is None:
                input_data = PluginInput(
                    data_type=DataType.JSON,
                    data={},
                    metadata={
                        'source': 'EdgePlugHub',
                        'mode': 'manual_run'
                    }
                )
            
            # 在新线程中运行插件
            self._run_plugin_in_thread(plugin_id, plugin_instance, input_data)
            
            return True
            
        except Exception as e:
            self.logger.error(f"启动插件 {plugin_id} 失败: {str(e)}")
            self.logger.error(traceback.format_exc())
            
            # 发布插件运行失败事件
            self.event_system.publish('plugin.run_failed', {
                'plugin_id': plugin_id,
                'error': str(e)
            })
            
            return False
    
    def _run_plugin_in_thread(self, plugin_id, plugin_instance, input_data):
        """在新线程中运行插件
        
        Args:
            plugin_id: 插件ID
            plugin_instance: 插件实例
            input_data: 输入数据
        """
        # 检查插件是否已在运行
        with self.lock:
            if plugin_id in self.running_plugins:
                self.logger.warning(f"插件 {plugin_id} 已在运行中")
                return
        
        # 创建并启动线程
        thread = Thread(
            target=self._process_plugin,
            args=(plugin_id, plugin_instance, input_data),
            name=f"plugin-{plugin_id}",
            daemon=True
        )
        
        # 记录运行中的插件
        with self.lock:
            self.running_plugins[plugin_id] = thread
        
        # 发布插件运行开始事件
        self.event_system.publish('plugin.run_started', {
            'plugin_id': plugin_id
        })
        
        # 启动线程
        thread.start()
        self.logger.info(f"插件 {plugin_id} 已在新线程中启动")
    
    def _process_plugin(self, plugin_id, plugin_instance, input_data):
        """处理插件（在线程中执行）
        
        Args:
            plugin_id: 插件ID
            plugin_instance: 插件实例
            input_data: 输入数据
        """
        try:
            self.logger.info(f"开始运行插件 {plugin_id}")
            
            # 判断是否是FitVerse风格的适配器（查看是否有run_func属性）
            if hasattr(plugin_instance, 'run_func'):
                self.logger.info(f"检测到FitVerse风格插件适配器，直接调用run_func")
                # 直接调用run_non_interactive函数
                output = plugin_instance.run_func()
            else:
                # 调用标准插件的process方法
                self.logger.info(f"调用标准插件的process方法")
                output = plugin_instance.process(input_data)
            
            self.logger.info(f"插件 {plugin_id} 运行完成")
            
            # 发布插件运行完成事件
            self.event_system.publish('plugin.run_completed', {
                'plugin_id': plugin_id,
                'success': output.success if hasattr(output, 'success') else True,
                'data': output.data if hasattr(output, 'data') else output,
                'error': output.error_message if hasattr(output, 'error_message') else None
            })
            
        except Exception as e:
            self.logger.error(f"运行插件 {plugin_id} 时出错: {str(e)}")
            self.logger.error(traceback.format_exc())
            
            # 发布插件运行失败事件
            self.event_system.publish('plugin.run_failed', {
                'plugin_id': plugin_id,
                'error': str(e)
            })
            
        finally:
            # 从运行中的插件列表中移除
            with self.lock:
                if plugin_id in self.running_plugins:
                    del self.running_plugins[plugin_id]
    
    def _on_app_stopping(self, _):
        """应用停止时的处理"""
        self.logger.info("应用正在停止，终止所有运行中的插件")
        
        # 获取运行中的插件列表
        with self.lock:
            running_plugins = list(self.running_plugins.keys())
        
        # 发布插件停止事件
        for plugin_id in running_plugins:
            self.event_system.publish('plugin.run_stopping', {
                'plugin_id': plugin_id
            })
        
        # 等待所有线程完成（最多5秒）
        with self.lock:
            for thread in self.running_plugins.values():
                thread.join(timeout=1.0)
        
        self.logger.info("所有插件线程已终止")
    
    def stop_plugin(self, plugin_id):
        """停止正在运行的插件
        
        目前仅发出停止事件通知，由插件自行处理
        
        Args:
            plugin_id: 插件ID
            
        Returns:
            bool: 是否成功发送停止请求
        """
        with self.lock:
            if plugin_id not in self.running_plugins:
                self.logger.warning(f"插件 {plugin_id} 未在运行中，无需停止")
                return False
        
        # 发布插件停止事件
        self.event_system.publish('plugin.run_stopping', {
            'plugin_id': plugin_id
        })
        
        self.logger.info(f"已发送停止请求给插件 {plugin_id}")
        return True 