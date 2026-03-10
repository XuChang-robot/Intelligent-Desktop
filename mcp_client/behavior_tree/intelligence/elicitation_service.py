# Elicitation 服务
# 负责在参数缺失时引导用户补充信息

import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class ElicitationType(Enum):
    """Elicitation 类型"""
    PARAMETER_MISSING = "parameter_missing"  # 参数缺失
    CONFIRMATION = "confirmation"            # 确认操作
    DANGEROUS_OPERATION = "dangerous_operation"  # 危险操作确认
    AMBIGUITY_RESOLUTION = "ambiguity_resolution"  # 歧义消解
    PARTIAL_INFERENCE = "partial_inference"  # 部分推断确认


@dataclass
class ElicitationRequest:
    """Elicitation 请求"""
    type: ElicitationType
    node_id: str
    node_name: str
    tool_name: str
    message: str
    missing_params: List[Dict[str, Any]]
    suggested_values: Dict[str, Any] = field(default_factory=dict)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 300
    allow_modify: bool = True
    countdown_seconds: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'type': self.type.value,
            'node_id': self.node_id,
            'node_name': self.node_name,
            'tool_name': self.tool_name,
            'message': self.message,
            'missing_params': self.missing_params,
            'suggested_values': self.suggested_values,
            'confidence_scores': self.confidence_scores,
            'context': self.context,
            'timeout_seconds': self.timeout_seconds,
            'allow_modify': self.allow_modify,
            'countdown_seconds': self.countdown_seconds
        }


@dataclass
class ElicitationResponse:
    """Elicitation 响应"""
    success: bool
    user_input: Dict[str, Any]
    action: str  # "confirm", "modify", "cancel", "timeout"
    modified_params: List[str] = field(default_factory=list)
    error: Optional[str] = None


class ElicitationService:
    """Elicitation 服务
    
    负责在关键参数缺失或需要确认时，引导用户补充信息。
    支持多种Elicitation类型和交互模式。
    """
    
    def __init__(
        self,
        timeout_seconds: int = 300,
        default_countdown: int = 5
    ):
        """
        Args:
            timeout_seconds: 默认超时时间
            default_countdown: 默认倒计时秒数（用于确认模式）
        """
        self.timeout_seconds = timeout_seconds
        self.default_countdown = default_countdown
        self.logger = logging.getLogger(__name__)
        
        # 存储活动的Elicitation请求
        self.active_requests: Dict[str, ElicitationRequest] = {}
    
    async def elicit(
        self,
        request: ElicitationRequest,
        user_callback: Callable[[ElicitationRequest], Dict[str, Any]]
    ) -> ElicitationResponse:
        """执行Elicitation
        
        Args:
            request: Elicitation请求
            user_callback: 用户交互回调函数
        
        Returns:
            ElicitationResponse: 用户响应
        """
        self.logger.info(f"触发Elicitation: {request.node_name} ({request.type.value})")
        
        # 存储请求
        self.active_requests[request.node_id] = request
        
        try:
            # 调用用户交互回调
            user_result = await self._call_user_callback(request, user_callback)
            
            # 处理用户响应
            response = self._process_user_response(request, user_result)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Elicitation失败: {e}")
            return ElicitationResponse(
                success=False,
                user_input={},
                action="error",
                error=str(e)
            )
        finally:
            # 清理请求
            if request.node_id in self.active_requests:
                del self.active_requests[request.node_id]
    
    def create_parameter_elicitation(
        self,
        node_id: str,
        node_name: str,
        tool_name: str,
        missing_params: List[Dict[str, Any]],
        suggested_values: Optional[Dict[str, Any]] = None,
        confidence_scores: Optional[Dict[str, float]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ElicitationRequest:
        """创建参数缺失Elicitation请求"""
        
        # 构建消息
        param_list = ", ".join([p['name'] for p in missing_params])
        message = f"执行'{node_name}'需要以下参数：{param_list}"
        
        # 如果有建议值，添加到消息
        if suggested_values:
            message += "\n\n系统已推断以下值（请确认或修改）："
            for param_name, value in suggested_values.items():
                confidence = confidence_scores.get(param_name, 0.0) if confidence_scores else 0.0
                message += f"\n• {param_name}: {value} (置信度: {confidence:.0%})"
        
        return ElicitationRequest(
            type=ElicitationType.PARAMETER_MISSING,
            node_id=node_id,
            node_name=node_name,
            tool_name=tool_name,
            message=message,
            missing_params=missing_params,
            suggested_values=suggested_values or {},
            confidence_scores=confidence_scores or {},
            context=context or {},
            timeout_seconds=self.timeout_seconds,
            allow_modify=True
        )
    
    def create_confirmation_elicitation(
        self,
        node_id: str,
        node_name: str,
        tool_name: str,
        inferred_params: Dict[str, Any],
        confidence: float,
        reasoning: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ElicitationRequest:
        """创建确认Elicitation请求"""
        
        # 构建消息
        message = f"系统将基于推断执行'{node_name}':\n\n"
        
        for param_name, value in inferred_params.items():
            message += f"• {param_name}: {value}\n"
        
        message += f"\n推断依据: {reasoning}\n"
        message += f"置信度: {confidence:.0%}"
        
        if confidence >= 0.85:
            message += "\n\n高置信度，建议直接执行。"
        elif confidence >= 0.60:
            message += f"\n\n[{self.default_countdown}秒]后自动确认..."
        
        return ElicitationRequest(
            type=ElicitationType.CONFIRMATION,
            node_id=node_id,
            node_name=node_name,
            tool_name=tool_name,
            message=message,
            missing_params=[],  # 确认模式下没有缺失参数
            suggested_values=inferred_params,
            confidence_scores={'overall': confidence},
            context=context or {},
            timeout_seconds=self.timeout_seconds,
            allow_modify=True,
            countdown_seconds=self.default_countdown if confidence >= 0.60 else None
        )
    
    def create_dangerous_operation_elicitation(
        self,
        node_id: str,
        node_name: str,
        tool_name: str,
        operation_details: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ElicitationRequest:
        """创建危险操作Elicitation请求"""
        
        message = f"⚠️ 警告：'{node_name}'可能是一个危险操作！\n\n"
        message += f"操作详情:\n"
        
        for key, value in operation_details.items():
            message += f"• {key}: {value}\n"
        
        message += "\n请确认是否继续执行？"
        
        return ElicitationRequest(
            type=ElicitationType.DANGEROUS_OPERATION,
            node_id=node_id,
            node_name=node_name,
            tool_name=tool_name,
            message=message,
            missing_params=[],
            suggested_values={},
            confidence_scores={},
            context=context or {},
            timeout_seconds=self.timeout_seconds,
            allow_modify=False,  # 危险操作不允许修改，只能确认或取消
            countdown_seconds=None  # 危险操作不自动确认
        )
    
    def create_partial_inference_elicitation(
        self,
        node_id: str,
        node_name: str,
        tool_name: str,
        pre_filled_params: Dict[str, Any],
        to_ask_params: List[Dict[str, Any]],
        confidence_scores: Dict[str, float],
        context: Optional[Dict[str, Any]] = None
    ) -> ElicitationRequest:
        """创建部分推断Elicitation请求"""
        
        message = f"请确认并补充'{node_name}'的参数:\n\n"
        
        # 已预填写的参数
        if pre_filled_params:
            message += "✓ 已自动填写（请确认）:\n"
            for param_name, value in pre_filled_params.items():
                confidence = confidence_scores.get(param_name, 0.0)
                highlight = "✓" if confidence > 0.7 else "~"
                message += f"  {highlight} {param_name}: {value} ({confidence:.0%})\n"
        
        # 需要用户填写的参数
        if to_ask_params:
            message += "\n✏️ 需要您填写:\n"
            for param in to_ask_params:
                param_name = param['name']
                description = param.get('description', '')
                suggested = param.get('suggested_value', '')
                
                message += f"  • {param_name}"
                if description:
                    message += f" ({description})"
                if suggested:
                    message += f"\n    建议值: {suggested}"
                message += "\n"
        
        return ElicitationRequest(
            type=ElicitationType.PARTIAL_INFERENCE,
            node_id=node_id,
            node_name=node_name,
            tool_name=tool_name,
            message=message,
            missing_params=to_ask_params,
            suggested_values=pre_filled_params,
            confidence_scores=confidence_scores,
            context=context or {},
            timeout_seconds=self.timeout_seconds,
            allow_modify=True
        )
    
    async def _call_user_callback(
        self,
        request: ElicitationRequest,
        user_callback: Callable[[ElicitationRequest], Dict[str, Any]]
    ) -> Dict[str, Any]:
        """调用用户交互回调"""
        import asyncio
        
        # 设置超时
        try:
            result = await asyncio.wait_for(
                user_callback(request),
                timeout=request.timeout_seconds
            )
            return result
        except asyncio.TimeoutError:
            self.logger.warning(f"Elicitation超时: {request.node_id}")
            return {
                'action': 'timeout',
                'user_input': {}
            }
    
    def _process_user_response(
        self,
        request: ElicitationRequest,
        user_result: Dict[str, Any]
    ) -> ElicitationResponse:
        """处理用户响应"""
        action = user_result.get('action', 'cancel')
        user_input = user_result.get('user_input', {})
        
        if action == 'timeout' and request.countdown_seconds:
            # 超时且启用了倒计时，默认确认
            self.logger.info(f"倒计时结束，默认确认: {request.node_id}")
            return ElicitationResponse(
                success=True,
                user_input=request.suggested_values,
                action='confirm'
            )
        
        elif action == 'confirm':
            # 用户确认
            # 合并建议值和用户输入
            final_input = {**request.suggested_values, **user_input}
            
            return ElicitationResponse(
                success=True,
                user_input=final_input,
                action='confirm',
                modified_params=list(user_input.keys())
            )
        
        elif action == 'modify':
            # 用户修改
            return ElicitationResponse(
                success=True,
                user_input=user_input,
                action='modify',
                modified_params=list(user_input.keys())
            )
        
        elif action == 'cancel':
            # 用户取消
            return ElicitationResponse(
                success=False,
                user_input={},
                action='cancel'
            )
        
        else:
            # 未知操作
            return ElicitationResponse(
                success=False,
                user_input={},
                action='unknown',
                error=f"未知的操作类型: {action}"
            )
    
    def check_dangerous_operation(
        self,
        tool_name: str,
        tool_args: Dict[str, Any]
    ) -> Optional[str]:
        """检查是否为危险操作"""
        dangerous_patterns = [
            # 文件系统危险操作
            ('file_operations', 'delete', True),  # 删除操作
            ('file_operations', 'move', True),    # 移动操作
            ('system_command', 'command', ['rm -rf', 'format', 'shutdown', 'reboot', 'del /f', 'rd /s']),
        ]
        
        for pattern_tool, pattern_arg, dangerous_value in dangerous_patterns:
            if tool_name == pattern_tool:
                arg_value = tool_args.get(pattern_arg, '')
                
                if isinstance(dangerous_value, bool):
                    # 布尔值表示只要存在该参数就是危险的
                    if dangerous_value and arg_value:
                        return f"检测到危险操作: {pattern_arg}，是否确认执行？"
                
                elif isinstance(dangerous_value, list):
                    # 列表表示检查特定关键词
                    if isinstance(arg_value, str):
                        for keyword in dangerous_value:
                            if keyword in arg_value.lower():
                                return f"检测到危险操作: {keyword}，是否确认执行？"
        
        return None
