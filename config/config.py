# 配置管理模块

import yaml
import os
from typing import Dict, Any

class ConfigLoader:
    """配置加载器"""
    
    def __init__(self):
        self.config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
        self.config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            # 使用默认配置
            self.config = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "mcp": {
                "server": {
                    "host": "localhost",
                    "port": 8765,
                    "max_connections": 10
                },
                "client": {
                    "timeout": 30,
                    "retry_attempts": 3
                }
            },
            "llm": {
                "model": "qwen3:30b",
                "base_url": "http://localhost:11434",
                "temperature": 0.7,
                "max_tokens": 2000
            },
            "security": {
                "enable_sandbox": True,
                "dangerous_commands": ["rm -rf", "format", "shutdown", "reboot"],
                "allow_network": True,
                "allow_file_system": True,
                "max_execution_time": 30
            },
            "ui": {
                "title": "智能桌面系统",
                "width": 800,
                "height": 600,
                "theme": "light"
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value

# 全局配置实例
_config_loader = ConfigLoader()

def load_config() -> Dict[str, Any]:
    """加载配置"""
    return _config_loader.config

def get_config(key: str, default: Any = None) -> Any:
    """获取配置值"""
    return _config_loader.get(key, default)
