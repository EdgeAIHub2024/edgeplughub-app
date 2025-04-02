#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
工具函数模块

提供各种辅助函数，供应用程序其他部分使用
"""

import os
import sys
import platform
import hashlib
import json
import logging
import time
import uuid
import shutil
import tempfile
import zipfile
import requests
from pathlib import Path
from functools import wraps
from PyQt5.QtCore import QThread, pyqtSignal

# 设置日志
logger = logging.getLogger('core.utils')

def get_platform_info():
    """获取平台信息
    
    Returns:
        dict: 包含平台信息的字典
    """
    return {
        'system': platform.system(),
        'release': platform.release(),
        'version': platform.version(),
        'machine': platform.machine(),
        'processor': platform.processor(),
        'python_version': platform.python_version(),
        'python_implementation': platform.python_implementation()
    }

def compute_file_hash(file_path, algorithm='sha256'):
    """计算文件的哈希值
    
    Args:
        file_path: 文件路径
        algorithm: 哈希算法，默认为SHA-256
        
    Returns:
        str: 文件的哈希值
    """
    if not os.path.isfile(file_path):
        logger.error(f"文件不存在: {file_path}")
        return None
    
    try:
        hash_obj = None
        if algorithm.lower() == 'md5':
            hash_obj = hashlib.md5()
        elif algorithm.lower() == 'sha1':
            hash_obj = hashlib.sha1()
        elif algorithm.lower() == 'sha256':
            hash_obj = hashlib.sha256()
        else:
            hash_obj = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()
    except Exception as e:
        logger.error(f"计算文件 {file_path} 的哈希值失败: {str(e)}")
        return None

def create_unique_id():
    """创建唯一标识符
    
    Returns:
        str: UUID字符串
    """
    return str(uuid.uuid4())

def ensure_dir(directory):
    """确保目录存在，如果不存在则创建
    
    Args:
        directory: 目录路径
        
    Returns:
        bool: 是否成功创建或已存在
    """
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"创建目录 {directory} 失败: {str(e)}")
        return False

def sanitize_filename(filename):
    """净化文件名，移除不安全字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        str: 安全的文件名
    """
    # 替换不安全的字符
    unsafe_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    
    # 确保文件名不为空
    if not filename:
        return "unnamed"
    
    return filename

def extract_zip(zip_path, extract_to):
    """解压ZIP文件
    
    Args:
        zip_path: ZIP文件路径
        extract_to: 解压目标目录
        
    Returns:
        bool: 是否成功解压
    """
    try:
        ensure_dir(extract_to)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        return True
    except Exception as e:
        logger.error(f"解压文件 {zip_path} 到 {extract_to} 失败: {str(e)}")
        return False

def create_zip(source_path, zip_path):
    """创建ZIP文件
    
    Args:
        source_path: 源文件或目录路径
        zip_path: 目标ZIP文件路径
        
    Returns:
        bool: 是否成功创建
    """
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            if os.path.isfile(source_path):
                zipf.write(source_path, os.path.basename(source_path))
            else:
                for root, _, files in os.walk(source_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, os.path.dirname(source_path))
                        zipf.write(file_path, arcname)
        return True
    except Exception as e:
        logger.error(f"创建ZIP文件 {zip_path} 失败: {str(e)}")
        return False

def download_file(url, local_path, progress_callback=None):
    """下载文件
    
    Args:
        url: 文件URL
        local_path: 本地保存路径
        progress_callback: 进度回调函数，接收参数(当前大小, 总大小)
        
    Returns:
        bool: 是否成功下载
    """
    try:
        # 创建目标目录
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        # 下载到临时文件
        temp_file = local_path + '.download'
        
        # 开始下载
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # 获取文件大小
        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0
        
        # 写入文件
        with open(temp_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    if progress_callback:
                        progress_callback(downloaded_size, total_size)
        
        # 下载完成后重命名
        if os.path.exists(local_path):
            os.remove(local_path)
        shutil.move(temp_file, local_path)
        
        return True
    except Exception as e:
        logger.error(f"下载文件 {url} 到 {local_path} 失败: {str(e)}")
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return False

def is_valid_json(json_str):
    """检查字符串是否为有效的JSON
    
    Args:
        json_str: JSON字符串
        
    Returns:
        bool: 是否为有效的JSON
    """
    try:
        json.loads(json_str)
        return True
    except:
        return False

def timeit(func):
    """函数执行时间装饰器
    
    Args:
        func: 被装饰的函数
        
    Returns:
        function: 装饰后的函数
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.debug(f"函数 {func.__name__} 执行时间: {end_time - start_time:.4f} 秒")
        return result
    return wrapper

class WorkerThread(QThread):
    """工作线程基类"""
    
    # 信号定义
    started_signal = pyqtSignal()
    finished_signal = pyqtSignal(object)  # 传递结果
    progress_signal = pyqtSignal(int)     # 进度百分比
    error_signal = pyqtSignal(str)        # 错误信息
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cancelled = False
    
    def run(self):
        """线程执行函数，需要在子类中重写"""
        raise NotImplementedError("在子类中实现run方法")
    
    def cancel(self):
        """取消线程执行"""
        self.cancelled = True 