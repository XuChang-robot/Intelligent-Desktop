# MCP Server 安全检查模块

import logging
import ast
import re
from typing import Dict, Any
import sys
sys.path.append('..')
from config.config import load_config

class SecurityChecker:
    def __init__(self):
        self.config = load_config()
        self.logger = logging.getLogger(__name__)
        self.dangerous_patterns = self._load_dangerous_patterns()
    
    def _load_dangerous_patterns(self) -> list:
        """加载危险模式"""
        return [
            # 文件系统危险操作
            r"rm\s+-rf",
            r"format\s+",
            r"del\s+/f\s+/s\s+/q",
            r"Remove-Item\s+-Recurse\s+-Force",
            
            # 系统危险操作
            r"shutdown\s+",
            r"reboot\s+",
            r"halt\s+",
            r"poweroff\s+",
            
            # 网络危险操作
            r"netstat\s+",
            r"arp\s+",
            r"ipconfig\s+/all",
            
            # Python危险操作
            r"import\s+os\s*;\s*os\.system",
            r"subprocess\.run\s*\(",
            r"eval\s*\(",
            r"exec\s*\(",
            r"open\s*\(.*,\s*['\"](?:w|a|x)['\"]",
            r"__import__\s*\(",
            
            # 其他危险操作
            r"sudo\s+",
            r"su\s+",
            r"passwd\s+",
        ]
    
    def check_dangerous_operation(self, code: str) -> str:
        """检查代码是否包含危险操作，返回危险操作描述
        
        Returns:
            如果是危险操作，返回描述消息；否则返回None
        """
        code_lower = code.lower()
        
        # 检查文件写入操作
        if "open(" in code_lower:
            write_modes = ["'w'", '"w"', "'a'", '"a"', "'x'", '"x"']
            has_write_mode = any(mode in code_lower for mode in write_modes)
            if has_write_mode:
                # 提取文件路径
                files = self._extract_file_paths(code, ["open("])
                if files:
                    return f"检测到文件写入操作，要写入的文件: {', '.join(files)}，是否确认执行？"
                return "检测到文件写入操作，是否确认执行？"
        
        # 检查文件删除操作
        dangerous_delete_patterns = [
            "os.remove",
            "os.unlink",
            "os.rmdir",
            "os.removedirs",
            "shutil.rmtree",
            ".unlink",
            ".remove",
            ".rmdir",
            ".removedirs"
        ]
        
        has_delete_operation = False
        delete_files = set()
        
        for operation in dangerous_delete_patterns:
            if operation in code_lower:
                has_delete_operation = True
                # 提取要删除的文件路径
                files = self._extract_file_paths(code, [operation])
                delete_files.update(files)
        
        if has_delete_operation:
            if delete_files:
                return f"检测到文件删除操作，要删除的文件: {', '.join(delete_files)}，是否确认执行？"
            return "检测到文件删除操作，是否确认执行？"
        
        # 检查目录操作
        dangerous_dir_keywords = ["os.mkdir", "os.makedirs", "os.listdir", "os.walk"]
        for keyword in dangerous_dir_keywords:
            if keyword in code_lower:
                # 提取目录路径
                dirs = self._extract_file_paths(code, [keyword])
                if dirs:
                    return f"检测到目录操作，操作的目录: {', '.join(dirs)}，是否确认执行？"
                return "检测到目录操作，是否确认执行？"
        
        # 检查其他危险操作
        dangerous_keywords = [
            "os.system", "subprocess", "eval(", "exec(", "__import__",
            "compile(", "pickle", "marshal",
            "socket", "urllib", "requests", "http.client", "https.client"
        ]
        
        for keyword in dangerous_keywords:
            if keyword in code_lower:
                return f"检测到危险操作: {keyword}，是否确认执行？"
        
        return None
    
    def _extract_file_paths(self, code: str, operations: list) -> list:
        """提取代码中指定操作的文件路径
        
        Args:
            code: Python代码
            operations: 要提取文件路径的操作列表，如["os.remove", "open("]
            
        Returns:
            提取的文件路径列表
        """
        file_paths = []
        
        # 过滤掉的非文件路径关键字
        filter_keywords = ["'w'", '"w"', "'a'", '"a"', "'x'", '"x"', "w", "a", "x"]
        
        for operation in operations:
            # 使用正则表达式提取操作后的括号内容
            if "(" in operation:
                # 对于带括号的操作，如 open(
                pattern = rf"{re.escape(operation)}\s*([^)]*)"
            else:
                # 对于不带括号的操作，如 os.remove
                pattern = rf"{re.escape(operation)}\s*\(\s*([^)]*)\s*\)"
            
            matches = re.findall(pattern, code)
            for match in matches:
                # 临时集合，用于存储当前匹配中的文件路径，避免重复
                current_paths = set()
                
                # 首先尝试匹配完整的字符串路径（单引号或双引号包围）
                # 匹配单引号包围的字符串（支持转义）
                single_quote_pattern = r"'([^'\\]*(\\.[^'\\]*)*)'"
                single_matches = re.findall(single_quote_pattern, match)
                for path_tuple in single_matches:
                    path = path_tuple[0]
                    if path and path not in filter_keywords:
                        current_paths.add(path)
                
                # 匹配双引号包围的字符串（支持转义）
                double_quote_pattern = r'"([^"\\]*(\\.[^"\\]*)*)"'
                double_matches = re.findall(double_quote_pattern, match)
                for path_tuple in double_matches:
                    path = path_tuple[0]
                    if path and path not in filter_keywords:
                        current_paths.add(path)
                
                # 如果没有找到字符串路径，尝试匹配变量名
                if not (single_matches or double_matches):
                    var_pattern = r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b"
                    var_matches = re.findall(var_pattern, match)
                    for var in var_matches:
                        if var and not any(keyword in var for keyword in ["True", "False", "None"] + filter_keywords):
                            var_name = f"{var} (变量)"
                            current_paths.add(var_name)
                
                # 将当前匹配中的文件路径添加到总列表中
                file_paths.extend(current_paths)
        
        # 去重并过滤空字符串
        unique_paths = list(set(file_paths))
        filtered_paths = [path for path in unique_paths if path]
        return filtered_paths[:5]  # 最多显示5个文件
    
    def check_tool_call(self, tool_name: str, tool_args: Dict[str, Any]) -> bool:
        """检查工具调用是否安全"""
        try:
            self.logger.info(f"检查工具调用: {tool_name}, 参数: {tool_args}")
            if tool_name == "execute_python":
                code = tool_args.get("code", "")
                self.logger.info(f"检查Python代码: {code}")
                result = self._check_python_code(code)
                self.logger.info(f"Python代码检查结果: {result}")
                return result
            elif tool_name == "system_command":
                command = tool_args.get("command", "")
                self.logger.info(f"检查系统命令: {command}")
                result = self._check_system_command(command)
                self.logger.info(f"系统命令检查结果: {result}")
                return result
            result = True
            self.logger.info(f"工具调用检查结果: {result}")
            return result
        except Exception as e:
            self.logger.error(f"安全检查出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _check_python_code(self, code: str) -> bool:
        """检查Python代码是否安全
        
        采用白箱模式，允许绝大部分Python代码通过安全检查
        对于危险代码，返回False，触发elicitation模式与用户进行交互获取权限
        """
        code_lower = code.lower()
        
        # 只检查真正危险的操作
        dangerous_keywords = [
            "os.system", "subprocess", "eval(", "exec(", "__import__",
            "compile(", "pickle", "marshal",
            "socket", "urllib", "requests", "http.client", "https.client"
        ]
        
        for keyword in dangerous_keywords:
            if keyword in code_lower:
                self.logger.warning(f"检测到危险Python代码: {keyword}")
                self.logger.warning(f"匹配的代码: {code}")
                # 返回False，触发elicitation模式
                return False
        
        # 对于导入os模块的检查，只允许基本使用，不允许危险操作
        # 使用正则表达式匹配真正的import语句，避免误判
        import_pattern = r'\bimport\s+os\b'
        if re.search(import_pattern, code_lower):
            # 检查是否有危险的os操作
            dangerous_os_patterns = ["os.system", "os.popen", "os.spawn", "os.exec", "os.fork", "os.kill"]
            has_dangerous_os = any(pattern in code_lower for pattern in dangerous_os_patterns)
            if has_dangerous_os:
                self.logger.warning(f"检测到危险的os模块使用")
                self.logger.warning(f"匹配的代码: {code}")
                return False
        
        # 对于open()函数的检查，只允许读取操作，不允许写入操作
        if "open(" in code_lower:
            # 检查是否有写入模式
            write_modes = ["'w'", '"w"', "'a'", '"a"', "'x'", '"x"']
            has_write_mode = any(mode in code_lower for mode in write_modes)
            if has_write_mode:
                self.logger.warning(f"检测到文件写入操作")
                self.logger.warning(f"匹配的代码: {code}")
                return False
        
        # 对于所有其他代码，默认允许通过安全检查
        return True
    
    def _check_system_command(self, command: str) -> bool:
        """检查系统命令是否安全"""
        command_lower = command.lower()
        
        # 检查危险模式
        for pattern in self.dangerous_patterns:
            if re.search(pattern, command_lower):
                self.logger.warning(f"检测到危险系统命令: {pattern}")
                return False
        
        # 检查危险命令
        dangerous_commands = self.config["security"]["dangerous_commands"]
        for dangerous_cmd in dangerous_commands:
            if dangerous_cmd in command_lower:
                self.logger.warning(f"检测到危险命令: {dangerous_cmd}")
                return False
        
        return True
