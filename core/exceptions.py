#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
异常类模块

定义应用程序中使用的自定义异常类
"""

class EdgePlugHubException(Exception):
    """EdgePlugHub应用程序的基础异常类"""
    
    def __init__(self, message="EdgePlugHub错误", code=None):
        """初始化异常
        
        Args:
            message: 错误消息
            code: 错误代码
        """
        self.message = message
        self.code = code
        super().__init__(self.message)

class ConfigError(EdgePlugHubException):
    """配置相关错误"""
    
    def __init__(self, message="配置错误", code=None):
        super().__init__(message, code)

class PluginError(EdgePlugHubException):
    """插件相关错误"""
    
    def __init__(self, message="插件错误", code=None, plugin_id=None):
        self.plugin_id = plugin_id
        message_with_id = f"{message} [插件ID: {plugin_id}]" if plugin_id else message
        super().__init__(message_with_id, code)

class PluginLoadError(PluginError):
    """插件加载错误"""
    
    def __init__(self, message="插件加载失败", code=None, plugin_id=None):
        super().__init__(message, code, plugin_id)

class PluginRunError(PluginError):
    """插件运行错误"""
    
    def __init__(self, message="插件运行失败", code=None, plugin_id=None):
        super().__init__(message, code, plugin_id)

class PluginInstallError(PluginError):
    """插件安装错误"""
    
    def __init__(self, message="插件安装失败", code=None, plugin_id=None):
        super().__init__(message, code, plugin_id)

class PluginDependencyError(PluginError):
    """插件依赖错误"""
    
    def __init__(self, message="插件依赖错误", code=None, plugin_id=None, dependency=None):
        self.dependency = dependency
        message_with_dep = f"{message} [依赖: {dependency}]" if dependency else message
        super().__init__(message_with_dep, code, plugin_id)

class NetworkError(EdgePlugHubException):
    """网络相关错误"""
    
    def __init__(self, message="网络错误", code=None, url=None):
        self.url = url
        message_with_url = f"{message} [URL: {url}]" if url else message
        super().__init__(message_with_url, code)

class ApiError(NetworkError):
    """API调用错误"""
    
    def __init__(self, message="API错误", code=None, url=None, response=None):
        self.response = response
        super().__init__(message, code, url)

class FileSystemError(EdgePlugHubException):
    """文件系统错误"""
    
    def __init__(self, message="文件系统错误", code=None, path=None):
        self.path = path
        message_with_path = f"{message} [路径: {path}]" if path else message
        super().__init__(message_with_path, code)

class SecurityError(EdgePlugHubException):
    """安全相关错误"""
    
    def __init__(self, message="安全错误", code=None):
        super().__init__(message, code)

class ValidationError(EdgePlugHubException):
    """数据验证错误"""
    
    def __init__(self, message="验证错误", code=None, field=None):
        self.field = field
        message_with_field = f"{message} [字段: {field}]" if field else message
        super().__init__(message_with_field, code) 