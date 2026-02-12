# MCP Server 主文件 - 使用官方FastMCP

import logging
from typing import Dict, Any, Optional, Callable
from pydantic import BaseModel
from mcp.server.fastmcp import FastMCP, Context
from mcp_server.sandbox import SandboxExecutor
from mcp_server.security import SecurityChecker
from config.config import load_config

# 导入工具模块
from mcp_server.tools import file_operations, system_info, text_processing, network_request, document_converter, pdf_processor, email_processor


class ConfirmModel(BaseModel):
    """确认模型"""
    confirmed: bool


class MCPServer:
    def __init__(self):
        self.config = load_config()
        self.sandbox = SandboxExecutor()
        self.security_checker = SecurityChecker()
        self.logger = logging.getLogger(__name__)
        self.output_callback: Optional[Callable[[str], None]] = None
        
        # 创建FastMCP服务器，从配置文件读取端口
        self.mcp = FastMCP(
            "Intelligence_Desktop",
            host=self.config["mcp"]["server"]["host"],
            port=self.config["mcp"]["server"]["port"]
        )
        
        # 注册工具
        self._register_tools()
    
    def set_output_callback(self, callback: Callable[[str], None]):
        """设置输出回调函数"""
        self.output_callback = callback
    
    def _register_tools(self):
        """注册所有工具"""
        # 注册文件系统操作工具
        file_operations.register_file_operations_tools(
            self.mcp,
            security_checker=self.security_checker,
            output_callback=self.output_callback
        )
        
        # 注册系统信息工具
        system_info.register_system_info_tools(self.mcp)
        
        # 注册文本处理工具
        text_processing.register_text_processing_tools(self.mcp)
        
        # 注册网络请求工具
        network_request.register_network_request_tools(self.mcp)
        
        # 注册文档转换工具
        document_converter.register_document_converter_tools(
            self.mcp,
            security_checker=self.security_checker,
            output_callback=self.output_callback
        )
        
        # 注册PDF处理工具
        pdf_processor.register_pdf_processor_tools(
            self.mcp,
            security_checker=self.security_checker,
            output_callback=self.output_callback
        )
        
        # 注册邮件处理工具
        email_processor.register_email_processor_tools(
            self.mcp,
            security_checker=self.security_checker,
            output_callback=self.output_callback
        )
        
        # 注册execute_python工具（兜底工具）
        @self.mcp.tool()
        async def execute_python(code: str, ctx: Context) -> Dict[str, Any]:
            """执行Python代码
            
            Args:
                code: 要执行的Python代码
                ctx: FastMCP上下文，用于elicitation
                
            Returns:
                执行结果，包含success、output、error等字段
            """
            # 检查是否为危险操作
            dangerous_message = self.security_checker.check_dangerous_operation(code)
            if dangerous_message:
                # 使用MCP官方的elicitation机制请求用户确认
                result = await ctx.elicit(
                    message=dangerous_message,
                    schema=ConfirmModel
                )
                
                if result.action != "accept" or not getattr(result.data, "confirmed", False):
                    return {
                        "success": False,
                        "error": "用户取消执行"
                    }
            
            # 创建输出回调函数
            def output_callback(text: str):
                if self.output_callback:
                    self.output_callback(text)
            
            # 在沙箱中执行，使用输出回调
            result = await self.sandbox.execute_code(code, output_callback=output_callback)
            return result
    
    def start(self):
        """启动服务器"""
        host = self.config["mcp"]["server"]["host"]
        port = self.config["mcp"]["server"]["port"]
        
        print(f"MCP Server 启动在 {host}:{port}")
        print(f"使用FastMCP，传输类型: streamable-http")
        print("正在启动服务器...")
        
        try:
            # 使用FastMCP的run方法启动服务器
            # 使用streamable-http传输，host和port已在FastMCP初始化时设置
            self.mcp.run(transport="streamable-http")
        except Exception as e:
            print(f"服务器启动失败: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    # 初始化日志
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 创建服务器实例
    server = MCPServer()
    
    # 启动服务器
    server.start()
