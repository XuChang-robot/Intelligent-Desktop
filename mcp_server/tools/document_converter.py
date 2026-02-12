# 文档转换工具

import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
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


def register_document_converter_tools(mcp, security_checker=None, output_callback=None):
    """注册文档转换工具到MCP服务器
    
    Args:
        mcp: FastMCP实例
        security_checker: 安全检查器（可选）
        output_callback: 输出回调函数（可选）
    """
    
    @mcp.tool()
    async def document_converter(
        operation: str,
        input_path: str,
        output_path: str,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """文档转换工具
        
        支持 PDF 与 Word 文档的互转。
        
        Args:
            operation: 操作类型，可选值：
                - "pdf_to_word": PDF 转 Word
                - "word_to_pdf": Word 转 PDF
            input_path: 输入文件路径
            output_path: 输出文件路径
            ctx: FastMCP上下文，用于elicitation（可选）
        
        Returns:
            {
                "success": True/False,
                "result": 操作结果描述,
                "input_path": 输入文件路径,
                "output_path": 输出文件路径,
                "error": 错误信息（如果失败）
            }
        
        Examples:
            - PDF 转 Word: document_converter("pdf_to_word", "input.pdf", "output.docx")
            - Word 转 PDF: document_converter("word_to_pdf", "input.docx", "output.pdf")
        """
        try:
            # 处理路径
            input_path = process_path(input_path)
            output_path = process_path(output_path)
            
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            # 检查文件扩展名是否正确
            if operation == "pdf_to_word":
                if not input_path.lower().endswith(".pdf"):
                    return {"success": False, "error": "输入文件必须是PDF格式", "input_path": input_path, "output_path": output_path}
                if not output_path.lower().endswith(".docx"):
                    return {"success": False, "error": "输出文件必须是Word格式(.docx)", "input_path": input_path, "output_path": output_path}
            elif operation == "word_to_pdf":
                if not (input_path.lower().endswith(".docx") or input_path.lower().endswith(".doc")):
                    return {"success": False, "error": "输入文件必须是Word格式(.docx或.doc)", "input_path": input_path, "output_path": output_path}
                if not output_path.lower().endswith(".pdf"):
                    return {"success": False, "error": "输出文件必须是PDF格式", "input_path": input_path, "output_path": output_path}
            else:
                return {"success": False, "error": f"不支持的操作: {operation}", "input_path": input_path, "output_path": output_path}
            
            # 尝试使用不同的方法进行转换
            if operation == "pdf_to_word":
                # 尝试使用 PyPDF2 或其他库
                try:
                    if not PDF_AVAILABLE:
                        return {"success": False, "error": "缺少必要的库，请安装 PyPDF2", "input_path": input_path, "output_path": output_path}
                    
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
                    
                    return {"success": True, "result": "PDF 转 Word 成功", "input_path": input_path, "output_path": output_path}
                except Exception as e:
                    return {"success": False, "error": f"转换失败: {str(e)}", "input_path": input_path, "output_path": output_path}
            elif operation == "word_to_pdf":
                # 尝试使用 python-docx 或其他库
                try:
                    if not DOCX_AVAILABLE:
                        return {"success": False, "error": "缺少必要的库，请安装 python-docx 和 docx2pdf", "input_path": input_path, "output_path": output_path}
                    
                    # 检查文件是否存在且可访问
                    if not os.path.exists(input_path):
                        return {"success": False, "error": f"输入文件不存在: {input_path}", "input_path": input_path, "output_path": output_path}
                    
                    if not os.access(input_path, os.R_OK):
                        return {"success": False, "error": f"无法读取输入文件: {input_path}", "input_path": input_path, "output_path": output_path}
                    
                    # 确保输出目录存在且可写
                    output_dir = os.path.dirname(output_path)
                    if output_dir and not os.path.exists(output_dir):
                        os.makedirs(output_dir, exist_ok=True)
                    
                    if output_dir and not os.access(output_dir, os.W_OK):
                        return {"success": False, "error": f"无法写入输出目录: {output_dir}", "input_path": input_path, "output_path": output_path}
                    
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
                    
                    return {"success": True, "result": "Word 转 PDF 成功", "input_path": input_path, "output_path": output_path}
                except Exception as e:
                    # 提供更详细的错误信息
                    error_msg = f"转换失败: {str(e)}"
                    if "Word.Application" in str(e):
                        error_msg += " (可能是 Word 应用程序问题，请确保 Word 已正确安装且未被其他进程占用)"
                    return {"success": False, "error": error_msg, "input_path": input_path, "output_path": output_path}
        
        except Exception as e:
            return {"success": False, "error": str(e), "input_path": input_path, "output_path": output_path}
