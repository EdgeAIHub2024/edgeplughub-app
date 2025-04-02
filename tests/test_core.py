#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
核心模块测试脚本
"""

import os
import sys
import time
import logging
import threading

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.app_core import AppCore
from PyQt5.QtWidgets import QApplication

def test_task(param):
    """测试任务"""
    print(f"测试任务执行中，参数: {param}")
    # 模拟耗时操作
    time.sleep(2)
    return f"测试任务完成: {param}"

def test_event_handler(data):
    """测试事件处理器"""
    print(f"收到事件，数据: {data}")

def on_task_result(result):
    """任务结果回调"""
    print(f"任务结果: {result}")

def on_task_error(error, tb):
    """任务错误回调"""
    print(f"任务错误: {error}")
    print(f"错误详情: {tb}")

def test_main_thread_callback(data):
    """测试主线程回调"""
    thread_id = threading.current_thread().ident
    main_thread_id = threading.main_thread().ident
    print(f"主线程回调: {data}")
    print(f"当前线程ID: {thread_id}, 主线程ID: {main_thread_id}")
    print(f"是否在主线程执行: {thread_id == main_thread_id}")

def main():
    """测试主函数"""
    # 创建Qt应用程序，用于测试主线程回调
    app = QApplication(sys.argv)
    
    # 创建测试目录
    test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_data")
    os.makedirs(test_dir, exist_ok=True)
    
    # 初始化核心
    core = AppCore("EdgePlugHubTest", test_dir)
    core.start()
    
    # 测试1: 线程池
    print("\n=== 测试1: 线程池 ===")
    core.run_in_thread(
        test_task, 
        "Hello Thread",
        on_result=on_task_result,
        on_error=on_task_error
    )
    
    # 测试2: 事件系统
    print("\n=== 测试2: 事件系统 ===")
    # 订阅事件
    core.event_system.subscribe("test.event", test_event_handler)
    # 发布事件
    core.event_system.publish("test.event", {"message": "Hello Event"})
    
    # 测试3: 在后台线程发布事件，主线程中处理
    print("\n=== 测试3: 主线程回调 ===")
    # 订阅事件，在主线程中处理
    core.event_system.subscribe("test.main_thread", test_main_thread_callback)
    
    # 在后台线程中发布事件
    def background_publisher():
        time.sleep(1)  # 等待一会儿
        thread_id = threading.current_thread().ident
        main_thread_id = threading.main_thread().ident
        print(f"后台线程ID: {thread_id}, 主线程ID: {main_thread_id}")
        # 请求在主线程中处理回调
        core.event_system.publish(
            "test.main_thread", 
            {"message": "Hello Main Thread"},
            main_thread=True
        )
    
    # 启动后台线程
    bg_thread = threading.Thread(target=background_publisher)
    bg_thread.daemon = True
    bg_thread.start()
    
    # 启动Qt事件循环，处理主线程回调
    # 设置定时器在3秒后退出
    from PyQt5.QtCore import QTimer
    timer = QTimer()
    timer.timeout.connect(app.quit)
    timer.start(3000)
    
    # 进入Qt事件循环
    app.exec_()
    
    # 停止核心
    core.stop()
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    main() 