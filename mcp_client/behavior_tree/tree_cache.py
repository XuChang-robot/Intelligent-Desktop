import json
import hashlib
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

class TreeCache:
    """行为树缓存
    
    缓存行为树配置，避免重复生成。
    支持基于哈希的精确匹配。
    """
    
    def __init__(self, cache_file: str = "cache/tree_cache.json", 
                 ttl_hours: int = 24):
        """
        Args:
            cache_file: 缓存文件路径
            ttl_hours: 缓存过期时间（小时）
        """
        self.cache_file = cache_file
        self.ttl = timedelta(hours=ttl_hours)
        self.logger = logging.getLogger(__name__)
        
        # 缓存数据
        self.cache: Dict[str, Dict[str, Any]] = {}
        
        # 加载缓存
        self._load_cache()
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """获取缓存的树配置
        
        Args:
            key: 缓存键
        
        Returns:
            缓存的树配置，如果不存在或已过期则返回 None
        """
        if key not in self.cache:
            self.logger.debug(f"缓存未命中: {key}")
            return None
        
        entry = self.cache[key]
        
        # 检查是否过期
        if self._is_expired(entry):
            self.logger.debug(f"缓存已过期: {key}")
            del self.cache[key]
            self._save_cache()
            return None
        
        self.logger.info(f"缓存命中: {key}")
        return entry["config"]
    
    def set(self, key: str, config: Dict[str, Any]):
        """缓存树配置
        
        Args:
            key: 缓存键
            config: 树配置
        """
        entry = {
            "config": config,
            "timestamp": datetime.now().isoformat(),
            "hash": self._compute_hash(config)
        }
        
        self.cache[key] = entry
        self.logger.info(f"缓存树配置: {key}")
        self._save_cache()
    
    def invalidate(self, key: str):
        """使缓存失效
        
        Args:
            key: 缓存键
        """
        if key in self.cache:
            del self.cache[key]
            self.logger.info(f"使缓存失效: {key}")
            self._save_cache()
    
    def clear(self):
        """清空所有缓存"""
        self.cache = {}
        self._save_cache()
        self.logger.info("缓存已清空")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息
        
        Returns:
            缓存统计字典
        """
        total_entries = len(self.cache)
        expired_entries = sum(
            1 for entry in self.cache.values() 
            if self._is_expired(entry)
        )
        valid_entries = total_entries - expired_entries
        
        return {
            "total_entries": total_entries,
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "cache_file": self.cache_file,
            "ttl_hours": self.ttl.total_seconds() / 3600
        }
    
    def cleanup_expired(self) -> int:
        """清理过期的缓存
        
        Returns:
            清理的缓存数量
        """
        expired_keys = [
            key for key, entry in self.cache.items()
            if self._is_expired(entry)
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            self._save_cache()
            self.logger.info(f"清理了 {len(expired_keys)} 个过期缓存")
        
        return len(expired_keys)
    
    def _load_cache(self):
        """从文件加载缓存"""
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                self.cache = json.load(f)
            self.logger.info(f"加载缓存: {len(self.cache)} 条记录")
        except FileNotFoundError:
            self.logger.info("缓存文件不存在，创建新缓存")
            self.cache = {}
        except Exception as e:
            self.logger.error(f"加载缓存失败: {e}")
            self.cache = {}
    
    def _save_cache(self):
        """保存缓存到文件"""
        try:
            import os
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存缓存失败: {e}")
    
    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """检查缓存是否过期
        
        Args:
            entry: 缓存条目
        
        Returns:
            如果过期返回 True
        """
        timestamp_str = entry.get("timestamp")
        if not timestamp_str:
            return True
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            return datetime.now() - timestamp > self.ttl
        except Exception:
            return True
    
    def _compute_hash(self, config: Dict[str, Any]) -> str:
        """计算配置的哈希值
        
        Args:
            config: 配置字典
        
        Returns:
            哈希字符串
        """
        config_str = json.dumps(config, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()
    
    def generate_key(self, user_input: str, intent: Dict[str, Any]) -> str:
        """生成缓存键
        
        Args:
            user_input: 用户输入
            intent: 意图字典
        
        Returns:
            缓存键
        """
        key_data = {
            "user_input": user_input,
            "intent_type": intent.get("intent", ""),
            "entities": intent.get("entities", {})
        }
        
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
