#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
线程管理模块

提供线程安全的任务执行和线程管理功能
"""

import logging
import traceback
from PyQt5.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool

class WorkerSignals(QObject):
    """工作线程信号
    
    提供线程完成、错误和结果的信号
    """
    result = pyqtSignal(object)
    error = pyqtSignal(str, object)  # 错误消息和详细信息
    finished = pyqtSignal()

class Worker(QRunnable):
    """工作线程
    
    在QThreadPool中执行的可运行任务
    """
    
    def __init__(self, fn, *args, **kwargs):
        """初始化工作线程
        
        Args:
            fn: 要执行的函数
            *args: 函数参数
            **kwargs: 函数关键字参数
        """
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        
    def run(self):
        """执行任务"""
        try:
            # 调用函数
            result = self.fn(*self.args, **self.kwargs)
            # 发出结果信号
            self.signals.result.emit(result)
        except Exception as e:
            # 记录错误并发出错误信号
            logging.error(f"线程任务执行出错: {str(e)}")
            tb = traceback.format_exc()
            self.signals.error.emit(str(e), tb)
        finally:
            # 无论成功或失败，都发出完成信号
            self.signals.finished.emit()

class ThreadManager:
    """线程管理器
    
    管理线程池，提供异步任务执行功能
    """
    
    def __init__(self, max_threads=None):
        """初始化线程管理器
        
        Args:
            max_threads: 最大线程数，默认使用Qt默认值
        """
        self.thread_pool = QThreadPool()
        if max_threads is not None:
            self.thread_pool.setMaxThreadCount(max_threads)
        logging.info(f"线程池初始化完成，最大线程数: {self.thread_pool.maxThreadCount()}")
        
    def run_task(self, task, *args, on_result=None, on_error=None, on_finished=None, **kwargs):
        """异步运行任务
        
        Args:
            task: 要执行的函数
            *args: 函数参数
            on_result: 结果回调函数
            on_error: 错误回调函数
            on_finished: 完成回调函数
            **kwargs: 函数关键字参数
            
        Returns:
            Worker: 工作线程实例
        """
        # 创建工作线程
        worker = Worker(task, *args, **kwargs)
        
        # 连接信号
        if on_result is not None:
            worker.signals.result.connect(on_result)
        if on_error is not None:
            worker.signals.error.connect(on_error)
        if on_finished is not None:
            worker.signals.finished.connect(on_finished)
            
        # 启动任务
        self.thread_pool.start(worker)
        return worker
        
    def wait_for_finished(self, timeout=None):
        """等待所有线程完成
        
        Args:
            timeout: 超时时间（毫秒），默认不限制
            
        Returns:
            bool: 是否全部完成
        """
        return self.thread_pool.waitForDone(timeout) 