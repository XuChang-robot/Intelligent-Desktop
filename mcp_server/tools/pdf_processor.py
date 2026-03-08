import os
import subprocess
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from mcp.server.fastmcp import Context
from .tool_base import ToolBase, ToolResult, OperationConfig, register_tool
from .file_operations import FileOperationsTool

try:
    from pypdf import PdfReader, PdfWriter
    import io
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


class PDFOperationEnum(str, Enum):
    MERGE = "merge"
    INSERT = "insert"
    PRINT = "print"
    EXTRACT = "extract"
    SPLIT = "split"


@register_tool("pdf_processor")
class PDFProcessorTool(ToolBase):
    """PDF 专用处理工具
    
    支持 PDF 文件的合并、修改、插入页、打印等常用功能。
    """
    
    TOOL_NAME = "pdf_processor"
    
    OPERATION_CONFIG = {
        'merge': OperationConfig(
            description='PDF 合并',
            required_params=['input_path', 'output_path'],
            optional_params=[],
            is_dangerous=False
        ),
        'insert': OperationConfig(
            description='PDF 插入页',
            required_params=['input_path', 'output_path'],
            optional_params=['insert_position'],
            is_dangerous=False
        ),
        'print': OperationConfig(
            description='PDF 打印',
            required_params=['input_path'],
            optional_params=[],
            is_dangerous=False
        ),
        'extract': OperationConfig(
            description='PDF 提取页',
            required_params=['input_path', 'output_path', 'pages'],
            optional_params=[],
            is_dangerous=False
        ),
        'split': OperationConfig(
            description='PDF 拆分',
            required_params=['input_path', 'output_path', 'pages'],
            optional_params=[],
            is_dangerous=False
        )
    }
    
    def validate_parameters(self, operation: str, **kwargs) -> Tuple[Dict[str, Any], Optional[str]]:
        params, config_error = super().validate_parameters(operation, **kwargs)
        if config_error:
            return params, config_error
        
        insert_position = kwargs.get('insert_position')
        if operation == 'insert' and insert_position is not None and insert_position < 1:
            return params, "insert_position参数必须大于0"
        
        return params, None
    
    def _process_paths(self, input_path: str, output_path: str = None) -> Tuple[List[str], str]:
        input_paths = []
        if ";" in input_path:
            raw_paths = [p.strip() for p in input_path.split(";")]
            for p in raw_paths:
                processed_path = FileOperationsTool.process_path_static(p)
                input_paths.append(processed_path)
        else:
            processed_path = FileOperationsTool.process_path_static(input_path)
            input_paths = [processed_path]
        
        output_processed = None
        if output_path:
            output_processed = FileOperationsTool.process_path_static(output_path)
            output_dir = os.path.dirname(output_processed)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
        
        return input_paths, output_processed
    
    def _validate_pdf_files(self, input_paths: List[str], output_path: str = None, operation: str = None) -> Optional[str]:
        for p in input_paths:
            if not p.lower().endswith(".pdf"):
                return f"输入文件必须是PDF格式: {p}"
        
        if operation != 'print' and output_path and not output_path.lower().endswith(".pdf"):
            return "输出文件必须是PDF格式"
        
        return None
    
    def _parse_page_range(self, pages: str, max_pages: int) -> List[int]:
        page_numbers = []
        for part in pages.split(','):
            if '-' in part:
                start, end = map(int, part.split('-'))
                page_numbers.extend(range(start - 1, min(end, max_pages)))
            else:
                page_num = int(part) - 1
                if 0 <= page_num < max_pages:
                    page_numbers.append(page_num)
        return sorted(set(page_numbers))
    
    async def execute(self, ctx: Optional[Context] = None, **kwargs) -> Dict[str, Any]:
        operation = kwargs.get('operation')
        input_path = kwargs.get('input_path')
        output_path = kwargs.get('output_path')
        insert_position = kwargs.get('insert_position', 1)
        pages = kwargs.get('pages')
        
        input_paths, output_processed = self._process_paths(input_path, output_path)
        
        validation_error = self._validate_pdf_files(input_paths, output_processed, operation)
        if validation_error:
            return ToolResult.error(validation_error).build()
        
        if operation == 'merge':
            return self._merge_pdfs(input_paths, output_processed)
        elif operation == 'insert':
            return self._insert_pages(input_paths, output_processed, insert_position)
        elif operation == 'print':
            return self._print_pdf(input_paths)
        elif operation == 'extract':
            return self._extract_pages(input_paths[0], output_processed, pages)
        elif operation == 'split':
            return self._split_pdf(input_paths[0], output_processed, pages)
        else:
            return ToolResult.error(f"不支持的操作: {operation}").build()
    
    def _merge_pdfs(self, input_paths: List[str], output_path: str) -> Dict[str, Any]:
        if not PDF_AVAILABLE:
            return ToolResult.error("缺少必要的库，请安装 pypdf").build()
        
        try:
            pdf_writer = PdfWriter()
            total_pages = 0
            
            for pdf_path in input_paths:
                with open(pdf_path, 'rb') as f:
                    pdf_reader = PdfReader(f)
                    total_pages += len(pdf_reader.pages)
                    
                    for page_num in range(len(pdf_reader.pages)):
                        page = pdf_reader.pages[page_num]
                        pdf_writer.add_page(page)
            
            with open(output_path, 'wb') as f:
                pdf_writer.write(f)
            
            return (ToolResult.success(f"PDF 合并成功，共 {len(input_paths)} 个文件")
                .with_extra("input_path", ";".join(input_paths))
                .with_extra("output_path", output_path)
                .with_message(f"✅ PDF 合并成功\n📁 输入文件数: {len(input_paths)}\n📄 输入文件:\n" + 
                    "\n".join([f"  - {os.path.basename(p)}" for p in input_paths]) + 
                    f"\n📄 输出文件: {os.path.basename(output_path)}\n📁 输出路径: {output_path}\n📊 总页数: {total_pages}")
                .build())
        except Exception as e:
            return ToolResult.error(f"合并失败: {str(e)}").build()
    
    def _insert_pages(self, input_paths: List[str], output_path: str, insert_position: int) -> Dict[str, Any]:
        if not PDF_AVAILABLE:
            return ToolResult.error("缺少必要的库，请安装 pypdf").build()
        
        if len(input_paths) < 2:
            return ToolResult.error("PDF 插入操作需要至少两个输入文件").build()
        
        try:
            pdf_writer = PdfWriter()
            inserted_pages = 0
            
            with open(input_paths[0], 'rb') as f:
                target_reader = PdfReader(f)
                target_pages = len(target_reader.pages)
                
                for page_num in range(min(insert_position - 1, target_pages)):
                    page = target_reader.pages[page_num]
                    pdf_writer.add_page(page)
            
            for pdf_path in input_paths[1:]:
                with open(pdf_path, 'rb') as f:
                    insert_reader = PdfReader(f)
                    inserted_pages += len(insert_reader.pages)
                    
                    for page_num in range(len(insert_reader.pages)):
                        page = insert_reader.pages[page_num]
                        pdf_writer.add_page(page)
            
            with open(input_paths[0], 'rb') as f:
                target_reader = PdfReader(f)
                
                for page_num in range(insert_position - 1, target_pages):
                    page = target_reader.pages[page_num]
                    pdf_writer.add_page(page)
            
            with open(output_path, 'wb') as f:
                pdf_writer.write(f)
            
            return (ToolResult.success(f"PDF 插入成功，插入位置: {insert_position}")
                .with_extra("input_path", ";".join(input_paths))
                .with_extra("output_path", output_path)
                .with_message(f"✅ PDF 插入成功\n📄 目标文件: {os.path.basename(input_paths[0])}\n📄 插入文件数: {len(input_paths) - 1}\n" + 
                    "\n".join([f"  - {os.path.basename(p)}" for p in input_paths[1:]]) + 
                    f"\n📍 插入位置: 第 {insert_position} 页\n📊 插入页数: {inserted_pages}\n📄 输出文件: {os.path.basename(output_path)}")
                .build())
        except Exception as e:
            return ToolResult.error(f"插入失败: {str(e)}").build()
    
    def _print_pdf(self, input_paths: List[str]) -> Dict[str, Any]:
        try:
            if os.name == 'nt':
                subprocess.run(['print', input_paths[0]], check=True, shell=True)
            else:
                subprocess.run(['lp', input_paths[0]], check=True)
            
            return (ToolResult.success("PDF 打印成功")
                .with_extra("input_path", input_paths[0])
                .with_message(f"✅ PDF 打印成功\n📄 文件: {os.path.basename(input_paths[0])}\n📁 路径: {input_paths[0]}")
                .build())
        except Exception as e:
            return ToolResult.error(f"打印失败: {str(e)}").build()
    
    def _extract_pages(self, input_path: str, output_path: str, pages: str) -> Dict[str, Any]:
        if not PDF_AVAILABLE:
            return ToolResult.error("缺少必要的库，请安装 pypdf").build()
        
        if not pages:
            return ToolResult.error("PDF 提取页操作需要指定页面范围").build()
        
        try:
            with open(input_path, 'rb') as f:
                pdf_reader = PdfReader(f)
                total_pages = len(pdf_reader.pages)
                page_numbers = self._parse_page_range(pages, total_pages)
                
                pdf_writer = PdfWriter()
                for page_num in page_numbers:
                    page = pdf_reader.pages[page_num]
                    pdf_writer.add_page(page)
                
                with open(output_path, 'wb') as out_f:
                    pdf_writer.write(out_f)
            
            return (ToolResult.success(f"PDF 提取成功，提取页数: {len(page_numbers)}")
                .with_extra("input_path", input_path)
                .with_extra("output_path", output_path)
                .with_message(f"✅ PDF 提取成功\n📄 输入文件: {os.path.basename(input_path)}\n📄 输出文件: {os.path.basename(output_path)}\n📊 提取页数: {len(page_numbers)}\n📋 页面范围: {pages}")
                .build())
        except Exception as e:
            return ToolResult.error(f"提取失败: {str(e)}").build()
    
    def _split_pdf(self, input_path: str, output_path: str, pages: str) -> Dict[str, Any]:
        if not PDF_AVAILABLE:
            return ToolResult.error("缺少必要的库，请安装 pypdf").build()
        
        if not pages:
            return ToolResult.error("PDF 拆分操作需要指定页面范围").build()
        
        try:
            with open(input_path, 'rb') as f:
                pdf_reader = PdfReader(f)
                total_pages = len(pdf_reader.pages)
                page_numbers = self._parse_page_range(pages, total_pages)
                
                pdf_writer = PdfWriter()
                for page_num in page_numbers:
                    page = pdf_reader.pages[page_num]
                    pdf_writer.add_page(page)
                
                with open(output_path, 'wb') as out_f:
                    pdf_writer.write(out_f)
            
            return (ToolResult.success(f"PDF 拆分成功，拆分页数: {len(page_numbers)}")
                .with_extra("input_path", input_path)
                .with_extra("output_path", output_path)
                .with_message(f"✅ PDF 拆分成功\n📄 输入文件: {os.path.basename(input_path)}\n📄 输出文件: {os.path.basename(output_path)}\n📊 拆分页数: {len(page_numbers)}\n📋 页面范围: {pages}")
                .build())
        except Exception as e:
            return ToolResult.error(f"拆分失败: {str(e)}").build()


def register_pdf_processor_tools(mcp, security_checker=None, output_callback=None):
    """注册 PDF 专用处理工具到 MCP 服务器"""
    tool = PDFProcessorTool()
    
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
            operation: 操作类型
                - "merge": PDF 合并
                - "insert": PDF 插入页
                - "print": PDF 打印
                - "extract": PDF 提取页
                - "split": PDF 拆分
            input_path: 输入文件路径（多个文件用分号分隔）
            output_path: 输出文件路径（print操作除外）
        
        insert 操作参数:
            insert_position: 插入位置（默认第1页）
        
        extract/split 操作参数:
            pages: 页面范围（例如："1-3,5"）
        
        Returns:
            执行结果字典
        """
        return await tool.safe_execute(
            operation=operation,
            input_path=input_path,
            output_path=output_path,
            insert_position=insert_position,
            pages=pages
        )
    
    return pdf_processor
