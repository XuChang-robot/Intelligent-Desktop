import os
import glob
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from mcp.server.fastmcp import Context
from .tool_base import ToolBase, ToolResult, OperationConfig, register_tool
from .file_operations import FileOperationsTool

try:
    from docx import Document
    import docx2pdf
    from pypdf import PdfReader
    import io
    DOCX_AVAILABLE = True
    PDF_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    PDF_AVAILABLE = False


class DocumentOperationEnum(str, Enum):
    PDF_TO_WORD = "pdf_to_word"
    WORD_TO_PDF = "word_to_pdf"


@register_tool("document_converter")
class DocumentConverterTool(ToolBase):
    """文档转换工具
    
    支持 PDF 与 Word 文档的互转，支持批量转换（使用通配符如 *.docx）。
    """
    
    TOOL_NAME = "document_converter"
    
    OPERATION_CONFIG = {
        'pdf_to_word': OperationConfig(
            description='PDF 转 Word',
            required_params=['input_path', 'output_path'],
            optional_params=[],
            is_dangerous=False
        ),
        'word_to_pdf': OperationConfig(
            description='Word 转 PDF',
            required_params=['input_path', 'output_path'],
            optional_params=[],
            is_dangerous=False
        )
    }
    
    def _get_output_extension(self, operation: str) -> str:
        if operation == 'pdf_to_word':
            return ".docx"
        elif operation == 'word_to_pdf':
            return ".pdf"
        return ""
    
    def _validate_file_extensions(self, operation: str, input_path: str, output_path: str) -> Optional[str]:
        if operation == 'pdf_to_word':
            if not input_path.lower().endswith(".pdf"):
                return "输入文件必须是PDF格式"
            if not output_path.lower().endswith(".docx"):
                return "输出文件必须是Word格式(.docx)"
        elif operation == 'word_to_pdf':
            if not (input_path.lower().endswith(".docx") or input_path.lower().endswith(".doc")):
                return "输入文件必须是Word格式(.docx或.doc)"
            if not output_path.lower().endswith(".pdf"):
                return "输出文件必须是PDF格式"
        return None
    
    async def execute(self, ctx: Optional[Context] = None, **kwargs) -> Dict[str, Any]:
        operation = kwargs.get('operation')
        input_path = kwargs.get('input_path')
        output_path = kwargs.get('output_path')
        
        input_processed = FileOperationsTool.process_path_static(input_path)
        output_processed = FileOperationsTool.process_path_static(output_path)
        
        if '*' in input_processed or '?' in input_processed:
            return self._batch_convert(operation, input_processed, output_processed)
        
        return self._single_convert(operation, input_processed, output_processed)
    
    def _batch_convert(self, operation: str, input_pattern: str, output_path: str) -> Dict[str, Any]:
        matched_files = glob.glob(input_pattern, recursive=False)
        
        if not matched_files:
            return (ToolResult.error(f"未找到匹配的文件: {input_pattern}")
                .with_message(f"❌ 错误: 未找到匹配的文件\n📍 模式: {input_pattern}")
                .build())
        
        output_ext = self._get_output_extension(operation)
        if not output_ext:
            return ToolResult.error(f"不支持的操作: {operation}").build()
        
        if os.path.isdir(output_path):
            output_dir = output_path
        else:
            if '*' in output_path or '?' in output_path:
                output_dir = os.path.dirname(output_path)
                if not output_dir:
                    output_dir = os.getcwd()
            else:
                output_dir = os.path.dirname(output_path)
                if not output_dir:
                    output_dir = os.getcwd()
        
        os.makedirs(output_dir, exist_ok=True)
        
        converted_files = []
        failed_files = []
        
        for input_file in matched_files:
            if os.path.isdir(input_file):
                continue
            
            input_filename = os.path.basename(input_file)
            input_name, _ = os.path.splitext(input_filename)
            output_file = os.path.join(output_dir, input_name + output_ext)
            
            result = self._convert_single_file(operation, input_file, output_file)
            
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
        
        total_files = len(converted_files) + len(failed_files)
        success_count = len(converted_files)
        failed_count = len(failed_files)
        
        if failed_count == 0:
            message = f"✅ 批量转换完成\n📊 总共: {total_files} 个文件\n✅ 成功: {success_count} 个文件\n📁 输出目录: {output_dir}"
        elif success_count == 0:
            message = f"❌ 批量转换失败\n📊 总共: {total_files} 个文件\n❌ 失败: {failed_count} 个文件"
        else:
            message = f"⚠️ 批量转换部分完成\n📊 总共: {total_files} 个文件\n✅ 成功: {success_count} 个文件\n❌ 失败: {failed_count} 个文件\n📁 输出目录: {output_dir}"
        
        return (ToolResult.success(message)
            .with_extra("converted_files", converted_files)
            .with_extra("failed_files", failed_files)
            .with_extra("total_files", total_files)
            .with_message(message)
            .build())
    
    def _single_convert(self, operation: str, input_path: str, output_path: str) -> Dict[str, Any]:
        if os.path.isdir(output_path):
            input_filename = os.path.basename(input_path)
            input_name, _ = os.path.splitext(input_filename)
            output_ext = self._get_output_extension(operation)
            output_path = os.path.join(output_path, input_name + output_ext)
        
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        return self._convert_single_file(operation, input_path, output_path)
    
    def _convert_single_file(self, operation: str, input_path: str, output_path: str) -> Dict[str, Any]:
        validation_error = self._validate_file_extensions(operation, input_path, output_path)
        if validation_error:
            return ToolResult.error(validation_error).build()
        
        if operation == 'pdf_to_word':
            return self._pdf_to_word(input_path, output_path)
        elif operation == 'word_to_pdf':
            return self._word_to_pdf(input_path, output_path)
        else:
            return ToolResult.error(f"不支持的操作: {operation}").build()
    
    def _pdf_to_word(self, input_path: str, output_path: str) -> Dict[str, Any]:
        if not PDF_AVAILABLE:
            return ToolResult.error("缺少必要的库，请安装 pypdf 和 python-docx").build()
        
        try:
            doc = Document()
            
            with open(input_path, 'rb') as f:
                pdf_reader = PdfReader(f)
                page_count = len(pdf_reader.pages)
                
                for page_num in range(page_count):
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()
                    
                    if text:
                        doc.add_paragraph(text)
                    
                    if page_num < page_count - 1:
                        doc.add_page_break()
            
            doc.save(output_path)
            
            return (ToolResult.success("PDF 转 Word 成功")
                .with_extra("input_path", input_path)
                .with_extra("output_path", output_path)
                .with_message(f"✅ PDF 转 Word 成功\n📄 输入文件: {os.path.basename(input_path)}\n📁 输入路径: {input_path}\n📄 输出文件: {os.path.basename(output_path)}\n📁 输出路径: {output_path}\n📊 页面数: {page_count}")
                .build())
        except Exception as e:
            return ToolResult.error(f"转换失败: {str(e)}").build()
    
    def _word_to_pdf(self, input_path: str, output_path: str) -> Dict[str, Any]:
        if not DOCX_AVAILABLE:
            return ToolResult.error("缺少必要的库，请安装 python-docx 和 docx2pdf").build()
        
        try:
            if not os.path.exists(input_path):
                return ToolResult.error(f"输入文件不存在: {input_path}").build()
            
            if not os.access(input_path, os.R_OK):
                return ToolResult.error(f"无法读取输入文件: {input_path}").build()
            
            docx2pdf.convert(input_path, output_path)
            
            return (ToolResult.success("Word 转 PDF 成功")
                .with_extra("input_path", input_path)
                .with_extra("output_path", output_path)
                .with_message(f"✅ Word 转 PDF 成功\n📄 输入文件: {os.path.basename(input_path)}\n📁 输入路径: {input_path}\n📄 输出文件: {os.path.basename(output_path)}\n📁 输出路径: {output_path}")
                .build())
        except Exception as e:
            return ToolResult.error(f"转换失败: {str(e)}").build()


def register_document_converter_tools(mcp, security_checker=None, output_callback=None):
    """注册文档转换工具到MCP服务器"""
    tool = DocumentConverterTool()
    
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
            operation: 操作类型
                - "pdf_to_word": PDF 转 Word
                - "word_to_pdf": Word 转 PDF
            input_path: 输入文件路径（支持通配符，如 "桌面/*.docx"）
            output_path: 输出文件路径（可以是文件路径或文件夹路径）
        
        Returns:
            执行结果字典
        
        注意:
            - input_path必须是单个文件路径或通配符模式
            - output_path可以是文件路径或文件夹路径
        """
        return await tool.safe_execute(
            operation=operation,
            input_path=input_path,
            output_path=output_path
        )
    
    return document_converter
