# Elicitation 管理器

import logging
from typing import Dict, Any, Optional
from mcp_client.llm import LLMClient

class ElicitationManager:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
    
    def check_dangerous_operation(self, tool_name: str, tool_args: Dict[str, Any]) -> Optional[str]:
        """检查是否为危险操作"""
        dangerous_patterns = [
            # 文件系统危险操作
            ("execute_python", "code", ["rm -rf", "os.system", "subprocess.run"]),
            ("system_command", "command", ["rm -rf", "format", "shutdown", "reboot"]),
        ]
        
        for pattern_tool, pattern_arg, dangerous_keywords in dangerous_patterns:
            if tool_name == pattern_tool:
                arg_value = tool_args.get(pattern_arg, "")
                if isinstance(arg_value, str):
                    for keyword in dangerous_keywords:
                        if keyword in arg_value:
                            return f"检测到危险操作: {keyword}，是否确认执行？"
        
        # 检查文件操作
        if tool_name == "execute_python":
            code = tool_args.get("code", "")
            if isinstance(code, str):
                # 检查文件写入操作
                if "open(" in code.lower() or "with open(" in code.lower():
                    if any(mode in code.lower() for mode in ["'w'", "'w", '"w"', '"w', "'a'", "'a", '"a"', '"a']):
                        return "检测到文件写入操作，是否确认执行？"
                
                # 检查文件删除操作
                if any(keyword in code.lower() for keyword in ["os.remove", "os.unlink", "os.rmdir", "os.removedirs", "shutil.rmtree"]):
                    return "检测到文件删除操作，是否确认执行？"
                
                # 检查目录操作
                if any(keyword in code.lower() for keyword in ["os.mkdir", "os.makedirs", "os.listdir", "os.walk"]):
                    return "检测到目录操作，是否确认执行？"
        
        return None
    
    def generate_elicitation_message(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """生成二次确认消息"""
        message = self.check_dangerous_operation(tool_name, tool_args)
        if message:
            return message
        
        # 通用危险操作提示
        return "此操作可能存在风险，是否确认执行？"
