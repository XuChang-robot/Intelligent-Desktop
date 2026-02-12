# 网络请求工具

from typing import Dict, Any, Optional


def register_network_request_tools(mcp):
    """注册网络请求工具到MCP服务器
    
    Args:
        mcp: FastMCP实例
    """
    
    @mcp.tool()
    async def network_request(
        method: str,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """网络请求工具
        
        支持发送HTTP请求，包括GET、POST、PUT、DELETE等方法。
        
        Args:
            method: HTTP方法，可选值：
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
                    method=method,
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
                    
                    return {
                        "success": response.status < 400,
                        "status_code": response.status,
                        "data": response_data
                    }
            
        except ImportError:
            return {"success": False, "error": "未安装aiohttp库，请运行: pip install aiohttp"}
        except Exception as e:
            return {"success": False, "error": str(e)}
