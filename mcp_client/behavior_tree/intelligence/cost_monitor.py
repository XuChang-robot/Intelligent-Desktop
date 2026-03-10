# 成本监控
# 监控推断服务的成本和性能

import logging
from typing import Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CostMetrics:
    """成本指标"""
    total_tokens: int = 0
    total_calls: int = 0
    total_latency_ms: float = 0
    by_model: Dict[str, Dict[str, int]] = field(default_factory=dict)
    by_node_type: Dict[str, Dict[str, int]] = field(default_factory=dict)


class InferenceCostMonitor:
    """推断成本监控器"""
    
    def __init__(self, budget_per_task: int = 500):
        """
        Args:
            budget_per_task: 单任务token预算
        """
        self.budget_per_task = budget_per_task
        self.logger = logging.getLogger(__name__)
        self.metrics = CostMetrics()
    
    def track_inference(
        self,
        model: str,
        tokens: int,
        latency_ms: float,
        node_type: str,
        success: bool
    ):
        """追踪推断调用"""
        self.metrics.total_tokens += tokens
        self.metrics.total_calls += 1
        self.metrics.total_latency_ms += latency_ms
        
        # 按模型统计
        if model not in self.metrics.by_model:
            self.metrics.by_model[model] = {'calls': 0, 'tokens': 0, 'successes': 0}
        self.metrics.by_model[model]['calls'] += 1
        self.metrics.by_model[model]['tokens'] += tokens
        if success:
            self.metrics.by_model[model]['successes'] += 1
        
        # 按节点类型统计
        if node_type not in self.metrics.by_node_type:
            self.metrics.by_node_type[node_type] = {'calls': 0, 'tokens': 0}
        self.metrics.by_node_type[node_type]['calls'] += 1
        self.metrics.by_node_type[node_type]['tokens'] += tokens
    
    def check_budget(self, estimated_tokens: int) -> Dict[str, Any]:
        """检查预算"""
        remaining = self.budget_per_task - self.metrics.total_tokens
        
        if self.metrics.total_tokens + estimated_tokens > self.budget_per_task:
            return {
                'allowed': False,
                'reason': 'budget_exceeded',
                'current': self.metrics.total_tokens,
                'budget': self.budget_per_task,
                'remaining': remaining
            }
        
        return {'allowed': True, 'remaining': remaining}
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        if self.metrics.total_calls == 0:
            return {'message': '暂无数据'}
        
        return {
            'total_calls': self.metrics.total_calls,
            'total_tokens': self.metrics.total_tokens,
            'avg_tokens_per_call': self.metrics.total_tokens / self.metrics.total_calls,
            'avg_latency_ms': self.metrics.total_latency_ms / self.metrics.total_calls,
            'by_model': self.metrics.by_model,
            'by_node_type': self.metrics.by_node_type
        }
