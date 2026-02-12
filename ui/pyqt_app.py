# UI主程序 (PyQt6版本)

import sys
import os
import asyncio
import logging
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QThread, pyqtSignal, QObject, QTimer, QEvent, QCoreApplication
from typing import Optional

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ui.pyqt_main_window import MainWindow, ModernStyle
from mcp_client.client import MCPClient
from config.config import load_config

class WorkerSignals(QObject):
    """工作线程信号"""
    message = pyqtSignal(str, str)
    task = pyqtSignal(dict)
    task_update = pyqtSignal(dict)
    status = pyqtSignal(str)
    progress = pyqtSignal(bool, int)
    loading = pyqtSignal(bool, str)
    model_list = pyqtSignal(list)
    system_status = pyqtSignal(dict)
    error = pyqtSignal(str)
    log = pyqtSignal(str)
    elicitation_request = pyqtSignal(str)

class TaskLogHandler(logging.Handler):
    """任务日志处理器"""
    
    def __init__(self, signals):
        super().__init__()
        self.signals = signals
        self.setLevel(logging.INFO)
        
    def emit(self, record):
        """发送日志记录"""
        if record.levelno >= logging.INFO:
            log_message = self.format(record)
            # 通过信号发送到UI
            self.signals.log.emit(log_message)

class WorkerThread(QThread):
    """工作线程"""
    
    def __init__(self, client: MCPClient):
        super().__init__()
        self.client = client
        self.signals = WorkerSignals()
        self.user_input_queue = asyncio.Queue()
        self.running = True
        self.logger = logging.getLogger(__name__)
        self.elicitation_future = None
        self.interrupted = False
        
        # 设置日志处理器
        self.setup_log_handler()
    
    def setup_log_handler(self):
        """设置日志处理器"""
        # 创建任务日志处理器
        task_handler = TaskLogHandler(self.signals)
        task_handler.setFormatter(logging.Formatter('%(message)s'))
        
        # 获取client的日志记录器
        client_logger = logging.getLogger('mcp_client')
        client_logger.setLevel(logging.INFO)
        client_logger.addHandler(task_handler)
        
        # 获取其他相关日志记录器
        llm_logger = logging.getLogger('mcp_client.llm')
        llm_logger.setLevel(logging.INFO)
        llm_logger.addHandler(task_handler)
    
    def run(self):
        """线程运行"""
        # 创建并运行事件循环
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._run())
        finally:
            self.loop.close()
    
    async def _run(self):
        """异步运行"""
        # 设置UI回调
        self.client.set_ui_callback(self.ui_callback)
        
        # 设置elicitation回调
        self.client.elicitation_callback = self._elicitation_callback
        
        # 连接到MCP Server
        connected = await self.client.connect()
        
        if not connected:
            self.signals.error.emit('无法连接到MCP Server')
            return
        
        # 发送初始系统状态
        self.emit_system_status()
        
        try:
            while self.running:
                # 处理用户输入
                try:
                    user_input = await asyncio.wait_for(
                        self.user_input_queue.get(),
                        timeout=0.1
                    )
                    await self.process_user_input(user_input)
                except asyncio.TimeoutError:
                    # 定期更新系统状态
                    self.emit_system_status()
        finally:
            await self.client.disconnect()
    
    def emit_system_status(self):
        """发送系统状态"""
        try:
            status_info = {
                "status": "就绪",
                "model": self.client.llm_client.get_current_model() if hasattr(self.client, 'llm_client') and self.client.llm_client else "未知",
                "connected": True,
                "tools": ["execute_python"]
            }
            self.signals.system_status.emit(status_info)
        except Exception as e:
            self.logger.error(f"发送系统状态失败: {e}")
    
    async def process_user_input(self, user_input: str):
        """处理用户输入"""
        # 更新UI状态
        self.signals.status.emit('处理中...')
        self.signals.progress.emit(True, 0)
        self.signals.loading.emit(True, '正在分析您的意图...')
        
        try:
            # 处理用户意图
            result = await self.client.process_user_intent(user_input)
            
            # 显示处理结果
            self.signals.loading.emit(True, '正在执行任务...')
            summary = result.get('summary', '')
            if summary:
                self.signals.message.emit('系统', summary)
            
            # 显示任务计划
            plan = result.get('plan', {})
            steps = plan.get('steps', [])
            for i, step in enumerate(steps):
                step_description = step.get('description', '')
                self.signals.loading.emit(True, f'正在执行: {step_description}')
                self.signals.task.emit(step)
                await asyncio.sleep(0.1)
                
        except Exception as e:
            self.signals.message.emit('系统', f'处理失败: {str(e)}')
            self.logger.error(f"处理用户输入失败: {e}", exc_info=True)
        finally:
            self.signals.status.emit('就绪')
            self.signals.progress.emit(False, 0)
            self.signals.loading.emit(False, '')
    
    def ui_callback(self, callback_type: str, *args):
        """UI回调"""
        if callback_type == 'message':
            sender, message = args
            self.signals.message.emit(sender, message)
        elif callback_type == 'task':
            task = args[0]
            self.signals.task.emit(task)
        elif callback_type == 'task_update':
            task = args[0]
            self.signals.task_update.emit(task)
        elif callback_type == 'status':
            status = args[0]
            self.signals.status.emit(status)
        elif callback_type == 'progress':
            visible, value = args
            self.signals.progress.emit(visible, value)
        elif callback_type == 'loading':
            if len(args) > 1:
                visible, message = args
            else:
                visible = args[0]
                message = "正在处理..."
            self.signals.loading.emit(visible, message)
    
    async def _elicitation_callback(self, message: str) -> bool:
        """MCP Client elicitation回调"""
        self.logger.info(f"收到elicitation请求: {message}")
        
        # 通过信号发送到主线程
        self.signals.elicitation_request.emit(message)
        
        # 创建future等待用户响应
        self.elicitation_future = self.loop.create_future()
        
        # 等待用户响应
        try:
            result = await asyncio.wait_for(self.elicitation_future, timeout=30.0)
            self.logger.info(f"用户响应已收到: {result}")
        except asyncio.TimeoutError:
            self.logger.error("用户响应超时，默认拒绝")
            result = False
        except Exception as e:
            self.logger.error(f"等待用户响应时出错: {e}")
            result = False
        
        return result
    
    def add_user_input(self, user_input: str):
        """添加用户输入"""
        async def put_input():
            await self.user_input_queue.put(user_input)
        
        # 使用WorkerThread线程的事件循环
        if hasattr(self, 'loop') and not self.loop.is_closed():
            asyncio.run_coroutine_threadsafe(put_input(), self.loop)
    
    def set_elicitation_result(self, result: bool):
        """设置elicitation结果"""
        if self.elicitation_future and not self.elicitation_future.done():
            self.elicitation_future.set_result(result)
    
    def interrupt(self):
        """中断执行"""
        self.logger.info("收到中断请求")
        self.interrupted = True
        # 通知客户端中断执行
        if hasattr(self.client, 'interrupt'):
            self.client.interrupt()
        # 取消当前的elicitation请求
        if self.elicitation_future and not self.elicitation_future.done():
            self.elicitation_future.cancel()
    
class App(QObject):
    """应用程序"""
    
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.app = QApplication(sys.argv)
        self.main_window = MainWindow()
        self.client = MCPClient()
        self.worker = None
        self.logger = logging.getLogger(__name__)
        
        # 应用现代化样式
        ModernStyle.apply_stylesheet(self.app)
        
    def run(self):
        """运行应用"""
        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        
        # 设置UI回调
        self.main_window.set_user_input_callback(self.on_user_input)
        # 设置中断回调
        self.main_window.set_interrupt_callback(self.on_interrupt)
        
        # 获取并设置可用模型列表
        self.update_model_list()
        
        # 添加欢迎消息
        self.main_window.add_message("系统", "欢迎使用智能桌面系统！请在下方输入您的指令。")
        
        # 创建并启动工作线程
        self.worker = WorkerThread(self.client)
        
        # 连接工作线程信号
        self.worker.signals.message.connect(self.on_message)
        self.worker.signals.task.connect(self.on_task)
        self.worker.signals.task_update.connect(self.on_task_update)
        self.worker.signals.status.connect(self.on_status)
        self.worker.signals.progress.connect(self.on_progress)
        self.worker.signals.loading.connect(self.on_loading)
        self.worker.signals.system_status.connect(self.on_system_status)
        self.worker.signals.error.connect(self.on_error)
        self.worker.signals.log.connect(self.on_log)
        self.worker.signals.elicitation_request.connect(self.on_elicitation_request)
        
        self.worker.start()
        
        # 显示主窗口
        self.main_window.show()
        
        # 运行应用
        sys.exit(self.app.exec())
    
    def update_model_list(self):
        """更新模型列表"""
        try:
            # 从LLM客户端获取可用模型
            if hasattr(self.client, 'llm_client') and self.client.llm_client:
                models = self.client.llm_client.get_available_models()
                
                # 更新UI下拉框
                if models:
                    # 确保当前模型在列表中
                    current_model = self.client.llm_client.get_current_model()
                    if current_model not in models and current_model:
                        models.insert(0, current_model)
                    
                    # 更新下拉框选项
                    self.main_window.model_combobox.clear()
                    self.main_window.model_combobox.addItems(models)
                    self.main_window.model_combobox.setCurrentText(current_model)
                    self.main_window.add_message("系统", f"已加载 {len(models)} 个可用模型")
        except Exception as e:
            self.logger.error(f"更新模型列表失败: {e}")
            self.main_window.add_message("系统", "获取模型列表失败，使用默认模型")
    
    def on_user_input(self, user_input: str):
        """用户输入回调"""
        # 在聊天区域显示用户输入
        self.main_window.add_message("用户", user_input)
        
        if self.worker:
            self.worker.add_user_input(user_input)
    
    def on_interrupt(self):
        """中断回调"""
        if self.worker:
            self.worker.interrupt()
    
    def on_message(self, sender: str, message: str):
        """消息信号处理"""
        self.main_window.add_message(sender, message)
    
    def on_task(self, task: dict):
        """任务信号处理"""
        self.main_window.update_task(task)
    
    def on_task_update(self, task: dict):
        """任务更新信号处理"""
        self.main_window.update_task(task)
    
    def on_status(self, status: str):
        """状态信号处理"""
        self.main_window.update_status(status)
    
    def on_progress(self, visible: bool, value: int):
        """进度信号处理"""
        self.main_window.show_progress(visible, value)
    
    def on_loading(self, visible: bool, message: str):
        """加载状态信号处理"""
        if visible:
            self.main_window.show_loading(message)
        else:
            self.main_window.hide_loading()
    
    def on_system_status(self, status_info: dict):
        """系统状态信号处理"""
        self.main_window.update_system_status(status_info)
    
    def on_error(self, error: str):
        """错误信号处理"""
        self.main_window.show_error("错误", error)
    
    def on_log(self, log_message: str):
        """日志信号处理"""
        # 显示日志信息到任务窗口
        self.main_window.update_task({
            "description": log_message,
            "status": "日志",
            "progress": None
        })
    
    def on_elicitation_request(self, message: str):
        """elicitation请求信号处理"""
        # 在聊天区域显示交互式确认消息
        def callback(confirmed: bool):
            # 设置结果
            if self.worker:
                self.worker.set_elicitation_result(confirmed)
        
        self.main_window.add_elicitation_message(message, callback)
    
if __name__ == "__main__":
    app = App()
    app.run()
