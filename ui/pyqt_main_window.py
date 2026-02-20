# 主窗口界面 (PyQt6版本)

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QTextEdit, QLineEdit, QPushButton, 
                               QComboBox, QFrame, QSplitter, QScrollArea,
                               QSizePolicy, QMessageBox, QProgressBar, QStatusBar)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl, QSize
from PyQt6.QtGui import QFont, QColor, QPalette, QTextCursor, QTextDocument, QIcon
from typing import Dict, Any, Optional, Callable
import logging

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
        
        # 清空现有内容，重新构建HTML
        current_html = self.chat_area.toHtml()
        
        # 确保HTML结构正确
        if "</body>" not in current_html:
            current_html = "<html><body style='font-family: Arial, sans-serif; font-size: 14px;'></body></html>"
        
        # 处理消息内容中的换行符，确保在HTML中正确显示
        # 首先将消息内容中的HTML特殊字符转义，然后将换行符转换为<br>标签
        import html
        processed_message = html.escape(message)
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
            message_html += f"<div style='text-align: right; padding: 8px; max-width: 80%; margin-left: auto;'>{processed_message}{thinking_html}</div>"
            message_html += "</div>"
        elif sender == "系统":
            # 系统消息：左对齐
            message_html = f"<div style='margin: 5px 0;'>"
            message_html += f"<div style='color: #4CAF50; font-weight: bold; text-align: left; margin-bottom: 3px;'>系统:</div>"
            message_html += f"<div style='text-align: left; padding: 8px; max-width: 80%; margin-right: auto;'>{processed_message}{thinking_html}</div>"
            message_html += "</div>"
        elif sender == "系统确认":
            # 系统确认消息：左对齐，橙色高亮
            message_html = f"<div style='margin: 5px 0;'>"
            message_html += f"<div style='color: #FF9800; font-weight: bold; text-align: left; margin-bottom: 3px;'>⚠️ 系统确认:</div>"
            message_html += f"<div style='text-align: left; padding: 12px; background-color: #FFF3E0; border-radius: 10px; max-width: 80%; margin-right: auto; border-left: 4px solid #FF9800;'>{processed_message}{thinking_html}</div>"
            message_html += "</div>"
        else:
            # 其他消息：左对齐
            message_html = f"<div style='margin: 5px 0;'>"
            message_html += f"<div style='color: #757575; font-weight: bold; text-align: left; margin-bottom: 3px;'>{sender}:</div>"
            message_html += f"<div style='text-align: left; padding: 8px; max-width: 80%; margin-right: auto;'>{processed_message}{thinking_html}</div>"
            message_html += "</div>"
        
        # 将新消息插入到HTML中
        new_html = current_html.replace("</body>", message_html + "</body>")
        
        # 设置新的HTML内容
        self.chat_area.setHtml(new_html)
        
        # 确保滚动到底部
        self.chat_area.moveCursor(QTextCursor.MoveOperation.End)
    
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
