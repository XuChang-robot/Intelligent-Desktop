# 文本处理工具

import asyncio
from typing import Dict, Any, Optional, Tuple
from enum import Enum
from pathlib import Path
from pydantic import Field


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
# 工具名称：text_processing
# 支持的操作类型（operation）：
#   - "to_audio": 文字转语音（使用pyttsx3）
#   - "summarize": 文本摘要（简单截取）
#   - "format": 文本格式化
#   - "count": 统计字符数、单词数、行数
# 必需参数：
#   - operation: 操作类型（必需）
#   - text: 输入文本（必需，除非提供input_file）
# 可选参数：
#   - input_file: 输入文件路径（可选，用于从文件读取文本，支持.txt和.docx文件）
#   - lang: 语言代码（用于to_audio，默认"zh"）
#   - format_type: 格式化类型（用于format，可选"upper"、"lower"、"title"、"plain"）
#   - output_path: 输出文件路径（用于to_audio，默认与输入文件同目录）
#   - voice: 声音（用于to_audio，默认系统默认）
#   - rate: 语速（用于to_audio，默认200，范围50-500）
#   - volume: 音量（用于to_audio，默认1.0，范围0.0-2.0）
#
# 参数验证规则：
#   - operation: 必须是支持的操作类型之一
#   - text: 不能为空（除非提供input_file）
#   - output_path: to_audio操作时不能为空
#
# 返回格式：
#   - 成功：{"success": True, "result": "...", "file": "...", "formatted_message": "..."}
#   - 配置错误：{"success": False, "config_error": "..."}
#   - 执行失败：{"success": False, "error": "...", "formatted_message": "..."}


# 操作类型枚举
class TextOperationEnum(str, Enum):
    TO_AUDIO = "to_audio"
    SUMMARIZE = "summarize"
    FORMAT = "format"
    COUNT = "count"

# 操作类型配置
OPERATION_CONFIG = {
    'to_audio': {
        'description': '文字转语音',
        'required_params': ['text'],
        'optional_params': ['lang', 'output_path', 'voice', 'rate', 'volume']
    },
    'summarize': {
        'description': '文本摘要',
        'required_params': ['text'],
        'optional_params': []
    },
    'format': {
        'description': '文本格式化',
        'required_params': ['text'],
        'optional_params': ['format_type']
    },
    'count': {
        'description': '统计字符数、单词数、行数',
        'required_params': ['text'],
        'optional_params': []
    }
}


def validate_parameters(operation: TextOperationEnum, text: str = None, output_path: str = None) -> Tuple[Dict[str, Any], Optional[str]]:
    """验证并调整参数
    
    Args:
        operation: 操作类型
        text: 输入文本
        output_path: 输出文件路径
    
    Returns:
        (调整后的参数字典, 配置错误信息)
    """
    params = {
        'operation': operation,
        'text': text,
        'output_path': output_path
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
        if param == 'text' and not text:
            config_error = config_error or f"{operation}操作需要text参数"
    
    # 验证特定操作的必需参数
    if operation == "to_audio" and not output_path:
        config_error = config_error or "to_audio操作需要output_path参数"
    
    return params, config_error


def register_text_processing_tools(mcp):
    """注册文本处理工具到MCP服务器
    
    Args:
        mcp: FastMCP实例
    """
    
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
        volume: float = 1.0
    ) -> Dict[str, Any]:
        """文本处理工具
        
        支持多种文本处理操作，包括文字转语音、摘要、格式化等。
        支持从文本文件和Word文档（.docx）读取内容。
        
        Args:
            operation: 操作类型
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
            - 文字转语音（自定义参数）: text_processing("to_audio", "你好世界", lang="zh", rate=150, volume=0.8)
            - 统计信息: text_processing("count", "hello world")
        """
        try:
            import os
            
            # 参数验证
            params, config_error = validate_parameters(operation, text, output_path)
            
            # 如果存在配置错误，返回错误
            if config_error:
                return {
                    "success": False,
                    "config_error": config_error
                }
            
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
                            return {
                                "success": False, 
                                "error": "未安装python-docx库，请运行: pip install python-docx",
                                "formatted_message": "❌ 错误: 未安装python-docx库，请运行: pip install python-docx"
                            }
                        except Exception as e:
                            return {
                                "success": False, 
                                "error": f"读取Word文档失败: {str(e)}",
                                "formatted_message": f"❌ 错误: 读取Word文档失败: {str(e)}"
                            }
                    elif file_ext in ['.doc', '.pdf', '.pptx']:
                        # 其他Office文档，暂不支持
                        return {
                            "success": False, 
                            "error": f"暂不支持{file_ext}文件格式，请使用文本文件或.docx文件",
                            "formatted_message": f"❌ 错误: 暂不支持{file_ext}文件格式，请使用文本文件或.docx文件"
                        }
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
                    return {
                        "success": False, 
                        "error": f"读取输入文件失败: {str(e)}",
                        "formatted_message": f"❌ 错误: 读取输入文件失败: {str(e)}"
                    }
            
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
                        "duration": len(text) * 0.1,
                        "formatted_message": f"🎵 音频生成成功\n📄 文本长度: {len(text)} 字符\n📁 输出文件: {os.path.basename(output_file)}\n📍 保存路径: {output_file}\n⚙️ 语速: {rate}\n🔊 音量: {volume}"
                    }
                except ImportError:
                    return {
                        "success": False, 
                        "error": "未安装pyttsx3库，请运行: pip install pyttsx3",
                        "formatted_message": "❌ 错误: 未安装pyttsx3库，请运行: pip install pyttsx3"
                    }
                except Exception as e:
                    return {
                        "success": False, 
                        "error": f"音频生成失败: {str(e)}",
                        "formatted_message": f"❌ 错误: 音频生成失败: {str(e)}"
                    }
            
            elif operation == TextOperationEnum.SUMMARIZE:
                summary = text[:100] + "..." if len(text) > 100 else text
                return {
                    "success": True,
                    "result": summary,
                    "original_length": len(text),
                    "formatted_message": f"📝 文本摘要\n📊 原始长度: {len(text)} 字符\n📊 摘要长度: {len(summary)} 字符\n\n摘要内容:\n{summary}"
                }
            
            elif operation == TextOperationEnum.FORMAT:
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
                    "format_type": format_type,
                    "formatted_message": f"📄 文本格式化\n🔧 格式类型: {format_type}\n📊 文本长度: {len(result)} 字符\n\n格式化结果:\n{result[:200]}{'...' if len(result) > 200 else ''}"
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
                    "result": result,
                    "formatted_message": f"📊 文本统计\n📝 总字符数: {result['characters']}\n📝 不含空格: {result['characters_no_spaces']}\n📖 单词数: {result['words']}\n📏 行数: {result['lines']}"
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
