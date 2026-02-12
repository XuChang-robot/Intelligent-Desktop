# 文本处理工具

import asyncio
from typing import Dict, Any


def register_text_processing_tools(mcp):
    """注册文本处理工具到MCP服务器
    
    Args:
        mcp: FastMCP实例
    """
    
    @mcp.tool()
    async def text_processing(
        operation: str,
        text: str = None,
        input_file: str = None,
        lang: str = "zh",
        format_type: str = "plain",
        output_path: str = None,
        voice: str = None,
        rate: int = 200,
        volume: float = 1.0
    ) -> Dict[str, Any]:
        """文本处理工具
        
        支持多种文本处理操作，包括文字转语音、摘要、格式化等。
        支持从文本文件和Word文档（.docx）读取内容。
        
        Args:
            operation: 操作类型，可选值：
                - "to_audio": 文字转语音（使用pyttsx3）
                - "summarize": 文本摘要（简单截取）
                - "format": 文本格式化
                - "count": 统计字符数、单词数、行数
            text: 输入文本（如果提供input_file则可选）
            input_file: 输入文件路径（可选，用于从文件读取文本，支持.txt和.docx文件）
            lang: 语言代码（用于to_audio，默认"zh"）
            format_type: 格式化类型（用于format，可选"upper"、"lower"、"title"、"plain"）
            output_path: 输出文件路径（用于to_audio，默认与输入文件同目录）
            voice: 声音（用于to_audio，默认系统默认）
            rate: 语速（用于to_audio，默认200，范围50-500）
            volume: 音量（用于to_audio，默认1.0，范围0.0-2.0）
        
        Returns:
            {
                "success": True/False,
                "result": 处理结果,
                "file": 音频文件路径（仅to_audio操作）,
                "error": 错误信息（如果失败）
            }
        
        Examples:
            - 文字转语音: text_processing("to_audio", "你好世界", lang="zh")
            - 文字转语音（自定义参数）: text_processing("to_audio", "你好世界", lang="zh", rate=150, volume=0.8)
            - 文本摘要: text_processing("summarize", "这是一段很长的文本...")
            - 文本格式化: text_processing("format", "hello world", format_type="upper")
            - 统计信息: text_processing("count", "hello world")
            - 从Word文档转语音: text_processing("to_audio", input_file="桌面/说明.docx", output_path="桌面/cx/说明.wav")
        """
        try:
            import os
            from pathlib import Path
            
            # 处理输入文件（如果提供）
            if input_file:
                input_file = os.path.expanduser(input_file)
                
                # 获取桌面路径
                desktop_path = str(Path.home() / "Desktop")
                
                # 处理桌面路径
                if input_file == "桌面" or input_file == "desktop":
                    input_file = desktop_path
                elif input_file.startswith("桌面/") or input_file.startswith("desktop/"):
                    input_file = str(Path(desktop_path) / input_file.split("/", 1)[1])
                
                # 读取输入文件内容
                try:
                    # 检测文件类型
                    file_ext = os.path.splitext(input_file)[1].lower()
                    
                    if file_ext == '.docx':
                        # Word文档，使用python-docx库读取
                        try:
                            from docx import Document
                            doc = Document(input_file)
                            file_text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
                        except ImportError:
                            return {"success": False, "error": "未安装python-docx库，请运行: pip install python-docx"}
                        except Exception as e:
                            return {"success": False, "error": f"读取Word文档失败: {str(e)}"}
                    elif file_ext in ['.doc', '.pdf', '.pptx']:
                        # 其他Office文档，暂不支持
                        return {"success": False, "error": f"暂不支持{file_ext}文件格式，请使用文本文件或.docx文件"}
                    else:
                        # 普通文本文件
                        with open(input_file, 'r', encoding='utf-8') as f:
                            file_text = f.read()
                    
                    # 如果同时提供了text和input_file，优先使用文件内容
                    if text:
                        import warnings
                        warnings.warn("同时提供了text和input_file参数，将优先使用input_file的内容")
                    text = file_text
                except Exception as e:
                    return {"success": False, "error": f"读取输入文件失败: {str(e)}"}
            
            # 验证文本输入
            if not text:
                return {"success": False, "error": "必须提供text或input_file参数"}
            
            if operation == "to_audio":
                # 确定输出文件路径
                if output_path:
                    # 展开路径中的~符号（Windows和Unix都支持）
                    output_path = os.path.expanduser(output_path)
                    
                    # 获取桌面路径
                    desktop_path = str(Path.home() / "Desktop")
                    
                    # 处理桌面路径
                    if output_path == "桌面" or output_path == "desktop":
                        output_path = desktop_path
                    elif output_path.startswith("桌面/") or output_path.startswith("desktop/"):
                        output_path = str(Path(desktop_path) / output_path.split("/", 1)[1])
                    
                    # 如果指定了输出路径，使用该路径
                    if os.path.isdir(output_path):
                        # 如果是目录，生成文件名
                        output_file = os.path.join(output_path, f"audio_{asyncio.get_event_loop().time()}.wav")
                    else:
                        # 如果是文件路径，直接使用
                        output_file = output_path
                elif input_file:
                    # 如果未指定输出路径但提供了输入文件，使用与输入文件相同的目录和文件名（不同后缀）
                    input_dir = os.path.dirname(input_file)
                    input_name = os.path.splitext(os.path.basename(input_file))[0]
                    output_file = os.path.join(input_dir, f"{input_name}.wav")
                else:
                    # 默认保存在当前目录
                    output_file = f"audio_{asyncio.get_event_loop().time()}.wav"
                
                try:
                    import pyttsx3
                    engine = pyttsx3.init()
                    
                    # 设置语速
                    engine.setProperty('rate', rate)
                    
                    # 设置音量
                    engine.setProperty('volume', volume)
                    
                    # 设置声音
                    if voice:
                        voices = engine.getProperty('voices')
                        for v in voices:
                            if voice in v.id or voice in v.name:
                                engine.setProperty('voice', v.id)
                                break
                    
                    # 保存到文件
                    engine.save_to_file(text, output_file)
                    engine.runAndWait()
                    
                    return {
                        "success": True,
                        "result": "音频生成成功（使用pyttsx3）",
                        "file": output_file,
                        "duration": len(text) * 0.1
                    }
                except ImportError:
                    return {"success": False, "error": "未安装pyttsx3库，请运行: pip install pyttsx3"}
                except Exception as e:
                    return {"success": False, "error": f"音频生成失败: {str(e)}"}
            
            elif operation == "summarize":
                summary = text[:100] + "..." if len(text) > 100 else text
                return {
                    "success": True,
                    "result": summary,
                    "original_length": len(text)
                }
            
            elif operation == "format":
                if format_type == 'upper':
                    result = text.upper()
                elif format_type == 'lower':
                    result = text.lower()
                elif format_type == 'title':
                    result = text.title()
                else:
                    result = text
                return {
                    "success": True,
                    "result": result,
                    "format_type": format_type
                }
            
            elif operation == "count":
                result = {
                    "characters": len(text),
                    "characters_no_spaces": len(text.replace(" ", "").replace("\n", "").replace("\t", "")),
                    "words": len(text.split()),
                    "lines": len(text.splitlines())
                }
                return {
                    "success": True,
                    "result": result
                }
            
            else:
                return {"success": False, "error": f"不支持的操作: {operation}"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
