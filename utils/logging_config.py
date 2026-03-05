# 日志配置模块

import logging
import os
from user_config.config import get_config

class LoggingConfig:
    """日志配置类"""
    
    def __init__(self):
        self.dev_mode = get_config("logging.dev_mode", False)
        self.log_dir = get_config("logging.log_dir", "logs")
        self.log_level = get_config("logging.level", "INFO")
        self.log_format = get_config("logging.format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        
        # 获取项目根目录
        self.project_root = os.path.dirname(os.path.dirname(__file__))
        self.log_dir_path = os.path.join(self.project_root, self.log_dir)
        
        # 确保日志目录存在
        if not os.path.exists(self.log_dir_path):
            os.makedirs(self.log_dir_path)
    
    def get_log_file_path(self, log_name: str = "app") -> str:
        """获取日志文件路径"""
        if not self.dev_mode:
            return None
        return os.path.join(self.log_dir_path, f"{log_name}.log")
    
    def configure_logger(self, logger_name: str = None, log_file: str = "app") -> logging.Logger:
        """配置日志记录器"""
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, self.log_level))
        
        # 清除现有的处理器
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, self.log_level))
        console_formatter = logging.Formatter(self.log_format)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # 如果是开发模式，添加文件处理器
        if self.dev_mode:
            log_file_path = self.get_log_file_path(log_file)
            if log_file_path:
                file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
                file_handler.setLevel(getattr(logging, self.log_level))
                file_formatter = logging.Formatter(self.log_format)
                file_handler.setFormatter(file_formatter)
                logger.addHandler(file_handler)
        
        return logger

# 全局日志配置实例
logging_config = LoggingConfig()

# 配置根日志记录器
def configure_root_logger():
    """配置根日志记录器"""
    return logging_config.configure_logger()

# 获取配置好的日志记录器
def get_logger(name: str = None, log_file: str = "app") -> logging.Logger:
    """获取配置好的日志记录器"""
    return logging_config.configure_logger(name, log_file)
