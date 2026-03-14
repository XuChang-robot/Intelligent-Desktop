"""
智能桌面系统主入口 (PyWebView版本)
使用 Vue3 + Element Plus 前端
"""

import sys
import os
import threading
import time
import asyncio
import queue
import logging
from typing import Dict, Any, Optional, Callable
import ctypes
from ctypes import wintypes
from mpmath.libmp import round_int

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import webview
from webview.window import FixPoint
from mcp_client.client import MCPClient


class WebViewLogHandler(logging.Handler):
    """
    WebView日志处理器
    将日志消息发送到Vue前端
    """
    
    def __init__(self, emit_func):
        super().__init__()
        self.emit_func = emit_func
        self.setLevel(logging.INFO)
        self.setFormatter(logging.Formatter('%(message)s'))
    
    def emit(self, record):
        """
        发送日志记录到前端
        """
        if record.levelno >= logging.INFO:
            log_message = self.format(record)
            # 通过emit_func发送到前端
            self.emit_func("task_log", {
                "description": log_message,
                "status": "日志",
                "progress": None
            })


# 配置全局日志处理器
webview_log_handler = None

def configure_webview_logging(emit_func):
    """
    配置WebView日志处理器
    """
    global webview_log_handler
    
    # 创建日志处理器
    webview_log_handler = WebViewLogHandler(emit_func)
    
    # 为mcp_client模块添加日志处理器
    # 由于日志系统是继承的，子模块的日志会自动传递给父模块的日志处理器
    # 所以只需要为父模块添加日志处理器即可，不需要为子模块单独添加
    client_logger = logging.getLogger('mcp_client')
    client_logger.setLevel(logging.INFO)
    
    # 清除现有的处理器，避免重复处理日志
    for handler in client_logger.handlers[:]:
        client_logger.removeHandler(handler)
    
    # 添加webview日志处理器
    client_logger.addHandler(webview_log_handler)
    
    # 阻止日志传播到根日志记录器，避免被basicConfig的处理器重复处理
    client_logger.propagate = False


class MCPWorker:
    """
    MCP工作线程类
    在单独的线程中运行MCPClient，处理所有后端逻辑
    参考原来的PyQt WorkerThread实现
    """
    
    def __init__(self, client: MCPClient):
        self.client = client
        self.loop = None
        self.thread = None
        self.message_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.running = False
        self.initialized = False
        self.stream_started = False
        self.current_response = ""
        self.current_thinking = ""
        self.buffer = ""
        self.buffer_size = 0
        self.buffer_threshold = 5
        self.elicitation_future = None
        self.interrupted = False
        self.last_status_time = time.time()
        
    def start(self):
        """启动工作线程"""
        if self.thread is None or not self.thread.is_alive():
            self.running = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
            
    def stop(self):
        """停止工作线程"""
        self.running = False
        if self.thread and self.thread.is_alive():
            # 发送停止信号
            self.message_queue.put(("stop", None))
            self.thread.join(timeout=5)
        
    def _run(self):
        """工作线程主循环"""
        # 创建事件循环
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # 设置elicitation回调
        self.client.set_elicitation_callback(self._elicitation_callback)
        
        # 连接到MCP Server
        connected = self.loop.run_until_complete(self.client.connect())
        if not connected:
            return
        
        self.initialized = True
        
        while self.running:
            try:
                # 非阻塞方式检查消息队列
                try:
                    msg_type, data = self.message_queue.get(timeout=0.1)
                except queue.Empty:
                    # 定期打印工作线程状态
                    if time.time() - self.last_status_time > 5:
                        print(f"🔄 工作线程运行中，消息队列大小: {self.message_queue.qsize()}")
                        self.last_status_time = time.time()
                    continue
                    
                if msg_type == "stop":
                    break
                elif msg_type == "send_message":
                    result = self.loop.run_until_complete(
                        self._process_user_input(data)
                    )
                    self.result_queue.put(("send_message", result))
                elif msg_type == "get_models":
                    result = self._get_models()
                    self.result_queue.put(("get_models", result))
                elif msg_type == "get_history":
                    result = self._get_history(data)
                    self.result_queue.put(("get_history", result))
                elif msg_type == "confirm_elicitation":
                    result = self._confirm_elicitation(data)
                    # 不需要将结果放入result_queue，因为前端不需要响应
                elif msg_type == "interrupt":
                    self._interrupt()
                    self.result_queue.put(("interrupt", {"success": True}))
                elif msg_type == "set_model":
                    result = self._set_model(data)
                    self.result_queue.put(("set_model", result))
                    
            except Exception as e:
                print(f"❌ 工作线程错误: {e}")
                import traceback
                traceback.print_exc()
                
        # 清理资源
        try:
            self.loop.run_until_complete(self.client.disconnect())
        except:
            pass
        self.loop.close()
        
    async def _process_user_input(self, user_input: str) -> Dict[str, Any]:
        """处理用户输入（流式）"""
        # 重置流式状态
        self.stream_started = False
        self.current_response = ""
        self.current_thinking = ""
        self.buffer = ""
        self.buffer_size = 0
        
        def stream_callback(chunk):
            """流式输出回调"""
            # 使用闭包访问self
            
            # 获取当前chunk的内容
            chunk_response = chunk.get("response", "")
            chunk_thinking = chunk.get("thinking", "")
            
            # 累加响应
            self.current_response += chunk_response
            self.current_thinking += chunk_thinking
            
            # 如果是第一次收到数据，开始流式消息
            if not self.stream_started and (chunk_response or chunk_thinking):
                # 开始流式消息
                self.stream_started = True
                self.buffer = ""
                self.buffer_size = 0
                
                # 发送流式开始事件
                self._emit_event("stream_start", {
                    "sender": "assistant",
                    "initial_message": chunk_response,
                    "thinking": chunk_thinking
                })
            # 如果不是第一次，更新流式消息
            elif self.stream_started:
                # 如果有思考过程，立即发送
                if chunk_thinking:
                    # 先发送缓冲区中的内容
                    if self.buffer:
                        self._emit_event("stream_update", {
                            "message": self.buffer,
                            "thinking": ""
                        })
                        self.buffer = ""
                        self.buffer_size = 0
                    # 发送思考过程
                    self._emit_event("stream_update", {
                        "message": "",
                        "thinking": chunk_thinking
                    })
                
                # 如果有响应内容，添加到缓冲区
                if chunk_response:
                    self.buffer += chunk_response
                    self.buffer_size += len(chunk_response)
                    
                    # 如果缓冲区达到阈值，发送更新
                    if self.buffer_size >= self.buffer_threshold:
                        self._emit_event("stream_update", {
                            "message": self.buffer,
                            "thinking": ""
                        })
                        self.buffer = ""
                        self.buffer_size = 0
        
        try:
            # 处理用户意图，传入流式回调
            result = await self.client.process_user_intent(user_input, stream_callback=stream_callback)
            
            return {
                "type": result.get("type", ""),
                "content": result.get("summary", ""),
                "thinking": result.get("thinking", ""),
                "plan": result.get("plan", {}),
                "tasks": result.get("plan", {}).get("steps", [])
            }
        except Exception as e:
            # 结束流式消息
            if self.stream_started:
                self._emit_event("stream_end", {})
            return {"error": str(e)}
    
    def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """发送事件到前端"""
        # 这里需要通过pywebview的API发送事件到前端
        # 由于pywebview的限制，我们使用全局回调函数
        if hasattr(self, 'ui_callback') and self.ui_callback:
            self.ui_callback(event_type, data)
    
    def set_ui_callback(self, callback: Callable):
        """设置UI回调"""
        self.ui_callback = callback
        # 同时设置MCPClient的回调
        self.client.set_ui_callback(callback)
    
    def _get_models(self) -> Dict[str, Any]:
        """获取模型列表"""
        try:
            models = self.client.get_available_models()
            # 获取当前实际使用的模型
            current_model = self.client.llm_client.get_current_model()
            return {
                "models": models,
                "current_model": current_model
            }
        except Exception as e:
            return {"error": str(e)}
            
    def _get_history(self, limit: int) -> Dict[str, Any]:
        """获取聊天历史"""
        try:
            history = self.client.get_chat_history(limit=limit)
            return {"history": history}
        except Exception as e:
            return {"error": str(e)}
            
    def _set_model(self, model: str) -> Dict[str, Any]:
        """设置模型"""
        try:
            self.client.set_model(model)
            return {"success": True, "message": f"模型已设置为: {model}"}
        except Exception as e:
            return {"error": str(e)}
            
    async def _elicitation_callback(self, message: str, schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """MCP Client elicitation回调"""
        
        # 发送elicitation请求到前端
        self._emit_event("elicitation_request", {
            "message": message,
            "schema": schema
        })
        
        # 创建future等待用户响应
        self.elicitation_future = self.loop.create_future()
        
        # 等待用户响应 - 注意：这个等待会阻塞工作线程
        # 但确认请求也是通过消息队列发送到工作线程的
        # 所以我们需要在主线程中处理确认请求
        try:
            result = await asyncio.wait_for(self.elicitation_future, timeout=60.0)
            return result
        except asyncio.TimeoutError:
            return {"action": "decline"}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"action": "decline"}
    
    def _interrupt(self):
        """中断执行"""
        self.interrupted = True
        # 通知客户端中断执行
        if hasattr(self.client, 'interrupt'):
            self.client.interrupt()
        # 取消当前的elicitation请求
        if self.elicitation_future and not self.elicitation_future.done():
            self.elicitation_future.cancel()
    
    # 对外接口（从主线程调用）
    def send_message(self, message: str) -> Dict[str, Any]:
        """发送消息"""
        try:
            self.message_queue.put(("send_message", message))
            msg_type, result = self.result_queue.get(timeout=300)
            return result
        except queue.Empty:
            return {"error": "操作超时，请重试"}
        except Exception as e:
            return {"error": f"操作失败: {str(e)}"}
        
    def get_models(self) -> Dict[str, Any]:
        """获取模型列表"""
        try:
            self.message_queue.put(("get_models", None))
            msg_type, result = self.result_queue.get(timeout=10)
            return result
        except queue.Empty:
            return {"error": "获取模型列表超时"}
        except Exception as e:
            return {"error": f"获取模型列表失败: {str(e)}"}
        
    def get_history(self, limit: int = 50) -> Dict[str, Any]:
        """获取聊天历史"""
        try:
            self.message_queue.put(("get_history", limit))
            msg_type, result = self.result_queue.get(timeout=10)
            return result
        except queue.Empty:
            return {"error": "获取历史记录超时"}
        except Exception as e:
            return {"error": f"获取历史记录失败: {str(e)}"}
        
    def confirm_elicitation(self, message: str, content: any, confirmed: bool) -> Dict[str, Any]:
        """处理澄清确认"""
        try:
            data = {
                "message": message,
                "content": content,
                "confirmed": confirmed
            }
            # 直接在主线程中处理确认请求，避免死锁
            if self.elicitation_future and not self.elicitation_future.done():
                self.elicitation_future.set_result({
                    "action": "accept" if data["confirmed"] else "decline",
                    "content": data["content"]
                })
                # 重置elicitation_future
                self.elicitation_future = None
            return {"success": True}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": f"确认操作失败: {str(e)}"}
    
    def interrupt(self) -> Dict[str, Any]:
        """中断执行"""
        try:
            self.message_queue.put(("interrupt", None))
            msg_type, result = self.result_queue.get(timeout=10)
            return result
        except queue.Empty:
            return {"error": "中断操作超时"}
        except Exception as e:
            return {"error": f"中断操作失败: {str(e)}"}
            
    def set_model(self, model: str) -> Dict[str, Any]:
        """设置模型"""
        try:
            self.message_queue.put(("set_model", model))
            msg_type, result = self.result_queue.get(timeout=10)
            return result
        except queue.Empty:
            return {"error": "设置模型超时"}
        except Exception as e:
            return {"error": f"设置模型失败: {str(e)}"}


# 全局回调列表（用于UI事件通知）
_ui_callbacks: list[Callable] = []

# 全局窗口引用（用于窗口控制）
_window = None

# 窗口状态记录
_window_normal_state = None  # 记录窗口正常状态的位置和大小


def emit_ui_event(event_type: str, data: Dict[str, Any]):
    """发送UI事件到前端"""
    global _window
    # 通过JavaScript发送事件到前端
    if _window:
        try:
            import json
            event_data = json.dumps({'type': event_type, 'data': data})
            js_code = f"""
            if (window.dispatchEvent) {{
                const event = new CustomEvent('pywebview_event', {{detail: {event_data}}});
                window.dispatchEvent(event);
            }}
            """
            _window.evaluate_js(js_code)
        except Exception as e:
            pass
    
    # 同时也调用回调函数（保持兼容性）
    for callback in _ui_callbacks:
        try:
            callback(event_type, data)
        except Exception as e:
            pass


class PyWebViewAPI:
    """PyWebView API类
    
    通过构造函数接收mcp_client和mcp_worker实例
    无需显式调用init方法初始化
    """
    
    def __init__(self, mcp_client_instance: MCPClient, mcp_worker_instance: MCPWorker):
        """初始化API类
        
        Args:
            mcp_client_instance: MCPClient实例
            mcp_worker_instance: MCPWorker实例
        """
        self.mcp_client = mcp_client_instance
        self.mcp_worker = mcp_worker_instance

    def send_message(self, message):
        """发送消息"""
        if self.mcp_worker is None:
            return {"error": "MCP Client 未初始化"}
        return self.mcp_worker.send_message(message)
    
    def get_models(self):
        """获取模型列表"""
        if self.mcp_worker is None:
            return {"error": "MCP Client 未初始化"}
        return self.mcp_worker.get_models()
    
    def get_history(self, limit=50):
        """获取聊天历史"""
        if self.mcp_worker is None:
            return {"error": "MCP Client 未初始化"}
        return self.mcp_worker.get_history(limit)
    
    def set_model(self, model):
        """设置模型"""
        if self.mcp_worker is None:
            return {"error": "MCP Client 未初始化"}
        return self.mcp_worker.set_model(model)
    
    def minimize_window(self):
        """最小化窗口"""
        global _window
        try:
            if _window:
                _window.minimize()
            return {"success": True}
        except Exception as e:
            return {"error": f"最小化窗口失败: {str(e)}"}
    
    def maximize_window(self):
        """最大化窗口（保留任务栏）"""
        global _window, _window_normal_state
        try:
            if _window:
                # 记录当前窗口状态（用于恢复）
                _window_normal_state = {
                    'x': _window.x,
                    'y': _window.y,
                    'width': _window.width,
                    'height': _window.height
                }
                # 获取屏幕工作区大小（不包含任务栏）
                import ctypes
                from ctypes import wintypes
                user32 = ctypes.windll.user32
                rect = wintypes.RECT()
                user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)
                # 获取DPI缩放因子
                scale_factor = self.get_dpi()['scale_factor']
                # 设置窗口大小和位置
                _window.resize(rect.right - rect.left, rect.bottom - rect.top)
                _window.move(rect.left / scale_factor, rect.top / scale_factor)
            return {"success": True}
        except Exception as e:
            return {"error": f"最大化窗口失败: {str(e)}"}
    
    def restore_window(self):
        """还原窗口"""
        global _window, _window_normal_state
        try:
            if _window and _window_normal_state:
                # 获取DPI缩放因子
                scale_factor = self.get_dpi()['scale_factor']
                # 恢复到之前记录的状态
                _window.resize(_window_normal_state['width'], _window_normal_state['height'])
                _window.move(_window_normal_state['x'] / scale_factor, _window_normal_state['y'] / scale_factor)
            return {"success": True}
        except Exception as e:
            return {"error": f"还原窗口失败: {str(e)}"}
    
    def restore_and_resize(self, new_width: int = None, new_height: int = None, new_x: int = None, new_y: int = None):
        """还原窗口并调整大小（一次性完成，避免闪烁）
        
        Args:
            new_width: 新的窗口宽度，如果为None则使用之前的宽度
            new_height: 新的窗口高度，如果为None则使用之前的高度
            new_x: 新的窗口X坐标，如果为None则使用之前的位置
            new_y: 新的窗口Y坐标，如果为None则使用之前的位置
        """
        global _window, _window_normal_state
        try:
            if _window:
                # 使用新大小或默认大小
                if new_width is not None and new_height is not None:
                    width = new_width
                    height = new_height
                elif _window_normal_state:
                    width = _window_normal_state['width']
                    height = _window_normal_state['height']
                else:
                    # 如果没有默认状态，使用当前窗口大小
                    width = _window.width 
                    height = _window.height 
                
                # 使用新位置或默认位置
                if new_x is not None and new_y is not None:
                    x = new_x
                    y = new_y
                elif _window_normal_state:
                    x = _window_normal_state['x']
                    y = _window_normal_state['y']
                else:
                    # 如果没有默认状态，使用当前窗口位置
                    x = _window.x
                    y = _window.y
                
                # 使用webview库的方法调整窗口大小和位置
                # TODO
                # 先调整大小，再移动位置
                # 确保参数为整数
                _window.resize(int(width * self.get_dpi()['scale_factor']), int(height * self.get_dpi()['scale_factor']))
                # _window.move(int(x / self.system_dpi_factor), int(y / self.system_dpi_factor))
                # user32 = ctypes.windll.user32
                # user32.SetWindowPos(ctypes.windll.user32.GetForegroundWindow(),
                #                     0,
                #                     int(x * self.get_dpi()['scale_factor']),
                #                     int(y * self.get_dpi()['scale_factor']),
                #                     int(width * self.get_dpi()['scale_factor']),
                #                     int(height * self.get_dpi()['scale_factor']),
                #                     0
                #                     )
                # 更新窗口正常状态，避免窗口回到原位
                _window_normal_state = {
                    'x': x,
                    'y': y,
                    'width': width,
                    'height': height
                }
            return {"success": True}
        except Exception as e:
            return {"error": f"还原并调整窗口失败: {str(e)}"}
    
    def close_window(self):
        """关闭窗口"""
        global _window
        try:
            if _window:
                _window.destroy()
            return {"success": True}
        except Exception as e:
            return {"error": f"关闭窗口失败: {str(e)}"}
    
    def move_window(self, x: int, y: int):
        """移动窗口到指定位置
        
        Args:
            x: 窗口左上角的X坐标
            y: 窗口左上角的Y坐标
        """
        global _window
        try:
            if _window:
                # 获取DPI缩放因子
                scale_factor = self.get_dpi()['scale_factor']
                _window.move(x / scale_factor, y / scale_factor) #(x/scale_factor, y/scale_factor)
                return {"success": True}
            return {"error": "窗口未初始化"}
        except Exception as e:
            return {"error": f"移动窗口失败: {str(e)}"}
    
    def resize_window_with_fixpoint(self, width: int, height: int, fix_point: str):
        """调整窗口大小（使用固定点）
        
        Args:
            width: 窗口宽度
            height: 窗口高度
            fix_point: 固定点，可选值: NW, NE, SW, SE
                      NW - 西北（左上角）
                      NE - 东北（右上角）
                      SW - 西南（左下角）
                      SE - 东南（右下角）
        """
        global _window
        try:
            if _window:
                # 将字符串转换为FixPoint
                fix_point_map = {
                    'NW': FixPoint.NORTH | FixPoint.WEST,
                    'NE': FixPoint.NORTH | FixPoint.EAST,
                    'SW': FixPoint.SOUTH | FixPoint.WEST,
                    'SE': FixPoint.SOUTH | FixPoint.EAST
                }
                
                fp = fix_point_map.get(fix_point, FixPoint.NORTH | FixPoint.WEST)
                _window.resize(width, height, fix_point=fp)
            return {"success": True}
        except Exception as e:
            return {"error": f"调整窗口大小失败: {str(e)}"}
    
    def get_window_position(self):
        """获取窗口当前位置"""
        global _window
        try:
            if _window:
                return {"x": _window.x, "y": _window.y}
            return {"error": "窗口未初始化"}
        except Exception as e:
            return {"error": f"获取窗口位置失败: {str(e)}"}
    
    def get_window_rect(self):
        """获取窗口当前位置和大小"""
        global _window
        try:
            if _window:
                return {
                    "x": _window.x,
                    "y": _window.y,
                    "width": _window.width,
                    "height": _window.height
                }
            return {"error": "窗口未初始化"}
        except Exception as e:
            return {"error": f"获取窗口矩形失败: {str(e)}"}
    
    def confirm_elicitation(self, message, content, confirmed):
        """处理澄清确认"""
        if self.mcp_worker is None:
            return {"error": "MCP Client 未初始化"}
        return self.mcp_worker.confirm_elicitation(message, content, confirmed)
    
    def interrupt(self):
        """中断执行"""
        if self.mcp_worker is None:
            return {"error": "MCP Client 未初始化"}
        return self.mcp_worker.interrupt()
    
    def register_callback(self, callback_id, callback):
        """注册UI回调"""
        global _ui_callbacks
        # 这里需要处理回调的注册和管理
        # 由于pywebview的限制，我们使用全局回调列表
        _ui_callbacks.append(callback)
        return {"status": "ok"}
    
    def get_dpi(self):
        """获取系统DPI设置
        
        Returns:
            dict: 包含DPI信息的字典
        """
        try:
            # 获取系统DPI
            dpi = ctypes.windll.user32.GetDpiForSystem()
            # 获取窗口DPI（如果窗口已初始化）
            window_dpi = None
            global _window
            if _window:
                window_dpi = ctypes.windll.user32.GetDpiForWindow(ctypes.windll.user32.GetForegroundWindow())
            
            return {
                "system_dpi": dpi,
                "window_dpi": window_dpi,
                "scale_factor": dpi / 96.0
            }
        except Exception as e:
            return {"error": f"获取DPI失败: {str(e)}"}


def main():
    
    """主函数"""
    # 初始化日志配置
    configure_webview_logging(emit_ui_event)
    
    # 初始化MCPClient（在主线程）
    mcp_client = MCPClient()
    mcp_worker = MCPWorker(mcp_client)
    # 设置UI回调
    mcp_worker.set_ui_callback(emit_ui_event)
    mcp_worker.start()
    
    # 确定前端文件路径
    frontend_path = os.path.join(os.path.dirname(__file__), 'frontend', 'dist', 'index.html')
    
    # 检查前端构建文件是否存在
    if os.path.exists(frontend_path):
        url = frontend_path
    else:
        url = "http://localhost:5173"
    
    # 创建 PyWebViewAPI 实例（通过构造函数传递mcp_client和mcp_worker）
    pwvapi = PyWebViewAPI(mcp_client, mcp_worker)
    
    # 设置只有标题栏可以拖拽（必须在窗口创建前设置）
    webview.DRAG_REGION_SELECTOR = ".custom-titlebar"
    
    # 创建窗口 - 无边框窗口，使用自定义标题栏
    global _window
    _window = webview.create_window(
        title="智能桌面系统",
        url=url,
        width=1400,
        height=900,
        min_size=(1000, 600),
        js_api=pwvapi,
        text_select=True,
        frameless=True,  # 无边框窗口
        easy_drag=True  # 启用拖拽功能
    )
    
    # 定义窗口显示事件处理函数
    def on_shown():
        """窗口显示时最大化（保留任务栏）"""
        global _window, _window_normal_state
        if _window:
            # 记录初始窗口状态（用于恢复）
            _window_normal_state = {
                'x': _window.x,
                'y': _window.y,
                'width': _window.width,
                'height': _window.height
            }
            # 使用手动最大化，保留任务栏
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            # 获取主显示器的工作区（不包含任务栏）
            rect = wintypes.RECT()
            user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)
            # 获取DPI缩放因子
            dpi = ctypes.windll.user32.GetDpiForSystem()
            scale_factor = dpi / 96.0
            # 设置窗口大小和位置
            _window.resize(rect.right - rect.left, rect.bottom - rect.top)
            _window.move(rect.left / scale_factor, rect.top / scale_factor)
    
    def on_maximized():
        """窗口最大化时通知前端"""
        emit_ui_event('window_maximized', {'maximized': True})
    
    def on_restored():
        """窗口还原时通知前端"""
        emit_ui_event('window_restored', {'maximized': False})
    
    def on_minimized():
        """窗口最小化时通知前端"""
        emit_ui_event('window_minimized', {'minimized': True})
    
    def on_loaded():
        """窗口加载完成后执行"""
        # 在窗口加载完成后发送测试日志
        logging.getLogger('mcp_client').info("智能桌面系统已启动，欢迎使用！")
    
    # 绑定事件
    _window.events.shown += on_shown
    _window.events.maximized += on_maximized
    _window.events.restored += on_restored
    _window.events.minimized += on_minimized
    _window.events.loaded += on_loaded
    
    # 启动应用
    webview.start(
        debug=True,
        http_server=True,
        storage_path=os.path.join(os.path.dirname(__file__), '.pywebview_cache')
    )
    
    # 应用关闭时停止MCP工作线程
    if mcp_worker:
        mcp_worker.stop()


if __name__ == "__main__":
    main()