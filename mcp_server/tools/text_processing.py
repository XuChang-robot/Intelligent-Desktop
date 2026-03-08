# 文本处理工具

import asyncio
import os
from typing import Dict, Any, Optional, Tuple
from enum import Enum
from pathlib import Path
from mcp.server.fastmcp import Context
from .tool_base import (
    ToolBase, ToolResult, OperationConfig, register_tool, ConfirmModel, extract_path_from_blackboard
)


class TextOperationEnum(str, Enum):
    TO_AUDIO = "to_audio"
    SUMMARIZE = "summarize"
    FORMAT = "format"
    COUNT = "count"


@register_tool("text_processing")
class TextProcessingTool(ToolBase):
    """文本处理工具
    
    支持多种文本处理操作，包括文字转语音、摘要、格式化等。
    """
    
    TOOL_NAME = "text_processing"
    
    OPERATION_CONFIG = {
        'to_audio': OperationConfig(
            description='文字转语音（使用pyttsx3）',
            required_params=[],
            optional_params=['text', 'input_file', 'lang', 'output_path', 'voice', 'rate', 'volume']
        ),
        'summarize': OperationConfig(
            description='文本摘要（简单截取）',
            required_params=[],
            optional_params=['text', 'input_file']
        ),
        'format': OperationConfig(
            description='文本格式化',
            required_params=[],
            optional_params=['text', 'input_file', 'format_type']
        ),
        'count': OperationConfig(
            description='统计字符数、单词数、行数',
            required_params=[],
            optional_params=['text', 'input_file']
        )
    }
    
    @classmethod
    def validate_parameters(cls, operation: str, **kwargs) -> Tuple[Dict[str, Any], Optional[str]]:
        """验证并调整参数
        
        Args:
            operation: 操作类型
            **kwargs: 参数字典
            
        Returns:
            (调整后的参数字典, 配置错误信息)
        """
        params, config_error = super().validate_parameters(operation, **kwargs)
        
        if config_error:
            return params, config_error
        
        text = kwargs.get('text')
        input_file = kwargs.get('input_file')
        
        if not text and not input_file:
            config_error = f"{operation}操作需要text或input_file参数"
        
        if operation == "to_audio" and not kwargs.get('output_path'):
            config_error = config_error or "to_audio操作需要output_path参数"
        
        return params, config_error
    
    async def execute(self, ctx: Optional[Context] = None, **kwargs) -> Dict[str, Any]:
        """执行文本处理操作"""
        operation = kwargs.get('operation')
        text = kwargs.get('text')
        input_file = kwargs.get('input_file')
        lang = kwargs.get('lang', 'zh')
        format_type = kwargs.get('format_type', 'plain')
        output_path = kwargs.get('output_path')
        voice = kwargs.get('voice')
        rate = kwargs.get('rate', 200)
        volume = kwargs.get('volume', 1.0)
        
        if input_file:
            text, error = self._read_input_file(input_file)
            if error:
                return error
            if text and kwargs.get('text'):
                self.logger.warning("同时提供了text和input_file参数，将优先使用input_file的内容")
        
        if operation == "to_audio":
            return await self._to_audio(text, output_path, input_file, rate, volume, voice)
        elif operation == "summarize":
            return self._summarize(text)
        elif operation == "format":
            return self._format(text, format_type)
        elif operation == "count":
            return self._count(text)
        else:
            return ToolResult.error(f"不支持的操作: {operation}").build()
    
    def _read_input_file(self, input_file: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """读取输入文件
        
        Returns:
            (text, error_result) - 成功时error_result为None，失败时text为None
        """
        # 使用通用函数处理路径（支持从列表字符串中提取第一个路径）
        try:
            input_file = extract_path_from_blackboard(input_file)
        except ValueError as e:
            return None, ToolResult.error(f"路径解析失败: {str(e)}").build()
        
        input_file = os.path.expanduser(input_file)
        desktop_path = str(Path.home() / "Desktop")
        
        if input_file == "桌面" or input_file == "desktop":
            input_file = desktop_path
        elif input_file.startswith("桌面/") or input_file.startswith("desktop/"):
            input_file = str(Path(desktop_path) / input_file.split("/", 1)[1])
        
        try:
            file_ext = os.path.splitext(input_file)[1].lower()
            
            if file_ext == '.docx':
                try:
                    from docx import Document
                    doc = Document(input_file)
                    file_text = '\n'.join([p.text for p in doc.paragraphs])
                    return file_text, None
                except ImportError:
                    return None, ToolResult.error(
                        "未安装python-docx库，请运行: pip install python-docx"
                    ).build()
            elif file_ext in ['.doc', '.pdf', '.pptx']:
                return None, ToolResult.error(
                    f"暂不支持{file_ext}文件格式，请使用文本文件或.docx文件"
                ).build()
            else:
                with open(input_file, 'r', encoding='utf-8') as f:
                    return f.read(), None
        except Exception as e:
            return None, ToolResult.error(f"读取输入文件失败: {str(e)}").build()
    
    async def _to_audio(
        self, text: str, output_path: Optional[str], 
        input_file: Optional[str], rate: int, volume: float, voice: Optional[str]
    ) -> Dict[str, Any]:
        """文字转语音"""
        try:
            import pyttsx3
        except ImportError:
            return ToolResult.error(
                "未安装pyttsx3库，请运行: pip install pyttsx3"
            ).build()
        
        output_file = self._determine_output_path(output_path, input_file)
        
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', rate)
            engine.setProperty('volume', volume)
            
            if voice:
                voices = engine.getProperty('voices')
                for v in voices:
                    if voice in v.id or voice in v.name:
                        engine.setProperty('voice', v.id)
                        break
            
            engine.save_to_file(text, output_file)
            engine.runAndWait()
            
            return (ToolResult.success("音频生成成功（使用pyttsx3）")
                .with_path(output_file)
                .with_extra("file", output_file)
                .with_extra("duration", len(text) * 0.1)
                .with_message(
                    f"🎵 音频生成成功\n"
                    f"📄 文本长度: {len(text)} 字符\n"
                    f"📁 输出文件: {os.path.basename(output_file)}\n"
                    f"📍 保存路径: {output_file}\n"
                    f"⚙️ 语速: {rate}\n"
                    f"🔊 音量: {volume}"
                ).build())
        except Exception as e:
            return ToolResult.error(f"音频生成失败: {str(e)}").build()
    
    def _determine_output_path(self, output_path: Optional[str], input_file: Optional[str]) -> str:
        """确定输出文件路径"""
        if output_path:
            output_path = os.path.expanduser(output_path)
            desktop_path = str(Path.home() / "Desktop")
            
            if output_path == "桌面" or output_path == "desktop":
                output_path = desktop_path
            elif output_path.startswith("桌面/") or output_path.startswith("desktop/"):
                output_path = str(Path(desktop_path) / output_path.split("/", 1)[1])
            
            if os.path.isdir(output_path):
                return os.path.join(output_path, f"audio_{asyncio.get_event_loop().time()}.wav")
            return output_path
        elif input_file:
            input_dir = os.path.dirname(input_file)
            input_name = os.path.splitext(os.path.basename(input_file))[0]
            return os.path.join(input_dir, f"{input_name}.wav")
        else:
            return f"audio_{asyncio.get_event_loop().time()}.wav"
    
    def _summarize(self, text: str) -> Dict[str, Any]:
        """文本摘要"""
        summary = text[:100] + "..." if len(text) > 100 else text
        return (ToolResult.success(summary)
            .with_extra("original_length", len(text))
            .with_message(
                f"📝 文本摘要\n"
                f"📊 原始长度: {len(text)} 字符\n"
                f"📊 摘要长度: {len(summary)} 字符\n\n"
                f"摘要内容:\n{summary}"
            ).build())
    
    def _format(self, text: str, format_type: str) -> Dict[str, Any]:
        """文本格式化"""
        if format_type == 'upper':
            result = text.upper()
        elif format_type == 'lower':
            result = text.lower()
        elif format_type == 'title':
            result = text.title()
        else:
            result = text
        
        preview = result[:200] + "..." if len(result) > 200 else result
        return (ToolResult.success(result)
            .with_extra("format_type", format_type)
            .with_message(
                f"📄 文本格式化\n"
                f"🔧 格式类型: {format_type}\n"
                f"📊 文本长度: {len(result)} 字符\n\n"
                f"格式化结果:\n{preview}"
            ).build())
    
    def _count(self, text: str) -> Dict[str, Any]:
        """统计文本"""
        result = {
            "characters": len(text),
            "characters_no_spaces": len(text.replace(" ", "").replace("\n", "").replace("\t", "")),
            "words": len(text.split()),
            "lines": len(text.splitlines())
        }
        return (ToolResult.success(result)
            .with_message(
                f"📊 文本统计\n"
                f"📝 总字符数: {result['characters']}\n"
                f"📝 不含空格: {result['characters_no_spaces']}\n"
                f"📖 单词数: {result['words']}\n"
                f"📏 行数: {result['lines']}"
            ).build())


def register_text_processing_tools(mcp):
    """注册文本处理工具到MCP服务器
    
    Args:
        mcp: FastMCP实例
    """
    tool = TextProcessingTool()
    
    @mcp.tool()
    async def text_processing(
        operation: TextOperationEnum,
        text: str = None,
        input_file: str = None,
        lang: str = "zh",
        format_type: str = "plain",
        output_path: str = None,
        voice: str = None,
        rate: int = 200,
        volume: float = 1.0,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """文本处理工具
        
        支持多种文本处理操作，包括文字转语音、摘要、格式化等。
        支持从文本文件和Word文档（.docx）读取内容。
        
        Args:
            operation: 操作类型，可选值: to_audio, summarize, format, count
            其中：

                to_audio 用于将文本转语音，操作参数:
                    input_file: 输入文件路径（支持.txt和.docx文件，与text参数二选一）
                    text: 输入字符串（与input_file参数二选一）
                    output_path: 输出音频文件路径（必需）
                    lang: 语言代码（默认"zh"）
                    voice: 声音（默认系统默认）
                    rate: 语速（默认200，范围50-500）
                    volume: 音量（默认1.0，范围0.0-2.0）
                
                format 用于格式化文本，操作参数:
                    format_type: 格式化类型（默认"plain"）
                        - "upper": 转换为大写
                        - "lower": 转换为小写
                        - "title": 转换为标题格式
                        - "plain": 保持原样
                    input_file: 输入文件路径（支持.txt和.docx文件，与text参数二选一）
                    text: 输入字符串（与input_file参数二选一）

                summarize/count 用于对文本进行摘要统计，操作参数:
                    仅需 text 或 input_file
                    input_file: 输入文件路径（支持.txt和.docx文件，与text参数二选一）
                    text: 输入字符串（与input_file参数二选一）

        Returns:
            执行结果字典
        """
        return await tool.safe_execute(
            ctx=ctx,
            operation=operation,
            text=text,
            input_file=input_file,
            lang=lang,
            format_type=format_type,
            output_path=output_path,
            voice=voice,
            rate=rate,
            volume=volume
        )
