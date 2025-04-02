#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
EdgePlugHub 插件管理器启动脚本

这是一个便捷的启动脚本，直接启动插件管理器的图形界面。
也可以通过命令行参数指定更新或下载特定插件。

用法:
    python launch_manager.py                   # 启动插件管理器界面
    python launch_manager.py --update plugin1  # 更新特定插件后启动插件管理器界面
    python launch_manager.py --download plugin2 # 下载特定插件后启动插件管理器界面
"""

import sys
import os

def main():
    """启动插件管理器界面的入口点"""
    # 获取当前脚本的目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 导入main模块
    sys.path.insert(0, script_dir)
    from main import main as main_entry
    
    # 准备命令行参数
    args = ["--plugin-manager"]
    
    # 添加传递给脚本的其他参数
    original_args = sys.argv[1:]
    if original_args:
        args.extend(original_args)
    
    # 调用主入口函数
    sys.argv = [sys.argv[0]] + args
    return main_entry()

if __name__ == "__main__":
    sys.exit(main()) 