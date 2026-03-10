# LLM 推断服务
# 负责在行为树节点执行阶段进行参数推断

import json
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime


@dataclass
class InferenceResult:
    """推断结果"""
    success: bool
    inferred_params: Dict[str, Any]
    confidence: float
    reasoning: str
    sources: List[str]
    alternatives: List[Dict[str, Any]]
    model_used: str
    tokens_used: int
    latency_ms: float
    error: Optional[str] = None


class LLMInferenceService:
    """LLM 推断服务
    
    基于上下文自动推断缺失的参数值。
    使用轻量级模型，追求快速响应。
    """
    
    def __init__(
        self,
        llm_client: Optional[Any] = None,
        model: str = "qwen:1.8b",
        temperature: float = 0.1,
        max_tokens: int = 200
    ):
        """
        Args:
            llm_client: LLM客户端实例（可选，如果为None则使用默认配置）
            model: 使用的模型名称
            temperature: 温度参数（低温度提高确定性）
            max_tokens: 最大生成token数
        """
        self.llm_client = llm_client
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.logger = logging.getLogger(__name__)
        
        # 如果未提供llm_client，创建默认客户端
        if self.llm_client is None:
            from mcp_client.llm import LLMClient
            self.llm_client = LLMClient()
    
    async def infer(
        self,
        node_type: str,
        tool_name: str,
        missing_params: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> InferenceResult:
        """执行推断
        
        Args:
            node_type: 节点类型
            tool_name: 工具名称
            missing_params: 缺失的参数列表
            context: 上下文数据（黑板内容、用户输入等）
        
        Returns:
            InferenceResult: 推断结果
        """
        import time
        start_time = time.time()
        
        try:
            # 1. 构建推断提示词
            prompt = self._build_inference_prompt(
                node_type, tool_name, missing_params, context
            )
            
            # 2. 调用LLM
            response = await self._call_llm(prompt)
            
            # 3. 解析响应
            parsed = self._parse_response(response)
            
            # 4. 评估置信度
            confidence = self._evaluate_confidence(
                parsed, missing_params, context
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            return InferenceResult(
                success=True,
                inferred_params=parsed.get('inferred_params', {}),
                confidence=confidence,
                reasoning=parsed.get('reasoning', ''),
                sources=parsed.get('sources', []),
                alternatives=parsed.get('alternatives', []),
                model_used=self.model,
                tokens_used=parsed.get('tokens_used', 0),
                latency_ms=latency_ms
            )
            
        except Exception as e:
            self.logger.error(f"推断失败: {e}")
            latency_ms = (time.time() - start_time) * 1000
            
            return InferenceResult(
                success=False,
                inferred_params={},
                confidence=0.0,
                reasoning="",
                sources=[],
                alternatives=[],
                model_used=self.model,
                tokens_used=0,
                latency_ms=latency_ms,
                error=str(e)
            )
    
    def _build_inference_prompt(
        self,
        node_type: str,
        tool_name: str,
        missing_params: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> str:
        """构建推断提示词"""
        
        # 格式化缺失参数
        params_desc = []
        for param in missing_params:
            desc = f"- {param['name']}"
            if 'description' in param:
                desc += f": {param['description']}"
            if 'type' in param:
                desc += f" (类型: {param['type']})"
            params_desc.append(desc)
        
        # 格式化上下文
        context_parts = []
        
        if 'user_input' in context:
            context_parts.append(f"用户原始输入: {context['user_input']}")
        
        if 'available_data' in context:
            context_parts.append(f"可用数据: {json.dumps(context['available_data'], ensure_ascii=False, indent=2)}")
        
        if 'user_history' in context and context['user_history']:
            context_parts.append(f"用户历史偏好: {context['user_history']}")
        
        if 'previous_results' in context and context['previous_results']:
            context_parts.append(f"前序节点结果: {json.dumps(context['previous_results'], ensure_ascii=False, indent=2)}")
        
        prompt = f"""你是一个智能参数推断助手。基于提供的上下文，推断缺失的参数值。

## 任务信息
- 节点类型: {node_type}
- 工具名称: {tool_name}

## 需要推断的参数
{chr(10).join(params_desc)}

## 上下文信息
{chr(10).join(context_parts)}

## 输出要求
请输出JSON格式：
{{
    "inferred_params": {{
        "param_name": "inferred_value"
    }},
    "confidence": 0.0-1.0,
    "reasoning": "简要说明推断依据",
    "sources": ["使用的数据源"],
    "alternatives": [
        {{
            "value": "备选值",
            "confidence": 0.0-1.0
        }}
    ]
}}

注意：
1. confidence 表示你对推断结果的置信度（0-1）
2. 如果无法推断，confidence 设为 0
3. 提供 1-2 个备选方案（如果有）
"""
        
        return prompt
    
    async def _call_llm(self, prompt: str) -> str:
        """调用LLM"""
        try:
            # 使用现有的LLM客户端
            if hasattr(self.llm_client, 'generate'):
                response = await self.llm_client.generate(
                    prompt=prompt,
                    system_prompt="你是一个智能参数推断助手。只输出JSON格式，不要添加任何其他内容。",
                    timeout=30
                )
                return response.get('content', '')
            else:
                # 使用Ollama直接调用
                import ollama
                response = ollama.generate(
                    model=self.model,
                    prompt=prompt,
                    system="你是一个智能参数推断助手。只输出JSON格式，不要添加任何其他内容。",
                    options={
                        'temperature': self.temperature,
                        'num_predict': self.max_tokens
                    }
                )
                return response['response']
        except Exception as e:
            self.logger.error(f"LLM调用失败: {e}")
            raise
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析LLM响应"""
        try:
            # 清理响应内容
            response = response.strip()
            
            # 尝试直接解析JSON
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                pass
            
            # 尝试从代码块中提取JSON
            if '```json' in response:
                json_str = response.split('```json')[1].split('```')[0].strip()
                return json.loads(json_str)
            elif '```' in response:
                json_str = response.split('```')[1].split('```')[0].strip()
                return json.loads(json_str)
            
            # 尝试查找JSON对象
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end != -1:
                return json.loads(response[start:end+1])
            
            raise ValueError("无法解析JSON响应")
            
        except Exception as e:
            self.logger.error(f"解析响应失败: {e}")
            return {
                'inferred_params': {},
                'confidence': 0.0,
                'reasoning': f"解析失败: {e}",
                'sources': [],
                'alternatives': []
            }
    
    def _evaluate_confidence(
        self,
        parsed: Dict[str, Any],
        missing_params: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> float:
        """评估置信度
        
        基于多个因素综合评估推断的可靠性。
        """
        base_confidence = parsed.get('confidence', 0.5)
        
        # 因素1：上下文充分性
        context_score = self._calculate_context_score(context, missing_params)
        
        # 因素2：历史匹配度
        history_score = self._calculate_history_score(context, parsed['inferred_params'])
        
        # 因素3：备选方案分散度
        alternative_score = self._calculate_alternative_score(parsed.get('alternatives', []))
        
        # 加权综合
        final_confidence = (
            base_confidence * 0.5 +
            context_score * 0.3 +
            history_score * 0.1 +
            alternative_score * 0.1
        )
        
        return min(max(final_confidence, 0.0), 1.0)
    
    def _calculate_context_score(
        self,
        context: Dict[str, Any],
        missing_params: List[Dict[str, Any]]
    ) -> float:
        """计算上下文充分性分数"""
        score = 0.0
        
        # 有用户输入
        if context.get('user_input'):
            score += 0.3
        
        # 有可用数据
        if context.get('available_data'):
            score += 0.3
        
        # 有用户历史
        if context.get('user_history'):
            score += 0.2
        
        # 有前序节点结果
        if context.get('previous_results'):
            score += 0.2
        
        return score
    
    def _calculate_history_score(
        self,
        context: Dict[str, Any],
        inferred_params: Dict[str, Any]
    ) -> float:
        """计算历史匹配度分数"""
        user_history = context.get('user_history', [])
        if not user_history:
            return 0.5
        
        # 检查推断结果是否与历史偏好匹配
        match_count = 0
        for param_name, param_value in inferred_params.items():
            for history_item in user_history:
                if history_item.get('param_name') == param_name:
                    if history_item.get('preferred_value') == param_value:
                        match_count += 1
                        break
        
        if not inferred_params:
            return 0.5
        
        return match_count / len(inferred_params)
    
    def _calculate_alternative_score(self, alternatives: List[Dict[str, Any]]) -> float:
        """计算备选方案分散度分数
        
        如果备选方案的置信度都很接近，说明不确定性高。
        """
        if not alternatives or len(alternatives) < 2:
            return 0.7  # 没有备选说明比较确定
        
        confidences = [alt.get('confidence', 0) for alt in alternatives]
        if not confidences:
            return 0.5
        
        # 计算置信度差异
        max_conf = max(confidences)
        min_conf = min(confidences)
        diff = max_conf - min_conf
        
        # 差异越大，说明主方案越可靠
        return 0.5 + diff * 0.5
