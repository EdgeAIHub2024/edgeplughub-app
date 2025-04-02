#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
插件下载器模块

负责从远程服务器获取插件列表并下载插件
"""

import os
import json
import logging
import requests
import tempfile
from urllib.parse import urljoin
from typing import Dict, List, Any, Optional, Union

from core.utils import ensure_dir, extract_zip
from core.exceptions import PluginError, PluginInstallError

# 设置日志
logger = logging.getLogger('plugins.downloader')

class PluginDownloader:
    """插件下载器
    
    负责从远程服务器获取插件列表和下载插件
    """
    
    def __init__(self, config, repository):
        """初始化插件下载器
        
        Args:
            config: 配置管理器实例
            repository: 数据仓库实例
        """
        self.config = config
        self.repository = repository
        
        # 获取服务器URL
        self.server_url = self.config.get('plugin_server.url', 'http://localhost:5000')
        
        # 设置请求超时时间
        self.timeout = self.config.get('plugin_server.timeout', 30)
        
        # 设置下载目录
        self.download_dir = self.config.get('download_directory')
        if not self.download_dir:
            self.download_dir = os.path.join(os.path.expanduser("~"), ".edgeplughub", "downloads")
        
        # 确保下载目录存在
        ensure_dir(self.download_dir)
        
        # 创建一个会话对象，用于保持连接
        self.session = requests.Session()
        
        # 设置基本请求头
        self.session.headers.update({
            'User-Agent': f'EdgePlugHub-Client/{self.config.get("app.version", "0.1.0")}'
        })
        
        logger.info(f"插件下载器初始化完成，服务器URL: {self.server_url}")
    
    def get_server_status(self) -> Dict[str, Any]:
        """获取服务器状态
        
        Returns:
            dict: 服务器状态信息
        """
        try:
            url = urljoin(self.server_url, '/api/server/status')
            logger.debug(f"获取服务器状态: {url}")
            
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            status = response.json()
            logger.info(f"服务器状态: 在线")
            
            return {
                'success': True,
                'online': True,
                'status': status.get('status', 'unknown'),
                'version': status.get('version', 'unknown')
            }
            
        except requests.RequestException as e:
            logger.error(f"获取服务器状态失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_available_plugins(self, category: str = None) -> Dict[str, Any]:
        """获取服务器上可用的插件列表
        
        Args:
            category: 可选，指定插件类别
            
        Returns:
            dict: 包含可用插件列表
        """
        try:
            if category:
                url = urljoin(self.server_url, f'/api/plugins/available?category={category}')
            else:
                url = urljoin(self.server_url, '/api/plugins/available')
                
            logger.debug(f"获取可用插件列表: {url}")
            
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            plugins_data = response.json()
            plugins = plugins_data if isinstance(plugins_data, list) else plugins_data.get('plugins', [])
            
            logger.info(f"找到 {len(plugins)} 个可用插件")
            
            return {
                'success': True,
                'plugins': plugins
            }
            
        except requests.RequestException as e:
            logger.error(f"获取插件列表失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_plugin_info(self, plugin_id: str) -> Dict[str, Any]:
        """获取插件详细信息
        
        Args:
            plugin_id: 插件ID
            
        Returns:
            dict: 插件详细信息
        """
        try:
            url = urljoin(self.server_url, f'/api/plugins/{plugin_id}')
            logger.debug(f"获取插件信息: {url}")
            
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            plugin_info = response.json()
            logger.info(f"获取到插件 {plugin_id} 的信息")
            
            return {
                'success': True,
                'plugin': plugin_info
            }
            
        except requests.RequestException as e:
            logger.error(f"获取插件 {plugin_id} 信息失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def download_plugin(self, plugin_id: str) -> Dict[str, Any]:
        """下载插件
        
        Args:
            plugin_id: 插件ID
            
        Returns:
            dict: 下载结果，包括本地文件路径
        """
        try:
            url = urljoin(self.server_url, f'/api/plugins/{plugin_id}/download')
            logger.info(f"开始下载插件 {plugin_id}: {url}")
            
            # 创建临时文件用于保存下载内容
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
                temp_path = temp_file.name
                
                # 流式下载，避免将大文件完全加载到内存
                with self.session.get(url, stream=True, timeout=self.timeout) as response:
                    response.raise_for_status()
                    
                    # 获取总文件大小（如果服务器提供）
                    total_size = int(response.headers.get('content-length', 0))
                    
                    # 下载文件
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            temp_file.write(chunk)
                            downloaded += len(chunk)
                            logger.debug(f"下载进度: {downloaded}/{total_size} ({downloaded/total_size*100:.1f}% 完成)")
            
            # 保存到下载目录
            target_path = os.path.join(self.download_dir, f"{plugin_id}.zip")
            
            # 复制临时文件到目标位置
            import shutil
            shutil.copy2(temp_path, target_path)
            
            # 删除临时文件
            os.unlink(temp_path)
            
            logger.info(f"插件 {plugin_id} 下载完成: {target_path}")
            
            return {
                'success': True,
                'plugin_id': plugin_id,
                'file_path': target_path
            }
            
        except requests.RequestException as e:
            logger.error(f"下载插件 {plugin_id} 失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
        except Exception as e:
            logger.error(f"处理插件 {plugin_id} 下载时发生错误: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def download_and_install(self, plugin_id: str, plugin_manager) -> Dict[str, Any]:
        """下载并安装插件
        
        Args:
            plugin_id: 插件ID
            plugin_manager: 插件管理器实例
            
        Returns:
            dict: 安装结果
        """
        try:
            # 首先检查插件是否已安装
            existing_plugin = self.repository.get_plugin(plugin_id)
            if existing_plugin:
                logger.info(f"插件 {plugin_id} 已安装，版本: {existing_plugin.get('version', '未知')}")
                
                # 获取服务器上的插件信息以比较版本
                server_info = self.get_plugin_info(plugin_id)
                if not server_info.get('success', False):
                    return server_info
                
                server_plugin = server_info.get('plugin', {})
                server_version = server_plugin.get('version', '0.0.0')
                local_version = existing_plugin.get('version', '0.0.0')
                
                # 如果本地版本已是最新，不需要重新下载
                if server_version == local_version:
                    logger.info(f"插件 {plugin_id} 已是最新版本: {local_version}")
                    return {
                        'success': True,
                        'plugin_id': plugin_id,
                        'status': 'up_to_date',
                        'version': local_version
                    }
            
            # 下载插件
            download_result = self.download_plugin(plugin_id)
            if not download_result.get('success', False):
                return download_result
            
            # 插件文件路径
            plugin_file = download_result.get('file_path')
            
            # 安装插件
            logger.info(f"安装插件: {plugin_file}")
            install_result = plugin_manager.install_plugin(plugin_file, enable=True)
            
            # 安装成功后，不再需要zip文件
            if install_result.get('success', False) and os.path.exists(plugin_file):
                try:
                    os.remove(plugin_file)
                    logger.debug(f"已删除插件临时文件: {plugin_file}")
                except:
                    pass
            
            return install_result
            
        except Exception as e:
            logger.error(f"下载并安装插件 {plugin_id} 失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_plugin_categories(self) -> Dict[str, Any]:
        """获取插件类别列表
        
        Returns:
            dict: 包含插件类别的字典
        """
        try:
            url = urljoin(self.server_url, '/api/plugins/categories')
            logger.debug(f"获取插件类别: {url}")
            
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            categories_data = response.json()
            
            # 服务器可能返回列表或包含categories字段的字典
            if isinstance(categories_data, list):
                # 转换列表为字典格式 {'类别名': 数量}
                categories = {}
                for category in categories_data:
                    if isinstance(category, str):
                        categories[category] = 0  # 默认数量为0
                logger.info(f"从列表格式获取到 {len(categories)} 个插件类别")
            else:
                # 从字典中提取categories字段
                categories = categories_data.get('categories', {})
                logger.info(f"从字典格式获取到 {len(categories)} 个插件类别")
            
            return {
                'success': True,
                'categories': categories
            }
            
        except requests.RequestException as e:
            logger.error(f"获取插件类别失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def search_plugins(self, query: str) -> Dict[str, Any]:
        """搜索插件
        
        Args:
            query: 搜索关键词
            
        Returns:
            dict: 搜索结果
        """
        try:
            url = urljoin(self.server_url, f'/api/plugins/search?q={query}')
            logger.debug(f"搜索插件: {url}")
            
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            search_results = response.json()
            plugins = search_results.get('plugins', [])
            
            logger.info(f"搜索 '{query}' 找到 {len(plugins)} 个插件")
            
            return {
                'success': True,
                'plugins': plugins
            }
            
        except requests.RequestException as e:
            logger.error(f"搜索插件失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def cleanup(self):
        """清理下载器资源"""
        try:
            # 关闭会话
            self.session.close()
            logger.debug("已关闭插件下载器会话")
        except:
            pass 