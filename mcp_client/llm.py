# LLM Client 模块

import ollama
import logging
import json
import asyncio
from typing import Dict, Any, Optional
from config.config import load_config

class LLMClient:
    def __init__(self):
        self.config = load_config()
        self.model = self.config["llm"]["model"]
        self.base_url = self.config["llm"]["base_url"]
        self.temperature = self.config["llm"]["temperature"]
        self.max_tokens = self.config["llm"]["max_tokens"]
        self.repeat_penalty = self.config["llm"].get("repeat_penalty", 1.1)
        self.top_p = self.config["llm"].get("top_p", 0.9)
        self.top_k = self.config["llm"].get("top_k", 40)
        self.logger = logging.getLogger(__name__)
        
        # Ollama默认连接到http://localhost:11434
        # 注意：如果需要自定义Ollama服务地址，请设置环境变量 OLLAMA_HOST
        # 例如：set OLLAMA_HOST=http://localhost:11434
    
    def update_model(self, model_name: str):
        """更新模型名称"""
        self.model = model_name
        self.logger.info(f"模型已更新为: {model_name}")
    
    def get_current_model(self):
        """获取当前模型名称"""
        return self.model
    
    def get_available_models(self):
        """获取可用的模型列表"""
        try:
            import httpx
            response = httpx.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [model["name"] for model in data.get("models", [])]
                self.logger.info(f"获取到可用模型: {models}")
                return models
            else:
                self.logger.error(f"获取模型列表失败: {response.status_code}")
                return ["qwen3:30b", "qwen3:7b", "llama2:7b"]
        except Exception as e:
            self.logger.error(f"获取模型列表异常: {e}")
            return ["qwen3:30b", "qwen3:7b", "llama2:7b"]
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None, timeout: int = 120) -> str:
        """生成LLM响应"""
        try:
            import time
            start_time = time.time()
            
            options = {
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "repeat_penalty": self.repeat_penalty,
                "top_p": self.top_p,
                "top_k": self.top_k
            }
            
            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                system=system_prompt,
                options=options
            )
            
            elapsed_time = time.time() - start_time
            self.logger.info(f"LLM生成完成，耗时: {elapsed_time:.2f}秒")
            
            return response.get("response", "")
        except Exception as e:
            self.logger.error(f"LLM生成失败: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def validate_and_fix_json(self, json_str: str) -> str:
        """验证并修复JSON格式问题
        
        Args:
            json_str: 要验证和修复的JSON字符串
            
        Returns:
            修复后的JSON字符串
        """
        import json
        import re
        
        # 首先尝试直接解析
        try:
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON格式错误: {e}")
        
        # 开始修复过程
        fixed_json = json_str
        
        # 1. 移除控制字符，并处理因控制字符导致的格式问题
        import re
        control_char_pattern = re.compile(r'[\x00-\x1F\x7F]')
        
        # 先移除控制字符
        fixed_json = control_char_pattern.sub('', fixed_json)
        
        # 检查是否有字符串未闭合的情况（因为控制字符可能打断了字符串）
        # 查找所有键值对，检查值是否正确闭合
        # 修复模式: "key": "value" (未闭合的字符串)
        # 检查是否有 "key": "value 这样的模式（后面没有闭合引号）
        # 这种情况通常是因为控制字符打断了字符串
        
        # 修复: "key": "value 后面直接是另一个键的情况
        fixed_json = re.sub(r'("[^"]+":\s*)"([^"]*)(\s*"[^"]+":)', r'\1"\2", \3', fixed_json)
        
        # 2. 修复多余的逗号
        # 修复对象开头的多余逗号: { , "key":
        fixed_json = re.sub(r'\{\s*,\s*"[^"]+":', '{ "', fixed_json)
        # 修复对象中间的多余逗号: "key": "value", , "key":
        fixed_json = re.sub(r'("[^"]+":\s*"[^"]+")(,\s*)(,\s*)("[^"]+":)', r'\1, \4', fixed_json)
        
        # 3. 修复缺少逗号的问题
        # 修复: "key": "value""key":
        fixed_json = re.sub(r'("[^"]+":\s*"[^"]+")("[^"]+":)', r'\1, \2', fixed_json)
        
        # 4. 修复引号不匹配的问题
        # 计算引号数量
        quote_count = fixed_json.count('"')
        if quote_count % 2 != 0:
            # 如果引号数量为奇数，尝试在适当位置添加引号
            # 查找最后一个冒号后的内容，确保字符串闭合
            last_colon = fixed_json.rfind(':')
            if last_colon != -1:
                # 在最后一个引号后添加引号
                last_quote = fixed_json.rfind('"')
                if last_quote != -1 and last_quote > last_colon:
                    fixed_json = fixed_json[:last_quote+1] + '"' + fixed_json[last_quote+1:]
        
        # 5. 修复括号不匹配的问题
        open_braces = fixed_json.count('{')
        close_braces = fixed_json.count('}')
        if open_braces > close_braces:
            fixed_json += '}' * (open_braces - close_braces)
        elif close_braces > open_braces:
            fixed_json = '{' * (close_braces - open_braces) + fixed_json
        
        open_brackets = fixed_json.count('[')
        close_brackets = fixed_json.count(']')
        if open_brackets > close_brackets:
            fixed_json += ']' * (open_brackets - close_brackets)
        elif close_brackets > open_brackets:
            fixed_json = '[' * (close_brackets - open_brackets) + fixed_json
        
        # 尝试再次解析修复后的JSON
        try:
            json.loads(fixed_json)
            self.logger.info("JSON格式修复成功")
            return fixed_json
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON格式修复失败: {e}")
            # 如果修复失败，返回原始字符串
            return json_str
    
    def clean_json_response(self, response: str) -> str:
        """清理JSON响应，移除markdown代码块标记和其他无关内容"""
        response = response.strip()
        
        # 首先验证JSON格式，如果已经是正确的格式，直接返回
        try:
            import json
            json.loads(response)
            return response
        except json.JSONDecodeError:
            # 如果JSON格式不正确，继续清理
            pass
        
        # 移除markdown代码块标记
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        
        # 移除注释（但要避免误删URL中的//）
        lines = response.split('\n')
        cleaned_lines = []
        in_string = False
        for line in lines:
            # 检查是否在JSON字符串内
            quote_count = line.count('"')
            if quote_count % 2 != 0:
                in_string = not in_string
            
            # 只在不在字符串内时才移除注释
            if not in_string and '//' in line:
                line = line[:line.index('//')]
            cleaned_lines.append(line)
        
        response = '\n'.join(cleaned_lines).strip()
        
        # 验证并修复JSON格式
        response = self.validate_and_fix_json(response)
        
        return response
    
    async def parse_intent(self, user_input: str) -> Dict[str, Any]:
        """解析用户意图"""
        system_prompt = "你是一个智能桌面系统的意图解析器，负责分析用户的自然语言输入并提取出明确的意图和关键信息。你必须只返回有效的JSON格式，不要包含任何其他文字、解释或markdown标记。"
        
        prompt = f"""请分析以下用户输入，提取出用户的意图和关键信息：

用户输入：{user_input}

重要规则：
1. 意图类型只能是以下几种：
   - "task": 任务型意图（默认），包括文件操作、系统信息、文本处理、网络请求等
   - "execute_code": 仅当用户明确要求执行Python代码时使用
2. 对于文件操作（创建、读取、写入、删除文件/文件夹），使用"task"意图
3. 对于获取系统信息，使用"task"意图
4. 对于文本处理（转语音、摘要、格式化），使用"task"意图
5. 对于网络请求，使用"task"意图
6. 不要使用"execute_code"意图，除非用户明确提到"执行Python代码"、"运行代码"等关键词

请严格按照以下JSON格式返回结果，不要添加任何其他内容：
{{
  "intent": "用户的主要意图（只能是task或execute_code）",
  "entities": {{
    "关键信息1": "值1",
    "关键信息2": "值2"
  }},
  "confidence": 0.9
}}

注意：只返回JSON，不要包含任何解释、注释或其他文字。"""
        
        response = self.generate(prompt, system_prompt)
        response = self.clean_json_response(response)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            self.logger.error(f"解析意图响应失败: {e}, 原始响应: {response}")
            return {
                "intent": "task",
                "entities": {},
                "confidence": 0.5
            }
    
    def format_tools_for_llm(self, tools) -> str:
        """将MCP工具列表格式化为LLM可理解的文本格式
        
        Args:
            tools: MCP工具列表（从server获取）
            
        Returns:
            格式化后的工具描述文本
        """
        if not tools:
            return "没有可用的工具"
        
        tool_descriptions = ["可用工具列表：\n"]
        
        for i, tool in enumerate(tools, 1):
            tool_name = tool.name if hasattr(tool, 'name') else str(tool)
            tool_desc = tool.description if hasattr(tool, 'description') else ""
            
            tool_descriptions.append(f"{i}. {tool_name}")
            
            if tool_desc:
                tool_descriptions.append(f"   描述: {tool_desc}")
            
            # 处理参数信息
            if hasattr(tool, 'inputSchema'):
                input_schema = tool.inputSchema
                if hasattr(input_schema, 'properties'):
                    properties = input_schema.properties
                    if properties:
                        tool_descriptions.append("   参数:")
                        for param_name, param_info in properties.items():
                            param_type = param_info.get('type', 'unknown')
                            param_desc = param_info.get('description', '')
                            required = param_name in input_schema.get('required', [])
                            
                            param_line = f"   - {param_name} ({param_type}"
                            if required:
                                param_line += ", 必需"
                            else:
                                param_line += ", 可选"
                            param_line += ")"
                            tool_descriptions.append(param_line)
                            
                            if param_desc:
                                tool_descriptions.append(f"     {param_desc}")
            
            tool_descriptions.append("")  # 空行分隔
        
        return "\n".join(tool_descriptions)
    
    async def plan_task(self, intent: Dict[str, Any], tools=None) -> Dict[str, Any]:
        """规划任务步骤
        
        Args:
            intent: 用户意图
            tools: 可用工具列表（从server获取）
        """
        system_prompt = """
                            你是一个智能桌面系统的任务规划器，负责根据用户的意图生成详细的任务执行计划。
                            你必须只返回有效的JSON格式，不要包含任何其他文字、解释或markdown标记。
                            注意，须符合以下要求：
                            1. 不要任何解释、注释、代码块标记
                            2. 键名必须使用双引号
                            3. 字符串值必须使用双引号
                            4. 不要尾随逗号
                        """
        
        # 格式化工具列表
        available_tools = self.format_tools_for_llm(tools) if tools else "没有可用的工具"
        
        prompt = f"""请根据以下用户意图，生成详细的任务执行计划：\n\n用户意图：{intent}\n\n{available_tools}\n\n重要规则：
1. 优先使用上面列出的专用工具
2. 只有当专用工具无法满足需求时，才使用 execute_python 工具（如果存在）
3. 不要使用不存在的工具，只能使用上面列出的工具
4. 如果可用工具无法完成用户任务，请返回空的steps数组，并在plan字段说明无法完成的原因\n\n请严格按照以下JSON格式返回结果，不要添加任何其他内容：\n{{\n  \"plan\": \"任务计划概述\",\n  \"steps\": [\n    {{\n      \"tool\": \"工具名称\",\n      \"args\": {{\n        \"参数名\": \"参数值\"\n      }},\n      \"description\": \"步骤描述\"\n    }}\n  ]\n}}\n\n注意：只返回JSON，不要包含任何解释、注释或其他文字。"""
        
        response = self.generate(prompt, system_prompt)
        response = self.clean_json_response(response)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            self.logger.error(f"解析任务计划失败: {e}, 原始响应: {response}")
            return {
                "plan": "无法生成任务计划",
                "steps": []
            }
    
    async def generate_summary(self, user_input: str, plan: Dict[str, Any], results: list) -> str:
        """生成执行结果总结"""
        system_prompt = "你是一个智能桌面系统的总结器，负责根据任务执行结果向用户提供清晰的总结。"
        
        prompt = f"请根据以下信息，生成一个清晰的执行结果总结：\n\n用户输入：{user_input}\n\n任务计划：{plan}\n\n执行结果：{results}\n\n请用自然语言总结执行过程和结果，确保用户能够理解。"
        
        return self.generate(prompt, system_prompt)
    
    async def generate_python_code(self, task_description: str) -> str:
        """生成Python代码"""
        self.logger.info(f"开始生成Python代码，任务描述: {task_description[:50]}...")
        system_prompt = "你是一个智能桌面系统的代码生成器，负责根据任务描述生成安全、有效的Python代码。"
        
        prompt = f"""请根据以下任务描述，生成安全、有效的Python代码：\n\n任务描述：{task_description}\n\n要求：\n1. 代码必须安全，不能包含危险操作\n2. 代码必须有效，能够完成任务\n3. 代码必须清晰，有适当的注释\n4. 代码必须返回有意义的结果\n5. 只返回Python代码，不要包含markdown代码块标记（如```python）或其他解释\n6. 对于长时间运行的代码（如循环处理多个文件、批量操作等），必须使用tqdm库显示进度条，以便用户了解执行进度\n7. 使用tqdm时，确保进度信息通过print()输出，格式为：print(f\"进度: {{i+1}}/{{total}}\") 或使用tqdm的进度条\n8. 严禁在代码末尾添加任何提示词、说明、示例或其他无关文本\n9. 代码必须以if __name__ == \"__main__\":块结束，之后不能再有任何内容\n\n可用库：\n- os: 文件路径操作\n- pathlib: 路径操作\n- json: JSON数据处理\n- re: 正则表达式\n- datetime: 日期时间处理\n- math: 数学计算\n- random: 随机数生成\n- collections: 集合工具\n- itertools: 迭代工具\n- typing: 类型提示\n- numpy: 数值计算\n- matplotlib: 绘图\n- sympy: 符号计算\n- scipy: 科学计算\n- tqdm: 进度条显示（用于长时间运行的任务）\n- win32com.client: Windows COM接口（用于Office文件操作）\n\n注意：\n1. 不要使用subprocess、os.system等系统命令\n2. 不要使用eval、exec等危险函数\n3. 不要使用pickle、marshal等序列化模块\n4. 不要使用socket、urllib、requests等网络模块\n5. 对于Word到PDF转换，使用win32com.client库调用Word的COM接口\n6. 对于循环处理多个文件、批量操作等长时间运行的任务，使用tqdm显示进度，并确保进度信息通过print()输出\n7. 代码结束后立即停止，不要添加任何额外的文本、说明或示例\n8. 对于文件操作，特别是涉及桌面路径的操作，使用os.path.expanduser('~')来获取用户主目录，然后拼接桌面路径\n9. 对于删除文件夹的操作，使用shutil.rmtree()函数，并确保添加适当的错误处理"""
        
        # 使用asyncio.run_in_executor在单独的线程中运行generate，避免阻塞
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()
        
        try:
            self.logger.info(f"开始调用LLM生成代码")
            # 移除超时设置
            result = await loop.run_in_executor(None, self.generate, prompt, system_prompt)
            self.logger.info(f"LLM生成代码完成，结果长度: {len(result)}")
            # 不要使用clean_json_response清理Python代码
            return result
        except Exception as e:
            self.logger.error(f"LLM生成代码异常: {e}")
            import traceback
            traceback.print_exc()
            return ""
