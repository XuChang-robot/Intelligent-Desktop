#!/usr/bin/env python3
# MCP Client 启动脚本

import logging
import asyncio
from mcp_client.client import MCPClient, initialize_global_session, close_global_session
from config.config import load_config

# 配置日志
config = load_config()
logging.basicConfig(
    level=getattr(logging, config["logging"]["level"]),
    format=config["logging"]["format"]
)

async def main():
    """主函数"""
    print("正在启动MCP客户端...")
    
    try:
        # 初始化全局会话
        await initialize_global_session()
        
        # 创建客户端实例
        client = MCPClient()
        
        # 测试文件写入操作
        print("\n测试文件写入操作...")
        result = await client.process_user_intent("在当前目录创建一个测试文件，写入'Hello World'")
        print(f"测试结果: {result}")
        
        # 保持客户端运行，等待用户输入
        print("\n客户端已启动，按Ctrl+C退出")
        await asyncio.Future()  # 永久等待
    finally:
        # 关闭全局会话
        await close_global_session()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("客户端已停止")
    except Exception as e:
        logging.error(f"启动客户端出错: {e}")
