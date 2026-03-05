# MCP Server 启动脚本

import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mcp_server.server import MCPServer
from utils.logging_config import configure_root_logger

# 配置日志
configure_root_logger()

def main():
    """主函数"""
    server = MCPServer()
    server.start()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("服务器已停止")
    except Exception as e:
        logging.error(f"启动服务器出错: {e}")
