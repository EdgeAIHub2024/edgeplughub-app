#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
EdgePlugHub入口点

启动EdgePlugHub应用程序，支持GUI、CLI和插件管理器模式
"""

import os
import sys
import time
import logging
from app import EdgePlugHubApp

def main():
    """程序入口点"""
    try:
        # 创建应用程序实例
        app = EdgePlugHubApp()
        
        # 启动应用程序
        if app.start():
            # 应用程序启动成功，但start方法中已经处理了UI循环或命令行循环
            # 如果代码执行到这里，表示应用已退出
            return 0
        else:
            # 启动失败
            logging.error("应用程序启动失败")
            return 1
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        return 130  # 标准的SIGINT退出码
    except Exception as e:
        logging.error(f"程序启动失败: {str(e)}", exc_info=True)
        print(f"错误: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 