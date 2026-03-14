# 工具基类
# 所有工具都应继承自此类，确保统一的接口和参数验证机制

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, Callable, List, Type
from enum import Enum
from pydantic import BaseModel
from mcp.server.fastmcp import Context
import logging
import json

from .tool_llm_client import ToolLLMClient


class ToolResult:
    """工具结果构建器，提供流畅的API构建返回结果"""
    
    def __init__(self):
        self._success: bool = True
        self._result: Any = None
        self._error: Optional[str] = None
        self._config_error: Optional[str] = None
        self._formatted_message: Optional[str] = None
        self._path: Optional[str] = None
        self._extra: Dict[str, Any] = {}
        self._result_blackboard: Optional[Any] = None
    
    @classmethod
    def success(cls, result: Any = None) -> "ToolResult":
        """创建成功结果"""
        instance = cls()
        instance._success = True
        instance._result = result
        return instance
    
    @classmethod
    def error(cls, error: str) -> "ToolResult":
        """创建执行错误结果"""
        instance = cls()
        instance._success = False
        instance._error = error
        instance._formatted_message = f"❌ 错误: {error}"
        return instance
    
    @classmethod
    def config_error(cls, error: str) -> "ToolResult":
        """创建配置错误结果"""
        instance = cls()
        instance._success = False
        instance._config_error = error
        instance._formatted_message = f"❌ 配置错误: {error}"
        return instance
    
    def with_message(self, message: str) -> "ToolResult":
        """设置格式化消息"""
        self._formatted_message = message
        return self
    
    def with_path(self, path: str) -> "ToolResult":
        """设置路径"""
        self._path = path
        return self
    
    def with_extra(self, key: str, value: Any) -> "ToolResult":
        """添加额外字段"""
        self._extra[key] = value
        return self
    
    def with_blackboard(self, value: Any) -> "ToolResult":
        """设置黑板结果（用于行为树节点结果）"""
        self._result_blackboard = value
        return self
    
    def build(self) -> Dict[str, Any]:
        """构建最终结果字典"""
        formatted_message = self._formatted_message or self._generate_default_message()
        result = {
            "success": self._success,
            "formatted_message": formatted_message
        }
        
        if self._result is not None:
            result["result"] = self._result
        if self._error:
            result["error"] = self._error
        if self._config_error:
            result["config_error"] = self._config_error
        if self._path:
            result["path"] = self._path
        
        # 如果设置了 result_blackboard，使用设置的值；否则默认使用 formatted_message
        if self._result_blackboard is not None:
            result["result_blackboard"] = self._result_blackboard
        else:
            result["result_blackboard"] = formatted_message
            
        if self._extra:
            result.update(self._extra)
        
        return result
    
    def _generate_default_message(self) -> str:
        """生成默认消息"""
        if self._success:
            return f"✅ 操作成功"
        elif self._config_error:
            return f"❌ 配置错误: {self._config_error}"
        elif self._error:
            return f"❌ 错误: {self._error}"
        return "操作完成"


class OperationConfig:
    """操作配置"""
    
    def __init__(
        self,
        description: str,
        required_params: List[str] = None,
        optional_params: List[str] = None,
        is_dangerous: bool = False
    ):
        self.description = description
        self.required_params = required_params or []
        self.optional_params = optional_params or []
        self.is_dangerous = is_dangerous


class ToolBase(ABC):
    """工具基类，定义统一的工具接口和参数验证机制"""
    
    TOOL_NAME: str = ""
    OPERATION_CONFIG: Dict[str, OperationConfig] = {}
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @classmethod
    def get_supported_operations(cls) -> List[str]:
        """获取支持的操作类型列表"""
        return list(cls.OPERATION_CONFIG.keys())
    
    @classmethod
    def validate_parameters(cls, operation: str, **kwargs) -> Tuple[Dict[str, Any], Optional[str]]:
        """验证并调整参数
        
        Args:
            operation: 操作类型
            **kwargs: 参数字典
            
        Returns:
            (调整后的参数字典, 配置错误信息)
        """
        params = {'operation': operation, **kwargs}
        config_error = None
        
        if not operation:
            config_error = "operation参数不能为空"
            return params, config_error
        
        if operation not in cls.OPERATION_CONFIG:
            supported = ', '.join(cls.OPERATION_CONFIG.keys())
            config_error = f"不支持的操作类型: {operation}，支持的操作: {supported}"
            return params, config_error
        
        op_config = cls.OPERATION_CONFIG[operation]
        
        for param in op_config.required_params:
            if param not in params or params[param] is None or params[param] == "":
                config_error = config_error or f"{operation}操作需要{param}参数"
        
        return params, config_error
    
    @classmethod
    def is_dangerous_operation(cls, operation: str) -> bool:
        """检查是否为危险操作"""
        if operation in cls.OPERATION_CONFIG:
            return cls.OPERATION_CONFIG[operation].is_dangerous
        return False
    
    @abstractmethod
    async def execute(self, ctx: Optional[Context] = None, **kwargs) -> Dict[str, Any]:
        """执行工具操作
        
        Args:
            ctx: FastMCP上下文，用于elicitation
            **kwargs: 参数字典
            
        Returns:
            执行结果，包含success、result、error等字段
        """
        pass
    
    async def safe_execute(self, ctx: Optional[Context] = None, **kwargs) -> Dict[str, Any]:
        """安全执行工具操作，包含参数验证、推理修正和异常处理
        
        Args:
            ctx: FastMCP上下文
            **kwargs: 参数字典（包含 execution_mode 字段）
            
        Returns:
            执行结果
        """
        try:
            from user_config.config import get_config
            max_inference_attempts = get_config('execution_intelligence.inference.max_attempts', 2)
            
            for attempt in range(max_inference_attempts + 1):
                # 1. 验证参数
                params, config_error = self.validate_parameters(**kwargs)
                
                # 2. 验证通过，执行工具
                if not config_error:
                    return await self.execute(ctx=ctx, **params)
                
                # 3. 验证失败，尝试推理（如果还有尝试次数）
                if attempt < max_inference_attempts and self.has_infer_permission(**kwargs):
                    inference_result = await self._infer_and_fix_parameters(config_error, kwargs)
                    
                    if inference_result['success']:
                        # 推理成功，更新参数，继续验证
                        kwargs = inference_result['params']
                        self.logger.info(f"参数推理修正成功（第 {attempt + 1} 次）")
                        continue
                
                # 4. 推理失败或无推理权限，尝试确认
                if self.has_confirm_permission(**kwargs):
                    return await self._confirm_with_errors(ctx, config_error, kwargs)
                
                # 5. 无任何权限，返回错误
                return ToolResult.config_error(config_error).build()
            
            # 6. 达到最大尝试次数仍未成功
            return ToolResult.config_error("参数验证失败，已达最大推理次数").build()
            
        except Exception as e:
            self.logger.error(f"工具执行异常: {e}", exc_info=True)
            return ToolResult.error(str(e)).build()
    
    def get_execution_mode(self, **kwargs) -> str:
        """获取执行模式
        
        Args:
            **kwargs: 参数字典
            
        Returns:
            执行模式字符串
        """
        return kwargs.get('execution_mode', 'direct')
    
    def has_confirm_permission(self, **kwargs) -> bool:
        """检查是否有确认权限
        
        Args:
            **kwargs: 参数字典
            
        Returns:
            是否有确认权限
        """
        mode = self.get_execution_mode(**kwargs)
        return mode in ['confirm', 'intelligent']
    
    def has_infer_permission(self, **kwargs) -> bool:
        """检查是否有推断权限
        
        Args:
            **kwargs: 参数字典
            
        Returns:
            是否有推断权限
        """
        mode = self.get_execution_mode(**kwargs)
        return mode in ['infer', 'intelligent']
    
    def _get_confirm_model(self):
        """获取确认模型，用于elicitation"""
        return self._ConfirmModel()
    
    async def _trigger_elicitation(self, ctx, message: str) -> bool:
        """触发确认
        
        Args:
            ctx: FastMCP上下文
            message: 确认消息
            
        Returns:
            用户是否确认
        """
        result = await ctx.elicit(
            message=message,
            schema=self._get_confirm_model()
        )
        return result.action == "accept" and getattr(result.data, "confirmed", False)
    
    async def _confirm_with_permission(self, ctx: Optional[Context], message: str, **kwargs) -> bool:
        """根据权限触发确认
        
        Args:
            ctx: FastMCP上下文
            message: 确认消息
            **kwargs: 参数字典（包含 execution_mode）
            
        Returns:
            是否继续执行（True=继续，False=取消）
        """
        if not self.has_confirm_permission(**kwargs) or not ctx:
            return True
        return await self._trigger_elicitation(ctx, message)
    
    async def _infer_and_fix_parameters(self, error: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """推理修正参数
        
        Args:
            error: 参数错误信息
            params: 当前参数字典
            
        Returns:
            推理结果，包含 success 和 params 字段
        """
        try:
            tool_llm_client = ToolLLMClient()
            
            # 获取工具支持的操作和参数信息
            operation = params.get('operation', 'unknown')
            op_config = self.OPERATION_CONFIG.get(operation, None)
            
            # 构建参数说明
            param_info = ""
            if op_config:
                param_info = f"""必需参数: {', '.join(op_config.required_params) if op_config.required_params else '无'}
                                 可选参数: {', '.join(op_config.optional_params) if op_config.optional_params else '无'}
                                 操作说明: {op_config.description}"""
            else:
                # 如果没有操作配置，显示所有支持的操作
                supported_ops = list(self.OPERATION_CONFIG.keys())
                param_info = f"""支持的操作: {', '.join(supported_ops) if supported_ops else '未配置'}
                                 注意: 当前操作 '{operation}' 不在支持列表中"""
            
            prompt = f"""你是一个参数校正大师，请根据已知信息和错误信息分析原因，仅修正引发错误问题的参数并按格式输出。

                        【工具信息】
                        工具名称: {self.TOOL_NAME}
                        操作类型: {operation}

                        【当前参数】
                        {json.dumps(params, ensure_ascii=False, indent=2)}

                        【错误信息】
                        {error}
                        
                        【输出格式】
                        返回 JSON 对象，包含：
                        - success: 是否成功修正引发错误的全部参数（必需）
                        - fixed_params: 修正后的参数对象（必需）
                        - reason: 修正原因说明（可选）

                        ## 示例：
                        如果某工具缺失参数1和参数2，可以合理推断两者值为值1和值2，返回：
                        {{
                        "success": true,
                        "fixed_params": {{"参数1": "值1", "参数2": "值2"}},
                        "reason": "xxx"
                        }}

                        如果无法修正引发错误的全部参数，返回：
                        {{
                        "success": false,
                        "fixed_params": {{}},
                        "reason": "无法推断合理的参数值"
                        }}

                        如果仅能修正引发错误的部分参数，例如参数1可以推断为值1，但是参数2无法推断，返回：
                        {{
                        "success": false,
                        "fixed_params": {{"参数1": "值1" }},
                        "reason": "无法推断全部参数值"
                        }}

                        ## 示例结束

                        注意：只返回JSON，不要包含任何解释、注释或其他文字。
                        """
            
            # 记录提示词
            self.logger.info(f"执行智能参数推理，提示词: {prompt}")

            # 使用结构化输出
            result = await tool_llm_client.generate_structured(prompt)
            
            success = result.get('success', False)
            fixed_params = result.get('fixed_params', {})
            reason = result.get('reason', '')
            
            if not success:
                self.logger.warning(f"参数推理失败: {reason}")
                return {'success': False, 'params': params}
            
            # 合并修正后的参数
            merged_params = {**params, **fixed_params}
            self.logger.info(f"参数推理成功: {reason}。修正前: {json.dumps(params, ensure_ascii=False)}，修正后: {json.dumps(merged_params, ensure_ascii=False)}")
            return {'success': True, 'params': merged_params}
            
        except Exception as e:
            self.logger.error(f"参数推理失败: {e}")
            return {'success': False, 'params': params}
    
    def _create_parameter_fix_model(self, params: Dict[str, Any]) -> Type[BaseModel]:
        """创建参数修正模型
        
        Args:
            params: 当前参数字典
            
        Returns:
            动态创建的参数修正模型
        """
        # 创建注解字典
        annotations = {}
        # 创建字段字典
        fields = {}
        
        for key, value in params.items():
            # 为每个参数添加类型注解
            # 如果值为 None，使用 Optional[str] 类型
            if value is None:
                from typing import Optional
                annotations[key] = Optional[str]
            else:
                annotations[key] = str
            # 设置默认值
            fields[key] = value
        
        # 创建并返回动态模型
        return type('ParameterFixModel', (BaseModel,), {
            '__annotations__': annotations,
            **fields
        })
    
    async def _confirm_with_errors(self, ctx: Optional[Context], error: str, params: Dict[str, Any], attempt: int = 0) -> Dict[str, Any]:
        """参数错误时触发用户修正
        
        Args:
            ctx: FastMCP上下文
            error: 错误信息
            params: 当前参数
            attempt: 当前尝试次数（用于防止无限递归）
            
        Returns:
            执行结果
        """
        if not ctx:
            return ToolResult.config_error(error).build()
        
        # 获取最大尝试次数配置
        from user_config.config import get_config
        max_attempts = get_config('execution_intelligence.inference.max_attempts', 3)
        
        # 检查是否超过最大尝试次数
        if attempt >= max_attempts:
            return ToolResult.error(f"参数验证失败，已达最大尝试次数({max_attempts})").build()
        
        # 创建参数修正模型
        fix_model = self._create_parameter_fix_model(params)
        
        # 构建修正消息
        message = f"""参数验证失败: {error}\n请修正以下参数（第 {attempt + 1}/{max_attempts} 次尝试）："""
        
        # 触发参数修正界面
        result = await ctx.elicit(
            message=message,
            schema=fix_model
        )
        
        if result.action != "accept":
            return ToolResult.error("用户取消执行").build()
        
        # 获取修正后的参数
        # AcceptedElicitation 包含 data 字段，DeclinedElicitation/CancelledElicitation 没有 data
        if hasattr(result, 'data'):
            corrected_params = result.data.model_dump() if hasattr(result.data, 'model_dump') else dict(result.data)
        else:
            return ToolResult.error("用户取消执行").build()
        
        # 验证修正后的参数
        validated_params, validation_error = self.validate_parameters(**corrected_params)
        
        if validation_error:
            # 参数仍有问题，再次触发修正（递归调用，尝试次数+1）
            return await self._confirm_with_errors(ctx, validation_error, corrected_params, attempt + 1)
        
        # 参数验证通过，执行工具
        return await self.execute(ctx=ctx, **validated_params)

    
    def _format_params(self, params: Dict[str, Any]) -> str:
        """格式化参数显示"""
        import json
        return json.dumps(params, ensure_ascii=False, indent=2)
    
    class _ConfirmModel(BaseModel):
        """确认模型，用于elicitation"""
        confirmed: bool = True


class ToolRegistry:
    """工具注册表，管理所有工具的注册和获取"""
    
    _tools: Dict[str, Type[ToolBase]] = {}
    
    @classmethod
    def register(cls, tool_class: Type[ToolBase]) -> Type[ToolBase]:
        """注册工具类"""
        if tool_class.TOOL_NAME:
            cls._tools[tool_class.TOOL_NAME] = tool_class
        return tool_class
    
    @classmethod
    def get(cls, tool_name: str) -> Optional[Type[ToolBase]]:
        """获取工具类"""
        return cls._tools.get(tool_name)
    
    @classmethod
    def get_all(cls) -> Dict[str, Type[ToolBase]]:
        """获取所有注册的工具"""
        return cls._tools.copy()
    
    @classmethod
    def create_instance(cls, tool_name: str) -> Optional[ToolBase]:
        """创建工具实例"""
        tool_class = cls.get(tool_name)
        if tool_class:
            return tool_class()
        return None


def register_tool(tool_name: str):
    """工具注册装饰器
    
    Args:
        tool_name: 工具名称
        
    Returns:
        装饰器函数
    """
    def decorator(cls: Type[ToolBase]) -> Type[ToolBase]:
        cls.TOOL_NAME = tool_name
        ToolRegistry.register(cls)
        return cls
    return decorator


class ConfirmModel(BaseModel):
    """确认模型，用于elicitation"""
    confirmed: bool = True


class ToolParameters(BaseModel):
    """工具参数模型基类"""
    pass


class ToolResponse(BaseModel):
    """工具响应模型"""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    config_error: Optional[str] = None
    formatted_message: Optional[str] = None
    path: Optional[str] = None


def extract_path_from_blackboard(path_value: Any) -> str:
    """从黑板数据中提取单个文件路径
    
    处理行为树传递的路径数据，支持以下格式：
    1. 单个路径字符串: "C:\\Users\\file.txt"
    2. 路径列表字符串: "['C:\\Users\\file1.txt', 'C:\\Users\\file2.txt']"
    3. 实际列表: ['C:\\Users\\file1.txt', 'C:\\Users\\file2.txt']
    4. 逗号分隔的字符串: "'C:\\Users\\file1.txt', 'C:\\Users\\file2.txt'"
    
    Args:
        path_value: 从黑板获取的路径值
        
    Returns:
        第一个文件路径字符串
        
    Raises:
        ValueError: 如果无法提取有效路径
    """
    import ast
    
    if path_value is None:
        raise ValueError("路径值为空")
    
    # 如果已经是字符串路径
    if isinstance(path_value, str):
        path_str = path_value.strip()
        
        # 尝试从字符串列表表示中提取第一个路径
        if path_str.startswith('[') and path_str.endswith(']'):
            try:
                path_list = ast.literal_eval(path_str)
                if isinstance(path_list, list) and len(path_list) > 0:
                    return str(path_list[0]).strip()
            except:
                pass
        
        # 如果是逗号分隔的路径列表，取第一个
        if ',' in path_str and ("'" in path_str or '"' in path_str):
            try:
                # 尝试解析为 Python 表达式
                path_list = ast.literal_eval(f"[{path_str}]")
                if isinstance(path_list, list) and len(path_list) > 0:
                    return str(path_list[0]).strip()
            except:
                # 手动分割
                paths = [p.strip().strip("'\"") for p in path_str.split(',') if p.strip()]
                if paths:
                    return paths[0]
        
        # 普通路径字符串
        return path_str
    
    # 如果是列表，取第一个
    if isinstance(path_value, list):
        if len(path_value) > 0:
            return str(path_value[0]).strip()
        raise ValueError("路径列表为空")
    
    # 其他类型，转换为字符串
    return str(path_value).strip()
