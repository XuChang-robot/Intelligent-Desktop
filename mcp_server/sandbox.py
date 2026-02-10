# MCP Server 沙箱模块

import asyncio
import io
import sys
import traceback
import logging
import math
import numpy as np
from scipy import integrate
import sympy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import builtins
from typing import Dict, Any, Optional, Callable

class StreamingOutput:
    """流式输出捕获器"""
    
    def __init__(self, callback: Optional[Callable[[str], None]] = None):
        self.callback = callback
        self.buffer = io.StringIO()
        # 获取主事件循环
        try:
            self.loop = asyncio.get_event_loop()
            if self.loop.is_closed():
                # 如果事件循环已关闭，创建一个新的
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
        except RuntimeError:
            # 如果没有事件循环，创建一个新的
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
    
    def write(self, text: str):
        """写入文本"""
        self.buffer.write(text)
        if self.callback:
            # 检查回调是否是异步函数
            if asyncio.iscoroutinefunction(self.callback):
                # 如果是异步函数，在事件循环中调度执行
                try:
                    if self.loop.is_running():
                        asyncio.run_coroutine_threadsafe(self.callback(text), self.loop)
                    else:
                        # 如果事件循环没有运行，直接运行
                        self.loop.run_until_complete(self.callback(text))
                except Exception as e:
                    # 如果调度失败，忽略错误
                    pass
            else:
                # 如果是同步函数，直接调用
                self.callback(text)
    
    def flush(self):
        """刷新缓冲区"""
        pass
    
    def getvalue(self) -> str:
        """获取所有输出"""
        return self.buffer.getvalue()

class SandboxExecutor:
    """沙箱执行器，用于安全执行Python代码"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def execute_code(self, code: str, output_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """在沙箱中执行Python代码"""
        try:
            # 创建执行任务
            loop = asyncio.get_event_loop()
            future = loop.run_in_executor(
                None,
                self._execute_in_sandbox,
                code,
                output_callback
            )
            
            # 不设置超时限制
            result = await future
            return result
        except Exception as e:
            return {
                "output": "",
                "error": str(e)
            }
    
    def _execute_in_sandbox(self, code: str, output_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """在沙箱中执行代码的实际方法"""
        # 重定向标准输出
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        
        stdout_capture = StreamingOutput(output_callback)
        stderr_capture = StreamingOutput(output_callback)
        
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture
        
        result = {}
        
        try:
            # 构建安全的执行环境
            safe_globals = {
                '__builtins__': self._get_safe_builtins(),
                '__name__': '__main__'
            }
            
            # 执行代码
            exec(code, safe_globals)
            
            # 获取输出
            output = stdout_capture.getvalue()
            error = stderr_capture.getvalue()
            
            result = {
                "output": output,
                "error": error
            }
            
        except Exception as e:
            # 捕获执行错误
            error_trace = traceback.format_exc()
            result = {
                "output": stdout_capture.getvalue(),
                "error": f"执行错误: {str(e)}\n{error_trace}"
            }
        finally:
            # 恢复标准输出
            sys.stdout = old_stdout
            sys.stderr = old_stderr
        
        return result
    
    def _get_safe_builtins(self) -> Dict[str, Any]:
        """获取安全的内置函数"""
        # 禁止导入的危险模块列表（黑名单）
        # 注意：os、pathlib等文件操作模块已移除，允许文件读写
        # 真正危险的模块：网络、系统命令、并发等
        dangerous_modules = {
            'subprocess', 'shutil', 'socket',
            'http', 'urllib', 'ftplib', 'telnetlib',
            'pickle', 'marshal', 'ctypes', 'importlib', 'builtins',
            'multiprocessing', 'threading', 'concurrent',
            'webbrowser', 'mimetypes',
            'cmd', 'pipes', 'pty', 'fcntl', 'resource',
            'signal', 'select', 'selectors',
            'hashlib', 'hmac', 'secrets', 'uuid',
            'sqlite3', 'dbm', 'anydbm', 'gdbm',
            'configparser', 'xml', 'html',
            'yaml', 'toml', 'base64',
            'binascii', 'struct', 'codecs',
            'platform', 'getpass', 'pwd', 'grp',
            'netrc', 'nturl2path', 'ntpath', 'posixpath',
            'macpath', 'os2emxpath',
        }
        
        # 安全的import函数
        def safe_import(name, *args, **kwargs):
            """安全的import函数，禁止导入危险模块"""
            # 检查是否是危险模块
            module_name = name.split('.')[0]
            if module_name in dangerous_modules:
                raise ImportError(f"模块 '{name}' 被禁止在沙箱中导入（安全限制）")
            
            # 检查是否是危险模块的子模块
            for dangerous in dangerous_modules:
                if name.startswith(dangerous + '.'):
                    raise ImportError(f"模块 '{name}' 被禁止在沙箱中导入（安全限制）")
            
            # 允许导入其他所有模块
            return __import__(name, *args, **kwargs)
        
        # 使用真正的黑名单模式：允许所有Python内置函数，只替换__import__
        safe_builtins = builtins.__dict__.copy()
        safe_builtins['__import__'] = safe_import
        
        return safe_builtins
