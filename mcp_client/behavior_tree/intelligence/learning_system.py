# 学习系统
# 记录用户修正，优化未来推断

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path


class InferenceLearningSystem:
    """推断学习系统
    
    记录用户对推断结果的修正，形成个性化偏好模型。
    """
    
    def __init__(self, model_path: str = "data/inference_learning.json"):
        """
        Args:
            model_path: 学习模型存储路径
        """
        self.model_path = Path(model_path)
        self.logger = logging.getLogger(__name__)
        
        # 内存中的学习数据
        self.correction_history: List[Dict[str, Any]] = []
        self.user_patterns: Dict[str, Any] = {}
        
        # 加载已有数据
        self._load_model()
    
    def _load_model(self):
        """加载学习模型"""
        if self.model_path.exists():
            try:
                with open(self.model_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.correction_history = data.get('corrections', [])
                    self.user_patterns = data.get('patterns', {})
                self.logger.info(f"加载学习模型: {len(self.correction_history)} 条记录")
            except Exception as e:
                self.logger.error(f"加载学习模型失败: {e}")
    
    def _save_model(self):
        """保存学习模型"""
        try:
            self.model_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.model_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'corrections': self.correction_history,
                    'patterns': self.user_patterns,
                    'last_updated': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存学习模型失败: {e}")
    
    def record_correction(
        self,
        node_type: str,
        param_name: str,
        inferred_value: Any,
        user_value: Any,
        context: Optional[Dict[str, Any]] = None
    ):
        """记录用户修正"""
        record = {
            'timestamp': datetime.now().isoformat(),
            'node_type': node_type,
            'param_name': param_name,
            'inferred_value': inferred_value,
            'user_value': user_value,
            'context': context or {}
        }
        
        self.correction_history.append(record)
        
        # 更新模式
        if inferred_value != user_value:
            self._update_pattern(record)
        
        # 定期保存
        if len(self.correction_history) % 10 == 0:
            self._save_model()
    
    def _update_pattern(self, record: Dict[str, Any]):
        """更新用户模式"""
        key = f"{record['node_type']}.{record['param_name']}"
        
        if key not in self.user_patterns:
            self.user_patterns[key] = {
                'corrections': [],
                'preference_score': {}
            }
        
        pattern = self.user_patterns[key]
        pattern['corrections'].append({
            'from': record['inferred_value'],
            'to': record['user_value'],
            'timestamp': record['timestamp'],
            'context': record['context']
        })
        
        # 更新偏好分数
        user_value = str(record['user_value'])
        pattern['preference_score'][user_value] = \
            pattern['preference_score'].get(user_value, 0) + 1
    
    def get_learned_preference(
        self,
        node_type: str,
        param_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """获取学习到的偏好"""
        key = f"{node_type}.{param_name}"
        
        if key not in self.user_patterns:
            return None
        
        pattern = self.user_patterns[key]
        
        # 获取最高分的偏好
        if not pattern['preference_score']:
            return None
        
        top_value = max(
            pattern['preference_score'].items(),
            key=lambda x: x[1]
        )
        
        total_corrections = sum(pattern['preference_score'].values())
        confidence = top_value[1] / total_corrections if total_corrections > 0 else 0
        
        return {
            'value': top_value[0],
            'confidence': confidence,
            'source': 'learned_preference',
            'correction_count': total_corrections
        }
