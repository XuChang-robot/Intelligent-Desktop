# 主窗口界面

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QListWidget, QListWidgetItem, QLabel, QSplitter,
    QProgressBar, QMessageBox, QFrame, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QProperty, QEasingCurve
from PyQt6.QtGui import QFont, QColor, QMovie, QPainter, QColor as QtColor

class MainWindow(QMainWindow):
    """主窗口"""
    
    # 信号
    user_input_signal = pyqtSignal(str)
    elicitation_response_signal = pyqtSignal(bool)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("智能桌面系统")
        self.setGeometry(100, 100, 1000, 700)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 顶部标题
        title_label = QLabel("智能桌面系统")
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2196F3; padding: 10px;")
        main_layout.addWidget(title_label)
        
        # 分割器
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(2)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #ddd;
            }
            QSplitter::handle:hover {
                background-color: #2196F3;
            }
        """)
        
        # 聊天区域
        self.chat_area = QTextEdit()
        self.chat_area.setReadOnly(True)
        self.chat_area.setFont(QFont("Microsoft YaHei", 12))
        self.chat_area.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        splitter.addWidget(self.chat_area)
        
        # 任务展示区域
        self.task_area = QListWidget()
        self.task_area.setFont(QFont("Microsoft YaHei", 11))
        self.task_area.setMaximumHeight(150)
        self.task_area.setStyleSheet("""
            QListWidget {
                background-color: #fff;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 5px;
            }
            QListWidget::item {
                border-bottom: 1px solid #eee;
                padding: 5px;
            }
        """)
        splitter.addWidget(self.task_area)
        
        # 调整分割器大小，给输出框更多空间
        splitter.setSizes([500, 150])
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter, 1)  # 给聊天区域更多空间
        
        # 输入区域容器
        input_container = QFrame()
        input_container.setStyleSheet("""
            QFrame {
                background-color: #f9f9f9;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(5)
        
        # 输入框
        self.input_text = QTextEdit()
        self.input_text.setMaximumHeight(120)
        self.input_text.setMinimumHeight(60)
        self.input_text.setFont(QFont("Microsoft YaHei", 12))
        self.input_text.setPlaceholderText("请输入您的指令...")
        self.input_text.setStyleSheet("""
            QTextEdit {
                background-color: #fff;
                border: 1px solid #ddd;
                border-radius: 3px;
                padding: 8px;
            }
            QTextEdit:focus {
                border: 2px solid #2196F3;
            }
        """)
        input_layout.addWidget(self.input_text)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        self.send_button = QPushButton("发送")
        self.send_button.setFont(QFont("Microsoft YaHei", 12))
        self.send_button.setMaximumWidth(100)
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
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
                background-color: #ccc;
            }
        """)
        self.send_button.clicked.connect(self.on_send_clicked)
        button_layout.addWidget(self.send_button)
        
        button_layout.addStretch()
        
        input_layout.addLayout(button_layout)
        main_layout.addWidget(input_container)
        
        # 底部状态栏
        self.status_label = QLabel("就绪")
        self.status_label.setFont(QFont("Microsoft YaHei", 10))
        self.status_label.setStyleSheet("color: #666; padding: 5px;")
        self.statusBar().addWidget(self.status_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ddd;
                border-radius: 3px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                border-radius: 2px;
            }
        """)
        self.statusBar().addPermanentWidget(self.progress_bar)
        
        # 加载动画标签
        self.loading_label = QLabel()
        self.loading_label.setVisible(False)
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 200);
                border: 1px solid #2196F3;
                border-radius: 5px;
                padding: 10px 20px;
                color: #2196F3;
                font-weight: bold;
            }
        """)
        self.statusBar().addPermanentWidget(self.loading_label)
        
        # 创建加载动画
        self.loading_animation_timer = QTimer()
        self.loading_animation_timer.timeout.connect(self.update_loading_animation)
        self.loading_dots = 0
        
        # 确保窗口大小合适
        self.setMinimumSize(800, 600)
    
    def on_send_clicked(self):
        """发送按钮点击事件"""
        text = self.input_text.toPlainText().strip()
        if text:
            # 显示用户输入
            self.add_message("用户", text)
            
            # 清空输入框
            self.input_text.clear()
            
            # 发送信号
            self.user_input_signal.emit(text)
    
    def add_message(self, sender: str, message: str):
        """添加消息到聊天区域"""
        if sender == "用户":
            color = "#4CAF50"
            background = "#e8f5e9"
        elif sender == "系统":
            color = "#2196F3"
            background = "#e3f2fd"
        else:
            color = "#9E9E9E"
            background = "#f5f5f5"
        
        html = f"<div style='margin: 10px 0; background-color: {background}; padding: 10px; border-radius: 5px;'>"
        html += f"<strong style='color: {color}; font-size: 14px;'>{sender}:</strong>"
        html += f"<p style='margin: 5px 0; color: #333; line-height: 1.6;'>{message}</p>"
        html += "</div>"
        
        self.chat_area.append(html)
        # 滚动到底部
        self.chat_area.verticalScrollBar().setValue(
            self.chat_area.verticalScrollBar().maximum()
        )
    
    def add_task(self, task: dict):
        """添加任务到任务列表"""
        item = QListWidgetItem()
        item_widget = TaskItemWidget(task)
        item.setSizeHint(item_widget.sizeHint())
        self.task_area.addItem(item)
        self.task_area.setItemWidget(item, item_widget)
    
    def update_status(self, status: str):
        """更新状态栏"""
        self.status_label.setText(status)
    
    def show_progress(self, visible: bool, value: int = 0):
        """显示/隐藏进度条"""
        self.progress_bar.setVisible(visible)
        if visible:
            self.progress_bar.setValue(value)
    
    def show_loading(self, visible: bool, message: str = "正在处理..."):
        """显示/隐藏加载动画"""
        if visible:
            self.loading_label.setText(f"⏳ {message}")
            self.loading_label.setVisible(True)
            self.loading_dots = 0
            self.loading_animation_timer.start(500)
            self.input_text.setEnabled(False)
            self.send_button.setEnabled(False)
        else:
            self.loading_label.setVisible(False)
            self.loading_animation_timer.stop()
            self.input_text.setEnabled(True)
            self.send_button.setEnabled(True)
            self.input_text.setFocus()
    
    def update_loading_animation(self):
        """更新加载动画"""
        self.loading_dots = (self.loading_dots + 1) % 4
        dots = "." * self.loading_dots
        self.loading_label.setText(f"⏳ 正在处理{dots}")
    
    def show_elicitation(self, message: str):
        """显示二次确认对话框"""
        reply = QMessageBox.question(
            self,
            "安全确认",
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        self.elicitation_response_signal.emit(reply == QMessageBox.Yes)

class TaskItemWidget(QWidget):
    """任务项组件"""
    
    def __init__(self, task: dict):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # 任务描述
        description = task.get("description", "")
        tool = task.get("tool", "")
        
        title_label = QLabel(f"📋 {description}")
        title_label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        title_label.setStyleSheet("color: #333;")
        layout.addWidget(title_label)
        
        # 工具信息
        tool_label = QLabel(f"🔧 工具: {tool}")
        tool_label.setFont(QFont("Microsoft YaHei", 10))
        tool_label.setStyleSheet("color: #666;")
        layout.addWidget(tool_label)
        
        # 参数信息
        args = task.get("args", {})
        if args:
            args_text = "📝 参数: " + ", ".join([f"{k}={v}" for k, v in args.items()])
            args_label = QLabel(args_text)
            args_label.setFont(QFont("Microsoft YaHei", 10))
            args_label.setStyleSheet("color: #999;")
            args_label.setWordWrap(True)
            layout.addWidget(args_label)
        
        # 状态指示器
        status_label = QLabel("⏳ 待执行")
        status_label.setFont(QFont("Microsoft YaHei", 9))
        status_label.setStyleSheet("color: #FF9800; padding: 3px 8px; background-color: #FFF3E0; border-radius: 3px;")
        layout.addWidget(status_label)
