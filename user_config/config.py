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
            # 如果加载失败，使用空配置
            self.config = {}
    
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
