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
# 工具名称：document_converter
# 支持的操作类型（operation）：
#   - "pdf_to_word": PDF 转 Word
#   - "word_to_pdf": Word 转 PDF
# 必需参数：
#   - operation: 操作类型（必需）
#   - input_path: 输入文件路径（必需，支持通配符如 *.docx）
#   - output_path: 输出文件路径（必需，可以是文件路径或文件夹路径）
# 可选参数：
#   - ctx: FastMCP上下文，用于elicitation（可选）
#
# 参数验证规则：
#   - operation: 必须是支持的操作类型之一
#   - input_path: 不能为空
#   - output_path: 不能为空
#
# 返回格式：
#   - 成功：{"success": True, "result": "...", "input_path": "...", "output_path": "...", "formatted_message": "..."}
#   - 配置错误：{"success": False, "config_error": "..."}
#   - 执行失败：{"success": False, "error": "...", "formatted_message": "..."}


import os
import subprocess
import glob
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from pydantic import BaseModel
from mcp.server.fastmcp import Context

# 尝试导入必要的库
try:
    from docx import Document
    import docx2pdf
    from pypdf import PdfReader
    import io
except ImportError:
    # 如果导入失败，设置一个标志
    DOCX_AVAILABLE = False
    PDF_AVAILABLE = False
else:
    DOCX_AVAILABLE = True
    PDF_AVAILABLE = True

# 从file_operations导入process_path函数
from mcp_server.tools.file_operations import process_path


# 操作类型枚举
class DocumentOperationEnum(str, Enum):
    PDF_TO_WORD = "pdf_to_word"
    WORD_TO_PDF = "word_to_pdf"

# 操作类型配置
OPERATION_CONFIG = {
    'pdf_to_word': {
        'description': 'PDF 转 Word',
        'required_params': ['input_path', 'output_path'],
        'optional_params': ['ctx']
    },
    'word_to_pdf': {
        'description': 'Word 转 PDF',
        'required_params': ['input_path', 'output_path'],
        'optional_params': ['ctx']
    }
}


def validate_parameters(operation: DocumentOperationEnum, input_path: str, output_path: str) -> Tuple[Dict[str, Any], Optional[str]]:
    """验证并调整参数
    
    Args:
        operation: 操作类型
        input_path: 输入文件路径
        output_path: 输出文件路径
    
    Returns:
        (调整后的参数字典, 配置错误信息)
    """
    params = {
        'operation': operation.value,
        'input_path': input_path,
        'output_path': output_path
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
    if not input_path:
        config_error = config_error or "input_path参数不能为空"
    if not output_path:
        config_error = config_error or "output_path参数不能为空"
    
    return params, config_error


def register_document_converter_tools(mcp, security_checker=None, output_callback=None):
    """注册文档转换工具到MCP服务器
    
    Args:
        mcp: FastMCP实例
        security_checker: 安全检查器（可选）
        output_callback: 输出回调函数（可选）
    """
    
    @mcp.tool()
    async def document_converter(
        operation: DocumentOperationEnum,
        input_path: str,
        output_path: str,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """文档转换工具
        
        支持 PDF 与 Word 文档的互转，支持批量转换（使用通配符如 *.docx）。
        
        Args:
            operation: 操作类型，包括：
                - "pdf_to_word": PDF 转 Word
                - "word_to_pdf": Word 转 PDF
            input_path: 输入文件路径（支持通配符，如 "桌面/*.docx"）
            output_path: 输出文件路径（可以是文件路径或文件夹路径）
            ctx: FastMCP上下文，用于elicitation（可选）
        
        Returns:
            {
                "success": True/False,
                "result": 操作结果描述,
                "input_path": 输入文件路径,
                "output_path": 输出文件路径,
                "error": 错误信息（如果失败）,
                "converted_files": 转换成功的文件列表（批量转换时）,
                "failed_files": 转换失败的文件列表（批量转换时）
            }

        注意：
            - input_path必须是单个文件路径或通配符模式，不能是多个路径的组合。
            - output_path可以是文件路径或文件夹路径。
            - 如果output_path是文件夹，将在该文件夹下生成与输入文件对应的转换文件。

        Examples:
            - PDF 转 Word: document_converter("pdf_to_word", "input.pdf", "output.docx")
            - Word 转 PDF: document_converter("word_to_pdf", "input.docx", "output.pdf")
        """
        # 验证参数
        validated_params, config_error = validate_parameters(operation, input_path, output_path)
        if config_error:
            return {
                "success": False,
                "config_error": config_error,
                "input_path": input_path,
                "output_path": output_path,
                "formatted_message": f"❌ 配置错误: {config_error}"
            }
        
        # 使用验证后的参数
        input_path = validated_params['input_path']
        output_path = validated_params['output_path']
        
        try:
            # 处理路径
            input_path = process_path(input_path)
            output_path = process_path(output_path)
            
            # 检查输入路径是否包含通配符
            if '*' in input_path or '?' in input_path:
                # 批量转换模式
                return await _batch_convert(operation, input_path, output_path)
            
            # 单个文件转换模式
            return await _single_convert(operation, input_path, output_path)
            
        except Exception as e:
            return {
                "success": False, 
                "error": str(e), 
                "input_path": input_path, 
                "output_path": output_path,
                "formatted_message": f"❌ 错误: {str(e)}"
            }


async def _batch_convert(operation: DocumentOperationEnum, input_pattern: str, output_path: str) -> Dict[str, Any]:
    """批量转换文件
    
    Args:
        operation: 操作类型
        input_pattern: 输入文件模式（包含通配符）
        output_path: 输出路径（可以是文件夹或文件）
    
    Returns:
        批量转换结果
    """
    # 使用 glob 匹配文件
    matched_files = glob.glob(input_pattern, recursive=False)
    
    if not matched_files:
        return {
            "success": False,
            "error": f"未找到匹配的文件: {input_pattern}",
            "input_path": input_pattern,
            "output_path": output_path,
            "formatted_message": f"❌ 错误: 未找到匹配的文件\n📍 模式: {input_pattern}"
        }
    
    # 确定输出扩展名
    if operation == DocumentOperationEnum.PDF_TO_WORD:
        output_ext = ".docx"
    elif operation == DocumentOperationEnum.WORD_TO_PDF:
        output_ext = ".pdf"
    else:
        return {
            "success": False,
            "error": f"不支持的操作: {operation.value}",
            "input_path": input_pattern,
            "output_path": output_path,
            "formatted_message": f"❌ 错误: 不支持的操作 '{operation.value}'"
        }
    
    # 检查输出路径是否是文件夹
    if os.path.isdir(output_path):
        output_dir = output_path
    else:
        # 如果不是文件夹，检查是否包含通配符
        if '*' in output_path or '?' in output_path:
            # 输出路径也包含通配符，提取目录部分
            output_dir = os.path.dirname(output_path)
            if not output_dir:
                output_dir = os.getcwd()
        else:
            # 输出路径是单个文件，提取目录
            output_dir = os.path.dirname(output_path)
            if not output_dir:
                output_dir = os.getcwd()
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 批量转换
    converted_files = []
    failed_files = []
    
    for input_file in matched_files:
        # 跳过目录
        if os.path.isdir(input_file):
            continue
        
        # 生成输出文件名
        input_filename = os.path.basename(input_file)
        input_name, _ = os.path.splitext(input_filename)
        output_file = os.path.join(output_dir, input_name + output_ext)
        
        # 执行转换
        result = await _convert_single_file(operation, input_file, output_file)
        
        if result["success"]:
            converted_files.append({
                "input_file": input_file,
                "output_file": output_file,
                "filename": os.path.basename(input_file)
            })
        else:
            failed_files.append({
                "input_file": input_file,
                "output_file": output_file,
                "filename": os.path.basename(input_file),
                "error": result.get("error", "未知错误")
            })
    
    # 生成结果消息
    total_files = len(converted_files) + len(failed_files)
    success_count = len(converted_files)
    failed_count = len(failed_files)
    
    if failed_count == 0:
        message = f"✅ 批量转换完成\n📊 总共: {total_files} 个文件\n✅ 成功: {success_count} 个文件\n📁 输出目录: {output_dir}"
    elif success_count == 0:
        message = f"❌ 批量转换失败\n📊 总共: {total_files} 个文件\n❌ 失败: {failed_count} 个文件"
    else:
        message = f"⚠️ 批量转换部分完成\n📊 总共: {total_files} 个文件\n✅ 成功: {success_count} 个文件\n❌ 失败: {failed_count} 个文件\n📁 输出目录: {output_dir}"
    
    return {
        "success": success_count > 0,
        "result": message,
        "input_path": input_pattern,
        "output_path": output_dir,
        "formatted_message": message,
        "converted_files": converted_files,
        "failed_files": failed_files,
        "total_files": total_files,
        "success_count": success_count,
        "failed_count": failed_count
    }


async def _single_convert(operation: DocumentOperationEnum, input_path: str, output_path: str) -> Dict[str, Any]:
    """单个文件转换
    
    Args:
        operation: 操作类型
        input_path: 输入文件路径
        output_path: 输出文件路径
    
    Returns:
        转换结果
    """
    # 检查输出路径是否是文件夹
    if os.path.isdir(output_path):
        # 如果是文件夹，使用输入文件名（更改扩展名）
        input_filename = os.path.basename(input_path)
        input_name, _ = os.path.splitext(input_filename)
        
        # 根据操作类型确定输出扩展名
        if operation == DocumentOperationEnum.PDF_TO_WORD:
            output_ext = ".docx"
        elif operation == DocumentOperationEnum.WORD_TO_PDF:
            output_ext = ".pdf"
        else:
            output_ext = ""
        
        # 拼接完整的输出路径
        output_path = os.path.join(output_path, input_name + output_ext)
    
    # 确保输出目录存在
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # 执行转换
    return await _convert_single_file(operation, input_path, output_path)


async def _convert_single_file(operation: DocumentOperationEnum, input_path: str, output_path: str) -> Dict[str, Any]:
    """转换单个文件的核心逻辑
    
    Args:
        operation: 操作类型
        input_path: 输入文件路径
        output_path: 输出文件路径
    
    Returns:
        转换结果
    """
    try:
        # 检查文件扩展名是否正确
        if operation == DocumentOperationEnum.PDF_TO_WORD:
            if not input_path.lower().endswith(".pdf"):
                return {
                    "success": False, 
                    "error": "输入文件必须是PDF格式", 
                    "input_path": input_path, 
                    "output_path": output_path,
                    "formatted_message": f"❌ 错误: 输入文件必须是PDF格式\n📄 输入文件: {os.path.basename(input_path)}"
                }
            if not output_path.lower().endswith(".docx"):
                return {
                    "success": False, 
                    "error": "输出文件必须是Word格式(.docx)", 
                    "input_path": input_path, 
                    "output_path": output_path,
                    "formatted_message": f"❌ 错误: 输出文件必须是Word格式(.docx)\n📄 输出文件: {os.path.basename(output_path)}"
                }
        elif operation == DocumentOperationEnum.WORD_TO_PDF:
            if not (input_path.lower().endswith(".docx") or input_path.lower().endswith(".doc")):
                return {
                    "success": False, 
                    "error": "输入文件必须是Word格式(.docx或.doc)", 
                    "input_path": input_path, 
                    "output_path": output_path,
                    "formatted_message": f"❌ 错误: 输入文件必须是Word格式(.docx或.doc)\n📄 输入文件: {os.path.basename(input_path)}"
                }
            if not output_path.lower().endswith(".pdf"):
                return {
                    "success": False, 
                    "error": "输出文件必须是PDF格式", 
                    "input_path": input_path, 
                    "output_path": output_path,
                    "formatted_message": f"❌ 错误: 输出文件必须是PDF格式\n📄 输出文件: {os.path.basename(output_path)}"
                }
        else:
            return {
                "success": False, 
                "error": f"不支持的操作: {operation.value}", 
                "input_path": input_path, 
                "output_path": output_path,
                "formatted_message": f"❌ 错误: 不支持的操作 '{operation.value}'"
            }
        
        # 尝试使用不同的方法进行转换
        if operation == DocumentOperationEnum.PDF_TO_WORD:
            # 尝试使用 PyPDF2 或其他库
            try:
                if not PDF_AVAILABLE:
                    return {
                        "success": False, 
                        "error": "缺少必要的库，请安装 PyPDF2", 
                        "input_path": input_path, 
                        "output_path": output_path,
                        "formatted_message": "❌ 错误: 缺少必要的库，请安装 PyPDF2"
                    }
                
                # 创建一个新的 Word 文档
                doc = Document()
                
                # 读取 PDF 文件
                with open(input_path, 'rb') as f:
                    pdf_reader = PdfReader(f)
                    
                    # 遍历 PDF 中的每一页
                    for page_num in range(len(pdf_reader.pages)):
                        page = pdf_reader.pages[page_num]
                        text = page.extract_text()
                        
                        # 将提取的文本添加到 Word 文档中
                        if text:
                            doc.add_paragraph(text)
                        
                        # 在页之间添加分页符
                        if page_num < len(pdf_reader.pages) - 1:
                            doc.add_page_break()
                
                # 保存 Word 文档
                doc.save(output_path)
                
                return {
                    "success": True, 
                    "result": "PDF 转 Word 成功", 
                    "input_path": input_path, 
                    "output_path": output_path,
                    "formatted_message": f"✅ PDF 转 Word 成功\n📄 输入文件: {os.path.basename(input_path)}\n📁 输入路径: {input_path}\n📄 输出文件: {os.path.basename(output_path)}\n📁 输出路径: {output_path}\n📊 页面数: {len(pdf_reader.pages)}"
                }
            except Exception as e:
                return {
                    "success": False, 
                    "error": f"转换失败: {str(e)}", 
                    "input_path": input_path, 
                    "output_path": output_path,
                    "formatted_message": f"❌ 转换失败: {str(e)}\n📄 输入文件: {os.path.basename(input_path)}"
                }
        elif operation == DocumentOperationEnum.WORD_TO_PDF:
            # 尝试使用 python-docx 或其他库
            try:
                if not DOCX_AVAILABLE:
                    return {
                        "success": False, 
                        "error": "缺少必要的库，请安装 python-docx 和 docx2pdf", 
                        "input_path": input_path, 
                        "output_path": output_path,
                        "formatted_message": "❌ 错误: 缺少必要的库，请安装 python-docx 和 docx2pdf"
                    }
                
                # 检查文件是否存在且可访问
                if not os.path.exists(input_path):
                    return {
                        "success": False, 
                        "error": f"输入文件不存在: {input_path}", 
                        "input_path": input_path, 
                        "output_path": output_path,
                        "formatted_message": f"❌ 错误: 输入文件不存在\n📍 路径: {input_path}"
                    }
                
                if not os.access(input_path, os.R_OK):
                    return {
                        "success": False, 
                        "error": f"无法读取输入文件: {input_path}", 
                        "input_path": input_path, 
                        "output_path": output_path,
                        "formatted_message": f"❌ 错误: 无法读取输入文件\n📍 路径: {input_path}"
                    }
                
                # 确保输出目录存在且可写
                output_dir = os.path.dirname(output_path)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir, exist_ok=True)
                
                if output_dir and not os.access(output_dir, os.W_OK):
                    return {
                        "success": False, 
                        "error": f"无法写入输出目录: {output_dir}", 
                        "input_path": input_path, 
                        "output_path": output_path,
                        "formatted_message": f"❌ 错误: 无法写入输出目录\n📍 路径: {output_dir}"
                    }
                
                # 使用 docx2pdf 将 Word 文档转换为 PDF
                # 尝试使用不同的转换方法
                try:
                    # 方法1: 使用默认转换
                    docx2pdf.convert(input_path, output_path)
                except Exception as e1:
                    # 如果默认转换失败，尝试使用无后台模式
                    try:
                        from docx2pdf import convert
                        convert(input_path, output_path, keep_active=False)
                    except Exception as e2:
                        # 所有方法都失败，抛出最终错误
                        raise Exception(f"转换失败: {str(e1)} (尝试其他方法也失败: {str(e2)})")
                
                return {
                    "success": True, 
                    "result": "Word 转 PDF 成功", 
                    "input_path": input_path, 
                    "output_path": output_path,
                    "formatted_message": f"✅ Word 转 PDF 成功\n📄 输入文件: {os.path.basename(input_path)}\n📁 输入路径: {input_path}\n📄 输出文件: {os.path.basename(output_path)}\n📁 输出路径: {output_path}"
                }
            except Exception as e:
                # 提供更详细的错误信息
                error_msg = f"转换失败: {str(e)}"
                if "Word.Application" in str(e):
                    error_msg += " (可能是 Word 应用程序问题，请确保 Word 已正确安装且未被其他进程占用)"
                return {
                    "success": False, 
                    "error": error_msg, 
                    "input_path": input_path, 
                    "output_path": output_path,
                    "formatted_message": f"❌ {error_msg}\n📄 输入文件: {os.path.basename(input_path)}"
                }
        
        return {
            "success": False,
            "error": "未知错误",
            "input_path": input_path,
            "output_path": output_path,
            "formatted_message": "❌ 错误: 未知错误"
        }
        
    except Exception as e:
        return {
            "success": False, 
            "error": str(e), 
            "input_path": input_path, 
            "output_path": output_path,
            "formatted_message": f"❌ 错误: {str(e)}"
        }
