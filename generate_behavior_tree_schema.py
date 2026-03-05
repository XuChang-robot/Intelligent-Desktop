#!/usr/bin/env python3
"""
从MCP服务器生成行为树schema的脚本
实现"工具即分支"的方案，为每种工具创建独立的参数schema
"""

import json
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

def create_tool_branch(tool_name: str, tool_schema: dict) -> dict:
    """
    根据MCP工具schema生成精确的oneOf分支
    
    Args:
        tool_name: 工具名称
        tool_schema: 工具的schema定义
    
    Returns:
        工具对应的oneOf分支
    """
    # 获取工具的input_schema
    params_schema = tool_schema.get('input_schema', {})
    
    # 构建精确的参数字段
    properties = {}
    required = params_schema.get('required', [])
    
    for prop_name, prop_schema in params_schema.get('properties', {}).items():
        prop_type = prop_schema.get('type')
        
        # 转换JSON schema类型为Ollama支持的格式
        if prop_type == 'string':
            if 'enum' in prop_schema:
                properties[prop_name] = {
                    'type': 'string',
                    'enum': prop_schema['enum']
                }
            else:
                properties[prop_name] = {'type': 'string'}
        elif prop_type == 'integer':
            properties[prop_name] = {'type': 'integer'}
        elif prop_type == 'number':
            properties[prop_name] = {'type': 'number'}
        elif prop_type == 'boolean':
            properties[prop_name] = {'type': 'boolean'}
        elif prop_type == 'array':
            items_type = prop_schema.get('items', {}).get('type', 'string')
            properties[prop_name] = {
                'type': 'array',
                'items': {'type': items_type}
            }
    
    # 返回完整的Action节点分支
    return {
        "type": "object",
        "properties": {
            "type": {"const": "Action"},
            "name": {"type": "string"},
            "tool": {"const": tool_name},
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False  # 禁止额外字段
            }
        },
        "required": ["type", "name", "tool", "parameters"],
        "additionalProperties": False
    }

def create_condition_branch() -> dict:
    """
    创建Condition节点分支
    
    Returns:
        Condition节点的oneOf分支
    """
    return {
        "type": "object",
        "properties": {
            "type": {"const": "Condition"},
            "name": {"type": "string"},
            "condition": {"type": "string"}
        },
        "required": ["type", "name", "condition"],
        "additionalProperties": False
    }

def create_composite_branch() -> dict:
    """
    创建复合节点分支（Sequence/Selector/Parallel）
    
    Returns:
        复合节点的oneOf分支
    """
    return {
        "type": "object",
        "properties": {
            "type": {"enum": ["Sequence", "Selector", "Parallel"]},
            "name": {"type": "string"},
            "children": {
                "type": "array",
                "items": {"$ref": "#"}  # 递归引用整个schema
            }
        },
        "required": ["type", "name", "children"],
        "additionalProperties": False
    }

async def generate_behavior_tree_schema_from_mcp() -> dict:
    """
    从MCP Server获取所有工具schema，生成完整的行为树schema
    
    Returns:
        完整的行为树schema
    """
    # 连接MCP Server获取工具列表
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server/start_server.py"]
    )
    
    tool_branches = []
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # 获取所有工具的schema
                tools_response = await session.list_tools()
                
                # 为每个工具创建精确分支
                for tool_name, tool_info in tools_response.items():
                    print(f"处理工具: {tool_name}")
                    tool_branch = create_tool_branch(tool_name, tool_info)
                    tool_branches.append(tool_branch)
    except Exception as e:
        print(f"连接MCP服务器失败: {e}")
        # 如果连接失败，手动构建工具分支
        tool_branches = create_manual_tool_branches()
    
    # 添加其他节点类型
    all_branches = [
        *tool_branches,  # 所有工具分支
        create_condition_branch(),  # Condition分支
        create_composite_branch()  # 复合节点分支
    ]
    
    # 最终schema
    return {
        "oneOf": all_branches,
        "$defs": {  # 也可以用definitions
            "behaviorTreeNode": {"$ref": "#"}
        }
    }

def create_manual_tool_branches() -> list:
    """
    手动创建工具分支（当无法连接MCP服务器时使用）
    
    Returns:
        手动构建的工具分支列表
    """
    # 手动定义已知工具的schema
    manual_tools = [
        {
            "tool_name": "file_operations",
            "input_schema": {
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["create", "read", "write", "delete", "move", "copy", "list", "search"]
                    },
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "destination": {"type": "string"},
                    "overwrite": {"type": "boolean"}
                },
                "required": ["operation", "path"]
            }
        },
        {
            "tool_name": "system_info",
            "input_schema": {
                "properties": {
                    "info_type": {
                        "type": "string",
                        "enum": ["os", "cpu", "memory", "disk", "network", "all"]
                    }
                },
                "required": ["info_type"]
            }
        },
        {
            "tool_name": "text_processing",
            "input_schema": {
                "properties": {
                    "text": {"type": "string"},
                    "operation": {
                        "type": "string",
                        "enum": ["summarize", "translate", "extract_keywords", " sentiment_analysis"]
                    },
                    "lang": {"type": "string"}
                },
                "required": ["text", "operation"]
            }
        },
        {
            "tool_name": "network_request",
            "input_schema": {
                "properties": {
                    "url": {"type": "string"},
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST", "PUT", "DELETE"]
                    },
                    "data": {"type": "string"},
                    "headers": {"type": "string"},
                    "params": {"type": "string"}
                },
                "required": ["url", "method"]
            }
        },
        {
            "tool_name": "document_converter",
            "input_schema": {
                "properties": {
                    "input_file": {"type": "string"},
                    "output_format": {
                        "type": "string",
                        "enum": ["pdf", "docx", "txt", "md"]
                    },
                    "output_path": {"type": "string"}
                },
                "required": ["input_file", "output_format"]
            }
        },
        {
            "tool_name": "pdf_processor",
            "input_schema": {
                "properties": {
                    "input_file": {"type": "string"},
                    "operation": {
                        "type": "string",
                        "enum": ["extract_text", "extract_images", "merge", "split"]
                    },
                    "pages": {"type": "string"},
                    "output_path": {"type": "string"}
                },
                "required": ["input_file", "operation"]
            }
        },
        {
            "tool_name": "email_processor",
            "input_schema": {
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["send", "read", "search"]
                    },
                    "recipient": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                    "attachments": {"type": "string"},
                    "smtp_server": {"type": "string"},
                    "smtp_port": {"type": "string"},
                    "smtp_username": {"type": "string"},
                    "smtp_password": {"type": "string"},
                    "imap_server": {"type": "string"},
                    "imap_port": {"type": "string"}
                },
                "required": ["operation"]
            }
        },
        {
            "tool_name": "weather_query",
            "input_schema": {
                "properties": {
                    "province": {"type": "string"},
                    "city": {"type": "string"},
                    "days": {"type": "integer"}
                },
                "required": ["province", "city"]
            }
        }
    ]
    
    # 为每个手动定义的工具创建分支
    branches = []
    for tool in manual_tools:
        branch = create_tool_branch(tool['tool_name'], tool)
        branches.append(branch)
    
    return branches

async def main():
    """
    主函数
    """
    print("开始生成行为树schema...")
    
    # 生成行为树schema
    behavior_tree_schema = await generate_behavior_tree_schema_from_mcp()
    
    # 保存到文件
    output_file = "behavior_tree_schema.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(behavior_tree_schema, f, indent=2, ensure_ascii=False)
    
    print(f"行为树schema已生成并保存到: {output_file}")
    print(f"生成的oneOf分支数量: {len(behavior_tree_schema.get('oneOf', []))}")

if __name__ == "__main__":
    asyncio.run(main())
