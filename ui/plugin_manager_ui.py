#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
插件管理器图形界面

提供插件的管理、安装和查看功能
"""

import os
import sys
import time
import logging
from datetime import datetime
from urllib.parse import urljoin

try:
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QTabWidget, 
                                QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
                                QPushButton, QComboBox, QListWidget, QListWidgetItem,
                                QTextEdit, QSplitter, QFrame, QMessageBox, 
                                QProgressBar, QDialog, QLineEdit, QCheckBox, QScrollArea,
                                QGroupBox)
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
    from PyQt5.QtGui import QIcon, QColor, QPixmap, QFont, QTextCursor
except ImportError:
    print("PyQt5 模块未安装，请安装后重试")
    print("可以使用命令: pip install PyQt5")
    sys.exit(1)

# 创建自定义日志处理器，将日志重定向到界面
class QTextEditLogger(logging.Handler):
    """自定义日志处理器，将日志输出到QTextEdit控件"""
    
    def __init__(self, widget):
        """初始化日志处理器
        
        Args:
            widget: QTextEdit实例
        """
        super().__init__()
        self.widget = widget
        self.widget.setReadOnly(True)
        
        # 设置不同级别日志的颜色
        self.colors = {
            logging.DEBUG: '#808080',  # 灰色
            logging.INFO: '#000000',   # 黑色
            logging.WARNING: '#FFA500', # 橙色
            logging.ERROR: '#FF0000',  # 红色
            logging.CRITICAL: '#800000' # 深红色
        }
        
        # 设置格式化器
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.setFormatter(formatter)
    
    def emit(self, record):
        """输出日志记录到界面
        
        Args:
            record: 日志记录
        """
        msg = self.format(record)
        color = self.colors.get(record.levelno, '#000000')
        
        # 在GUI线程中更新界面
        self.widget.append(f'<font color="{color}">{msg}</font>')
        
        # 确保滚动到最新消息
        self.widget.moveCursor(QTextCursor.End)


class PluginListItemWidget(QWidget):
    """插件列表项控件"""
    
    def __init__(self, plugin_data, is_installed=False, parent=None):
        """初始化插件列表项控件
        
        Args:
            plugin_data: 插件数据字典
            is_installed: 是否是已安装的插件
            parent: 父控件
        """
        super().__init__(parent)
        
        # 保存插件数据
        self.plugin_data = plugin_data
        self.is_installed = is_installed
        
        # 获取插件基本信息
        self.plugin_id = plugin_data.get('id', 'unknown')
        self.name = plugin_data.get('name', self.plugin_id)
        self.version = plugin_data.get('version', 'unknown')
        self.description = plugin_data.get('description', '无描述')
        self.author = plugin_data.get('author', 'unknown')
        self.category = plugin_data.get('category', 'unknown')
        
        # 获取图标路径
        self.icon_path = plugin_data.get('icon_path', '')
        
        # 创建界面
        self._setup_ui()
    
    def _setup_ui(self):
        """设置界面"""
        # 主布局 - 垂直布局
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        self.setLayout(layout)
        
        # 图标
        icon_size = 64
        icon_label = QLabel()
        icon_label.setFixedSize(icon_size, icon_size)
        icon_label.setAlignment(Qt.AlignCenter)
        
        # 尝试加载插件图标
        pixmap = None
        if self.icon_path:
            try:
                # 尝试加载图标
                pixmap = QPixmap(self.icon_path)
            except:
                pixmap = None
                
        if pixmap and not pixmap.isNull():
            pixmap = pixmap.scaled(icon_size, icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_label.setPixmap(pixmap)
        else:
            # 使用默认图标
            icon_label.setStyleSheet("""
                background-color: #007ACC;
                color: white;
                font-size: 24px;
                border-radius: 8px;
            """)
            # 使用插件名称首字母作为图标
            icon_text = self.name[0].upper() if self.name else "P"
            icon_label.setText(icon_text)
            
        layout.addWidget(icon_label, alignment=Qt.AlignCenter)
        
        # 插件名称
        name_label = QLabel(self.name)
        name_label.setAlignment(Qt.AlignCenter)
        font = name_label.font()
        font.setPointSize(10)
        font.setBold(True)
        name_label.setFont(font)
        name_label.setWordWrap(True)
        layout.addWidget(name_label)
        
        # 按钮区域
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 5, 0, 0)
        
        if self.is_installed:
            # 已安装插件显示运行和删除按钮
            self.run_button = QPushButton("运行")
            self.run_button.clicked.connect(self._on_run_clicked)
            button_layout.addWidget(self.run_button)
            
            # 添加更新按钮
            self.update_button = QPushButton("更新")
            self.update_button.clicked.connect(self._on_update_clicked)
            button_layout.addWidget(self.update_button)
            
            self.delete_button = QPushButton("删除")
            self.delete_button.clicked.connect(self._on_delete_clicked)
            button_layout.addWidget(self.delete_button)
        else:
            # 未安装插件显示下载按钮
            self.download_button = QPushButton("下载")
            self.download_button.clicked.connect(self._on_download_clicked)
            button_layout.addWidget(self.download_button)
        
        layout.addWidget(button_widget)
        
        # 鼠标悬停效果
        self.setMouseTracking(True)
        
        # 设置边框和背景
        self.setStyleSheet("""
            PluginListItemWidget {
                border: 1px solid #CCCCCC;
                border-radius: 8px;
                background-color: #F9F9F9;
                padding: 10px;
                margin: 5px;
            }
            PluginListItemWidget:hover {
                background-color: #F0F0F0;
                border-color: #AAAAAA;
            }
            QPushButton {
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 9pt;
            }
        """)
        
        # 设置固定大小 - 类似手机应用图标
        self.setFixedSize(120, 160)
    
    def mousePressEvent(self, event):
        """鼠标点击事件处理"""
        if event.button() == Qt.LeftButton:
            self._show_plugin_details()
        super().mousePressEvent(event)
    
    def _show_plugin_details(self):
        """显示插件详情对话框"""
        # 查找窗口层级中的PluginManagerUI实例
        manager_ui = None
        parent = self
        while parent is not None:
            parent = parent.parent()
            if isinstance(parent, PluginManagerUI):
                manager_ui = parent
                break
                
        # 创建对话框 - 使用当前窗口作为父窗口，而不是使用特定层级的父窗口
        dialog = QDialog(self.window())
        dialog.setWindowTitle(f"插件详情 - {self.name}")
        dialog.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(dialog)
        
        # 标题
        title_label = QLabel(f"<h2>{self.name} v{self.version}</h2>")
        layout.addWidget(title_label)
        
        # 基本信息
        info_grid = QGridLayout()
        info_grid.addWidget(QLabel("<b>作者:</b>"), 0, 0)
        info_grid.addWidget(QLabel(self.author), 0, 1)
        info_grid.addWidget(QLabel("<b>类别:</b>"), 1, 0)
        info_grid.addWidget(QLabel(self.category), 1, 1)
        info_widget = QWidget()
        info_widget.setLayout(info_grid)
        layout.addWidget(info_widget)
        
        # 描述区域
        desc_group = QGroupBox("插件描述")
        desc_layout = QVBoxLayout(desc_group)
        desc_text = QTextEdit()
        desc_text.setPlainText(self.description)
        desc_text.setReadOnly(True)
        desc_layout.addWidget(desc_text)
        layout.addWidget(desc_group)
        
        # 按钮区域
        button_box = QWidget()
        button_layout = QHBoxLayout(button_box)
        
        if self.is_installed:
            run_btn = QPushButton("运行")
            run_btn.clicked.connect(self._on_run_clicked)
            button_layout.addWidget(run_btn)
            
            update_btn = QPushButton("更新")
            update_btn.clicked.connect(self._on_update_clicked)
            button_layout.addWidget(update_btn)
            
            delete_btn = QPushButton("删除")
            delete_btn.clicked.connect(self._on_delete_clicked)
            button_layout.addWidget(delete_btn)
        else:
            download_btn = QPushButton("下载并安装")
            download_btn.clicked.connect(self._on_download_clicked)
            button_layout.addWidget(download_btn)
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)
        
        layout.addWidget(button_box)
        
        dialog.exec_()
    
    def _on_run_clicked(self):
        """运行按钮点击处理"""
        try:
            # 查找窗口层级中的PluginManagerUI实例
            parent = self
            while parent is not None:
                parent = parent.parent()
                if isinstance(parent, PluginManagerUI):
                    parent.run_plugin(self.plugin_id)
                    break
            
            # 如果未找到PluginManagerUI实例，记录错误
            if parent is None or not isinstance(parent, PluginManagerUI):
                logging.error(f"未能找到PluginManagerUI实例来处理运行请求，plugin_id: {self.plugin_id}")
                QMessageBox.warning(
                    self,
                    "操作失败",
                    "无法处理运行请求，请联系开发者。",
                    QMessageBox.Ok
                )
        except Exception as e:
            logging.error(f"处理运行请求失败: {str(e)}")
            QMessageBox.critical(
                self,
                "错误",
                f"处理运行请求失败: {str(e)}",
                QMessageBox.Ok
            )
    
    def _on_delete_clicked(self):
        """删除按钮点击处理"""
        # 确认删除
        reply = QMessageBox.question(
            self, 
            "确认删除", 
            f"确定要删除插件 {self.name} 吗？", 
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # 查找窗口层级中的PluginManagerUI实例
                parent = self
                while parent is not None:
                    parent = parent.parent()
                    if isinstance(parent, PluginManagerUI):
                        parent.delete_plugin(self.plugin_id)
                        break
                
                # 如果未找到PluginManagerUI实例，记录错误
                if parent is None or not isinstance(parent, PluginManagerUI):
                    logging.error(f"未能找到PluginManagerUI实例来处理删除请求，plugin_id: {self.plugin_id}")
                    QMessageBox.warning(
                        self,
                        "操作失败",
                        "无法处理删除请求，请联系开发者。",
                        QMessageBox.Ok
                    )
            except Exception as e:
                logging.error(f"处理删除请求失败: {str(e)}")
                QMessageBox.critical(
                    self,
                    "错误",
                    f"处理删除请求失败: {str(e)}",
                    QMessageBox.Ok
                )
    
    def _on_download_clicked(self):
        """下载按钮点击处理"""
        try:
            # 查找窗口层级中的PluginManagerUI实例
            parent = self
            while parent is not None:
                parent = parent.parent()
                if isinstance(parent, PluginManagerUI):
                    parent.download_plugin(self.plugin_id)
                    break
            
            # 如果未找到PluginManagerUI实例，记录错误
            if parent is None or not isinstance(parent, PluginManagerUI):
                logging.error(f"未能找到PluginManagerUI实例来处理下载请求，plugin_id: {self.plugin_id}")
                QMessageBox.warning(
                    self,
                    "操作失败",
                    "无法处理下载请求，请联系开发者。",
                    QMessageBox.Ok
                )
                return
                
            # 暂时禁用下载按钮
            if hasattr(self, 'download_button'):
                self.download_button.setEnabled(False)
                self.download_button.setText("下载中...")
                
        except Exception as e:
            logging.error(f"处理下载请求失败: {str(e)}")
            QMessageBox.critical(
                self,
                "错误",
                f"处理下载请求失败: {str(e)}",
                QMessageBox.Ok
            )
    
    def _on_update_clicked(self):
        """更新按钮点击处理"""
        # 确认更新
        reply = QMessageBox.question(
            self, 
            "确认更新", 
            f"确定要更新插件 {self.name} 吗？", 
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # 查找窗口层级中的PluginManagerUI实例
                parent = self
                while parent is not None:
                    parent = parent.parent()
                    if isinstance(parent, PluginManagerUI):
                        parent.update_plugin(self.plugin_id)
                        break
                
                # 如果未找到PluginManagerUI实例，记录错误
                if parent is None or not isinstance(parent, PluginManagerUI):
                    logging.error(f"未能找到PluginManagerUI实例来处理更新请求，plugin_id: {self.plugin_id}")
                    QMessageBox.warning(
                        self,
                        "操作失败",
                        "无法处理更新请求，请联系开发者。",
                        QMessageBox.Ok
                    )
                    return
                
                # 暂时禁用更新按钮
                self.update_button.setEnabled(False)
                self.update_button.setText("更新中...")
            except Exception as e:
                logging.error(f"处理更新请求失败: {str(e)}")
                QMessageBox.critical(
                    self,
                    "错误",
                    f"处理更新请求失败: {str(e)}",
                    QMessageBox.Ok
                )


class PluginManagerUI(QMainWindow):
    """插件管理器图形界面"""
    
    # 添加信号
    download_complete = pyqtSignal(dict)
    update_complete = pyqtSignal(dict)
    
    def __init__(self, app_core, parent=None):
        """初始化插件管理器界面
        
        Args:
            app_core: AppCore实例
            parent: 父窗口
        """
        super().__init__(parent)
        
        # 保存应用核心引用
        self.app_core = app_core
        
        # 从app_core获取所需组件
        self.config = app_core.config
        self.event_system = app_core.event_system
        self.repository = app_core.repository
        self.plugin_manager = app_core.plugin_manager
        self.thread_manager = app_core.thread_manager
        
        # 日志记录器
        self.logger = logging.getLogger('ui.plugin_manager')
        
        # 设置窗口属性
        self.setWindowTitle("EdgePlugHub 插件管理器")
        self.setMinimumSize(800, 600)
        
        # 服务器地址
        self.server_url = self.config.get('server_url', 'http://localhost:8000')
        
        # 创建界面
        self._setup_ui()
        
        # 创建日志处理器
        self._setup_logger()
        
        # 注册事件处理器
        self._register_event_handlers()
        
        # 刷新插件列表
        self.refresh_installed_plugins()
        
        # 加载插件分类
        self.load_plugin_categories()
        
        # 加载商店插件
        self._on_refresh_store()
    
    def _setup_ui(self):
        """设置界面"""
        # 创建中央控件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建Tab控件
        self.tab_widget = QTabWidget()
        
        # 已安装插件页面
        self.installed_page = QWidget()
        installed_layout = QVBoxLayout(self.installed_page)
        
        # 已安装插件列表
        self.installed_list = QListWidget()
        self.installed_list.setViewMode(QListWidget.IconMode)  # 使用图标模式
        self.installed_list.setIconSize(QSize(64, 64))
        self.installed_list.setResizeMode(QListWidget.Adjust)
        self.installed_list.setSpacing(10)
        self.installed_list.setMovement(QListWidget.Static)  # 禁止拖动
        installed_layout.addWidget(self.installed_list)
        
        # 添加到Tab
        self.tab_widget.addTab(self.installed_page, "已安装")
        
        # 插件中心页面
        self.store_page = QWidget()
        store_layout = QVBoxLayout(self.store_page)
        
        # 顶部工具栏
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        
        # 分类下拉框
        category_label = QLabel("分类:")
        toolbar_layout.addWidget(category_label)
        
        self.category_combo = QComboBox()
        self.category_combo.addItem("所有类别", "all")
        self.category_combo.currentIndexChanged.connect(self._on_category_changed)
        toolbar_layout.addWidget(self.category_combo)
        
        # 添加间隔
        toolbar_layout.addStretch()
        
        # 刷新按钮
        refresh_button = QPushButton("刷新")
        refresh_button.clicked.connect(self._on_refresh_store)
        toolbar_layout.addWidget(refresh_button)
        
        store_layout.addWidget(toolbar)
        
        # 插件列表
        self.store_list = QListWidget()
        self.store_list.setViewMode(QListWidget.IconMode)  # 使用图标模式
        self.store_list.setIconSize(QSize(64, 64))
        self.store_list.setResizeMode(QListWidget.Adjust)
        self.store_list.setSpacing(10)
        self.store_list.setMovement(QListWidget.Static)  # 禁止拖动
        store_layout.addWidget(self.store_list)
        
        # 添加到Tab
        self.tab_widget.addTab(self.store_page, "插件中心")
        
        # 添加Tab控件到主布局
        main_layout.addWidget(self.tab_widget, 3)
        
        # 日志区域
        log_group = QGroupBox("日志")
        log_layout = QVBoxLayout(log_group)
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        log_layout.addWidget(self.log_area)
        
        main_layout.addWidget(log_group, 1)
        
        # 配置日志输出
        self._setup_logger()
        
        # 设置窗口属性
        self.resize(800, 600)
        self.setMinimumSize(600, 400)
    
    def _setup_logger(self):
        """设置日志处理器"""
        # 添加日志控件
        logger_widget = self.log_area
        
        # 创建自定义日志处理器
        log_handler = QTextEditLogger(logger_widget)
        log_handler.setLevel(logging.INFO)
        
        # 添加到日志系统
        root_logger = logging.getLogger()
        root_logger.addHandler(log_handler)
        
        # 将PluginManagerUI的日志也重定向到控件
        self.logger.addHandler(log_handler)
        
        # 写入初始日志
        self.logger.info("插件管理器界面已启动")
    
    def refresh_installed_plugins(self):
        """刷新已安装的插件列表"""
        # 清空列表
        self.installed_list.clear()
        
        # 使用异步API获取插件列表
        def on_plugins_loaded(plugins):
            # 这个回调会在主线程中执行
            if not plugins:
                self.logger.warning("没有已安装的插件")
                return
                
            for plugin_data in plugins:
                # 设置图标路径
                icon_path = None
                metadata = plugin_data.get('metadata', {})
                if metadata and 'icon' in metadata:
                    icon_path = os.path.join(
                        self.plugin_manager._get_plugin_path(plugin_data['id'], metadata),
                        metadata['icon']
                    )
                    
                # 确保图标路径存在    
                if icon_path and not os.path.exists(icon_path):
                    icon_path = None
                    
                # 设置图标路径
                plugin_data['icon_path'] = icon_path
                
                # 创建列表项和控件
                item = QListWidgetItem(self.installed_list)
                widget = PluginListItemWidget(plugin_data, is_installed=True, parent=self.installed_list)
                
                # 调整列表项大小
                item.setSizeHint(widget.sizeHint())
                
                # 设置列表项控件
                self.installed_list.setItemWidget(item, widget)
        
        # 异步获取插件列表
        self.repository.async_get_all_plugins(callback=on_plugins_loaded)
    
    def load_plugin_categories(self):
        """加载插件分类"""
        # 清空下拉框
        self.category_combo.clear()
        
        # 添加所有分类选项
        self.category_combo.addItem("所有分类")
        
        # 添加其他分类选项
        categories = ["工具", "开发", "数据处理", "分析", "UI", "系统"]
        for category in categories:
            self.category_combo.addItem(category)
            
        # 选择第一项（所有分类）
        self.category_combo.setCurrentIndex(0)
    
    def _on_category_changed(self, index):
        """分类下拉框选择变更事件处理
        
        Args:
            index: 选择的索引
        """
        # 清空商店列表
        self.store_list.clear()
        
        # 获取选择的分类
        category = self.category_combo.currentText()
        if category == "所有分类":
            category = None
            
        # 显示加载提示
        item = QListWidgetItem(self.store_list)
        loading_label = QLabel("正在加载插件...")
        loading_label.setAlignment(Qt.AlignCenter)
        item.setSizeHint(loading_label.sizeHint())
        self.store_list.setItemWidget(item, loading_label)
        
        # 在线程中获取商店插件
        def get_store_plugins():
            # 这里使用模拟数据，实际应用中应从服务器获取
            # 使用本地仓库中的插件作为演示
            plugins = self.repository.get_all_plugins(enabled_only=False)
            
            # 如果有分类过滤，应用过滤
            if category:
                plugins = [p for p in plugins if p.get('category', '') == category]
                
            # 添加模拟的插件商店数据
            for i in range(3):
                plugin_id = f"demo_plugin_{i}"
                # 确保不重复
                if not any(p['id'] == plugin_id for p in plugins):
                    plugins.append({
                        'id': plugin_id,
                        'name': f"演示插件 {i+1}",
                        'version': '1.0.0',
                        'author': '开发者',
                        'description': '这是一个演示插件，用于测试商店功能',
                        'category': '工具' if i % 2 == 0 else '数据处理',
                    })
            
            return plugins
            
        def on_plugins_fetched(plugins):
            # 清空列表
            self.store_list.clear()
            
            if not plugins:
                # 添加提示项
                item = QListWidgetItem(self.store_list)
                label = QLabel("没有找到插件")
                label.setAlignment(Qt.AlignCenter)
                item.setSizeHint(label.sizeHint())
                self.store_list.setItemWidget(item, label)
                return
                
            # 添加插件到列表
            for plugin_data in plugins:
                # 检查插件是否已安装
                is_installed = self.repository.get_plugin(plugin_data['id']) is not None
                
                # 如果已安装，跳过（已安装的插件在另一个选项卡中显示）
                if is_installed:
                    continue
                
                # 创建列表项
                item = QListWidgetItem(self.store_list)
                widget = PluginListItemWidget(plugin_data, is_installed=False, parent=self.store_list)
                item.setSizeHint(widget.sizeHint())
                self.store_list.setItemWidget(item, widget)
            
            self.logger.info(f"已加载 {len(plugins)} 个商店插件")
        
        # 异步获取商店插件
        self.thread_manager.run_task(get_store_plugins, on_result=on_plugins_fetched)
    
    def _on_refresh_store(self):
        """刷新商店按钮点击事件处理"""
        # 重新触发分类变更事件
        self._on_category_changed(self.category_combo.currentIndex())
    
    def run_plugin(self, plugin_id):
        """运行插件
        
        Args:
            plugin_id: 插件ID
        """
        self.logger.info(f"尝试运行插件: {plugin_id}")
        
        try:
            # 获取插件信息
            plugin_info = self.plugin_manager.get_plugin_info(plugin_id)
            if not plugin_info:
                raise Exception(f"找不到插件: {plugin_id}")
                
            # 检查插件是否已加载
            if not plugin_info.get('is_loaded', False):
                # 尝试加载插件
                self.logger.info(f"插件 {plugin_id} 尚未加载，正在加载...")
                if not self.plugin_manager.load_plugin(plugin_id):
                    raise Exception(f"无法加载插件: {plugin_id}")
            
            # 使用事件系统发布插件运行事件
            self.event_system.publish('plugin.run_request', {
                'plugin_id': plugin_id,
                'name': plugin_info.get('name', plugin_id)
            })
            
            self.logger.info(f"已请求运行插件: {plugin_id}")
            
        except Exception as e:
            self.logger.error(f"运行插件 {plugin_id} 失败: {str(e)}")
            QMessageBox.critical(self, "运行失败", f"无法运行插件: {str(e)}")
    
    def delete_plugin(self, plugin_id):
        """删除插件
        
        Args:
            plugin_id: 插件ID
        """
        self.logger.info(f"请求删除插件: {plugin_id}")
        
        try:
            # 获取插件信息
            plugin_info = self.plugin_manager.get_plugin_info(plugin_id)
            if not plugin_info:
                raise Exception(f"找不到插件: {plugin_id}")
                
            # 显示确认对话框
            plugin_name = plugin_info.get('name', plugin_id)
            reply = QMessageBox.question(
                self, 
                "确认删除", 
                f"确定要删除插件 {plugin_name} 吗？\n\n这将移除插件文件，但保留插件数据。",
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
                
            # 询问是否同时删除数据
            reply_data = QMessageBox.question(
                self, 
                "删除数据", 
                f"是否同时删除插件 {plugin_name} 的数据？",
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            
            remove_data = (reply_data == QMessageBox.Yes)
            
            # 使用线程管理器执行删除操作
            def on_delete_result(success):
                if success:
                    self.logger.info(f"插件 {plugin_name} ({plugin_id}) 已成功删除")
                    if remove_data:
                        self.logger.info(f"插件 {plugin_name} 的数据已删除")
                    # UI会通过事件更新
                else:
                    self.logger.error(f"删除插件 {plugin_id} 失败")
                    QMessageBox.critical(self, "删除失败", f"无法删除插件 {plugin_name}。")
            
            # 在后台线程中执行卸载
            self.thread_manager.run_task(
                lambda: self.plugin_manager.uninstall_plugin(plugin_id, remove_data),
                on_result=on_delete_result
            )
            
        except Exception as e:
            self.logger.error(f"删除插件 {plugin_id} 失败: {str(e)}")
            QMessageBox.critical(self, "删除失败", f"无法删除插件: {str(e)}")
    
    def download_plugin(self, plugin_id):
        """下载插件
        
        Args:
            plugin_id: 插件ID
        """
        self.logger.info(f"开始下载插件: {plugin_id}")
        
        # 使用线程管理器启动下载
        def on_download_result(result):
            # 更新UI
            self.download_complete.emit(result)
        
        # 发布下载请求事件
        self.event_system.publish('plugin.download_request', {
            'plugin_id': plugin_id,
            'callback': on_download_result
        })
    
    def update_plugin(self, plugin_id):
        """更新插件
        
        Args:
            plugin_id: 插件ID
        """
        self.logger.info(f"开始更新插件: {plugin_id}")
        
        # 使用线程管理器启动更新
        def on_update_result(result):
            # 更新UI
            self.update_complete.emit(result)
        
        # 在线程中执行更新
        self.thread_manager.run_task(
            lambda: self.plugin_manager.update_plugin(plugin_id),
            on_result=on_update_result
        )

    def _show_download_result(self, result):
        """在主线程中显示下载结果"""
        if result.get('success', False):
            status = result.get('status', '')
            if status == 'up_to_date':
                logging.info(f"插件 {result.get('plugin_id')} 已是最新版本")
                QMessageBox.information(
                    self,
                    "下载完成",
                    f"插件 {result.get('plugin_id')} 已是最新版本",
                    QMessageBox.Ok
                )
            else:
                logging.info(f"插件 {result.get('plugin_id')} 下载并安装成功")
                QMessageBox.information(
                    self,
                    "下载完成",
                    f"插件 {result.get('plugin_id')} 已成功下载并安装",
                    QMessageBox.Ok
                )
            
            # 刷新已安装插件列表
            self.refresh_installed_plugins()
        else:
            error = result.get('error', '未知错误')
            logging.error(f"下载插件失败: {error}")
            
            QMessageBox.warning(
                self,
                "下载失败",
                f"无法下载插件 {result.get('plugin_id')}：{error}",
                QMessageBox.Ok
            )
            
            # 刷新插件中心列表
            self._on_category_changed(self.category_combo.currentIndex())

    def _show_update_result(self, result):
        """在主线程中显示更新结果"""
        if result.get('success'):
            plugin_id = result.get('plugin_id')
            name = result.get('name', plugin_id)
            old_version = result.get('old_version', 'unknown')
            new_version = result.get('new_version', 'unknown')
            
            # 显示成功消息
            QMessageBox.information(
                self,
                "更新成功",
                f"插件 {name} 已成功更新。\n从 v{old_version} 更新到 v{new_version}。"
            )
            
            # 刷新插件列表
            self.refresh_installed_plugins()
        else:
            error = result.get('error', '未知错误')
            
            # 显示错误消息
            QMessageBox.critical(
                self,
                "更新失败",
                f"更新插件失败: {error}"
            )
            
            # 刷新插件列表，恢复按钮状态
            self.refresh_installed_plugins()

    def _register_event_handlers(self):
        """注册事件处理器"""
        # 注册插件事件处理器
        self.event_system.subscribe('plugin.installed', self._on_plugin_installed)
        self.event_system.subscribe('plugin.uninstalled', self._on_plugin_uninstalled)
        self.event_system.subscribe('plugin.updated', self._on_plugin_updated)
        self.event_system.subscribe('plugin.enabled', self._on_plugin_enabled)
        self.event_system.subscribe('plugin.disabled', self._on_plugin_disabled)
        self.event_system.subscribe('plugin.loaded', self._on_plugin_loaded)
        self.event_system.subscribe('plugin.unloaded', self._on_plugin_unloaded)
        
        # 连接信号到槽
        self.download_complete.connect(self._show_download_result)
        self.update_complete.connect(self._show_update_result)
        
        # 创建刷新计时器
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_installed_plugins)
        self.refresh_timer.start(10000)  # 每10秒刷新一次
    
    def _on_plugin_installed(self, data):
        """插件安装事件处理器
        
        Args:
            data: 事件数据，包含plugin_id、name等信息
        """
        plugin_id = data.get('plugin_id')
        name = data.get('name', plugin_id)
        self.logger.info(f"插件 {name} ({plugin_id}) 已安装")
        self.refresh_installed_plugins()
    
    def _on_plugin_uninstalled(self, data):
        """插件卸载事件处理器
        
        Args:
            data: 事件数据，包含plugin_id、name等信息
        """
        plugin_id = data.get('plugin_id')
        name = data.get('name', plugin_id)
        self.logger.info(f"插件 {name} ({plugin_id}) 已卸载")
        self.refresh_installed_plugins()
    
    def _on_plugin_updated(self, data):
        """插件更新事件处理器
        
        Args:
            data: 事件数据，包含plugin_id、name、old_version、new_version等信息
        """
        plugin_id = data.get('plugin_id')
        name = data.get('name', plugin_id)
        old_version = data.get('old_version', '?')
        new_version = data.get('new_version', '?')
        self.logger.info(f"插件 {name} ({plugin_id}) 已从 v{old_version} 更新到 v{new_version}")
        self.refresh_installed_plugins()
    
    def _on_plugin_enabled(self, data):
        """插件启用事件处理器
        
        Args:
            data: 事件数据，包含plugin_id、name等信息
        """
        plugin_id = data.get('plugin_id')
        name = data.get('name', plugin_id)
        self.logger.info(f"插件 {name} ({plugin_id}) 已启用")
        self.refresh_installed_plugins()
    
    def _on_plugin_disabled(self, data):
        """插件禁用事件处理器
        
        Args:
            data: 事件数据，包含plugin_id、name等信息
        """
        plugin_id = data.get('plugin_id')
        name = data.get('name', plugin_id)
        self.logger.info(f"插件 {name} ({plugin_id}) 已禁用")
        self.refresh_installed_plugins()
    
    def _on_plugin_loaded(self, data):
        """插件加载事件处理器
        
        Args:
            data: 事件数据，包含plugin_id、name、version等信息
        """
        plugin_id = data.get('plugin_id')
        name = data.get('name', plugin_id)
        version = data.get('version', '?')
        self.logger.info(f"插件 {name} v{version} ({plugin_id}) 已加载")
    
    def _on_plugin_unloaded(self, data):
        """插件卸载事件处理器
        
        Args:
            data: 事件数据，包含plugin_id等信息
        """
        plugin_id = data.get('plugin_id')
        self.logger.info(f"插件 {plugin_id} 已卸载")


def launch_plugin_manager_ui(app_core):
    """启动插件管理器界面
    
    Args:
        app_core: AppCore实例
        
    Returns:
        PluginManagerUI: 插件管理器界面实例
    """
    try:
        # 创建插件管理器界面
        ui = PluginManagerUI(app_core)
        ui.show()
        
        # 返回界面实例，以便调用者进一步操作
        return ui
        
    except Exception as e:
        app_core.logger.error(f"启动插件管理器界面失败: {str(e)}", exc_info=True)
        raise 