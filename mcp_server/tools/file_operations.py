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


# 原因：
# - 统一的参数验证机制确保LLM生成的配置能够被正确验证，避免参数错误导致执行失败
# - 统一的返回格式便于行为树自动修复机制识别配置错误和执行失败，只在配置错误时触发修复
# - 标准化的工具文档和配置格式便于维护和扩展，提高代码可读性
# - config_error字段代表LLM生成的行为树匹配错误，用于与行为树正常的执行失败区分。当config_error非空时，会触发行为树配置修复机制。
# - formatted_message字段为UI提供清晰的操作结果展示，提升用户体验
# - operation参数是工具操作的核心标识符，确保工具能够正确执行指定的操作


# 文件系统操作工具

import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum
from pydantic import BaseModel, Field
from mcp.server.fastmcp import Context
from .security_sandbox import SecurityChecker, create_default_security_checker


# 工具说明：
# 工具名称：file_operations
# 支持的操作类型（operation）：
#   - "create": 创建文件/文件夹
#   - "read": 读取文件内容
#   - "write": 写入文件内容
#   - "delete": 删除文件/文件夹
#   - "move": 移动文件/文件夹
#   - "copy": 复制文件/文件夹
#   - "list": 列出目录内容
#   - "search": 搜索文件
#   - "check_permission": 检查文件/文件夹权限
#   - "read_write": 读写文件内容（支持ReadWriteMode.R_PLUS/ReadWriteMode.W_PLUS/ReadWriteMode.A_PLUS三种模式）
# 必需参数：
#   - operation: 操作类型（必需）
#   - path: 文件/文件夹路径（必需）
# 可选参数：
#   - content: 文件内容（用于write/read_write操作）
#   - destination: 目标路径（用于move/copy操作）
#   - mode: 读写模式（用于read_write操作，ReadWriteMode.R_PLUS表示读写模式文件必须存在，ReadWriteMode.W_PLUS表示读写模式会覆盖文件，ReadWriteMode.A_PLUS表示读写模式追加）
#   - ctx: FastMCP上下文，用于elicitation（可选）
# 
# 参数验证规则：
#   - operation: 必须是支持的操作类型之一
#   - path: 不能为空
#   - destination: move和copy操作时不能为空
# 
# 返回格式：
#   - 成功：{"success": True, "result": "...", "path": "...", "formatted_message": "..."}
#   - 配置错误：{"success": False, "config_error": "..."}
#   - 执行失败：{"success": False, "error": "...", "formatted_message": "..."}


# 操作类型枚举
class FileOperationEnum(str, Enum):
    CREATE = "create"
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    MOVE = "move"
    COPY = "copy"
    LIST = "list"
    SEARCH = "search"
    CHECK_PERMISSION = "check_permission"
    READ_WRITE = "read_write"


# 读写模式枚举
class ReadWriteMode(str, Enum):
    R_PLUS = "r+"
    W_PLUS = "w+"
    A_PLUS = "a+"

# 操作类型配置
OPERATION_CONFIG = {
    'create': {
        'description': '创建文件/文件夹',
        'required_params': ['path'],
        'optional_params': []
    },
    'read': {
        'description': '读取文件内容',
        'required_params': ['path'],
        'optional_params': []
    },
    'write': {
        'description': '写入文件内容',
        'required_params': ['path', 'content'],
        'optional_params': ['overwrite']
    },
    'delete': {
        'description': '删除文件/文件夹',
        'required_params': ['path'],
        'optional_params': []
    },
    'move': {
        'description': '移动文件/文件夹',
        'required_params': ['path', 'destination'],
        'optional_params': []
    },
    'copy': {
        'description': '复制文件/文件夹',
        'required_params': ['path', 'destination'],
        'optional_params': []
    },
    'list': {
        'description': '列出目录内容',
        'required_params': ['path'],
        'optional_params': []
    },
    'search': {
        'description': '搜索文件',
        'required_params': ['path', 'content'],
        'optional_params': []
    },
    'check_permission': {
        'description': '检查文件/文件夹权限',
        'required_params': ['path'],
        'optional_params': []
    },
    'read_write': {
        'description': '读写文件内容',
        'required_params': ['path', 'content'],
        'optional_params': ['mode']
    }
}


def validate_parameters(operation: FileOperationEnum, path: str, destination: str = None, content: str = None, mode: ReadWriteMode = None) -> Tuple[Dict[str, Any], Optional[str]]:
    """验证并调整参数
    
    Args:
        operation: 操作类型
        path: 文件/文件夹路径
        destination: 目标路径
        content: 文件内容
        mode: 读写模式
    
    Returns:
        (调整后的参数字典, 配置错误信息)
    """
    params = {
        'operation': operation,
        'path': path,
        'destination': destination,
        'content': content,
        'mode': mode
    }
    
    config_error = None
    
    # 验证operation参数
    if not operation:
        config_error = "operation参数不能为空"
    elif operation not in OPERATION_CONFIG:
        config_error = f"不支持的操作类型: {operation}，支持的操作: {', '.join(OPERATION_CONFIG.keys())}"
    
    # 如果存在配置错误，直接返回
    if config_error:
        return params, config_error
    
    # 获取操作配置
    op_config = OPERATION_CONFIG[operation]
    
    # 验证必需参数
    for param in op_config['required_params']:
        if param == 'path' and not path:
            config_error = config_error or "path参数不能为空"
        elif param == 'destination' and not destination:
            config_error = config_error or f"{operation}操作需要destination参数"
        elif param == 'content' and not content:
            config_error = config_error or f"{operation}操作需要content参数"
    
    # 验证mode参数（仅用于read_write操作）
    if operation == "read_write" and mode:
        if mode not in [ReadWriteMode.R_PLUS, ReadWriteMode.W_PLUS, ReadWriteMode.A_PLUS]:
            config_error = config_error or f"不支持的读写模式: {mode}，支持的模式: r+、w+、a+"
    
    return params, config_error


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
    # 如果没有提供安全检查器，使用默认的
    if security_checker is None:
        security_checker = create_default_security_checker()
    @mcp.tool()
    async def file_operations(
        operation: FileOperationEnum,
        path: str,
        content: Optional[str] = None,
        destination: Optional[str] = None,
        overwrite: bool = True,
        mode: Optional[ReadWriteMode] = None,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """文件系统操作工具
        
        支持多种文件和文件夹操作，包括创建、读取、写入、删除、移动、复制、列出、搜索和读写。
        
        Args:
            operation: 操作类型
            path: 文件/文件夹路径
            content: 文件内容（用于write/read_write操作）
            destination: 目标路径（用于move/copy操作）
            overwrite: 是否覆盖（用于write操作，默认True表示覆盖模式，会覆盖文件原有内容；False表示追加模式，会在文件末尾追加内容）
            mode: 读写模式（用于read_write操作，ReadWriteMode.R_PLUS表示读写模式文件必须存在，ReadWriteMode.W_PLUS表示读写模式会覆盖文件，ReadWriteMode.A_PLUS表示读写模式追加）
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
            - 写入文件（覆盖模式）: file_operations("write", "test.txt", content="Hello World", overwrite=True)
            - 写入文件（追加模式）: file_operations("write", "test.txt", content="Hello World", overwrite=False)
            - 检查文件权限: file_operations("check_permission", "test.txt")
            - 读写文件（r+模式）: file_operations("read_write", "test.txt", content="New Content", mode=ReadWriteMode.R_PLUS)
            - 读写文件（w+模式）: file_operations("read_write", "test.txt", content="New Content", mode=ReadWriteMode.W_PLUS)
            - 读写文件（a+模式）: file_operations("read_write", "test.txt", content="New Content", mode=ReadWriteMode.A_PLUS)
        """
        try:
            # 参数验证
            params, config_error = validate_parameters(operation, path, destination, content, mode)
            
            # 如果存在配置错误，返回错误
            if config_error:
                return {
                    "success": False,
                    "config_error": config_error
                }
            
            # 处理路径
            processed_path = process_path(params['path'])
            
            # 安全检查
            if security_checker:
                # 检查路径安全
                is_path_safe, path_error = security_checker.check_path(processed_path)
                if not is_path_safe:
                    return {
                        "success": False,
                        "error": path_error,
                        "formatted_message": f"❌ 安全错误: {path_error}"
                    }
                
                # 检查目标路径安全（如果有）
                if params['destination']:
                    dest_path = process_path(params['destination'])
                    is_dest_safe, dest_error = security_checker.check_path(dest_path)
                    if not is_dest_safe:
                        return {
                            "success": False,
                            "error": dest_error,
                            "formatted_message": f"❌ 安全错误: {dest_error}"
                        }
                
                # 检查操作安全
                is_op_safe, op_error = security_checker.check_operation(operation)
                if not is_op_safe:
                    return {
                        "success": False,
                        "error": op_error,
                        "formatted_message": f"❌ 安全错误: {op_error}"
                    }
                
                # 危险操作确认
                if security_checker.is_dangerous_operation(operation) and ctx:
                    dangerous_message = f"检测到危险操作 '{operation}'，要操作的路径: {processed_path}，是否确认执行？"
                    result = await ctx.elicit(
                        message=dangerous_message,
                        schema=ConfirmModel
                    )
                    if result.action != "accept" or not getattr(result.data, "confirmed", False):
                        return {
                            "success": False, 
                            "error": "用户取消执行",
                            "formatted_message": "❌ 用户取消操作"
                        }
            
            print(f"[DEBUG] 当前工作目录: {os.getcwd()}")
            print(f"[DEBUG] 原始路径: {params['path']}")
            print(f"[DEBUG] 原始路径类型: {type(params['path'])}")
            print(f"[DEBUG] 处理后路径: {processed_path}")
            print(f"[DEBUG] 操作: {operation}")
            
            if operation == "create":
                if processed_path.endswith("/") or "." not in os.path.basename(processed_path):
                    # 创建文件夹
                    if os.path.exists(processed_path):
                        return {
                            "success": True, 
                            "result": "文件夹已存在", 
                            "path": processed_path,
                            "formatted_message": f"📁 文件夹已存在\n📍 路径: {processed_path}"
                        }
                    os.makedirs(processed_path, exist_ok=True)
                    return {
                        "success": True, 
                        "result": "文件夹创建成功", 
                        "path": processed_path,
                        "formatted_message": f"✅ 文件夹创建成功\n📁 文件夹: {os.path.basename(processed_path)}\n📍 路径: {processed_path}"
                    }
                else:
                    # 创建文件
                    if os.path.exists(processed_path):
                        return {
                            "success": True, 
                            "result": "文件已存在", 
                            "path": processed_path,
                            "formatted_message": f"📄 文件已存在\n📍 路径: {processed_path}"
                        }
                    dir_path = os.path.dirname(processed_path)
                    if dir_path:
                        os.makedirs(dir_path, exist_ok=True)
                    with open(processed_path, 'w', encoding='utf-8') as f:
                        f.write("")
                    return {
                        "success": True, 
                        "result": "文件创建成功", 
                        "path": processed_path,
                        "formatted_message": f"✅ 文件创建成功\n📄 文件: {os.path.basename(processed_path)}\n📍 路径: {processed_path}"
                    }
            
            elif operation == "write":
                os.makedirs(os.path.dirname(processed_path), exist_ok=True)
                mode = 'a' if not overwrite else 'w'
                content_length = len(content or "")
                with open(processed_path, mode, encoding='utf-8') as f:
                    f.write(content or "")
                return {
                    "success": True, 
                    "result": "文件写入成功", 
                    "path": processed_path,
                    "formatted_message": f"✅ 文件写入成功\n📄 文件: {os.path.basename(processed_path)}\n📍 路径: {processed_path}\n📝 写入模式: {'追加' if not overwrite else '覆盖'}\n📊 写入长度: {content_length} 字符"
                }
            
            elif operation == "read":
                with open(processed_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                content_preview = content[:200] + ("..." if len(content) > 200 else "")
                return {
                    "success": True, 
                    "result": content, 
                    "path": processed_path,
                    "formatted_message": f"📄 文件读取成功\n📍 路径: {processed_path}\n📊 文件长度: {len(content)} 字符\n\n预览:\n{content_preview}"
                }
            
            elif operation == FileOperationEnum.DELETE:
                # 危险操作确认已在安全检查中处理
                
                if os.path.isdir(processed_path):
                    item_type = "文件夹"
                else:
                    item_type = "文件"
                
                if os.path.isdir(processed_path):
                    shutil.rmtree(processed_path)
                else:
                    os.remove(processed_path)
                return {
                    "success": True, 
                    "result": "删除成功", 
                    "path": processed_path,
                    "formatted_message": f"✅ 删除成功\n{'📁' if os.path.isdir(processed_path) else '📄'} {item_type}: {os.path.basename(processed_path)}"
                }
            
            elif operation == FileOperationEnum.LIST:
                items = os.listdir(processed_path)
                files = [item for item in items if os.path.isfile(os.path.join(processed_path, item))]
                folders = [item for item in items if os.path.isdir(os.path.join(processed_path, item))]
                
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
                
                message = f"📋 目录内容\n📍 路径: {processed_path}\n📊 总计: {len(folders)}个文件夹, {len(files)}个文件\n\n" + "\n".join(formatted_items)
                
                return {
                    "success": True, 
                    "result": items, 
                    "path": processed_path,
                    "formatted_message": message
                }
            
            elif operation == FileOperationEnum.MOVE:
                # 危险操作确认已在安全检查中处理
                
                if not destination:
                    return {
                        "success": False, 
                        "error": "move操作需要destination参数",
                        "formatted_message": "❌ 错误: move操作需要destination参数"
                    }
                dest_path = process_path(destination)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.move(processed_path, dest_path)
                return {
                    "success": True, 
                    "result": "移动成功", 
                    "path": dest_path,
                    "formatted_message": f"✅ 移动成功\n📄 项目: {os.path.basename(processed_path)}\n📍 目标路径: {dest_path}"
                }
            
            elif operation == FileOperationEnum.COPY:
                if not destination:
                    return {
                        "success": False, 
                        "error": "copy操作需要destination参数",
                        "formatted_message": "❌ 错误: copy操作需要destination参数"
                    }
                dest_path = process_path(destination)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                if os.path.isdir(processed_path):
                    shutil.copytree(processed_path, dest_path, dirs_exist_ok=True)
                else:
                    shutil.copy2(processed_path, dest_path)
                return {
                    "success": True, 
                    "result": "复制成功", 
                    "path": dest_path,
                    "formatted_message": f"✅ 复制成功\n{'📁' if os.path.isdir(processed_path) else '📄'} {'文件夹' if os.path.isdir(processed_path) else '文件'}: {os.path.basename(processed_path)}\n📍 目标路径: {dest_path}"
                }
            
            elif operation == FileOperationEnum.SEARCH:
                matches = []
                for root, dirs, files in os.walk(processed_path):
                    # 限制搜索深度
                    depth = root[len(processed_path):].count(os.sep)
                    if depth > 10:  # 限制深度为10
                        dirs[:] = []  # 清空dirs，停止递归
                        continue
                    
                    for file in files:
                        if content and content.lower() in file.lower():
                            matches.append(os.path.join(root, file))
                
                formatted_matches = []
                for match in matches[:10]:  # 只显示前10个
                    formatted_matches.append(f"  - {os.path.basename(match)}")
                if len(matches) > 10:
                    formatted_matches.append(f"  ... 等{len(matches) - 10}个文件")
                
                message = f"🔍 搜索结果\n📍 搜索路径: {processed_path}\n🔤 搜索关键词: {content}\n📊 找到 {len(matches)} 个匹配文件\n\n" + "\n".join(formatted_matches)
                
                return {
                    "success": True, 
                    "result": matches[:50], 
                    "path": processed_path,
                    "formatted_message": message
                }
            
            elif operation == FileOperationEnum.CHECK_PERMISSION:
                if not os.path.exists(processed_path):
                    return {
                        "success": True,
                        "result": {
                            "exists": False,
                            "readable": False,
                            "writable": False,
                            "executable": False,
                            "is_file": False,
                            "is_dir": False
                        },
                        "path": processed_path,
                        "formatted_message": f"🔍 文件权限检查完成\n📍 路径: {processed_path}\n❌ 文件/文件夹不存在"
                    }
                
                is_file = os.path.isfile(processed_path)
                is_dir = os.path.isdir(processed_path)
                readable = os.access(processed_path, os.R_OK)
                writable = os.access(processed_path, os.W_OK)
                executable = os.access(processed_path, os.X_OK)
                
                permission_status = []
                if readable:
                    permission_status.append("✅ 可读")
                else:
                    permission_status.append("❌ 不可读")
                
                if writable:
                    permission_status.append("✅ 可写")
                else:
                    permission_status.append("❌ 不可写")
                
                if executable:
                    permission_status.append("✅ 可执行")
                else:
                    permission_status.append("❌ 不可执行")
                
                message = f"🔍 文件权限检查完成\n{'📄' if is_file else '📁'} {'文件' if is_file else '文件夹'}: {os.path.basename(processed_path)}\n📍 路径: {processed_path}\n\n权限状态:\n" + "\n".join(permission_status)
                
                return {
                    "success": True,
                    "result": {
                        "exists": True,
                        "readable": readable,
                        "writable": writable,
                        "executable": executable,
                        "is_file": is_file,
                        "is_dir": is_dir
                    },
                    "path": processed_path,
                    "formatted_message": message
                }
            
            elif operation == FileOperationEnum.READ_WRITE:
                if not mode:
                    mode = ReadWriteMode.W_PLUS  # 默认使用w+模式
                
                # 检查文件是否存在（r+模式需要文件存在）
                if mode == ReadWriteMode.R_PLUS and not os.path.exists(processed_path):
                    return {
                        "success": False,
                        "error": "文件不存在",
                        "formatted_message": f"❌ 错误: r+模式需要文件存在，但文件 '{processed_path}' 不存在"
                    }
                
                os.makedirs(os.path.dirname(processed_path), exist_ok=True)
                
                # 读取原文件内容（如果文件存在）
                original_content = ""
                if os.path.exists(processed_path):
                    try:
                        with open(processed_path, 'r', encoding='utf-8') as f:
                            original_content = f.read()
                    except Exception as e:
                        return {
                            "success": False,
                            "error": f"读取文件失败: {str(e)}",
                            "formatted_message": f"❌ 错误: 读取文件失败 - {str(e)}"
                        }
                
                # 写入新内容
                try:
                    with open(processed_path, mode.value, encoding='utf-8') as f:
                        if mode == ReadWriteMode.R_PLUS:
                            # r+模式：读取后修改，保留原内容
                            f.seek(0)
                            f.write(content or "")
                        elif mode == ReadWriteMode.W_PLUS:
                            # w+模式：覆盖文件
                            f.write(content or "")
                        elif mode == ReadWriteMode.A_PLUS:
                            # a+模式：追加内容
                            f.write(content or "")
                    
                    content_length = len(content or "")
                    mode_desc = {
                        ReadWriteMode.R_PLUS: '读写模式（文件必须存在）',
                        ReadWriteMode.W_PLUS: '读写模式（覆盖文件）',
                        ReadWriteMode.A_PLUS: '读写模式（追加内容）'
                    }.get(mode, '未知模式')
                    
                    return {
                        "success": True,
                        "result": "文件读写成功",
                        "path": processed_path,
                        "formatted_message": f"✅ 文件读写成功\n📄 文件: {os.path.basename(processed_path)}\n📍 路径: {processed_path}\n📝 模式: {mode_desc}\n📊 写入长度: {content_length} 字符"
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"文件读写失败: {str(e)}",
                        "formatted_message": f"❌ 错误: 文件读写失败 - {str(e)}"
                    }
            
            else:
                return {
                    "success": False, 
                    "error": f"不支持的操作: {operation.value}",
                    "formatted_message": f"❌ 错误: 不支持的操作 '{operation.value}'"
                }
        
        except Exception as e:
            return {
                "success": False, 
                "error": str(e),
                "formatted_message": f"❌ 错误: {str(e)}"
            }
