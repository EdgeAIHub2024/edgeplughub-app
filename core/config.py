#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
配置管理模块

负责应用程序配置的加载、保存和访问
"""

import os
import json
import logging
import threading

class ConfigManager:
    """配置管理类"""
    
    def __init__(self, config_file=None):
        """初始化配置管理器
        
        Args:
            config_file: 配置文件路径，如果为None则使用默认路径
        """
        self.logger = logging.getLogger('core.config')
        self._config = {}
        self._lock = threading.RLock()
        
        # 设置配置文件路径
        if config_file is None:
            self._config_dir = os.path.expanduser("~/.edgeplughub")
            self._config_file = os.path.join(self._config_dir, "config.json")
        else:
            self._config_file = os.path.abspath(config_file)
            self._config_dir = os.path.dirname(self._config_file)
        
        # 确保配置目录存在
        os.makedirs(self._config_dir, exist_ok=True)
        
        # 加载配置
        self._load()
        
        # 设置默认配置
        self._set_defaults()
    
    def _set_defaults(self):
        """设置内置默认配置值"""
        defaults = {
            "app_name": "EdgePlugHub",
            "app_version": "1.0.0",
            "plugins_directory": os.path.join(self._config_dir, "plugins"),
            "theme": "light",
            "language": "zh_CN",
            "check_updates": True,
            "log_level": "INFO",
            "first_run": True
        }
        
        # 将缺失的默认值添加到配置中
        for key, value in defaults.items():
            if key not in self._config:
                self._config[key] = value
    
    def set_defaults(self, defaults):
        """设置默认配置值
        
        Args:
            defaults: 默认配置字典
            
        Returns:
            bool: 是否成功设置默认值
        """
        try:
            with self._lock:
                # 将缺失的默认值添加到配置中
                for key, value in defaults.items():
                    if key not in self._config:
                        self._config[key] = value
                        
                self.logger.debug("已设置默认配置值")
                return True
        except Exception as e:
            self.logger.error(f"设置默认配置值失败: {str(e)}", exc_info=True)
            return False
    
    def _load(self):
        """从文件加载配置"""
        with self._lock:
            try:
                if os.path.exists(self._config_file):
                    with open(self._config_file, 'r', encoding='utf-8') as f:
                        self.logger.info(f"正在从 {self._config_file} 加载配置")
                        self._config = json.load(f)
                        self.logger.info("配置加载成功")
                else:
                    self.logger.info(f"配置文件 {self._config_file} 不存在，将使用默认配置")
            except Exception as e:
                self.logger.error(f"加载配置失败: {str(e)}", exc_info=True)
                self._config = {}
    
    def save(self):
        """保存配置到文件"""
        with self._lock:
            try:
                # 确保配置目录存在
                os.makedirs(self._config_dir, exist_ok=True)
                
                # 先写入临时文件，再重命名，避免写入过程中崩溃导致文件损坏
                temp_file = f"{self._config_file}.tmp"
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(self._config, f, ensure_ascii=False, indent=2)
                
                # 替换原文件
                if os.path.exists(self._config_file):
                    os.replace(temp_file, self._config_file)
                else:
                    os.rename(temp_file, self._config_file)
                    
                self.logger.info(f"配置已保存到 {self._config_file}")
                return True
            except Exception as e:
                self.logger.error(f"保存配置失败: {str(e)}", exc_info=True)
                return False
    
    def get(self, key, default=None):
        """获取配置值
        
        Args:
            key: 配置键
            default: 如果键不存在，返回的默认值
            
        Returns:
            配置值，如果键不存在则返回默认值
        """
        with self._lock:
            return self._config.get(key, default)
    
    def set(self, key, value):
        """设置配置值
        
        Args:
            key: 配置键
            value: 配置值
            
        Returns:
            bool: 是否设置成功
        """
        with self._lock:
            try:
                old_value = self._config.get(key)
                if old_value != value:
                    self._config[key] = value
                    self.logger.debug(f"配置已更新: {key} = {value}")
                return True
            except Exception as e:
                self.logger.error(f"设置配置失败: {str(e)}", exc_info=True)
                return False
    
    def delete(self, key):
        """删除配置项
        
        Args:
            key: 配置键
            
        Returns:
            bool: 是否成功删除
        """
        with self._lock:
            if key in self._config:
                del self._config[key]
                self.logger.debug(f"配置已删除: {key}")
                return True
            return False
    
    def get_all(self):
        """获取所有配置
        
        Returns:
            dict: 配置字典的副本
        """
        with self._lock:
            return dict(self._config)
    
    def reset(self):
        """重置配置到默认值"""
        with self._lock:
            self._config.clear()
            self._set_defaults()
            self.save()
            self.logger.info("配置已重置为默认值")
    
    def get_config_file(self):
        """获取配置文件路径"""
        return self._config_file
    
    def load(self):
        """从文件加载配置
        
        Returns:
            bool: 是否成功加载
        """
        with self._lock:
            try:
                if os.path.exists(self._config_file):
                    with open(self._config_file, 'r', encoding='utf-8') as f:
                        self.logger.info(f"正在从 {self._config_file} 加载配置")
                        self._config = json.load(f)
                        self.logger.info("配置加载成功")
                    return True
                else:
                    self.logger.info(f"配置文件 {self._config_file} 不存在，将使用默认配置")
                    return False
            except Exception as e:
                self.logger.error(f"加载配置失败: {str(e)}", exc_info=True)
                self._config = {}
                return False 