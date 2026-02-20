# 文件系统操作工具

import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel
from mcp.server.fastmcp import Context


def process_path(path: str) -> str:
    """处理文件路径，支持桌面路径、相对路径和绝对路径
    
    Args:
        path: 原始路径
        
    Returns:
        处理后的完整路径
    """
    # 展开路径中的~符号
    path = os.path.expanduser(path)
    
    # 获取桌面路径
    desktop_path = str(Path.home() / "Desktop")
    
    # 处理桌面路径
    if path == "桌面" or path == "desktop":
        return desktop_path
    elif path.startswith("桌面/") or path.startswith("desktop/"):
        return str(Path(desktop_path) / path.split("/", 1)[1])
    elif path.startswith("桌面\\") or path.startswith("desktop\\"):
        return str(Path(desktop_path) / path.split("\\", 1)[1])
    # 处理相对路径
    elif not os.path.isabs(path) and not path.startswith("./") and not path.startswith(".\\"):
        return str(Path(desktop_path) / path)
    else:
        return path


class ConfirmModel(BaseModel):
    """确认模型"""
    confirmed: bool


def register_file_operations_tools(mcp, security_checker=None, output_callback=None):
    """注册文件系统操作工具到MCP服务器
    
    Args:
        mcp: FastMCP实例
        security_checker: 安全检查器（可选）
        output_callback: 输出回调函数（可选）
    """
    
    @mcp.tool()
    async def file_operations(
        operation: str,
        path: str,
        content: Optional[str] = None,
        destination: Optional[str] = None,
        overwrite: bool = False,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """文件系统操作工具
        
        支持多种文件和文件夹操作，包括创建、读取、写入、删除、移动、复制、列出和搜索。
        
        Args:
            operation: 操作类型，可选值：
                - "create": 创建文件/文件夹
                - "read": 读取文件内容
                - "write": 写入文件内容
                - "delete": 删除文件/文件夹
                - "move": 移动文件/文件夹
                - "copy": 复制文件/文件夹
                - "list": 列出目录内容
                - "search": 搜索文件
            path: 文件/文件夹路径
            content: 文件内容（用于write操作）
            destination: 目标路径（用于move/copy操作）
            overwrite: 是否覆盖（用于write操作）
            ctx: FastMCP上下文，用于elicitation（可选）
        
        Returns:
            {
                "success": True/False,
                "result": 操作结果描述或数据,
                "path": 文件/文件夹路径,
                "error": 错误信息（如果失败）
            }
        
        Examples:
            - 创建文件夹: file_operations("create", "test_folder")
            - 写入文件: file_operations("write", "test.txt", content="Hello World")
        """
        try:
            # 处理路径
            path = process_path(path)
            
            if operation == "create":
                if path.endswith("/") or "." not in os.path.basename(path):
                    # 创建文件夹
                    if os.path.exists(path):
                        return {
                            "success": True, 
                            "result": "文件夹已存在", 
                            "path": path,
                            "formatted_message": f"📁 文件夹已存在\n📍 路径: {path}"
                        }
                    os.makedirs(path, exist_ok=True)
                    return {
                        "success": True, 
                        "result": "文件夹创建成功", 
                        "path": path,
                        "formatted_message": f"✅ 文件夹创建成功\n📁 文件夹: {os.path.basename(path)}\n📍 路径: {path}"
                    }
                else:
                    # 创建文件
                    if os.path.exists(path):
                        return {
                            "success": True, 
                            "result": "文件已存在", 
                            "path": path,
                            "formatted_message": f"📄 文件已存在\n📍 路径: {path}"
                        }
                    dir_path = os.path.dirname(path)
                    if dir_path:
                        os.makedirs(dir_path, exist_ok=True)
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write("")
                    return {
                        "success": True, 
                        "result": "文件创建成功", 
                        "path": path,
                        "formatted_message": f"✅ 文件创建成功\n📄 文件: {os.path.basename(path)}\n📍 路径: {path}"
                    }
            
            elif operation == "write":
                os.makedirs(os.path.dirname(path), exist_ok=True)
                mode = 'w' if overwrite else 'a'
                content_length = len(content or "")
                with open(path, mode, encoding='utf-8') as f:
                    f.write(content or "")
                return {
                    "success": True, 
                    "result": "文件写入成功", 
                    "path": path,
                    "formatted_message": f"✅ 文件写入成功\n📄 文件: {os.path.basename(path)}\n📍 路径: {path}\n📝 写入模式: {'覆盖' if overwrite else '追加'}\n📊 写入长度: {content_length} 字符"
                }
            
            elif operation == "read":
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                content_preview = content[:200] + ("..." if len(content) > 200 else "")
                return {
                    "success": True, 
                    "result": content, 
                    "path": path,
                    "formatted_message": f"📄 文件读取成功\n📍 路径: {path}\n📊 文件长度: {len(content)} 字符\n\n预览:\n{content_preview}"
                }
            
            elif operation == "delete":
                if ctx:
                    dangerous_message = f"检测到文件删除操作，要删除的文件: {path}，是否确认执行？"
                    result = await ctx.elicit(
                        message=dangerous_message,
                        schema=ConfirmModel
                    )
                    if result.action != "accept" or not getattr(result.data, "confirmed", False):
                        return {
                            "success": False, 
                            "error": "用户取消执行",
                            "formatted_message": "❌ 用户取消删除操作"
                        }
                
                if os.path.isdir(path):
                    item_type = "文件夹"
                else:
                    item_type = "文件"
                
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                return {
                    "success": True, 
                    "result": "删除成功", 
                    "path": path,
                    "formatted_message": f"✅ 删除成功\n{'📁' if os.path.isdir(path) else '📄'} {item_type}: {os.path.basename(path)}"
                }
            
            elif operation == "list":
                items = os.listdir(path)
                files = [item for item in items if os.path.isfile(os.path.join(path, item))]
                folders = [item for item in items if os.path.isdir(os.path.join(path, item))]
                
                formatted_items = []
                if folders:
                    formatted_items.append("📁 文件夹:")
                    for folder in folders[:10]:  # 只显示前10个
                        formatted_items.append(f"  - {folder}")
                    if len(folders) > 10:
                        formatted_items.append(f"  ... 等{len(folders) - 10}个文件夹")
                
                if files:
                    formatted_items.append("\n📄 文件:")
                    for file in files[:10]:  # 只显示前10个
                        formatted_items.append(f"  - {file}")
                    if len(files) > 10:
                        formatted_items.append(f"  ... 等{len(files) - 10}个文件")
                
                message = f"📋 目录内容\n📍 路径: {path}\n📊 总计: {len(folders)}个文件夹, {len(files)}个文件\n\n" + "\n".join(formatted_items)
                
                return {
                    "success": True, 
                    "result": items, 
                    "path": path,
                    "formatted_message": message
                }
            
            elif operation == "move":
                if not destination:
                    return {
                        "success": False, 
                        "error": "move操作需要destination参数",
                        "formatted_message": "❌ 错误: move操作需要destination参数"
                    }
                destination = process_path(destination)
                os.makedirs(os.path.dirname(destination), exist_ok=True)
                shutil.move(path, destination)
                return {
                    "success": True, 
                    "result": "移动成功", 
                    "path": destination,
                    "formatted_message": f"✅ 移动成功\n📄 项目: {os.path.basename(path)}\n📍 目标路径: {destination}"
                }
            
            elif operation == "copy":
                if not destination:
                    return {
                        "success": False, 
                        "error": "copy操作需要destination参数",
                        "formatted_message": "❌ 错误: copy操作需要destination参数"
                    }
                destination = process_path(destination)
                os.makedirs(os.path.dirname(destination), exist_ok=True)
                if os.path.isdir(path):
                    shutil.copytree(path, destination, dirs_exist_ok=True)
                else:
                    shutil.copy2(path, destination)
                return {
                    "success": True, 
                    "result": "复制成功", 
                    "path": destination,
                    "formatted_message": f"✅ 复制成功\n{'📁' if os.path.isdir(path) else '📄'} {'文件夹' if os.path.isdir(path) else '文件'}: {os.path.basename(path)}\n📍 目标路径: {destination}"
                }
            
            elif operation == "search":
                matches = []
                for root, dirs, files in os.walk(path):
                    for file in files:
                        if content and content.lower() in file.lower():
                            matches.append(os.path.join(root, file))
                
                formatted_matches = []
                for match in matches[:10]:  # 只显示前10个
                    formatted_matches.append(f"  - {os.path.basename(match)}")
                if len(matches) > 10:
                    formatted_matches.append(f"  ... 等{len(matches) - 10}个文件")
                
                message = f"🔍 搜索结果\n📍 搜索路径: {path}\n🔤 搜索关键词: {content}\n📊 找到 {len(matches)} 个匹配文件\n\n" + "\n".join(formatted_matches)
                
                return {
                    "success": True, 
                    "result": matches[:50], 
                    "path": path,
                    "formatted_message": message
                }
            
            else:
                return {
                    "success": False, 
                    "error": f"不支持的操作: {operation}",
                    "formatted_message": f"❌ 错误: 不支持的操作 '{operation}'"
                }
        
        except Exception as e:
            return {
                "success": False, 
                "error": str(e),
                "formatted_message": f"❌ 错误: {str(e)}"
            }
