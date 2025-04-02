#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据仓库模块

管理应用程序的数据存储和检索，提供统一的数据访问接口
"""

import os
import json
import sqlite3
import logging
import threading
import time
from pathlib import Path

class Repository:
    """数据仓库类
    
    管理应用程序的数据存储和检索，支持JSON文件和SQLite数据库
    """
    
    def __init__(self, app_core=None):
        """初始化数据仓库
        
        Args:
            app_core: 应用核心实例
        """
        self.app_core = app_core
        self.config = app_core.config if app_core else None
        self.event_system = app_core.event_system if app_core else None
        self.thread_manager = app_core.thread_manager if app_core else None
        self.logger = logging.getLogger('data.repository')
        
        self.data_dir = None
        self.db_path = None
        self.db_connection = None
        self.lock = threading.RLock()  # 用于线程安全
        
        # 从配置加载路径
        if self.config:
            self._load_paths_from_config()
    
    def _load_paths_from_config(self):
        """从配置加载路径设置"""
        try:
            app_name = self.config.get('app_name', 'edgeplughub').lower()
            user_home = os.path.expanduser("~")
            app_dir = self.config.get('app_dir', os.path.join(user_home, f".{app_name}"))
            
            self.data_dir = self.config.get('data_dir', os.path.join(app_dir, "data"))
            self.db_path = self.config.get('db_path', os.path.join(self.data_dir, f"{app_name}.db"))
        except Exception as e:
            self.logger.error(f"从配置加载路径失败: {str(e)}")
            # 设置默认路径
            user_home = os.path.expanduser("~")
            app_dir = os.path.join(user_home, ".edgeplughub")
            self.data_dir = os.path.join(app_dir, "data")
            self.db_path = os.path.join(self.data_dir, "edgeplughub.db")
    
    def initialize(self):
        """初始化数据仓库
        
        创建必要的目录和数据库结构
        
        Returns:
            bool: 是否成功初始化
        """
        try:
            # 确保数据目录存在
            os.makedirs(self.data_dir, exist_ok=True)
            
            # 初始化数据库
            self._init_database()
            
            self.logger.info(f"数据仓库初始化成功，数据目录: {self.data_dir}")
            self.logger.info(f"数据库路径: {self.db_path}")
            
            return True
        except Exception as e:
            self.logger.error(f"初始化数据仓库失败: {str(e)}")
            return False
    
    def _init_database(self):
        """初始化SQLite数据库
        
        创建必要的表和索引
        """
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 创建插件信息表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS plugins (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                version TEXT NOT NULL,
                author TEXT,
                description TEXT,
                install_date TEXT,
                enabled INTEGER DEFAULT 1,
                metadata TEXT
            )
            ''')
            
            # 创建插件配置表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS plugin_configs (
                plugin_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                PRIMARY KEY (plugin_id, key),
                FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE
            )
            ''')
            
            # 创建用户偏好表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            ''')
            
            # 创建缓存表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value TEXT,
                expiry INTEGER
            )
            ''')
            
            conn.commit()
    
    def get_db_connection(self):
        """获取数据库连接
        
        返回一个SQLite连接对象，如果连接不存在则创建
        
        Returns:
            sqlite3.Connection: 数据库连接
        """
        with self.lock:
            if self.db_connection is None:
                self.db_connection = sqlite3.connect(
                    self.db_path, 
                    detect_types=sqlite3.PARSE_DECLTYPES,
                    check_same_thread=False  # 允许在多个线程中使用相同的连接
                )
                # 启用外键约束
                self.db_connection.execute("PRAGMA foreign_keys = ON")
                # 配置数据库返回行为字典
                self.db_connection.row_factory = sqlite3.Row
            
            return self.db_connection
    
    def close(self):
        """关闭数据库连接"""
        with self.lock:
            if self.db_connection:
                self.db_connection.close()
                self.db_connection = None
                self.logger.debug("数据库连接已关闭")
    
    # 插件相关方法
    
    def save_plugin(self, plugin_data):
        """保存插件信息
        
        Args:
            plugin_data: 包含插件信息的字典，必须包含id、name和version字段
            
        Returns:
            bool: 是否成功保存
        """
        try:
            if not all(k in plugin_data for k in ['id', 'name', 'version']):
                self.logger.error("保存插件信息失败: 缺少必要字段")
                return False
            
            # 将dict类型的metadata转为JSON字符串
            if 'metadata' in plugin_data and isinstance(plugin_data['metadata'], dict):
                plugin_data['metadata'] = json.dumps(plugin_data['metadata'], ensure_ascii=False)
            
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                # 构建SQL语句
                fields = list(plugin_data.keys())
                placeholders = ['?'] * len(fields)
                values = [plugin_data[field] for field in fields]
                
                # 使用INSERT OR REPLACE语法
                sql = f"INSERT OR REPLACE INTO plugins ({', '.join(fields)}) VALUES ({', '.join(placeholders)})"
                
                cursor.execute(sql, values)
                conn.commit()
                
                self.logger.debug(f"插件 {plugin_data['id']} 保存成功")
                return True
        except Exception as e:
            self.logger.error(f"保存插件信息失败: {str(e)}")
            return False
    
    def get_plugin(self, plugin_id):
        """获取插件信息
        
        Args:
            plugin_id: 插件ID
            
        Returns:
            dict: 插件信息字典，如果不存在则返回None
        """
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM plugins WHERE id = ?", (plugin_id,))
                row = cursor.fetchone()
                
                if row:
                    # 将行转换为字典
                    plugin_data = dict(row)
                    
                    # 将JSON字符串转换回dict
                    if 'metadata' in plugin_data and plugin_data['metadata']:
                        try:
                            plugin_data['metadata'] = json.loads(plugin_data['metadata'])
                        except json.JSONDecodeError:
                            self.logger.warning(f"插件 {plugin_id} 的metadata不是有效的JSON")
                    
                    return plugin_data
                return None
        except Exception as e:
            self.logger.error(f"获取插件 {plugin_id} 信息失败: {str(e)}")
            return None
    
    def get_all_plugins(self, enabled_only=False):
        """获取所有插件信息
        
        Args:
            enabled_only: 是否只返回已启用的插件
            
        Returns:
            list: 插件信息字典列表
        """
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                if enabled_only:
                    cursor.execute("SELECT * FROM plugins WHERE enabled = 1")
                else:
                    cursor.execute("SELECT * FROM plugins")
                
                rows = cursor.fetchall()
                
                plugins = []
                for row in rows:
                    plugin_data = dict(row)
                    
                    # 将JSON字符串转换回dict
                    if 'metadata' in plugin_data and plugin_data['metadata']:
                        try:
                            plugin_data['metadata'] = json.loads(plugin_data['metadata'])
                        except json.JSONDecodeError:
                            self.logger.warning(f"插件 {plugin_data['id']} 的metadata不是有效的JSON")
                    
                    plugins.append(plugin_data)
                
                return plugins
        except Exception as e:
            self.logger.error(f"获取插件列表失败: {str(e)}")
            return []
    
    def delete_plugin(self, plugin_id):
        """删除插件信息
        
        Args:
            plugin_id: 插件ID
            
        Returns:
            bool: 是否成功删除
        """
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM plugins WHERE id = ?", (plugin_id,))
                conn.commit()
                
                rows_affected = cursor.rowcount
                self.logger.debug(f"删除插件 {plugin_id}: 影响了 {rows_affected} 行")
                return rows_affected > 0
        except Exception as e:
            self.logger.error(f"删除插件 {plugin_id} 失败: {str(e)}")
            return False
    
    def set_plugin_enabled(self, plugin_id, enabled):
        """设置插件启用状态
        
        Args:
            plugin_id: 插件ID
            enabled: 是否启用
            
        Returns:
            bool: 是否成功设置
        """
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE plugins SET enabled = ? WHERE id = ?",
                    (1 if enabled else 0, plugin_id)
                )
                conn.commit()
                
                rows_affected = cursor.rowcount
                self.logger.debug(f"设置插件 {plugin_id} 启用状态为 {enabled}: 影响了 {rows_affected} 行")
                return rows_affected > 0
        except Exception as e:
            self.logger.error(f"设置插件 {plugin_id} 启用状态失败: {str(e)}")
            return False
    
    # 插件配置相关方法
    
    def save_plugin_config(self, plugin_id, key, value):
        """保存插件配置
        
        Args:
            plugin_id: 插件ID
            key: 配置键
            value: 配置值（将自动转换为JSON字符串）
            
        Returns:
            bool: 是否成功保存
        """
        try:
            # 将值转换为JSON字符串
            if value is not None:
                if not isinstance(value, str):
                    value = json.dumps(value, ensure_ascii=False)
            
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO plugin_configs (plugin_id, key, value) VALUES (?, ?, ?)",
                    (plugin_id, key, value)
                )
                conn.commit()
                
                self.logger.debug(f"保存插件 {plugin_id} 配置 {key} 成功")
                return True
        except Exception as e:
            self.logger.error(f"保存插件 {plugin_id} 配置 {key} 失败: {str(e)}")
            return False
    
    def get_plugin_config(self, plugin_id, key, default=None):
        """获取插件配置
        
        Args:
            plugin_id: 插件ID
            key: 配置键
            default: 默认值，如果配置不存在则返回此值
            
        Returns:
            任意值: 配置值，如果是JSON字符串则转换为对应的Python对象
        """
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT value FROM plugin_configs WHERE plugin_id = ? AND key = ?",
                    (plugin_id, key)
                )
                row = cursor.fetchone()
                
                if row and row['value'] is not None:
                    value = row['value']
                    # 尝试将JSON字符串转换为Python对象
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        # 如果不是有效的JSON，则返回原始字符串
                        return value
                return default
        except Exception as e:
            self.logger.error(f"获取插件 {plugin_id} 配置 {key} 失败: {str(e)}")
            return default
    
    def get_all_plugin_configs(self, plugin_id):
        """获取插件的所有配置
        
        Args:
            plugin_id: 插件ID
            
        Returns:
            dict: 包含所有配置的字典
        """
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT key, value FROM plugin_configs WHERE plugin_id = ?",
                    (plugin_id,)
                )
                rows = cursor.fetchall()
                
                configs = {}
                for row in rows:
                    key = row['key']
                    value = row['value']
                    
                    # 尝试将JSON字符串转换为Python对象
                    if value is not None:
                        try:
                            configs[key] = json.loads(value)
                        except json.JSONDecodeError:
                            configs[key] = value
                    else:
                        configs[key] = None
                
                return configs
        except Exception as e:
            self.logger.error(f"获取插件 {plugin_id} 的所有配置失败: {str(e)}")
            return {}
    
    def delete_plugin_config(self, plugin_id, key):
        """删除插件配置
        
        Args:
            plugin_id: 插件ID
            key: 配置键
            
        Returns:
            bool: 是否成功删除
        """
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM plugin_configs WHERE plugin_id = ? AND key = ?",
                    (plugin_id, key)
                )
                conn.commit()
                
                rows_affected = cursor.rowcount
                self.logger.debug(f"删除插件 {plugin_id} 配置 {key}: 影响了 {rows_affected} 行")
                return rows_affected > 0
        except Exception as e:
            self.logger.error(f"删除插件 {plugin_id} 配置 {key} 失败: {str(e)}")
            return False
    
    # 用户偏好相关方法
    
    def save_preference(self, key, value):
        """保存用户偏好设置
        
        Args:
            key: 偏好键
            value: 偏好值（将自动转换为JSON字符串）
            
        Returns:
            bool: 是否成功保存
        """
        try:
            # 将值转换为JSON字符串
            if value is not None:
                if not isinstance(value, str):
                    value = json.dumps(value, ensure_ascii=False)
            
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO user_preferences (key, value) VALUES (?, ?)",
                    (key, value)
                )
                conn.commit()
                
                self.logger.debug(f"保存用户偏好 {key} 成功")
                return True
        except Exception as e:
            self.logger.error(f"保存用户偏好 {key} 失败: {str(e)}")
            return False
    
    def get_preference(self, key, default=None):
        """获取用户偏好设置
        
        Args:
            key: 偏好键
            default: 默认值，如果偏好不存在则返回此值
            
        Returns:
            任意值: 偏好值，如果是JSON字符串则转换为对应的Python对象
        """
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM user_preferences WHERE key = ?", (key,))
                row = cursor.fetchone()
                
                if row and row['value'] is not None:
                    value = row['value']
                    # 尝试将JSON字符串转换为Python对象
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        # 如果不是有效的JSON，则返回原始字符串
                        return value
                return default
        except Exception as e:
            self.logger.error(f"获取用户偏好 {key} 失败: {str(e)}")
            return default
    
    def get_all_preferences(self):
        """获取所有用户偏好设置
        
        Returns:
            dict: 包含所有偏好的字典
        """
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT key, value FROM user_preferences")
                rows = cursor.fetchall()
                
                preferences = {}
                for row in rows:
                    key = row['key']
                    value = row['value']
                    
                    # 尝试将JSON字符串转换为Python对象
                    if value is not None:
                        try:
                            preferences[key] = json.loads(value)
                        except json.JSONDecodeError:
                            preferences[key] = value
                    else:
                        preferences[key] = None
                
                return preferences
        except Exception as e:
            self.logger.error(f"获取所有用户偏好失败: {str(e)}")
            return {}
    
    def delete_preference(self, key):
        """删除用户偏好设置
        
        Args:
            key: 偏好键
            
        Returns:
            bool: 是否成功删除
        """
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM user_preferences WHERE key = ?", (key,))
                conn.commit()
                
                rows_affected = cursor.rowcount
                self.logger.debug(f"删除用户偏好 {key}: 影响了 {rows_affected} 行")
                return rows_affected > 0
        except Exception as e:
            self.logger.error(f"删除用户偏好 {key} 失败: {str(e)}")
            return False
    
    # 缓存相关方法
    
    def save_cache(self, key, value, ttl=3600):
        """保存缓存数据
        
        Args:
            key: 缓存键
            value: 缓存值（将自动转换为JSON字符串）
            ttl: 生存时间（秒），默认1小时
            
        Returns:
            bool: 是否成功保存
        """
        try:
            # 将值转换为JSON字符串
            if value is not None:
                if not isinstance(value, str):
                    value = json.dumps(value, ensure_ascii=False)
            
            # 计算过期时间戳
            expiry = int(time.time()) + ttl if ttl > 0 else 0
            
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO cache (key, value, expiry) VALUES (?, ?, ?)",
                    (key, value, expiry)
                )
                conn.commit()
                
                self.logger.debug(f"保存缓存 {key} 成功，TTL: {ttl} 秒")
                return True
        except Exception as e:
            self.logger.error(f"保存缓存 {key} 失败: {str(e)}")
            return False
    
    def get_cache(self, key, default=None):
        """获取缓存数据
        
        Args:
            key: 缓存键
            default: 默认值，如果缓存不存在或已过期则返回此值
            
        Returns:
            任意值: 缓存值，如果是JSON字符串则转换为对应的Python对象
        """
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT value, expiry FROM cache WHERE key = ?",
                    (key,)
                )
                row = cursor.fetchone()
                
                if row:
                    value, expiry = row['value'], row['expiry']
                    
                    # 检查是否过期
                    if expiry > 0 and int(time.time()) > expiry:
                        # 已过期，删除缓存并返回默认值
                        cursor.execute("DELETE FROM cache WHERE key = ?", (key,))
                        conn.commit()
                        self.logger.debug(f"缓存 {key} 已过期，已删除")
                        return default
                    
                    # 缓存有效，尝试将JSON字符串转换为Python对象
                    if value is not None:
                        try:
                            return json.loads(value)
                        except json.JSONDecodeError:
                            return value
                
                return default
        except Exception as e:
            self.logger.error(f"获取缓存 {key} 失败: {str(e)}")
            return default
    
    def delete_cache(self, key):
        """删除缓存数据
        
        Args:
            key: 缓存键
            
        Returns:
            bool: 是否成功删除
        """
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM cache WHERE key = ?", (key,))
                conn.commit()
                
                rows_affected = cursor.rowcount
                self.logger.debug(f"删除缓存 {key}: 影响了 {rows_affected} 行")
                return rows_affected > 0
        except Exception as e:
            self.logger.error(f"删除缓存 {key} 失败: {str(e)}")
            return False
    
    def clear_expired_cache(self):
        """清理过期的缓存数据
        
        Returns:
            int: 删除的缓存条目数量
        """
        try:
            current_time = int(time.time())
            
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM cache WHERE expiry > 0 AND expiry < ?",
                    (current_time,)
                )
                conn.commit()
                
                rows_affected = cursor.rowcount
                if rows_affected > 0:
                    self.logger.debug(f"清理过期缓存: 删除了 {rows_affected} 条记录")
                return rows_affected
        except Exception as e:
            self.logger.error(f"清理过期缓存失败: {str(e)}")
            return 0
    
    # 文件存储相关方法
    
    def save_json_file(self, filename, data):
        """保存JSON数据到文件
        
        Args:
            filename: 文件名（相对于数据目录）
            data: 要保存的数据（将自动转换为JSON）
            
        Returns:
            bool: 是否成功保存
        """
        try:
            file_path = os.path.join(self.data_dir, filename)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 先写入临时文件，然后重命名，避免写入过程中的文件损坏
            temp_file = file_path + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 重命名临时文件
            os.replace(temp_file, file_path)
            
            self.logger.debug(f"保存JSON文件 {filename} 成功")
            return True
        except Exception as e:
            self.logger.error(f"保存JSON文件 {filename} 失败: {str(e)}")
            return False
    
    def load_json_file(self, filename, default=None):
        """从文件加载JSON数据
        
        Args:
            filename: 文件名（相对于数据目录）
            default: 如果文件不存在或加载失败时返回的默认值
            
        Returns:
            dict/list: 加载的JSON数据，如果失败则返回默认值
        """
        try:
            file_path = os.path.join(self.data_dir, filename)
            
            if not os.path.exists(file_path):
                self.logger.debug(f"JSON文件 {filename} 不存在，返回默认值")
                return default
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.logger.debug(f"加载JSON文件 {filename} 成功")
            return data
        except Exception as e:
            self.logger.error(f"加载JSON文件 {filename} 失败: {str(e)}")
            return default
    
    def file_exists(self, path):
        """检查文件是否存在
        
        Args:
            path: 文件路径（相对于数据目录）
            
        Returns:
            bool: 文件是否存在
        """
        file_path = os.path.join(self.data_dir, path)
        return os.path.exists(file_path) and os.path.isfile(file_path)
    
    def ensure_directory(self, path):
        """确保目录存在
        
        Args:
            path: 目录路径（相对于数据目录）
            
        Returns:
            bool: 是否成功创建或已存在
        """
        try:
            dir_path = os.path.join(self.data_dir, path)
            os.makedirs(dir_path, exist_ok=True)
            return True
        except Exception as e:
            self.logger.error(f"创建目录 {path} 失败: {str(e)}")
            return False
    
    # 异步操作方法
    
    def async_save_plugin(self, plugin_data, callback=None):
        """异步保存插件信息
        
        Args:
            plugin_data: 包含插件信息的字典
            callback: 操作完成后的回调函数，接收一个参数表示操作是否成功
        """
        if not self.thread_manager:
            self.logger.error("异步保存插件失败: 未配置线程管理器")
            if callback:
                callback(False)
            return False
            
        def task():
            result = self.save_plugin(plugin_data)
            return result
            
        def on_result(result):
            if self.event_system:
                self.event_system.publish('repository.plugin_saved', {
                    'plugin_id': plugin_data.get('id'),
                    'success': result
                }, main_thread=True)
                
            if callback:
                callback(result)
        
        self.thread_manager.run_task(task, on_result=on_result)
        return True
    
    def async_get_all_plugins(self, enabled_only=False, callback=None):
        """异步获取所有插件信息
        
        Args:
            enabled_only: 是否只返回已启用的插件
            callback: 操作完成后的回调函数，接收获取到的插件列表
        """
        if not self.thread_manager:
            self.logger.error("异步获取插件列表失败: 未配置线程管理器")
            if callback:
                callback([])
            return False
            
        def task():
            return self.get_all_plugins(enabled_only)
            
        def on_result(result):
            if callback:
                callback(result)
        
        self.thread_manager.run_task(task, on_result=on_result)
        return True 