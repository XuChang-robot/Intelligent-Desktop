# 错误处理工具

import logging
from typing import Dict, Any, Optional, Callable
import traceback

class ErrorHandler:
    """错误处理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def handle_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """处理错误"""
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "context": context or {}
        }
        
        self.logger.error(f"错误处理: {error_info}")
        
        return error_info
    
    def retry_wrapper(self, max_retries: int = 3, delay: float = 1.0):
        """重试装饰器"""
        def decorator(func: Callable):
            async def wrapper(*args, **kwargs):
                for attempt in range(max_retries):
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        self.logger.warning(f"执行失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                        if attempt < max_retries - 1:
                            import asyncio
                            await asyncio.sleep(delay)
                            continue
                        raise
            return wrapper
        return decorator
    
    def sync_retry_wrapper(self, max_retries: int = 3, delay: float = 1.0):
        """同步重试装饰器"""
        def decorator(func: Callable):
            def wrapper(*args, **kwargs):
                for attempt in range(max_retries):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        self.logger.warning(f"执行失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                        if attempt < max_retries - 1:
                            import time
                            time.sleep(delay)
                            continue
                        raise
            return wrapper
        return decorator

# 全局错误处理器实例
error_handler = ErrorHandler()

def get_error_handler() -> ErrorHandler:
    """获取错误处理器"""
    return error_handler
