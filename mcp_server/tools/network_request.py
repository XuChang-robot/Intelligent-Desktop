from enum import Enum
from typing import Dict, Any, Optional, Tuple
from mcp.server.fastmcp import Context
from .tool_base import ToolBase, ToolResult, OperationConfig, register_tool


class NetworkOperationEnum(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


@register_tool("network_request")
class NetworkRequestTool(ToolBase):
    """网络请求工具
    
    支持发送HTTP请求，包括GET、POST、PUT、DELETE等方法。
    """
    
    TOOL_NAME = "network_request"
    
    OPERATION_CONFIG = {
        'GET': OperationConfig(
            description='获取数据',
            required_params=['url'],
            optional_params=['headers', 'params'],
            is_dangerous=False
        ),
        'POST': OperationConfig(
            description='提交数据',
            required_params=['url'],
            optional_params=['data', 'headers', 'params'],
            is_dangerous=False
        ),
        'PUT': OperationConfig(
            description='更新数据',
            required_params=['url'],
            optional_params=['data', 'headers', 'params'],
            is_dangerous=False
        ),
        'DELETE': OperationConfig(
            description='删除数据',
            required_params=['url'],
            optional_params=['headers', 'params'],
            is_dangerous=False
        )
    }
    
    async def execute(self, ctx: Optional[Context] = None, **kwargs) -> Dict[str, Any]:
        """执行网络请求"""
        operation = kwargs.get('operation')
        url = kwargs.get('url')
        data = kwargs.get('data')
        headers = kwargs.get('headers')
        params = kwargs.get('params')
        
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=operation,
                    url=url,
                    json=data,
                    headers=headers,
                    params=params
                ) as response:
                    response_text = await response.text()
                    try:
                        response_data = await response.json()
                    except:
                        response_data = response_text
                    
                    status_success = response.status < 400
                    
                    if status_success:
                        message_parts = [
                            f"🌐 网络请求成功",
                            f"📡 方法: {operation}",
                            f"🔗 URL: {url}",
                            f"✅ 状态码: {response.status}"
                        ]
                        
                        if params:
                            message_parts.append(f"📝 URL参数: {params}")
                        
                        if isinstance(response_data, dict):
                            data_preview = str(response_data)[:200] + ("..." if len(str(response_data)) > 200 else "")
                            message_parts.append(f"\n📄 响应数据预览:")
                            message_parts.append(data_preview)
                        elif isinstance(response_data, str):
                            data_preview = response_data[:200] + ("..." if len(response_data) > 200 else "")
                            message_parts.append(f"\n📄 响应文本预览:")
                            message_parts.append(data_preview)
                        
                        return (ToolResult.success(response_data)
                            .with_extra("status_code", response.status)
                            .with_message("\n".join(message_parts))
                            .build())
                    else:
                        return (ToolResult.error(f"HTTP {response.status}: {response_text[:200]}")
                            .with_extra("status_code", response.status)
                            .with_message(f"❌ 网络请求失败\n📡 方法: {operation}\n🔗 URL: {url}\n❌ 状态码: {response.status}\n📄 错误信息: {response_text[:200]}{'...' if len(response_text) > 200 else ''}")
                            .build())
        
        except ImportError:
            return ToolResult.error("未安装aiohttp库，请运行: pip install aiohttp").build()
        except Exception as e:
            return ToolResult.error(str(e)).build()


def register_network_request_tools(mcp):
    """注册网络请求工具到MCP服务器"""
    tool = NetworkRequestTool()
    
    @mcp.tool()
    async def network_request(
        operation: NetworkOperationEnum,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """网络请求工具
        
        支持发送HTTP请求，包括GET、POST、PUT、DELETE等方法。
        
        Args:
            operation: 操作类型
                - "GET": 获取数据
                - "POST": 提交数据
                - "PUT": 更新数据
                - "DELETE": 删除数据
            url: 请求URL（必需）
        
        POST/PUT 操作参数:
            data: 请求体数据（字典格式）
        
        可选参数:
            headers: 请求头（字典格式）
            params: URL参数（字典格式）
        
        Returns:
            执行结果字典
        """
        return await tool.safe_execute(
            operation=operation,
            url=url,
            data=data,
            headers=headers,
            params=params
        )
    
    return network_request
