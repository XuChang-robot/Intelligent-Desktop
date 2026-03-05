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
        self._ensure_directories()
    
    def _load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            # 如果加载失败，使用空配置
            self.config = {}
    
    def _ensure_directories(self):
        """确保必要的目录存在"""
        # 获取日志目录配置
        log_dir = self.get("logging.log_dir", "logs")
        visualization_dir = self.get("logging.visualization_dir", "logs/visualizations")
        
        # 创建项目根目录下的目录
        project_root = os.path.dirname(os.path.dirname(__file__))
        
        # 创建日志目录
        log_dir_path = os.path.join(project_root, log_dir)
        if not os.path.exists(log_dir_path):
            os.makedirs(log_dir_path)
        
        # 创建可视化目录
        visualization_dir_path = os.path.join(project_root, visualization_dir)
        if not os.path.exists(visualization_dir_path):
            os.makedirs(visualization_dir_path)
    
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
