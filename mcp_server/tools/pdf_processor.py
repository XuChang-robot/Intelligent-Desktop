# PDF 专用处理工具

import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
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


def register_pdf_processor_tools(mcp, security_checker=None, output_callback=None):
    """注册 PDF 专用处理工具到 MCP 服务器
    
    Args:
        mcp: FastMCP 实例
        security_checker: 安全检查器（可选）
        output_callback: 输出回调函数（可选）
    """
    
    @mcp.tool()
    async def pdf_processor(
        operation: str,
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
            - PDF 合并: pdf_processor("merge", "input1.pdf;input2.pdf", "output.pdf")
            - PDF 插入页: pdf_processor("insert", "input1.pdf;input2.pdf", "output.pdf", 2)
            - PDF 打印: pdf_processor("print", "input.pdf", "")
            - PDF 提取页: pdf_processor("extract", "input.pdf", "output.pdf", pages="1-3,5")
            - PDF 拆分: pdf_processor("split", "input.pdf", "output_", pages="1,3-4")
        """
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
                    return {"success": False, "error": f"输入文件必须是PDF格式: {p}", "input_path": input_path, "output_path": output_path}
            
            if operation != "print" and output_path and not output_path.lower().endswith(".pdf"):
                return {"success": False, "error": "输出文件必须是PDF格式", "input_path": input_path, "output_path": output_path}
            
            # 尝试使用不同的方法进行 PDF 处理
            if operation == "merge":
                # 尝试使用 pypdf 或其他库
                try:
                    if not PDF_AVAILABLE:
                        return {"success": False, "error": "缺少必要的库，请安装 pypdf", "input_path": input_path, "output_path": output_path}
                    
                    # 创建一个 PDF 写入器
                    pdf_writer = PdfWriter()
                    
                    # 遍历所有输入 PDF 文件
                    for pdf_path in input_paths:
                        # 打开当前 PDF 文件
                        with open(pdf_path, 'rb') as f:
                            pdf_reader = PdfReader(f)
                            
                            # 遍历 PDF 中的每一页
                            for page_num in range(len(pdf_reader.pages)):
                                page = pdf_reader.pages[page_num]
                                pdf_writer.add_page(page)
                    
                    # 保存合并后的 PDF 文件
                    with open(output_path, 'wb') as f:
                        pdf_writer.write(f)
                    
                    return {"success": True, "result": f"PDF 合并成功，共 {len(input_paths)} 个文件", "input_path": input_path, "output_path": output_path}
                except Exception as e:
                    return {"success": False, "error": f"合并失败: {str(e)}", "input_path": input_path, "output_path": output_path}
            elif operation == "insert":
                # 尝试使用 pypdf 或其他库
                try:
                    if not PDF_AVAILABLE:
                        return {"success": False, "error": "缺少必要的库，请安装 pypdf", "input_path": input_path, "output_path": output_path}
                    
                    if len(input_paths) < 2:
                        return {"success": False, "error": "PDF 插入操作需要至少两个输入文件", "input_path": input_path, "output_path": output_path}
                    
                    # 创建一个 PDF 写入器
                    pdf_writer = PdfWriter()
                    
                    # 打开第一个 PDF 文件（目标文件）
                    with open(input_paths[0], 'rb') as f:
                        target_reader = PdfReader(f)
                        
                        # 添加目标文件中插入位置之前的所有页
                        for page_num in range(min(insert_position - 1, len(target_reader.pages))):
                            page = target_reader.pages[page_num]
                            pdf_writer.add_page(page)
                    
                    # 遍历其他 PDF 文件（要插入的文件）
                    for pdf_path in input_paths[1:]:
                        with open(pdf_path, 'rb') as f:
                            insert_reader = PdfReader(f)
                            
                            # 添加要插入的文件的所有页
                            for page_num in range(len(insert_reader.pages)):
                                page = insert_reader.pages[page_num]
                                pdf_writer.add_page(page)
                    
                    # 添加目标文件中插入位置之后的所有页
                    with open(input_paths[0], 'rb') as f:
                        target_reader = PdfReader(f)
                        
                        for page_num in range(insert_position - 1, len(target_reader.pages)):
                            page = target_reader.pages[page_num]
                            pdf_writer.add_page(page)
                    
                    # 保存结果 PDF 文件
                    with open(output_path, 'wb') as f:
                        pdf_writer.write(f)
                    
                    return {"success": True, "result": f"PDF 插入成功，插入位置: {insert_position}", "input_path": input_path, "output_path": output_path}
                except Exception as e:
                    return {"success": False, "error": f"插入失败: {str(e)}", "input_path": input_path, "output_path": output_path}
            elif operation == "print":
                # 尝试使用系统默认打印机打印 PDF
                try:
                    # 使用系统默认打印机打印 PDF
                    if os.name == 'nt':  # Windows
                        subprocess.run(['print', input_paths[0]], check=True, shell=True)
                    else:  # Unix/Linux
                        subprocess.run(['lp', input_paths[0]], check=True)
                    
                    return {"success": True, "result": "PDF 打印成功", "input_path": input_path, "output_path": output_path}
                except Exception as e:
                    return {"success": False, "error": f"打印失败: {str(e)}", "input_path": input_path, "output_path": output_path}
            elif operation == "extract":
                # 尝试使用 pypdf 或其他库
                try:
                    if not PDF_AVAILABLE:
                        return {"success": False, "error": "缺少必要的库，请安装 pypdf", "input_path": input_path, "output_path": output_path}
                    
                    if not pages:
                        return {"success": False, "error": "PDF 提取页操作需要指定页面范围", "input_path": input_path, "output_path": output_path}
                    
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
                    
                    # 打开输入 PDF 文件
                    with open(input_paths[0], 'rb') as f:
                        pdf_reader = PdfReader(f)
                        
                        # 添加指定的页面
                        for page_num in page_numbers:
                            if 0 <= page_num < len(pdf_reader.pages):
                                page = pdf_reader.pages[page_num]
                                pdf_writer.add_page(page)
                    
                    # 保存提取后的 PDF 文件
                    with open(output_path, 'wb') as f:
                        pdf_writer.write(f)
                    
                    return {"success": True, "result": f"PDF 提取页成功，页面范围: {pages}", "input_path": input_path, "output_path": output_path}
                except Exception as e:
                    return {"success": False, "error": f"提取失败: {str(e)}", "input_path": input_path, "output_path": output_path}
            elif operation == "split":
                # 尝试使用 pypdf 或其他库
                try:
                    if not PDF_AVAILABLE:
                        return {"success": False, "error": "缺少必要的库，请安装 pypdf", "input_path": input_path, "output_path": output_path}
                    
                    if not pages:
                        return {"success": False, "error": "PDF 拆分操作需要指定页面范围", "input_path": input_path, "output_path": output_path}
                    
                    # 解析页面范围
                    page_numbers = []
                    for part in pages.split(','):
                        if '-' in part:
                            start, end = part.split('-')
                            page_numbers.extend(range(int(start) - 1, int(end)))
                        else:
                            page_numbers.append(int(part) - 1)
                    
                    # 打开输入 PDF 文件
                    with open(input_paths[0], 'rb') as f:
                        pdf_reader = PdfReader(f)
                        
                        # 为每个指定的页面创建一个新的 PDF 文件
                        for page_num in page_numbers:
                            if 0 <= page_num < len(pdf_reader.pages):
                                # 创建一个 PDF 写入器
                                pdf_writer = PdfWriter()
                                
                                # 添加当前页面
                                page = pdf_reader.pages[page_num]
                                pdf_writer.add_page(page)
                                
                                # 保存拆分后的 PDF 文件
                                split_output_path = f"{output_path}_{page_num + 1}.pdf"
                                with open(split_output_path, 'wb') as split_f:
                                    pdf_writer.write(split_f)
                    
                    return {"success": True, "result": f"PDF 拆分成功，页面范围: {pages}", "input_path": input_path, "output_path": output_path}
                except Exception as e:
                    return {"success": False, "error": f"拆分失败: {str(e)}", "input_path": input_path, "output_path": output_path}
            else:
                return {"success": False, "error": f"不支持的操作: {operation}", "input_path": input_path, "output_path": output_path}
        
        except Exception as e:
            return {"success": False, "error": str(e), "input_path": input_path, "output_path": output_path}
