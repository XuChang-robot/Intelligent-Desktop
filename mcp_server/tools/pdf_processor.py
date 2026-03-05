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
# 工具名称：pdf_processor
# 支持的操作类型（operation）：
#   - "merge": PDF 合并
#   - "insert": PDF 插入页
#   - "print": PDF 打印
#   - "extract": PDF 提取页
#   - "split": PDF 拆分
# 必需参数：
#   - operation: 操作类型（必需）
#   - input_path: 输入文件路径（必需，单个文件或多个文件用分号分隔）
#   - output_path: 输出文件路径（必需，print操作除外）
# 可选参数：
#   - insert_position: 插入位置（仅用于insert操作，默认为1）
#   - pages: 页面范围（仅用于extract和split操作，例如："1-3,5"）
#   - ctx: FastMCP上下文，用于elicitation（可选）
#
# 参数验证规则：
#   - operation: 必须是支持的操作类型之一
#   - input_path: 不能为空
#   - output_path: 不能为空（print操作除外）
#   - insert_position: insert操作时必须为正整数
#   - pages: extract和split操作时不能为空
#
# 返回格式：
#   - 成功：{"success": True, "result": "...", "input_path": "...", "output_path": "...", "formatted_message": "..."}
#   - 配置错误：{"success": False, "config_error": "..."}
#   - 执行失败：{"success": False, "error": "...", "formatted_message": "..."}


import os
import subprocess
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from pydantic import BaseModel
from mcp.server.fastmcp import Context

# 尝试导入必要的库
try:
    from pypdf import PdfReader, PdfWriter
    import io
except ImportError:
    # 如果导入失败，设置一个标志
    PDF_AVAILABLE = False
else:
    PDF_AVAILABLE = True

# 从file_operations导入process_path函数
from mcp_server.tools.file_operations import process_path


# 操作类型枚举
class PDFOperationEnum(str, Enum):
    MERGE = "merge"
    INSERT = "insert"
    PRINT = "print"
    EXTRACT = "extract"
    SPLIT = "split"

# 操作类型配置
OPERATION_CONFIG = {
    'merge': {
        'description': 'PDF 合并',
        'required_params': ['input_path', 'output_path'],
        'optional_params': ['ctx']
    },
    'insert': {
        'description': 'PDF 插入页',
        'required_params': ['input_path', 'output_path'],
        'optional_params': ['insert_position', 'ctx']
    },
    'print': {
        'description': 'PDF 打印',
        'required_params': ['input_path'],
        'optional_params': ['ctx']
    },
    'extract': {
        'description': 'PDF 提取页',
        'required_params': ['input_path', 'output_path', 'pages'],
        'optional_params': ['ctx']
    },
    'split': {
        'description': 'PDF 拆分',
        'required_params': ['input_path', 'output_path', 'pages'],
        'optional_params': ['ctx']
    }
}


def validate_parameters(operation: PDFOperationEnum, input_path: str, output_path: str, insert_position: Optional[int] = None, pages: Optional[str] = None) -> Tuple[Dict[str, Any], Optional[str]]:
    """验证并调整参数
    
    Args:
        operation: 操作类型
        input_path: 输入文件路径
        output_path: 输出文件路径
        insert_position: 插入位置
        pages: 页面范围
    
    Returns:
        (调整后的参数字典, 配置错误信息)
    """
    params = {
        'operation': operation.value,
        'input_path': input_path,
        'output_path': output_path,
        'insert_position': insert_position,
        'pages': pages
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
    
    # 获取操作配置
    op_config = OPERATION_CONFIG[operation.value]
    
    # 验证必需参数
    if not input_path:
        config_error = config_error or "input_path参数不能为空"
    
    if operation != PDFOperationEnum.PRINT and not output_path:
        config_error = config_error or f"{operation.value}操作需要output_path参数"
    
    if operation in [PDFOperationEnum.EXTRACT, PDFOperationEnum.SPLIT] and not pages:
        config_error = config_error or f"{operation.value}操作需要pages参数"
    
    # 验证insert_position参数
    if operation == PDFOperationEnum.INSERT and insert_position is not None and insert_position < 1:
        config_error = config_error or "insert_position参数必须大于0"
    
    return params, config_error


def register_pdf_processor_tools(mcp, security_checker=None, output_callback=None):
    """注册 PDF 专用处理工具到 MCP 服务器
    
    Args:
        mcp: FastMCP 实例
        security_checker: 安全检查器（可选）
        output_callback: 输出回调函数（可选）
    """
    
    @mcp.tool()
    async def pdf_processor(
        operation: PDFOperationEnum,
        input_path: str,
        output_path: str,
        insert_position: Optional[int] = 1,
        pages: Optional[str] = None,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """PDF 专用处理工具
        
        支持 PDF 文件的合并、修改、插入页、打印等常用功能。
        
        Args:
            operation: 操作类型，可选值：
                - "merge": PDF 合并
                - "insert": PDF 插入页
                - "print": PDF 打印
                - "extract": PDF 提取页
                - "split": PDF 拆分
            input_path: 输入文件路径（单个文件）或输入文件路径列表（多个文件，用分号分隔）
            output_path: 输出文件路径
            insert_position: 插入位置（仅用于 insert 操作）
            pages: 页面范围（仅用于 extract 和 split 操作，例如："1-3,5"）
            ctx: FastMCP 上下文，用于 elicitation（可选）
        
        Returns:
            {
                "success": True/False,
                "result": 操作结果描述,
                "input_path": 输入文件路径,
                "output_path": 输出文件路径,
                "error": 错误信息（如果失败）
            }
        
        Examples:
            - PDF 打印: pdf_processor("print", "input.pdf", "")
            - PDF 提取页: pdf_processor("extract", "input.pdf", "output.pdf", pages="1-3,5")
        """
        # 验证参数
        validated_params, config_error = validate_parameters(operation, input_path, output_path, insert_position, pages)
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
        insert_position = validated_params.get('insert_position', 1)
        pages = validated_params.get('pages')
        
        try:
            # 获取桌面路径
            desktop_path = str(Path.home() / "Desktop")
            
            # 处理多个输入文件路径（用分号分隔）
            input_paths = []
            if ";" in input_path:
                # 分割输入路径
                raw_paths = [p.strip() for p in input_path.split(";")]
                
                # 处理每个输入路径
                for p in raw_paths:
                    processed_path = process_path(p)
                    input_paths.append(processed_path)
            else:
                # 处理单个输入路径
                processed_path = process_path(input_path)
                input_paths = [processed_path]
            
            # 处理输出路径
            output_path = process_path(output_path)
            
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            # 检查文件扩展名是否正确
            for p in input_paths:
                if not p.lower().endswith(".pdf"):
                    return {
                        "success": False, 
                        "error": f"输入文件必须是PDF格式: {p}", 
                        "input_path": input_path, 
                        "output_path": output_path,
                        "formatted_message": f"❌ 错误: 输入文件必须是PDF格式\n📄 文件: {os.path.basename(p)}"
                    }
            
            if operation != PDFOperationEnum.PRINT and output_path and not output_path.lower().endswith(".pdf"):
                return {
                    "success": False, 
                    "error": "输出文件必须是PDF格式", 
                    "input_path": input_path, 
                    "output_path": output_path,
                    "formatted_message": f"❌ 错误: 输出文件必须是PDF格式\n📄 输出文件: {os.path.basename(output_path)}"
                }
            
            # 尝试使用不同的方法进行 PDF 处理
            if operation == PDFOperationEnum.MERGE:
                # 尝试使用 pypdf 或其他库
                try:
                    if not PDF_AVAILABLE:
                        return {
                            "success": False, 
                            "error": "缺少必要的库，请安装 pypdf", 
                            "input_path": input_path, 
                            "output_path": output_path,
                            "formatted_message": "❌ 错误: 缺少必要的库，请安装 pypdf"
                        }
                    
                    # 创建一个 PDF 写入器
                    pdf_writer = PdfWriter()
                    total_pages = 0
                    
                    # 遍历所有输入 PDF 文件
                    for pdf_path in input_paths:
                        # 打开当前 PDF 文件
                        with open(pdf_path, 'rb') as f:
                            pdf_reader = PdfReader(f)
                            total_pages += len(pdf_reader.pages)
                            
                            # 遍历 PDF 中的每一页
                            for page_num in range(len(pdf_reader.pages)):
                                page = pdf_reader.pages[page_num]
                                pdf_writer.add_page(page)
                    
                    # 保存合并后的 PDF 文件
                    with open(output_path, 'wb') as f:
                        pdf_writer.write(f)
                    
                    return {
                        "success": True, 
                        "result": f"PDF 合并成功，共 {len(input_paths)} 个文件", 
                        "input_path": input_path, 
                        "output_path": output_path,
                        "formatted_message": f"✅ PDF 合并成功\n📁 输入文件数: {len(input_paths)}\n📄 输入文件:\n" + "\n".join([f"  - {os.path.basename(p)}" for p in input_paths]) + f"\n📄 输出文件: {os.path.basename(output_path)}\n📁 输出路径: {output_path}\n📊 总页数: {total_pages}"
                    }
                except Exception as e:
                    return {
                        "success": False, 
                        "error": f"合并失败: {str(e)}", 
                        "input_path": input_path, 
                        "output_path": output_path,
                        "formatted_message": f"❌ 合并失败: {str(e)}"
                    }
            elif operation == PDFOperationEnum.INSERT:
                # 尝试使用 pypdf 或其他库
                try:
                    if not PDF_AVAILABLE:
                        return {
                            "success": False, 
                            "error": "缺少必要的库，请安装 pypdf", 
                            "input_path": input_path, 
                            "output_path": output_path,
                            "formatted_message": "❌ 错误: 缺少必要的库，请安装 pypdf"
                        }
                    
                    if len(input_paths) < 2:
                        return {
                            "success": False, 
                            "error": "PDF 插入操作需要至少两个输入文件", 
                            "input_path": input_path, 
                            "output_path": output_path,
                            "formatted_message": "❌ 错误: PDF 插入操作需要至少两个输入文件"
                        }
                    
                    # 创建一个 PDF 写入器
                    pdf_writer = PdfWriter()
                    inserted_pages = 0
                    
                    # 打开第一个 PDF 文件（目标文件）
                    with open(input_paths[0], 'rb') as f:
                        target_reader = PdfReader(f)
                        target_pages = len(target_reader.pages)
                        
                        # 添加目标文件中插入位置之前的所有页
                        for page_num in range(min(insert_position - 1, target_pages)):
                            page = target_reader.pages[page_num]
                            pdf_writer.add_page(page)
                    
                    # 遍历其他 PDF 文件（要插入的文件）
                    for pdf_path in input_paths[1:]:
                        with open(pdf_path, 'rb') as f:
                            insert_reader = PdfReader(f)
                            inserted_pages += len(insert_reader.pages)
                            
                            # 添加要插入的文件的所有页
                            for page_num in range(len(insert_reader.pages)):
                                page = insert_reader.pages[page_num]
                                pdf_writer.add_page(page)
                    
                    # 添加目标文件中插入位置之后的所有页
                    with open(input_paths[0], 'rb') as f:
                        target_reader = PdfReader(f)
                        
                        for page_num in range(insert_position - 1, target_pages):
                            page = target_reader.pages[page_num]
                            pdf_writer.add_page(page)
                    
                    # 保存结果 PDF 文件
                    with open(output_path, 'wb') as f:
                        pdf_writer.write(f)
                    
                    return {
                        "success": True, 
                        "result": f"PDF 插入成功，插入位置: {insert_position}", 
                        "input_path": input_path, 
                        "output_path": output_path,
                        "formatted_message": f"✅ PDF 插入成功\n📄 目标文件: {os.path.basename(input_paths[0])}\n📄 插入文件数: {len(input_paths) - 1}\n" + "\n".join([f"  - {os.path.basename(p)}" for p in input_paths[1:]]) + f"\n📍 插入位置: 第 {insert_position} 页\n📊 插入页数: {inserted_pages}\n📄 输出文件: {os.path.basename(output_path)}"
                    }
                except Exception as e:
                    return {
                        "success": False, 
                        "error": f"插入失败: {str(e)}", 
                        "input_path": input_path, 
                        "output_path": output_path,
                        "formatted_message": f"❌ 插入失败: {str(e)}"
                    }
            elif operation == PDFOperationEnum.PRINT:
                # 尝试使用系统默认打印机打印 PDF
                try:
                    # 使用系统默认打印机打印 PDF
                    if os.name == 'nt':  # Windows
                        subprocess.run(['print', input_paths[0]], check=True, shell=True)
                    else:  # Unix/Linux
                        subprocess.run(['lp', input_paths[0]], check=True)
                    
                    return {
                        "success": True, 
                        "result": "PDF 打印成功", 
                        "input_path": input_path, 
                        "output_path": output_path,
                        "formatted_message": f"✅ PDF 打印成功\n📄 文件: {os.path.basename(input_paths[0])}\n📁 路径: {input_paths[0]}"
                    }
                except Exception as e:
                    return {
                        "success": False, 
                        "error": f"打印失败: {str(e)}", 
                        "input_path": input_path, 
                        "output_path": output_path,
                        "formatted_message": f"❌ 打印失败: {str(e)}"
                    }
            elif operation == PDFOperationEnum.EXTRACT:
                # 尝试使用 pypdf 或其他库
                try:
                    if not PDF_AVAILABLE:
                        return {
                            "success": False, 
                            "error": "缺少必要的库，请安装 pypdf", 
                            "input_path": input_path, 
                            "output_path": output_path,
                            "formatted_message": "❌ 错误: 缺少必要的库，请安装 pypdf"
                        }
                    
                    if not pages:
                        return {
                            "success": False, 
                            "error": "PDF 提取页操作需要指定页面范围", 
                            "input_path": input_path, 
                            "output_path": output_path,
                            "formatted_message": "❌ 错误: PDF 提取页操作需要指定页面范围"
                        }
                    
                    # 解析页面范围
                    page_numbers = []
                    for part in pages.split(','):
                        if '-' in part:
                            start, end = part.split('-')
                            page_numbers.extend(range(int(start) - 1, int(end)))
                        else:
                            page_numbers.append(int(part) - 1)
                    
                    # 创建一个 PDF 写入器
                    pdf_writer = PdfWriter()
                    extracted_count = 0
                    
                    # 打开输入 PDF 文件
                    with open(input_paths[0], 'rb') as f:
                        pdf_reader = PdfReader(f)
                        total_pages = len(pdf_reader.pages)
                        
                        # 添加指定的页面
                        for page_num in page_numbers:
                            if 0 <= page_num < total_pages:
                                page = pdf_reader.pages[page_num]
                                pdf_writer.add_page(page)
                                extracted_count += 1
                    
                    # 保存提取后的 PDF 文件
                    with open(output_path, 'wb') as f:
                        pdf_writer.write(f)
                    
                    return {
                        "success": True, 
                        "result": f"PDF 提取页成功，页面范围: {pages}", 
                        "input_path": input_path, 
                        "output_path": output_path,
                        "formatted_message": f"✅ PDF 提取页成功\n📄 源文件: {os.path.basename(input_paths[0])}\n📊 源文件页数: {total_pages}\n🔢 提取页面范围: {pages}\n📊 成功提取页数: {extracted_count}\n📄 输出文件: {os.path.basename(output_path)}\n📍 输出路径: {output_path}"
                    }
                except Exception as e:
                    return {
                        "success": False, 
                        "error": f"提取失败: {str(e)}", 
                        "input_path": input_path, 
                        "output_path": output_path,
                        "formatted_message": f"❌ 提取失败: {str(e)}"
                    }
            elif operation == PDFOperationEnum.SPLIT:
                # 尝试使用 pypdf 或其他库
                try:
                    if not PDF_AVAILABLE:
                        return {
                            "success": False, 
                            "error": "缺少必要的库，请安装 pypdf", 
                            "input_path": input_path, 
                            "output_path": output_path,
                            "formatted_message": "❌ 错误: 缺少必要的库，请安装 pypdf"
                        }
                    
                    if not pages:
                        return {
                            "success": False, 
                            "error": "PDF 拆分操作需要指定页面范围", 
                            "input_path": input_path, 
                            "output_path": output_path,
                            "formatted_message": "❌ 错误: PDF 拆分操作需要指定页面范围"
                        }
                    
                    # 解析页面范围
                    page_numbers = []
                    for part in pages.split(','):
                        if '-' in part:
                            start, end = part.split('-')
                            page_numbers.extend(range(int(start) - 1, int(end)))
                        else:
                            page_numbers.append(int(part) - 1)
                    
                    # 打开输入 PDF 文件
                    split_files = []
                    with open(input_paths[0], 'rb') as f:
                        pdf_reader = PdfReader(f)
                        total_pages = len(pdf_reader.pages)
                        
                        # 为每个指定的页面创建一个新的 PDF 文件
                        for page_num in page_numbers:
                            if 0 <= page_num < total_pages:
                                # 创建一个 PDF 写入器
                                pdf_writer = PdfWriter()
                                
                                # 添加当前页面
                                page = pdf_reader.pages[page_num]
                                pdf_writer.add_page(page)
                                
                                # 保存拆分后的 PDF 文件
                                split_output_path = f"{output_path}_{page_num + 1}.pdf"
                                with open(split_output_path, 'wb') as split_f:
                                    pdf_writer.write(split_f)
                                split_files.append(os.path.basename(split_output_path))
                    
                    return {
                        "success": True, 
                        "result": f"PDF 拆分成功，页面范围: {pages}", 
                        "input_path": input_path, 
                        "output_path": output_path,
                        "formatted_message": f"✅ PDF 拆分成功\n📄 源文件: {os.path.basename(input_paths[0])}\n📊 源文件页数: {total_pages}\n🔢 拆分页面范围: {pages}\n📊 成功拆分页数: {len(split_files)}\n📄 输出文件:\n" + "\n".join([f"  - {f}" for f in split_files])
                    }
                except Exception as e:
                    return {
                        "success": False, 
                        "error": f"拆分失败: {str(e)}", 
                        "input_path": input_path, 
                        "output_path": output_path,
                        "formatted_message": f"❌ 拆分失败: {str(e)}"
                    }
            else:
                return {
                    "success": False, 
                    "error": f"不支持的操作: {operation.value}", 
                    "input_path": input_path, 
                    "output_path": output_path,
                    "formatted_message": f"❌ 错误: 不支持的操作 '{operation.value}'"
                }
        
        except Exception as e:
            return {
                "success": False, 
                "error": str(e), 
                "input_path": input_path, 
                "output_path": output_path,
                "formatted_message": f"❌ 错误: {str(e)}"
            }
