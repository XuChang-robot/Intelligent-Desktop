# 执行智能管理器
# 核心组件，协调LLM推断服务

import logging
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass

from .inference_service import LLMInferenceService, InferenceResult


class ExecutionStrategy(Enum):
    """执行策略"""
    DIRECT = "direct"            # 直接执行
    INFER = "infer"              # 纯推断
    CONFIRM = "confirm"          # 纯确认
    INTELLIGENT = "intelligent"  # 混合模式（推断+确认）


@dataclass
class IntelligenceExecutionResult:
    """智能执行结果"""
    success: bool
    strategy_used: str
    final_params: Dict[str, Any]
    inference_result: Optional[InferenceResult] = None
    execution_time_ms: float = 0.0
    error: Optional[str] = None


class IntelligenceExecutionManager:
    """执行智能管理器
    
    协调推断服务和Elicitation服务许可，实现混合模式的执行智能。
    """
    
    def __init__(
        self,
        strategy: ExecutionStrategy = ExecutionStrategy.INTELLIGENT,
        auto_execute_threshold: float = 0.85,
        confirm_threshold: float = 0.60,
        llm_client: Optional[Any] = None
    ):
        """
        Args:
            strategy: 执行策略
            auto_execute_threshold: 自动执行置信度阈值
            confirm_threshold: 确认模式置信度阈值
            llm_client: LLM客户端
        """
        self.strategy = strategy
        self.auto_execute_threshold = auto_execute_threshold
        self.confirm_threshold = confirm_threshold
        self.logger = logging.getLogger(__name__)
        
        # 初始化推断服务
        self.inference_service = LLMInferenceService(llm_client=llm_client)
    
    async def execute_intelligent_step(
        self,
        node,
        context: Dict[str, Any]
    ) -> IntelligenceExecutionResult:
        """执行智能步骤
        
        Args:
            node: 行为树节点
            context: 执行上下文（包含黑板数据）
        
        Returns:
            IntelligenceExecutionResult: 执行结果
        """
        import time
        start_time = time.time()
        
        try:
            # 1. 检查参数完整性
            missing_params = self._check_missing_params(node, context)
            
            if not missing_params:
                # 无缺失参数，直接执行
                return IntelligenceExecutionResult(
                    success=True,
                    strategy_used="direct",
                    final_params={}
                )
            
            # 2. 根据策略执行
            if self.strategy == ExecutionStrategy.INFER:
                result = await self._execute_inference_only(
                    node, missing_params, context
                )
            elif self.strategy == ExecutionStrategy.CONFIRM:
                # CONFIRM 策略：由工具端处理确认
                result = IntelligenceExecutionResult(
                    success=True,
                    strategy_used="confirm",
                    final_params={}
                )
            elif self.strategy == ExecutionStrategy.INTELLIGENT:
                result = await self._execute_hybrid(
                    node, missing_params, context
                )
            else:
                result = IntelligenceExecutionResult(
                    success=False,
                    strategy_used="unknown",
                    final_params={},
                    error=f"未知的执行策略: {self.strategy}"
                )
            
            result.execution_time_ms = (time.time() - start_time) * 1000
            return result
            
        except Exception as e:
            self.logger.error(f"智能执行失败: {e}")
            return IntelligenceExecutionResult(
                success=False,
                strategy_used="error",
                final_params={},
                execution_time_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )
    
    def _check_missing_params(
        self,
        node,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """检查缺失的参数"""
        missing = []
        
        # 获取节点配置中的参数
        config = getattr(node, 'config', {})
        parameters = config.get('parameters', {})
        
        for param_name, param_config in parameters.items():
            # 检查参数值是否已存在
            value = context.get(param_name)
            if value is None or value == '':
                # 处理参数配置，可能是字典或字符串
                if isinstance(param_config, dict):
                    description = param_config.get('description', '')
                    param_type = param_config.get('type', 'string')
                    required = param_config.get('required', True)
                else:
                    description = ''
                    param_type = 'string'
                    required = True
                
                missing.append({
                    'name': param_name,
                    'description': description,
                    'type': param_type,
                    'required': required
                })
        
        return missing
    
    async def _execute_inference_only(
        self,
        node,
        missing_params: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> IntelligenceExecutionResult:
        """纯推断模式"""
        inference_result = await self.inference_service.infer(
            node_type=type(node).__name__,
            tool_name=getattr(node, 'tool_name', ''),
            missing_params=missing_params,
            context=context
        )
        
        if inference_result.success:
            return IntelligenceExecutionResult(
                success=True,
                strategy_used="inference",
                final_params=inference_result.inferred_params,
                inference_result=inference_result
            )
        else:
            return IntelligenceExecutionResult(
                success=False,
                strategy_used="inference_failed",
                final_params={},
                inference_result=inference_result,
                error=inference_result.error
            )
    
    async def _execute_hybrid(
        self,
        node,
        missing_params: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> IntelligenceExecutionResult:
        """混合模式"""
        # 1. 先尝试推断
        inference_result = await self.inference_service.infer(
            node_type=type(node).__name__,
            tool_name=getattr(node, 'tool_name', ''),
            missing_params=missing_params,
            context=context
        )
        
        confidence = inference_result.confidence
        
        # 2. 根据置信度决定策略
        if confidence >= self.auto_execute_threshold:
            # 高置信度：自动执行
            self.logger.info(f"高置信度({confidence:.2f})，自动执行")
            return IntelligenceExecutionResult(
                success=True,
                strategy_used="hybrid_auto",
                final_params=inference_result.inferred_params,
                inference_result=inference_result
            )
        
        elif confidence >= self.confirm_threshold:
            # 中置信度：需要工具确认
            self.logger.info(f"中置信度({confidence:.2f})，需要工具确认")
            return IntelligenceExecutionResult(
                success=True,
                strategy_used="hybrid_confirm",
                final_params=inference_result.inferred_params,
                inference_result=inference_result
            )
        
        else:
            # 低置信度：推断失败
            self.logger.warning(f"低置信度({confidence:.2f})，推断失败")
            return IntelligenceExecutionResult(
                success=False,
                strategy_used="hybrid_failed",
                final_params={},
                inference_result=inference_result,
                error=f"推断置信度过低: {confidence:.2f}"
            )