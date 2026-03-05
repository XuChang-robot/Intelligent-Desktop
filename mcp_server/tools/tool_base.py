# 工具基类
# 所有工具都应继承自此类，确保统一的接口和参数验证机制

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from pydantic import BaseModel
from mcp.server.fastmcp import Context


class ToolBase(ABC):
    """工具基类，定义统一的工具接口和参数验证机制"""
    
    # 工具名称
    TOOL_NAME = ""
    
    # 操作类型配置
    OPERATION_CONFIG = {}
    
    @classmethod
    def validate_parameters(cls, operation: str, **kwargs) -> Tuple[Dict[str, Any], Optional[str]]:
        """验证并调整参数
        
        Args:
            operation: 操作类型
            **kwargs: 参数字典
            
        Returns:
            (调整后的参数字典, 配置错误信息)
        """
        params = {
            'operation': operation,
            **kwargs
        }
        
        config_error = None
        
        # 验证operation参数
        if not operation:
            config_error = "operation参数不能为空"
        elif operation not in cls.OPERATION_CONFIG:
            config_error = f"不支持的操作类型: {operation}，支持的操作: {', '.join(cls.OPERATION_CONFIG.keys())}"
        
        # 如果存在配置错误，直接返回
        if config_error:
            return params, config_error
        
        # 获取操作配置
        op_config = cls.OPERATION_CONFIG[operation]
        
        # 验证必需参数
        for param in op_config.get('required_params', []):
            if param not in params or not params[param]:
                config_error = config_error or f"{operation}操作需要{param}参数"
        
        return params, config_error
    
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
    
    def format_success_response(self, result: Any, path: Optional[str] = None) -> Dict[str, Any]:
        """格式化成功响应
        
        Args:
            result: 操作结果
            path: 文件/文件夹路径（如果适用）
            
        Returns:
            格式化的成功响应
        """
        response = {
            "success": True,
            "result": result,
            "formatted_message": f"✅ {str(result)}"
        }
        
        if path:
            response["path"] = path
        
        return response
    
    def format_config_error_response(self, error: str) -> Dict[str, Any]:
        """格式化配置错误响应
        
        Args:
            error: 配置错误信息
            
        Returns:
            格式化的配置错误响应
        """
        return {
            "success": False,
            "config_error": error,
            "formatted_message": f"❌ 配置错误: {error}"
        }
    
    def format_error_response(self, error: str) -> Dict[str, Any]:
        """格式化执行错误响应
        
        Args:
            error: 执行错误信息
            
        Returns:
            格式化的执行错误响应
        """
        return {
            "success": False,
            "error": error,
            "formatted_message": f"❌ 错误: {error}"
        }


# 工具参数模型基类
class ToolParameters(BaseModel):
    """工具参数模型基类"""
    pass


# 工具响应模型
class ToolResponse(BaseModel):
    """工具响应模型"""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    config_error: Optional[str] = None
    formatted_message: Optional[str] = None
    path: Optional[str] = None