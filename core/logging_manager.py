#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
日志管理模块

提供应用程序的日志记录服务，支持控制台和文件输出
"""

import os
import sys
import logging
import datetime
import traceback
from pathlib import Path

class LoggingManager:
    """日志管理类
    
    管理应用程序的日志系统，提供统一的日志记录接口
    """
    
    def __init__(self, log_level="INFO", log_dir=None, console_output=True):
        """初始化日志管理器
        
        Args:
            log_level: 日志级别
            log_dir: 日志目录
            console_output: 是否输出到控制台
        """
        self.log_level = self._get_log_level(log_level)
        self.log_dir = log_dir
        self.console_output = console_output
        
        # 确保日志目录存在
        if self.log_dir:
            os.makedirs(self.log_dir, exist_ok=True)
        
        # 配置根日志记录器
        self._setup_root_logger()
        
        # 创建应用日志记录器
        self.logger = logging.getLogger('app')
        self._setup_logger(self.logger, self.log_level)
        
        self.logger.info("日志系统初始化完成")
    
    def _get_log_level(self, level):
        """转换日志级别字符串为常量
        
        Args:
            level: 日志级别字符串
            
        Returns:
            int: 日志级别常量
        """
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        
        if isinstance(level, str):
            return level_map.get(level.upper(), logging.INFO)
        return level
    
    def _setup_root_logger(self):
        """配置根日志记录器"""
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # 清除现有处理器
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # 添加控制台处理器
        if self.console_output:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(self.log_level)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
    
    def _setup_logger(self, logger, level):
        """配置指定的日志记录器
        
        Args:
            logger: 日志记录器
            level: 日志级别
        """
        logger.setLevel(level)
        logger.propagate = False  # 避免日志消息传播到根日志记录器
        
        # 清除现有处理器
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # 添加控制台处理器
        if self.console_output:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        # 添加文件处理器
        if self.log_dir:
            log_file = os.path.join(self.log_dir, f"app_{datetime.datetime.now().strftime('%Y%m%d')}.log")
            try:
                file_handler = logging.FileHandler(log_file, encoding='utf-8')
                file_handler.setLevel(level)
                file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                file_handler.setFormatter(file_formatter)
                logger.addHandler(file_handler)
            except Exception as e:
                print(f"无法创建日志文件: {str(e)}")
    
    def get_logger(self, name):
        """获取指定名称的日志记录器
        
        Args:
            name: 日志记录器名称
            
        Returns:
            logging.Logger: 日志记录器
        """
        logger = logging.getLogger(name)
        self._setup_logger(logger, self.log_level)
        return logger
    
    def set_level(self, level):
        """设置日志级别
        
        Args:
            level: 日志级别
        """
        level = self._get_log_level(level)
        self.log_level = level
        
        # 更新根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        for handler in root_logger.handlers:
            handler.setLevel(level)
        
        # 更新应用日志记录器
        self.logger.setLevel(level)
        for handler in self.logger.handlers:
            handler.setLevel(level)
        
        self.logger.info(f"日志级别已设置为: {logging.getLevelName(level)}")
    
    def get_log_files(self):
        """获取日志文件列表
        
        Returns:
            list: 日志文件列表
        """
        if not self.log_dir or not os.path.exists(self.log_dir):
            return []
        
        log_files = []
        for file in os.listdir(self.log_dir):
            if file.endswith('.log'):
                log_files.append(os.path.join(self.log_dir, file))
        
        return log_files 