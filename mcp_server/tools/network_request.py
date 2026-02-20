# 网络请求工具

from typing import Dict, Any, Optional


def register_network_request_tools(mcp):
    """注册网络请求工具到MCP服务器
    
    Args:
        mcp: FastMCP实例
    """
    
    @mcp.tool()
    async def network_request(
        operation: str,
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
                    
                    # 构建formatted_message
                    status_success = response.status < 400
                    
                    if status_success:
                        # 成功响应
                        message_parts = [
                            f"🌐 网络请求成功",
                            f"📡 方法: {operation}",
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
                        formatted_message = f"❌ 网络请求失败\n📡 方法: {operation}\n🔗 URL: {url}\n❌ 状态码: {response.status}\n📄 错误信息: {response_text[:200]}{'...' if len(response_text) > 200 else ''}"
                    
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
