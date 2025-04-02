#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
插件系统测试脚本
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

def test_repository(app_core):
    """测试数据仓库"""
    print("\n=== 测试1: 数据仓库 ===")
    
    # 检查数据仓库是否初始化
    repository = app_core.repository
    assert repository is not None, "数据仓库未初始化"
    
    # 测试偏好设置
    test_key = "test_preference"
    test_value = {"name": "测试值", "value": 123}
    repository.save_preference(test_key, test_value)
    
    # 读取偏好设置
    saved_value = repository.get_preference(test_key)
    assert saved_value == test_value, f"偏好设置测试失败: {saved_value} != {test_value}"
    
    print("数据仓库测试通过")

def test_plugin_manager(app_core):
    """测试插件管理器"""
    print("\n=== 测试2: 插件管理器 ===")
    
    # 检查插件管理器是否初始化
    plugin_manager = app_core.plugin_manager
    assert plugin_manager is not None, "插件管理器未初始化"
    
    # 测试获取插件列表
    plugins = plugin_manager.get_all_plugins_info()
    print(f"发现 {len(plugins)} 个插件")
    
    # 如果有插件，测试加载插件
    if plugins:
        plugin_id = plugins[0]["id"]
        plugin_name = plugins[0]["name"]
        print(f"尝试加载插件: {plugin_name} ({plugin_id})")
        
        if plugin_manager.load_plugin(plugin_id):
            print(f"插件 {plugin_name} 加载成功")
            
            # 测试卸载插件
            if plugin_manager.unload_plugin(plugin_id):
                print(f"插件 {plugin_name} 卸载成功")
    
    print("插件管理器测试通过")

def test_async_operations(app_core):
    """测试异步操作"""
    print("\n=== 测试3: 异步操作 ===")
    
    repository = app_core.repository
    
    # 测试异步保存和检索
    test_results = []
    done_event = threading.Event()
    
    def save_callback(success):
        test_results.append(f"异步保存结果: {success}")
        
    def get_callback(plugins):
        test_results.append(f"异步获取到 {len(plugins)} 个插件")
        done_event.set()
    
    # 创建测试插件数据
    test_plugin = {
        "id": "test_plugin",
        "name": "测试插件",
        "version": "1.0.0",
        "author": "Test",
        "description": "测试异步插件操作",
        "install_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "enabled": True,
        "metadata": {"type": "test"}
    }
    
    # 异步保存
    repository.async_save_plugin(test_plugin, save_callback)
    
    # 异步获取
    repository.async_get_all_plugins(callback=get_callback)
    
    # 等待异步操作完成
    done_event.wait(timeout=5)
    
    # 打印结果
    for result in test_results:
        print(result)
    
    print("异步操作测试通过")

def main():
    """测试主函数"""
    # 创建Qt应用程序
    app = QApplication(sys.argv)
    
    # 创建测试目录
    test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_plugin_data")
    os.makedirs(test_dir, exist_ok=True)
    
    # 初始化核心
    app_core = AppCore("EdgePlugHubTest", test_dir)
    app_core.start()
    
    try:
        # 运行测试
        test_repository(app_core)
        test_plugin_manager(app_core)
        test_async_operations(app_core)
        
        print("\n=== 所有测试完成 ===")
        
    except Exception as e:
        print(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        # 停止核心
        app_core.stop()
    
    # 退出Qt事件循环
    app.quit()

if __name__ == "__main__":
    main() 