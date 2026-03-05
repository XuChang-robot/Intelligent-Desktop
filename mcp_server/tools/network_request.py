# 工具创建规则：
# 1. 必须在文件最前面定义工具说明，包括工具名称、支持的操作类型、必需参数、可选参数、参数验证规则和返回格式
# 2. 必须定义操作类型配置（OPERATION_CONFIG或其他类似配置），包含各操作类型的描述、必需参数和可选参数
# 3. 必须实现validate_parameters函数，用于验证和调整参数，返回(调整后的参数字典, 配置错误信息)
# 4. 必须在工具函数开始时调用validate_parameters进行参数验证，如果存在config_error则返回包含config_error字段的错误结果
# 5. 必须统一返回字典格式结果，包含success字段和formatted_message字段
# 6. 配置错误时返回{"success": False, "config_error": "...", "formatted_message": "❌ 配置错误: ..."}
# 7. 执行失败时返回{"success": False, "error": "...", "formatted_message": "❌ 错误: ..."}
# 8. 成功时返回{"success": True, "result": "...", "formatted_message": "✅ ..."}
# 9. 必须包含operation参数，用于指定具体的操作类型
# 10. 只有当返回结果包含config_error字段时，行为树自动修复机制才会触发配置修复
# 11. formatted_message字段是系统返回给UI的信息，必须包含清晰的操作结果描述和状态标识
# 
# 原因：
# - 统一的参数验证机制确保LLM生成的配置能够被正确验证，避免参数错误导致执行失败
# - 统一的返回格式便于行为树自动修复机制识别配置错误和执行失败，只在配置错误时触发修复
# - 标准化的工具文档和配置格式便于维护和扩展，提高代码可读性
# - config_error字段明确区分配置错误和执行失败，避免误触发自动修复机制
# - operation参数是工具操作的核心标识符，确保工具能够正确执行指定的操作
# - 只有通过config_error字段，行为树系统才能准确识别LLM生成的配置错误，从而触发修复机制
# - formatted_message字段为UI提供清晰的操作结果展示，提升用户体验


# 工具说明：
# 工具名称：network_request
# 支持的操作类型（operation）：
#   - "GET": 获取数据
#   - "POST": 提交数据
#   - "PUT": 更新数据
#   - "DELETE": 删除数据
# 必需参数：
#   - operation: 操作类型（必需）
#   - url: 请求URL（必需）
# 可选参数：
#   - data: 请求体数据（用于POST、PUT等）
#   - headers: 请求头（字典格式）
#   - params: URL参数（字典格式）
#
# 参数验证规则：
#   - operation: 必须是支持的操作类型之一
#   - url: 不能为空
#
# 返回格式：
#   - 成功：{"success": True, "status_code": ..., "data": {...}, "formatted_message": "..."}
#   - 配置错误：{"success": False, "config_error": "..."}
#   - 执行失败：{"success": False, "error": "...", "formatted_message": "..."}


from enum import Enum
from typing import Dict, Any, Optional, Tuple


# 操作类型枚举
class NetworkOperationEnum(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"

# 操作类型配置
OPERATION_CONFIG = {
    'GET': {
        'description': '获取数据',
        'required_params': ['url'],
        'optional_params': ['headers', 'params']
    },
    'POST': {
        'description': '提交数据',
        'required_params': ['url'],
        'optional_params': ['data', 'headers', 'params']
    },
    'PUT': {
        'description': '更新数据',
        'required_params': ['url'],
        'optional_params': ['data', 'headers', 'params']
    },
    'DELETE': {
        'description': '删除数据',
        'required_params': ['url'],
        'optional_params': ['headers', 'params']
    }
}


def validate_parameters(operation: NetworkOperationEnum, url: str) -> Tuple[Dict[str, Any], Optional[str]]:
    """验证并调整参数
    
    Args:
        operation: 操作类型
        url: 请求URL
    
    Returns:
        (调整后的参数字典, 配置错误信息)
    """
    params = {
        'operation': operation.value,
        'url': url
    }
    
    config_error = None
    
    # 验证operation参数
    if not operation:
        config_error = "operation参数不能为空"
    elif operation.value not in OPERATION_CONFIG:
        config_error = f"不支持的操作类型: {operation.value}，支持的操作: {', '.join(OPERATION_CONFIG.keys())}"
    
    # 如果存在配置错误，直接返回
    if config_error:
        return params, config_error
    
    # 验证必需参数
    if not url:
        config_error = "url参数不能为空"
    
    return params, config_error


def register_network_request_tools(mcp):
    """注册网络请求工具到MCP服务器
    
    Args:
        mcp: FastMCP实例
    """
    
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
            operation: 操作类型，可选值：
                - "GET": 获取数据
                - "POST": 提交数据
                - "PUT": 更新数据
                - "DELETE": 删除数据
            url: 请求URL
            data: 请求体数据（用于POST、PUT等）
            headers: 请求头（字典格式）
            params: URL参数（字典格式）
        
        Returns:
            {
                "success": True/False,
                "status_code": HTTP状态码,
                "data": 响应数据,
                "error": 错误信息（如果失败）
            }
        
        Examples:
            - GET请求: network_request("GET", "https://api.example.com/data")
            - POST请求: network_request("POST", "https://api.example.com/data", data={"key": "value"})
            - 带参数的GET请求: network_request("GET", "https://api.example.com/search", params={"q": "test"})
        """
        # 验证参数
        validated_params, config_error = validate_parameters(operation, url)
        if config_error:
            return {
                "success": False,
                "config_error": config_error,
                "formatted_message": f"❌ 配置错误: {config_error}"
            }
        
        # 使用验证后的参数
        url = validated_params['url']
        
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.request(
                method=operation.value,
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
                    
                    # 构建formatted_message
                    status_success = response.status < 400
                    
                    if status_success:
                        # 成功响应
                        message_parts = [
                            f"🌐 网络请求成功",
                            f"📡 方法: {operation.value}",
                            f"🔗 URL: {url}",
                            f"✅ 状态码: {response.status}"
                        ]
                        
                        # 添加参数信息
                        if params:
                            message_parts.append(f"📝 URL参数: {params}")
                        
                        # 添加数据预览
                        if isinstance(response_data, dict):
                            data_preview = str(response_data)[:200] + ("..." if len(str(response_data)) > 200 else "")
                            message_parts.append(f"\n📄 响应数据预览:")
                            message_parts.append(data_preview)
                        elif isinstance(response_data, str):
                            data_preview = response_data[:200] + ("..." if len(response_data) > 200 else "")
                            message_parts.append(f"\n📄 响应文本预览:")
                            message_parts.append(data_preview)
                        
                        formatted_message = "\n".join(message_parts)
                    else:
                        # 失败响应
                        formatted_message = f"❌ 网络请求失败\n📡 方法: {operation.value}\n🔗 URL: {url}\n❌ 状态码: {response.status}\n📄 错误信息: {response_text[:200]}{'...' if len(response_text) > 200 else ''}"
                    
                    return {
                        "success": status_success,
                        "status_code": response.status,
                        "data": response_data,
                        "formatted_message": formatted_message
                    }
            
        except ImportError:
            return {
                "success": False, 
                "error": "未安装aiohttp库，请运行: pip install aiohttp",
                "formatted_message": "❌ 错误: 未安装aiohttp库，请运行: pip install aiohttp"
            }
        except Exception as e:
            return {
                "success": False, 
                "error": str(e),
                "formatted_message": f"❌ 错误: {str(e)}"
            }
