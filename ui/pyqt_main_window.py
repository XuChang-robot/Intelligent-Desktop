# 主窗口界面 (PyQt6版本)

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QTextEdit, QLineEdit, QPushButton, 
                               QComboBox, QFrame, QSplitter, QScrollArea,
                               QSizePolicy, QMessageBox, QProgressBar, QStatusBar)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl, QSize, QBuffer, QIODevice
from PyQt6.QtGui import QFont, QColor, QPalette, QTextCursor, QTextDocument, QIcon, QPixmap, QImage, QTextImageFormat, QPen
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from typing import Dict, Any, Optional, Callable
import logging
import re
import base64

class ChatTextEdit(QTextEdit):
    """自定义文本编辑框，处理链接点击"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.anchor_clicked_callback = None
    
    def set_anchor_clicked_callback(self, callback):
        """设置链接点击回调"""
        self.anchor_clicked_callback = callback
    
    def mousePressEvent(self, event):
        """处理鼠标点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 获取点击位置
            cursor = self.cursorForPosition(event.pos())
            
            # 检查是否点击了链接
            char_format = cursor.charFormat()
            if char_format.isAnchor():
                href = char_format.anchorHref()
                if href and self.anchor_clicked_callback:
                    self.anchor_clicked_callback(href)
                    return
        
        super().mousePressEvent(event)

class ModernStyle:
    """现代化样式配置"""
    
    # 颜色方案
    PRIMARY_COLOR = "#2196F3"
    SECONDARY_COLOR = "#1976D2"
    BACKGROUND_COLOR = "#FAFAFA"
    SURFACE_COLOR = "#FFFFFF"
    TEXT_COLOR = "#212121"
    SECONDARY_TEXT_COLOR = "#757575"
    BORDER_COLOR = "#E0E0E0"
    SUCCESS_COLOR = "#4CAF50"
    WARNING_COLOR = "#FF9800"
    ERROR_COLOR = "#F44336"
    
    # 字体
    TITLE_FONT = QFont("Microsoft YaHei", 18, QFont.Weight.Bold)
    HEADING_FONT = QFont("Microsoft YaHei", 14, QFont.Weight.Bold)
    TEXT_FONT = QFont("Microsoft YaHei", 11)
    SMALL_FONT = QFont("Microsoft YaHei", 9)
    
    @staticmethod
    def apply_stylesheet(app):
        """应用现代化样式表"""
        stylesheet = """
        QMainWindow {
            background-color: #FAFAFA;
        }
        
        QWidget {
            background-color: #FFFFFF;
            color: #212121;
            font-family: "Microsoft YaHei";
            font-size: 11pt;
        }
        
        QLabel {
            color: #212121;
            background-color: transparent;
        }
        
        QTextEdit {
            background-color: #F5F5F5;
            border: 1px solid #E0E0E0;
            border-radius: 8px;
            padding: 12px;
            selection-background-color: #2196F3;
            selection-color: #FFFFFF;
        }
        
        QLineEdit {
            background-color: #F5F5F5;
            border: 1px solid #E0E0E0;
            border-radius: 6px;
            padding: 10px;
            selection-background-color: #2196F3;
            selection-color: #FFFFFF;
        }
        
        QLineEdit:focus {
            border: 2px solid #2196F3;
            background-color: #FFFFFF;
        }
        
        QPushButton {
            background-color: #2196F3;
            color: #FFFFFF;
            border: none;
            border-radius: 6px;
            padding: 10px 20px;
            font-weight: bold;
        }
        
        QPushButton:hover {
            background-color: #1976D2;
        }
        
        QPushButton:pressed {
            background-color: #0D47A1;
        }
        
        QPushButton:disabled {
            background-color: #BDBDBD;
            color: #757575;
        }
        
        QComboBox {
            background-color: #F5F5F5;
            border: 1px solid #E0E0E0;
            border-radius: 6px;
            padding: 8px;
            min-width: 150px;
        }
        
        QComboBox:hover {
            border: 1px solid #2196F3;
        }
        
        QComboBox::drop-down {
            border: none;
            padding-right: 20px;
        }
        
        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid #757575;
            margin-right: 10px;
        }
        
        QFrame {
            background-color: #FFFFFF;
            border: 1px solid #E0E0E0;
            border-radius: 8px;
        }
        
        QProgressBar {
            background-color: #E0E0E0;
            border: none;
            border-radius: 3px;
            height: 6px;
        }
        
        QProgressBar::chunk {
            background-color: #2196F3;
            border-radius: 3px;
        }
        """
        app.setStyleSheet(stylesheet)

class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.user_input_callback = None
        self.loading_animation_running = False
        self.loading_dots = 0
        self.logger = logging.getLogger(__name__)
        self.current_task_id = None  # 用于跟踪当前任务
        self.task_history = []  # 任务历史记录
        self.elicitation_callback = None  # 当前elicitation回调
        self.elicitation_handled = False  # 是否已处理elicitation响应
        
        # 流式消息管理
        self.stream_message_id = None  # 当前流式消息的ID
        self.stream_message_cursor = None  # 流式消息的游标位置
        self.stream_message_sender = None  # 流式消息的发送者
        self.stream_message_thinking = None  # 流式消息的思考过程
        self.stream_message_thinking_cursor = None  # 流式消息思考过程的游标位置
        
        # 图片下载管理
        self.network_manager = QNetworkAccessManager()
        self.network_manager.finished.connect(self.on_image_downloaded)
        self.pending_images = {}  # 待下载的图片 {url: (message_id, image_id)}
        self.image_timeout = 3000  # 图片下载超时时间（毫秒）
        
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("智能桌面系统")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # 标题栏
        self.create_title_bar(main_layout)
        
        # 模型选择栏
        self.create_model_bar(main_layout)
        
        # 主内容区域（使用分割器）
        splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(splitter, 1)
        
        # 聊天区域
        self.create_chat_area(splitter)
        
        # 任务显示区域
        self.create_task_area(splitter)
        
        # 设置分割器比例
        splitter.setSizes([600, 200])
        
        # 输入区域
        self.create_input_area(main_layout)
        
        # 创建状态栏
        self.create_status_bar()
        
    def create_status_bar(self):
        """创建状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setFont(ModernStyle.SMALL_FONT)
        self.status_label.setStyleSheet(f"color: {ModernStyle.SECONDARY_TEXT_COLOR};")
        
        # 加载状态标签
        self.loading_label = QLabel("")
        self.loading_label.setFont(ModernStyle.SMALL_FONT)
        self.loading_label.setStyleSheet(f"color: {ModernStyle.PRIMARY_COLOR};")
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setMaximumHeight(16)
        self.progress_bar.setVisible(False)
        
        # 添加到状态栏
        self.status_bar.addWidget(self.status_label, 1)
        self.status_bar.addWidget(self.loading_label)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
    def create_title_bar(self, parent_layout):
        """创建标题栏"""
        title_frame = QFrame()
        title_frame.setFrameShape(QFrame.Shape.NoFrame)
        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("智能桌面系统")
        title_label.setFont(ModernStyle.TITLE_FONT)
        title_label.setStyleSheet(f"color: {ModernStyle.PRIMARY_COLOR};")
        
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        parent_layout.addWidget(title_frame)
        
    def create_model_bar(self, parent_layout):
        """创建模型选择栏"""
        model_frame = QFrame()
        model_frame.setFrameShape(QFrame.Shape.NoFrame)
        model_layout = QHBoxLayout(model_frame)
        model_layout.setContentsMargins(0, 0, 0, 0)
        
        model_label = QLabel("选择模型:")
        model_label.setFont(ModernStyle.TEXT_FONT)
        model_label.setStyleSheet(f"color: {ModernStyle.SECONDARY_TEXT_COLOR};")
        
        self.model_combobox = QComboBox()
        self.model_combobox.setFont(ModernStyle.TEXT_FONT)
        self.model_combobox.addItems(["qwen3:30b", "qwen3:7b", "llama2:7b"])
        self.model_combobox.setMinimumWidth(200)
        self.model_combobox.currentTextChanged.connect(self.on_model_changed)
        
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_combobox)
        model_layout.addStretch()
        
        parent_layout.addWidget(model_frame)
        
    def create_chat_area(self, parent_splitter):
        """创建聊天区域"""
        chat_container = QWidget()
        chat_layout = QVBoxLayout(chat_container)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(10)
        
        chat_label = QLabel("对话历史")
        chat_label.setFont(ModernStyle.HEADING_FONT)
        chat_label.setStyleSheet(f"color: {ModernStyle.SECONDARY_TEXT_COLOR};")
        
        self.chat_area = ChatTextEdit()
        self.chat_area.setReadOnly(True)
        self.chat_area.setFont(ModernStyle.TEXT_FONT)
        self.chat_area.setMinimumHeight(300)
        # 确保HTML显示正确
        self.chat_area.setAcceptRichText(True)
        self.chat_area.setHtml("<html><body style='font-family: Arial, sans-serif; font-size: 14px;'></body></html>")
        
        # 设置链接点击回调
        self.chat_area.set_anchor_clicked_callback(self.handle_chat_link_clicked)
        
        # 启用鼠标跟踪
        self.chat_area.setMouseTracking(True)
        # 安装事件过滤器
        self.chat_area.viewport().installEventFilter(self)
        
        chat_layout.addWidget(chat_label)
        chat_layout.addWidget(self.chat_area)
        
        parent_splitter.addWidget(chat_container)
    
    def eventFilter(self, obj, event):
        """事件过滤器"""
        from PyQt6.QtCore import QEvent
        if obj is self.chat_area.viewport() and event.type() == QEvent.Type.MouseMove:
            # 获取鼠标位置
            pos = event.pos()
            # 转换为相对于chat_area的位置
            cursor = self.chat_area.cursorForPosition(pos)
            
            # 检查是否在链接上
            char_format = cursor.charFormat()
            if char_format.isAnchor():
                href = char_format.anchorHref()
                if href and (href == "confirm:yes" or href == "confirm:no"):
                    # 设置为手形光标
                    obj.setCursor(Qt.CursorShape.PointingHandCursor)
                    return True
            
            # 恢复默认光标
            obj.unsetCursor()
        return super().eventFilter(obj, event)
    
    def handle_chat_link_clicked(self, href: str):
        """处理聊天区域链接点击"""
        if href == "confirm:yes":
            self.handle_elicitation_response(True)
        elif href == "confirm:no":
            self.handle_elicitation_response(False)
        
    def create_task_area(self, parent_splitter):
        """创建任务显示区域"""
        task_container = QWidget()
        task_layout = QVBoxLayout(task_container)
        task_layout.setContentsMargins(0, 0, 0, 0)
        task_layout.setSpacing(10)
        
        task_label = QLabel("当前正在做的事")
        task_label.setFont(ModernStyle.HEADING_FONT)
        task_label.setStyleSheet(f"color: {ModernStyle.SECONDARY_TEXT_COLOR};")
        
        self.task_area = QTextEdit()
        self.task_area.setReadOnly(True)
        self.task_area.setFont(ModernStyle.TEXT_FONT)
        self.task_area.setMaximumHeight(200)
        self.task_area.setMinimumHeight(150)
        
        task_layout.addWidget(task_label)
        task_layout.addWidget(self.task_area)
        
        parent_splitter.addWidget(task_container)
        
    def create_input_area(self, parent_layout):
        """创建输入区域"""
        input_frame = QFrame()
        input_frame.setFrameShape(QFrame.Shape.NoFrame)
        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(10)
        
        input_label = QLabel("输入指令")
        input_label.setFont(ModernStyle.HEADING_FONT)
        input_label.setStyleSheet(f"color: {ModernStyle.SECONDARY_TEXT_COLOR};")
        
        input_container = QWidget()
        input_container_layout = QHBoxLayout(input_container)
        input_container_layout.setContentsMargins(0, 0, 0, 0)
        input_container_layout.setSpacing(10)
        
        self.input_field = QLineEdit()
        self.input_field.setFont(ModernStyle.TEXT_FONT)
        self.input_field.setPlaceholderText("请输入您的指令...")
        self.input_field.returnPressed.connect(self.on_send)
        
        # 创建发送按钮，使用图标代替文字
        self.send_button = QPushButton()
        self.send_button.setIcon(QIcon.fromTheme("mail-send"))  # 使用系统图标
        self.send_button.setIconSize(QSize(24, 24))
        self.send_button.setMinimumWidth(48)
        self.send_button.setMaximumWidth(48)
        self.send_button.clicked.connect(self.on_send)
        self.send_button.setToolTip("发送指令")
        
        # 按钮状态管理
        self.is_executing = False
        
        # 按钮样式设置
        self.send_button.setStyleSheet("""
            QPushButton {
                border: 2px solid #2196F3;
                border-radius: 20px;
                background-color: white;
                padding: 5px;
                transition: all 0.3s ease;
            }
            QPushButton:hover {
                background-color: #E3F2FD;
                transform: scale(1.05);
            }
            QPushButton:pressed {
                background-color: #BBDEFB;
                transform: scale(0.95);
            }
            QPushButton:disabled {
                border: 2px solid #BDBDBD;
                background-color: #F5F5F5;
            }
        """)
        
        input_container_layout.addWidget(self.input_field, 1)
        input_container_layout.addWidget(self.send_button)
        
        input_layout.addWidget(input_label)
        input_layout.addWidget(input_container)
        
        parent_layout.addWidget(input_frame)
        
    def on_model_changed(self, model_name):
        """模型选择改变"""
        self.logger.info(f"模型已更改为: {model_name}")
        
    def on_send(self):
        """发送按钮点击"""
        if self.is_executing:
            # 如果正在执行，中断执行
            self.is_executing = False
            self.send_button.setIcon(QIcon.fromTheme("mail-send"))
            self.send_button.setToolTip("发送指令")
            # 恢复按钮样式
            self.send_button.setStyleSheet("""
                QPushButton {
                    border: 2px solid #2196F3;
                    border-radius: 20px;
                    background-color: white;
                    padding: 5px;
                    transition: all 0.3s ease;
                }
                QPushButton:hover {
                    background-color: #E3F2FD;
                    transform: scale(1.05);
                }
                QPushButton:pressed {
                    background-color: #BBDEFB;
                    transform: scale(0.95);
                }
                QPushButton:disabled {
                    border: 2px solid #BDBDBD;
                    background-color: #F5F5F5;
                }
            """)
            # 发送中断信号
            if hasattr(self, 'interrupt_callback') and self.interrupt_callback:
                self.interrupt_callback()
        else:
            # 如果不在执行，开始新任务
            user_input = self.input_field.text().strip()
            if user_input:
                self.input_field.clear()
                # 清空任务历史和显示区域，准备显示新任务
                self.task_history = []
                self.task_area.clear()
                # 切换按钮状态为停止图标
                self.is_executing = True
                self.send_button.setIcon(QIcon.fromTheme("process-stop"))
                self.send_button.setToolTip("停止执行")
                # 添加繁忙状态样式
                self.send_button.setStyleSheet("""
                    QPushButton {
                        border: 2px solid #FF5722;
                        border-radius: 20px;
                        background-color: #FFF3E0;
                        padding: 5px;
                        transition: all 0.3s ease;
                        animation: pulse 1.5s infinite;
                    }
                    QPushButton:hover {
                        background-color: #FFE0B2;
                        transform: scale(1.05);
                    }
                    QPushButton:pressed {
                        background-color: #FFCC80;
                        transform: scale(0.95);
                    }
                    @keyframes pulse {
                        0% { box-shadow: 0 0 0 0 rgba(255, 87, 34, 0.7); }
                        70% { box-shadow: 0 0 0 10px rgba(255, 87, 34, 0); }
                        100% { box-shadow: 0 0 0 0 rgba(255, 87, 34, 0); }
                    }
                """)
                if self.user_input_callback:
                    self.user_input_callback(user_input)
                
    def set_user_input_callback(self, callback):
        """设置用户输入回调"""
        self.user_input_callback = callback
    
    def set_interrupt_callback(self, callback):
        """设置中断回调"""
        self.interrupt_callback = callback
        
    def add_message(self, sender: str, message: str, thinking: str = None):
        """添加消息到聊天区域
        
        Args:
            sender: 发送者名称
            message: 消息内容
            thinking: 思考过程（可选）
        """
        # 确保消息内容正确
        if not message:
            return
        
        # 生成消息ID
        import time
        message_id = f"msg_{int(time.time() * 1000)}"
        
        # 处理消息中的图片URL
        processed_message = self.process_images_in_message(message, message_id)
        
        # 清空现有内容，重新构建HTML
        current_html = self.chat_area.toHtml()
        
        # 确保HTML结构正确
        if "</body>" not in current_html:
            current_html = "<html><body style='font-family: Arial, sans-serif; font-size: 14px;'></body></html>"
        
        # 处理消息内容中的换行符，确保在HTML中正确显示
        # 首先将消息内容中的HTML特殊字符转义，然后将换行符转换为<br>标签
        import html
        processed_message = html.escape(processed_message)
        # 将换行符转换为HTML换行标签
        processed_message = processed_message.replace('\n', '<br>')
        
        # 处理思考过程
        thinking_html = ""
        if thinking:
            processed_thinking = html.escape(thinking)
            processed_thinking = processed_thinking.replace('\n', '<br>')
            thinking_html = f"<div style='margin-top: 8px;'>"
            thinking_html += f"<details>"
            thinking_html += f"<summary style='cursor: pointer; color: #757575; font-size: 12px; font-weight: bold;'>💭 查看思考过程</summary>"
            thinking_html += f"<div style='margin-top: 8px; padding: 8px; background-color: #F5F5F5; border-radius: 5px; font-size: 12px; color: #616161;'>{processed_thinking}</div>"
            thinking_html += f"</details>"
            thinking_html += f"</div>"
        
        # 创建新消息的HTML
        message_html = ""
        if sender == "用户":
            # 用户消息：右对齐
            message_html = f"<div style='margin: 5px 0;'>"
            message_html += f"<div style='color: #2196F3; font-weight: bold; text-align: right; margin-bottom: 3px;'>用户:</div>"
            message_html += f"<div style='text-align: right; padding: 8px; max-width: 80%; margin-left: auto;'>{thinking_html}{processed_message}</div>"
            message_html += "</div>"
        elif sender == "系统":
            # 系统消息：左对齐
            message_html = f"<div style='margin: 5px 0;'>"
            message_html += f"<div style='color: #4CAF50; font-weight: bold; text-align: left; margin-bottom: 3px;'>系统:</div>"
            message_html += f"<div style='text-align: left; padding: 8px; max-width: 80%; margin-right: auto;'>{thinking_html}{processed_message}</div>"
            message_html += "</div>"
        elif sender == "系统确认":
            # 系统确认消息：左对齐，橙色高亮
            message_html = f"<div style='margin: 5px 0;'>"
            message_html += f"<div style='color: #FF9800; font-weight: bold; text-align: left; margin-bottom: 3px;'>⚠️ 系统确认:</div>"
            message_html += f"<div style='text-align: left; padding: 12px; background-color: #FFF3E0; border-radius: 10px; max-width: 80%; margin-right: auto; border-left: 4px solid #FF9800;'>{thinking_html}{processed_message}</div>"
            message_html += "</div>"
        else:
            # 其他消息：左对齐
            message_html = f"<div style='margin: 5px 0;'>"
            message_html += f"<div style='color: #757575; font-weight: bold; text-align: left; margin-bottom: 3px;'>{sender}:</div>"
            message_html += f"<div style='text-align: left; padding: 8px; max-width: 80%; margin-right: auto;'>{thinking_html}{processed_message}</div>"
            message_html += "</div>"
        
        # 将新消息插入到HTML中
        new_html = current_html.replace("</body>", message_html + "</body>")
        
        # 设置新的HTML内容
        self.chat_area.setHtml(new_html)
        
        # 确保滚动到底部
        self.chat_area.moveCursor(QTextCursor.MoveOperation.End)
    
    def start_stream_message(self, sender: str, initial_message: str = "", thinking: str = None):
        """开始一个新的流式消息
        
        Args:
            sender: 发送者名称
            initial_message: 初始消息内容
            thinking: 思考过程（可选）
        """
        # 结束之前的流式消息
        if self.end_stream_message():
            pass
        
        # 生成新的消息ID
        import time
        self.stream_message_id = f"stream_{int(time.time() * 1000)}"
        self.stream_message_sender = sender
        self.stream_message_thinking = thinking or ""
        
        # 处理消息中的图片URL
        processed_message = self.process_images_in_message(initial_message, self.stream_message_id)
        
        # 创建初始消息HTML
        import html
        processed_message = html.escape(processed_message)
        processed_message = processed_message.replace('\n', '<br>')
        
        # 创建消息容器
        message_html = f"<div id='{self.stream_message_id}' style='margin: 5px 0;'>"
        
        # 根据发送者设置样式
        if sender == "用户":
            message_html += f"<div style='color: #2196F3; font-weight: bold; text-align: right; margin-bottom: 3px;'>用户:</div>"
            message_html += f"<div style='text-align: right; padding: 8px; max-width: 80%; margin-left: auto;'>"
        elif sender == "系统":
            message_html += f"<div style='color: #4CAF50; font-weight: bold; text-align: left; margin-bottom: 3px;'>系统:</div>"
            message_html += f"<div style='text-align: left; padding: 8px; max-width: 80%; margin-right: auto;'>"
        elif sender == "系统确认":
            message_html += f"<div style='color: #FF9800; font-weight: bold; text-align: left; margin-bottom: 3px;'>⚠️ 系统确认:</div>"
            message_html += f"<div style='text-align: left; padding: 12px; background-color: #FFF3E0; border-radius: 10px; max-width: 80%; margin-right: auto; border-left: 4px solid #FF9800;'>"
        else:
            message_html += f"<div style='color: #757575; font-weight: bold; text-align: left; margin-bottom: 3px;'>{sender}:</div>"
            message_html += f"<div style='text-align: left; padding: 8px; max-width: 80%; margin-right: auto;'>"
        
        # 添加聊天内容容器
        message_html += f"<div id='{self.stream_message_id}_content'>{processed_message}</div>"
        message_html += "</div></div>"
        
        # 添加到聊天区域
        current_html = self.chat_area.toHtml()
        if "</body>" not in current_html:
            current_html = "<html><body style='font-family: Arial, sans-serif; font-size: 14px;'></body></html>"
        
        new_html = current_html.replace("</body>", message_html + "</body>")
        self.chat_area.setHtml(new_html)
        
        # 强制刷新UI，确保文档完全渲染
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        
        # 保存游标位置用于后续更新
        # 1. 保存聊天内容的游标位置（移动到文档末尾）
        self.chat_area.moveCursor(QTextCursor.MoveOperation.End)
        self.stream_message_cursor = self.chat_area.textCursor()
        
        # 2. 保存思考过程内容的游标位置（使用更简单的方法）
        # 直接保存思考过程的完整内容，后续更新时直接替换
        self.stream_message_thinking = thinking or ""
    
    def update_stream_message(self, message: str, thinking: str = None):
        """更新流式消息内容
        
        Args:
            message: 新的消息内容
            thinking: 思考过程（可选）
        """
        print(f"[DEBUG] update_stream_message 被调用: message='{message}', thinking='{thinking}'")
        
        if self.stream_message_id is None:
            # 如果没有流式消息，开始一个新的
            print(f"[DEBUG] stream_message_id 为 None，开始新的流式消息")
            self.start_stream_message(self.stream_message_sender or "系统", message, thinking)
            return
        
        # 保存思考过程（但不显示）
        if thinking:
            print(f"[DEBUG] 保存思考过程: '{thinking}'")
            self.stream_message_thinking += thinking
            print(f"[DEBUG] 思考过程长度: {len(self.stream_message_thinking)}")
        
        # 更新聊天内容
        if message:
            print(f"[DEBUG] 更新聊天内容: '{message}'")
            # 处理消息中的图片URL
            processed_message = self.process_images_in_message(message, self.stream_message_id)
            
            # 使用保存的游标位置来插入新内容
            if self.stream_message_cursor is not None:
                # 使用保存的游标
                cursor = QTextCursor(self.stream_message_cursor)
                cursor.movePosition(QTextCursor.MoveOperation.End)
                
                # 插入新内容（使用 insertHtml 保持格式一致）
                import html
                processed_message = html.escape(processed_message)
                processed_message = processed_message.replace('\n', '<br>')
                cursor.insertHtml(processed_message)
                
                # 更新保存的游标位置
                self.stream_message_cursor = QTextCursor(cursor)
                
                # 确保滚动到底部
                self.chat_area.ensureCursorVisible()
                
                # 强制刷新 UI
                from PyQt6.QtWidgets import QApplication
                QApplication.processEvents()
            else:
                # 如果没有保存的游标，移动到文档末尾
                cursor = QTextCursor(self.chat_area.document())
                cursor.movePosition(QTextCursor.MoveOperation.End)
                
                # 插入新内容
                import html
                processed_message = html.escape(processed_message)
                processed_message = processed_message.replace('\n', '<br>')
                cursor.insertHtml(processed_message)
                
                # 确保滚动到底部
                self.chat_area.ensureCursorVisible()
                
                # 强制刷新 UI
                from PyQt6.QtWidgets import QApplication
                QApplication.processEvents()
    
    def end_stream_message(self):
        """结束当前的流式消息
        
        Returns:
            bool: 是否成功结束（如果有流式消息）
        """
        if self.stream_message_id is None:
            return False
        
        # 重置流式消息状态
        self.stream_message_id = None
        self.stream_message_cursor = None
        self.stream_message_sender = None
        self.stream_message_thinking = None
        return True
    
    def add_elicitation_message(self, message: str, callback: Callable[[bool], None]):
        """添加交互式确认消息到聊天区域"""
        # 确保消息内容正确
        if not message:
            return
        
        # 保存回调函数
        self.elicitation_callback = callback
        # 重置处理标志
        self.elicitation_handled = False
        
        # 清空现有内容，重新构建HTML
        current_html = self.chat_area.toHtml()
        
        # 确保HTML结构正确
        if "</body>" not in current_html:
            current_html = "<html><body style='font-family: Arial, sans-serif; font-size: 14px;'></body></html>"
        
        # 创建交互式确认消息的HTML
        message_html = f"<div style='margin: 5px 0;'>"
        message_html += f"<div style='color: #FF9800; font-weight: bold; text-align: left; margin-bottom: 3px;'>⚠️ 系统确认:</div>"
        message_html += f"<div style='text-align: left; padding: 12px; background-color: #FFF3E0; border-radius: 10px; max-width: 80%; margin-right: auto; border-left: 4px solid #FF9800; white-space: pre-wrap;'>"
        message_html += f"<div style='margin-bottom: 8px;'>{message}</div>"
        message_html += f"<div style='margin-top: 8px;'>"
        message_html += f"<a href='confirm:yes' style='display: inline-block; padding: 8px 16px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 6px; margin-right: 8px; border: 2px solid #388E3C; font-weight: bold; cursor: pointer;'>✅ 确认执行</a>"
        message_html += f"<a href='confirm:no' style='display: inline-block; padding: 8px 16px; background-color: #F44336; color: white; text-decoration: none; border-radius: 6px; border: 2px solid #D32F2F; font-weight: bold; cursor: pointer;'>❌ 取消执行</a>"
        message_html += f"</div>"
        message_html += f"</div>"
        message_html += "</div>"
        
        # 将新消息插入到HTML中
        new_html = current_html.replace("</body>", message_html + "</body>")
        
        # 设置新的HTML内容
        self.chat_area.setHtml(new_html)
        
        # 确保滚动到底部
        self.chat_area.moveCursor(QTextCursor.MoveOperation.End)
    
    def handle_elicitation_response(self, confirmed: bool):
        """处理elicitation响应"""
        # 检查是否已经处理过
        if self.elicitation_handled:
            return
        
        # 标记为已处理
        self.elicitation_handled = True
        
        # 清除回调函数
        callback = self.elicitation_callback
        self.elicitation_callback = None
        
        # 调用回调函数
        if callback:
            callback(confirmed)
        
        # 在聊天区域显示用户选择
        if confirmed:
            self.add_message("系统", "✅ 用户确认：允许执行")
        else:
            self.add_message("系统", "❌ 用户取消：拒绝执行")
    
    def update_task(self, task_info: Dict[str, Any]):
        """更新任务显示区域"""
        description = task_info.get("description", "")
        tool = task_info.get("tool", "")
        status = task_info.get("status", "")
        progress = task_info.get("progress", None)
        result = task_info.get("result", None)
        
        # 检查是否是有效的任务信息
        if not description and not tool and not status and progress is None and result is None:
            return
        
        # 检查是否是日志信息（特殊处理）
        is_log_message = status == "日志"
        
        # 添加到任务历史（去重）
        task_record = {
            "description": description,
            "tool": tool,
            "status": status,
            "progress": progress,
            "result": result
        }
        
        # 检查是否与最后一条记录重复
        if self.task_history:
            last_task = self.task_history[-1]
            if (last_task.get("description") == description and
                last_task.get("tool") == tool and
                last_task.get("status") == status and
                last_task.get("progress") == progress and
                last_task.get("result") == result):
                return  # 重复记录，跳过
        
        # 添加到历史
        self.task_history.append(task_record)
        
        # 不再限制历史记录数量
        # if len(self.task_history) > 10:
        #     self.task_history = self.task_history[-10:]
        
        # 重建显示内容
        self.task_area.clear()
        self.task_area.moveCursor(QTextCursor.MoveOperation.End)
        
        # 显示所有历史记录
        for i, task in enumerate(self.task_history):
            task_description = task.get("description", "")
            task_tool = task.get("tool", "")
            task_status = task.get("status", "")
            task_progress = task.get("progress", None)
            task_result = task.get("result", None)
            
            # 显示主要描述
            if task_description:
                if i > 0:
                    # 在步骤之间添加分隔线，不添加空行
                    self.task_area.insertHtml('<hr style="border: 1px solid #E0E0E0; margin: 5px 0;">')
                
                # 根据内容类型选择不同颜色
                if "错误" in task_description:
                    color = ModernStyle.ERROR_COLOR
                elif "成功" in task_description:
                    color = ModernStyle.SUCCESS_COLOR
                elif "警告" in task_description:
                    color = ModernStyle.WARNING_COLOR
                else:
                    color = ModernStyle.PRIMARY_COLOR
                
                self.task_area.insertHtml(f'<p style="color: {color}; font-weight: bold; font-size: 14px; margin: 0;">{task_description}</p>')
            
            # 显示工具信息
            if task_tool:
                self.task_area.insertHtml(f'<p style="color: {ModernStyle.SECONDARY_TEXT_COLOR}; margin: 2px 0; font-size: 13px;">🔧 工具: {task_tool}</p>')
            
            # 显示状态信息
            if task_status:
                status_color = ModernStyle.SUCCESS_COLOR if "成功" in task_status or "完成" in task_status else ModernStyle.WARNING_COLOR
                self.task_area.insertHtml(f'<p style="color: {status_color}; margin: 2px 0; font-size: 13px;">📊 状态: {task_status}</p>')
            
            # 显示进度信息
            if task_progress is not None:
                self.task_area.insertHtml(f'<p style="color: {ModernStyle.SECONDARY_TEXT_COLOR}; margin: 2px 0; font-size: 13px;">⏳ 进度: {task_progress}%</p>')
            
            # 显示结果信息
            if task_result:
                # 尝试解析结果
                try:
                    if isinstance(task_result, dict):
                        # 检查是否是工具响应格式：{"type": "tool_response", "result": {...}}
                        if "type" in task_result and task_result["type"] == "tool_response" and "result" in task_result:
                            # 提取真正的结果
                            actual_result = task_result["result"]
                            if isinstance(actual_result, dict):
                                # 检查是否是文件或文件夹已存在的情况
                                is_exists = False
                                if "result" in actual_result:
                                    is_exists = "已存在" in actual_result["result"]
                                elif "error" in actual_result:
                                    is_exists = "已存在" in actual_result["error"]
                                
                                if actual_result.get("success") or is_exists:
                                    success_msg = actual_result.get("result", "执行成功")
                                    path = actual_result.get("path", "")
                                    self.task_area.insertHtml(f'<p style="color: {ModernStyle.SUCCESS_COLOR}; margin: 2px 0; font-size: 13px;">✅ 结果: {success_msg}</p>')
                                    if path:
                                        self.task_area.insertHtml(f'<p style="color: {ModernStyle.SECONDARY_TEXT_COLOR}; margin: 2px 0; font-size: 13px;">📁 路径: {path}</p>')
                                else:
                                    error_msg = actual_result.get("error", "执行失败")
                                    self.task_area.insertHtml(f'<p style="color: {ModernStyle.ERROR_COLOR}; margin: 2px 0; font-size: 13px;">❌ 错误: {error_msg}</p>')
                            else:
                                # 如果是其他类型，直接显示
                                self.task_area.insertHtml(f'<p style="color: {ModernStyle.SECONDARY_TEXT_COLOR}; margin: 2px 0; font-size: 13px;">📋 结果: {str(actual_result)}</p>')
                        else:
                            # 如果是其他字典格式，直接检查 success 字段
                            if task_result.get("success"):
                                success_msg = task_result.get("result", "执行成功")
                                path = task_result.get("path", "")
                                self.task_area.insertHtml(f'<p style="color: {ModernStyle.SUCCESS_COLOR}; margin: 2px 0; font-size: 13px;">✅ 结果: {success_msg}</p>')
                                if path:
                                    self.task_area.insertHtml(f'<p style="color: {ModernStyle.SECONDARY_TEXT_COLOR}; margin: 2px 0; font-size: 13px;">📁 路径: {path}</p>')
                            else:
                                error_msg = task_result.get("error", "执行失败")
                                self.task_area.insertHtml(f'<p style="color: {ModernStyle.ERROR_COLOR}; margin: 2px 0; font-size: 13px;">❌ 错误: {error_msg}</p>')
                    else:
                        # 如果是其他类型，直接显示
                        self.task_area.insertHtml(f'<p style="color: {ModernStyle.SECONDARY_TEXT_COLOR}; margin: 2px 0; font-size: 13px;">📋 结果: {str(task_result)}</p>')
                except:
                    # 如果解析失败，直接显示
                    self.task_area.insertHtml(f'<p style="color: {ModernStyle.SECONDARY_TEXT_COLOR}; margin: 2px 0; font-size: 13px;">📋 结果: {str(task_result)}</p>')
        
        # 确保滚动到底部
        self.task_area.moveCursor(QTextCursor.MoveOperation.End)
            
    def update_system_status(self, status_info: Dict[str, Any]):
        """更新系统状态显示"""
        # 只在初始启动时显示系统状态，不覆盖任务执行过程
        # 检查是否是初始启动（任务历史为空）
        if not self.task_history:
            self.task_area.clear()
            self.task_area.moveCursor(QTextCursor.MoveOperation.End)
            
            # 标题
            self.task_area.insertHtml(f'<h3 style="color: {ModernStyle.PRIMARY_COLOR}; margin: 10px 0;">📋 系统状态</h3>')
            
            # 系统状态
            system_status = status_info.get("status", "就绪")
            status_color = ModernStyle.SUCCESS_COLOR if "就绪" in system_status else ModernStyle.WARNING_COLOR
            self.task_area.insertHtml(f'<p style="color: {status_color}; margin: 5px 0;">🔄 系统状态: {system_status}</p>')
            
            # 当前模型
            current_model = status_info.get("model", "未知")
            self.task_area.insertHtml(f'<p style="color: {ModernStyle.TEXT_COLOR}; margin: 5px 0;">🤖 当前模型: {current_model}</p>')
            
            # 连接状态
            connected = status_info.get("connected", False)
            conn_status = "已连接" if connected else "未连接"
            conn_color = ModernStyle.SUCCESS_COLOR if connected else ModernStyle.ERROR_COLOR
            self.task_area.insertHtml(f'<p style="color: {conn_color}; margin: 5px 0;">🔗 服务器连接: {conn_status}</p>')
            
            # 可用工具
            tools = status_info.get("tools", [])
            if tools:
                self.task_area.insertHtml(f'<p style="color: {ModernStyle.TEXT_COLOR}; margin: 5px 0;">🛠️ 可用工具: {" ".join(tools)}</p>')
            
    def clear_task(self):
        """清空任务显示区域"""
        self.task_area.clear()
        
    def show_message(self, title: str, message: str):
        """显示消息对话框"""
        QMessageBox.information(self, title, message)
        
    def show_error(self, title: str, message: str):
        """显示错误对话框"""
        QMessageBox.critical(self, title, message)
        
    def show_loading(self, message: str = "正在处理..."):
        """显示加载状态"""
        self.loading_label.setText(message)
        
    def hide_loading(self):
        """隐藏加载状态"""
        self.loading_label.setText("")
        
    def update_status(self, status: str):
        """更新状态栏"""
        self.status_label.setText(f"状态: {status}")
        # 如果状态变为就绪，恢复按钮状态
        if status == "就绪" and self.is_executing:
            self.is_executing = False
            self.send_button.setIcon(QIcon.fromTheme("mail-send"))
            self.send_button.setToolTip("发送指令")
            # 恢复按钮样式
            self.send_button.setStyleSheet("""
                QPushButton {
                    border: 2px solid #2196F3;
                    border-radius: 20px;
                    background-color: white;
                    padding: 5px;
                    transition: all 0.3s ease;
                }
                QPushButton:hover {
                    background-color: #E3F2FD;
                    transform: scale(1.05);
                }
                QPushButton:pressed {
                    background-color: #BBDEFB;
                    transform: scale(0.95);
                }
                QPushButton:disabled {
                    border: 2px solid #BDBDBD;
                    background-color: #F5F5F5;
                }
            """)
        
    def show_progress(self, visible: bool, value: int):
        """显示/隐藏进度条"""
        if visible:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(value)
        else:
            self.progress_bar.setVisible(False)
    
    def download_image(self, url: str, message_id: str = None, image_id: str = None):
        """下载图片
        
        Args:
            url: 图片URL
            message_id: 消息ID（用于标识图片属于哪条消息）
            image_id: 图片ID（用于标识图片）
        """
        if not url or not url.startswith(('http://', 'https://')):
            return
        
        # 生成唯一ID
        if message_id is None:
            message_id = self.stream_message_id or "default"
        if image_id is None:
            import time
            image_id = f"img_{int(time.time() * 1000)}"
        
        # 记录待下载的图片
        self.pending_images[url] = (message_id, image_id)
        
        try:
            # 创建网络请求
            request = QNetworkRequest(QUrl(url))
            request.setTransferTimeout(self.image_timeout)
            
            # 发起下载请求
            reply = self.network_manager.get(request)
            reply.setProperty("url", url)
            reply.setProperty("message_id", message_id)
            reply.setProperty("image_id", image_id)
            
            # 设置超时定时器（保存引用避免被垃圾回收）
            timeout_timer = QTimer()
            timeout_timer.setSingleShot(True)
            timeout_timer.setProperty("reply", reply)
            timeout_timer.setProperty("url", url)
            timeout_timer.setProperty("message_id", message_id)
            timeout_timer.setProperty("image_id", image_id)
            timeout_timer.timeout.connect(lambda: self.on_image_timeout(timeout_timer.property("reply"), timeout_timer.property("url"), timeout_timer.property("message_id"), timeout_timer.property("image_id")))
            timeout_timer.start(self.image_timeout)
            reply.setProperty("timeout_timer", timeout_timer)
        except Exception as e:
            self.logger.error(f"下载图片失败: {url}, 错误: {e}")
            # 从待下载列表中移除
            if url in self.pending_images:
                del self.pending_images[url]
            # 显示破损图标
            self.update_image_in_chat(message_id, image_id, None, failed=True)
    
    def on_image_downloaded(self, reply: QNetworkReply):
        """图片下载完成回调
        
        Args:
            reply: 网络回复对象
        """
        try:
            url = reply.property("url")
            message_id = reply.property("message_id")
            image_id = reply.property("image_id")
            timeout_timer = reply.property("timeout_timer")
            
            # 停止超时定时器
            if timeout_timer:
                timeout_timer.stop()
            
            # 从待下载列表中移除
            if url in self.pending_images:
                del self.pending_images[url]
            
            # 检查下载结果
            if reply.error() == QNetworkReply.NetworkError.NoError:
                # 下载成功
                image_data = reply.readAll()
                pixmap = QPixmap()
                if pixmap.loadFromData(image_data):
                    # 转换为base64编码
                    buffer = QBuffer()
                    buffer.open(QIODevice.OpenModeFlag.ReadWrite)
                    pixmap.save(buffer, "PNG")
                    image_base64 = buffer.data().toBase64().data().decode('utf-8')
                    buffer.close()
                    
                    # 更新聊天区域中的图片
                    self.update_image_in_chat(message_id, image_id, f"data:image/png;base64,{image_base64}")
                else:
                    # 图片加载失败，显示破损图标
                    self.logger.error(f"图片数据加载失败: {url}")
                    self.update_image_in_chat(message_id, image_id, None, failed=True)
            else:
                # 下载失败，显示破损图标
                self.logger.error(f"图片下载失败: {url}, 错误: {reply.errorString()}")
                self.update_image_in_chat(message_id, image_id, None, failed=True)
        except Exception as e:
            self.logger.error(f"处理下载的图片时出错: {e}", exc_info=True)
        finally:
            reply.deleteLater()
    
    def on_image_timeout(self, reply: QNetworkReply, url: str, message_id: str, image_id: str):
        """图片下载超时处理
        
        Args:
            reply: 网络回复对象
            url: 图片URL
            message_id: 消息ID
            image_id: 图片ID
        """
        # 取消下载
        reply.abort()
        
        # 从待下载列表中移除
        if url in self.pending_images:
            del self.pending_images[url]
        
        # 显示破损图标
        self.update_image_in_chat(message_id, image_id, None, failed=True)
    
    def update_image_in_chat(self, message_id: str, image_id: str, image_data: str = None, failed: bool = False):
        """更新聊天区域中的图片
        
        Args:
            message_id: 消息ID
            image_id: 图片ID
            image_data: 图片数据（base64编码的data URL）
            failed: 是否下载失败
        """
        if not message_id or not image_id:
            return
        
        # 创建破损图标
        if failed:
            # 加载本地破损图标
            import os
            broken_icon_path = os.path.join(os.path.dirname(__file__), 'resources', 'pictures', 'picture_load_fail.png')
            if os.path.exists(broken_icon_path):
                broken_pixmap = QPixmap(broken_icon_path)
                if not broken_pixmap.isNull():
                    # 转换为base64编码
                    buffer = QBuffer()
                    buffer.open(QIODevice.OpenModeFlag.ReadWrite)
                    broken_pixmap.save(buffer, "PNG")
                    broken_base64 = buffer.data().toBase64().data().decode('utf-8')
                    buffer.close()
                    image_data = f"data:image/png;base64,{broken_base64}"
        
        # 获取当前HTML
        current_html = self.chat_area.toHtml()
        
        # 替换占位符
        placeholder = f'{{IMG:{message_id}:{image_id}}}'
        if placeholder in current_html:
            # 插入图片标签（按原始比例显示，最大尺寸20px x 20px）
            img_tag = f'<img src="{image_data}" style="max-width: 20px; max-height: 20px; vertical-align: middle; margin: 0 5px;" />'
            current_html = current_html.replace(placeholder, img_tag)
            
            # 更新聊天区域
            self.chat_area.setHtml(current_html)
            
            # 确保滚动到底部
            self.chat_area.moveCursor(QTextCursor.MoveOperation.End)
        else:
            # 占位符不存在，可能是消息已经被更新了
            self.logger.warning(f"占位符不存在: {placeholder}")
    
    def process_images_in_message(self, message: str, message_id: str = None):
        """处理消息中的图片URL
        
        Args:
            message: 消息内容
            message_id: 消息ID
            
        Returns:
            str: 处理后的消息内容（图片URL替换为占位符）
        """
        if message_id is None:
            message_id = self.stream_message_id or "default"
        
        # 使用正则表达式匹配图片URL
        # 匹配 http:// 或 https:// 开头的URL，只匹配URL合法字符
        url_pattern = r'https?://[a-zA-Z0-9\-._~:/?#[\]@!$&\'()*+,;=%]+'
        
        # 查找所有URL
        urls = re.findall(url_pattern, message)
        
        self.logger.info(f"找到 {len(urls)} 个URL: {urls}")
        
        # 替换图片URL为占位符
        processed_message = message
        for i, url in enumerate(urls):
            # 清理URL：去掉URL后面的非URL字符（如中文标点、温度等）
            # URL应该以字母、数字、常见URL字符结尾
            # 找到第一个非URL字符的位置并截断
            cleaned_url = url
            for j, char in enumerate(url):
                # 检查字符是否是URL合法字符
                if not (char.isalnum() or char in '-._~:/?#[\\]@!$&\'()*+,;=%'):
                    cleaned_url = url[:j]
                    break
            
            # 检查是否是图片URL（通过扩展名或常见图片路径）
            is_image = False
            image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']
            for ext in image_extensions:
                if ext in cleaned_url.lower():
                    is_image = True
                    break
            
            # 如果URL中没有扩展名，但包含weather、img等关键词，也认为是图片
            if not is_image:
                image_keywords = ['weather', 'img', 'icon', 'picture', 'photo']
                for keyword in image_keywords:
                    if keyword in cleaned_url.lower():
                        is_image = True
                        break
            
            if is_image:
                image_id = f"img_{message_id}_{i}"
                placeholder = f'{{IMG:{message_id}:{image_id}}}'
                processed_message = processed_message.replace(url, placeholder)
                self.logger.info(f"替换图片URL: {url} -> {placeholder} (清理后: {cleaned_url})")
                
                # 下载图片
                self.download_image(cleaned_url, message_id, image_id)
        
        return processed_message
