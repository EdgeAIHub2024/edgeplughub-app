#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
EdgePlugHub 插件管理器启动脚本

这是一个便捷的启动脚本，直接启动插件管理器的图形界面。
也可以通过命令行参数指定更新或下载特定插件。

用法:
    python launch_manager.py                   # 启动图形界面
    python launch_manager.py --update plugin1  # 更新特定插件后启动图形界面
    python launch_manager.py --download plugin2 # 下载特定插件后启动图形界面
"""

import os
import sys
import argparse
import logging
from PyQt5.QtWidgets import QApplication

from core.app_core import AppCore
from ui.plugin_manager_ui import launch_plugin_manager_ui

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='EdgePlugHub 插件管理器启动脚本')
    parser.add_argument('--update', type=str, help='更新指定的插件后启动图形界面')
    parser.add_argument('--download', type=str, help='下载指定的插件后启动图形界面')
    parser.add_argument('--log-level', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='日志级别')
    parser.add_argument('--app-dir', type=str, help='应用程序数据目录')
    
    return parser.parse_args()

def main():
    """主函数"""
    # 解析命令行参数
    args = parse_args()
    
    # 设置日志级别
    logging.basicConfig(level=getattr(logging, args.log_level))
    
    # 创建Qt应用程序
    qt_app = QApplication(sys.argv)
    qt_app.setStyle("Fusion")
    
    # 设置应用程序数据目录
    if args.app_dir:
        app_dir = args.app_dir
    else:
        user_home = os.path.expanduser("~")
        app_dir = os.path.join(user_home, ".edgeplughub")
    
    # 创建应用核心
    app_core = AppCore("EdgePlugHub", app_dir)
    if not app_core.start():
        logging.error("启动应用程序核心失败")
        return 1
    
    try:
        # 处理下载和更新命令
        if args.download:
            logging.info(f"将下载插件 {args.download}")
            plugin_id = args.download
            
            # 这里需要添加下载插件的逻辑 
            app_core.event_system.publish('plugin.download_request', {
                'plugin_id': plugin_id,
                'callback': lambda r: logging.info(f"下载结果: {r}")
            })
            
        if args.update:
            logging.info(f"将更新插件 {args.update}")
            plugin_id = args.update
            
            # 使用线程管理器执行更新
            def on_update_done(result):
                logging.info(f"更新结果: {result}")
            
            app_core.thread_manager.run_task(
                lambda: app_core.plugin_manager.update_plugin(plugin_id),
                on_result=on_update_done
            )
        
        # 启动图形界面
        ui = launch_plugin_manager_ui(app_core)
        
        # 启动Qt事件循环
        result = qt_app.exec_()
        
        # 停止应用核心
        app_core.stop()
        
        return result
        
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        app_core.stop()
        return 0
    except Exception as e:
        logging.error(f"启动失败: {str(e)}", exc_info=True)
        app_core.stop()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 