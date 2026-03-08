# 工具基类
# 所有工具都应继承自此类，确保统一的接口和参数验证机制

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, Callable, List, Type
from enum import Enum
from pydantic import BaseModel
from mcp.server.fastmcp import Context
import logging


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
        """安全执行工具操作，包含参数验证和异常处理
        
        Args:
            ctx: FastMCP上下文
            **kwargs: 参数字典
            
        Returns:
            执行结果
        """
        try:
            params, config_error = self.validate_parameters(**kwargs)
            
            if config_error:
                return ToolResult.config_error(config_error).build()
            
            return await self.execute(ctx=ctx, **params)
            
        except Exception as e:
            self.logger.error(f"工具执行异常: {e}", exc_info=True)
            return ToolResult.error(str(e)).build()


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
    confirmed: bool


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