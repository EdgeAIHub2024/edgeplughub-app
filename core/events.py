#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
事件系统模块

实现发布-订阅模式，用于模块间的松耦合通信
支持在主线程中安全执行回调
"""

import logging
import threading
import time
import queue
import uuid
from PyQt5.QtCore import QObject, QTimer, Qt

class EventSystem(QObject):
    """事件系统类，实现发布-订阅模式"""
    
    def __init__(self):
        """初始化事件系统"""
        super().__init__()
        self._subscribers = {}  # 事件类型 -> [回调函数列表]
        self._subscribers_lock = threading.RLock()  # 防止并发修改订阅者列表
        self.logger = logging.getLogger('core.events')
        
        # 添加异步事件处理支持
        self._async_queue = queue.Queue()
        self._running = True  # 修复：添加_running属性
        self._async_thread = threading.Thread(target=self._process_async_events, daemon=True)
        self._async_thread.start()
    
    def subscribe(self, event_type, callback, subscriber_id=None):
        """订阅事件
        
        Args:
            event_type: 事件类型
            callback: 回调函数，接收事件数据作为参数
            subscriber_id: 订阅者ID，默认自动生成
            
        Returns:
            str: 订阅者ID，可用于取消订阅
        """
        if subscriber_id is None:
            subscriber_id = str(uuid.uuid4())
            
        with self._subscribers_lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            
            self._subscribers[event_type].append((subscriber_id, callback))
            
        self.logger.debug(f"已订阅事件: {event_type}, 订阅者ID: {subscriber_id}")
        return subscriber_id
    
    def unsubscribe(self, event_type, subscriber_id):
        """取消订阅
        
        Args:
            event_type: 事件类型
            subscriber_id: 订阅者ID
            
        Returns:
            bool: 是否成功取消订阅
        """
        with self._subscribers_lock:
            if event_type not in self._subscribers:
                return False
            
            # 过滤掉指定ID的订阅者
            original_count = len(self._subscribers[event_type])
            self._subscribers[event_type] = [
                (sid, callback) 
                for sid, callback in self._subscribers[event_type] 
                if sid != subscriber_id
            ]
            
            # 如果没有订阅者了，删除整个事件类型
            if not self._subscribers[event_type]:
                del self._subscribers[event_type]
                
            success = len(self._subscribers.get(event_type, [])) < original_count
            
            if success:
                self.logger.debug(f"已取消订阅: {event_type}, 订阅者ID: {subscriber_id}")
            else:
                self.logger.warning(f"未找到订阅: {event_type}, 订阅者ID: {subscriber_id}")
                
            return success
    
    def publish(self, event_type, data=None, main_thread=False):
        """同步发布事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
            main_thread: 是否在主线程中执行回调
        """
        self.logger.debug(f"发布事件: {event_type}, 主线程回调: {main_thread}")
        
        with self._subscribers_lock:
            if event_type not in self._subscribers:
                return
            
            # 复制订阅者列表，防止回调中修改订阅
            subscribers = list(self._subscribers[event_type])
        
        # 调用所有回调函数
        for subscriber_id, callback in subscribers:
            if main_thread and threading.current_thread() is not threading.main_thread():
                # 在主线程中执行回调
                self._execute_in_main_thread(callback, data, event_type, subscriber_id)
            else:
                # 在当前线程执行回调
                self._execute_callback(callback, data, event_type, subscriber_id)
    
    def publish_async(self, event_type, data=None, main_thread=False):
        """异步发布事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
            main_thread: 是否在主线程中执行回调
        """
        self.logger.debug(f"异步发布事件: {event_type}, 主线程回调: {main_thread}")
        self._async_queue.put((event_type, data, main_thread))
    
    def _execute_callback(self, callback, data, event_type, subscriber_id):
        """执行回调函数
        
        Args:
            callback: 回调函数
            data: 事件数据
            event_type: 事件类型
            subscriber_id: 订阅者ID
        """
        try:
            callback(data)
        except Exception as e:
            self.logger.error(f"事件处理器异常 ({event_type}, {subscriber_id}): {str(e)}", exc_info=True)
    
    def _execute_in_main_thread(self, callback, data, event_type, subscriber_id):
        """在主线程中执行回调
        
        Args:
            callback: 回调函数
            data: 事件数据
            event_type: 事件类型
            subscriber_id: 订阅者ID
        """
        # 使用QTimer.singleShot在主线程中执行回调
        QTimer.singleShot(0, lambda: self._execute_callback(callback, data, event_type, subscriber_id))
    
    def _process_async_events(self):
        """异步事件处理线程"""
        self.logger.info("异步事件处理线程已启动")
        
        while self._running:
            try:
                # 获取队列中的事件（阻塞，但有超时以便检查_running状态）
                try:
                    event_type, data, main_thread = self._async_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                
                # 处理事件
                try:
                    self.publish(event_type, data, main_thread)
                finally:
                    # 标记任务完成
                    self._async_queue.task_done()
                    
            except Exception as e:
                self.logger.error(f"异步事件处理错误: {str(e)}", exc_info=True)
    
    def shutdown(self):
        """关闭事件系统"""
        self.logger.info("正在关闭事件系统...")
        self._running = False
        
        # 等待异步线程结束
        if self._async_thread.is_alive():
            self._async_thread.join(timeout=2.0)
            
        # 清空订阅者
        with self._subscribers_lock:
            self._subscribers.clear()
            
        self.logger.info("事件系统已关闭")
        
    def flush(self):
        """等待所有异步事件处理完成"""
        try:
            self._async_queue.join()
            self.logger.debug("所有异步事件已处理完成")
        except Exception as e:
            self.logger.error(f"等待异步事件处理时出错: {str(e)}", exc_info=True) 