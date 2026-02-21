# LLM Client 模块

import ollama
import logging
import json
import asyncio
from typing import Dict, Any, Optional, Callable
from user_config.config import load_config

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
    
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, timeout: int = 120, stream_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """生成LLM响应
        
        Args:
            prompt: 提示词
            system_prompt: 系统提示词
            timeout: 超时时间
            stream_callback: 流式输出回调函数，接收chunk数据
            
        Returns:
            Dict[str, Any]: 包含response和thinking的字典
        """
        try:
            import time
            import asyncio
            start_time = time.time()
            
            options = {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,  # ollama使用num_predict，不是max_tokens
                "repeat_penalty": self.repeat_penalty,
                "top_p": self.top_p,
                "top_k": self.top_k
            }
            
            # 使用asyncio.run_in_executor在后台线程中运行同步的ollama.generate
            loop = asyncio.get_event_loop()
            
            # 存储完整响应
            full_response = ""
            full_thinking = ""
            
            def stream_handler():
                nonlocal full_response, full_thinking
                try:
                    # 使用ollama的流式生成
                    # 添加keep_alive参数，避免上下文缓存
                    chunk_count = 0
                    for chunk in ollama.generate(
                        model=self.model,
                        prompt=prompt,
                        system=system_prompt,
                        options=options,
                        stream=True,
                        keep_alive=0,  # 不保留上下文
                        context=None  # 明确不传递上下文
                    ):
                        chunk_count += 1
                        # 获取chunk数据
                        chunk_response = chunk.get("response", "")
                        chunk_thinking = chunk.get("thinking", "")
                        
                        # 确保是字符串类型
                        if chunk_response is None:
                            chunk_response = ""
                        if chunk_thinking is None:
                            chunk_thinking = ""
                        
                        # 调试信息：打印每个chunk的内容
                        # if chunk_count <= 5 or chunk_count % 10 == 0:
                        #     self.logger.info(f"Chunk {chunk_count}: response='{chunk_response}', thinking='{chunk_thinking}', done={chunk.get('done', False)}")
                        
                        # 累加到完整响应
                        full_response += chunk_response
                        if chunk_thinking:
                            full_thinking += chunk_thinking
                        
                        # 调用回调函数（同步调用）
                        if stream_callback:
                            stream_callback({
                                "response": chunk_response,
                                "thinking": chunk_thinking,
                                "done": False
                            })
                    
                    #self.logger.info(f"流式生成完成，共收到 {chunk_count} 个 chunk，总长度: {len(full_response)}")
                    
                    # 完成时调用回调
                    if stream_callback:
                        stream_callback({
                            "response": "",
                            "thinking": "",
                            "done": True
                        })
                except Exception as e:
                    self.logger.error(f"流式生成失败: {e}")
                    import traceback
                    traceback.print_exc()
                    # 发生错误时也调用回调
                    if stream_callback:
                        stream_callback({
                            "response": "",
                            "thinking": "",
                            "done": True,
                            "error": str(e)
                        })
            
            # 运行流式处理
            await loop.run_in_executor(
                None,  # 使用默认的线程池
                stream_handler
            )
            
            elapsed_time = time.time() - start_time
            self.logger.info(f"LLM生成完成，耗时: {elapsed_time:.2f}秒")
            
            # 检查响应中是否包含思考过程
            thinking = full_thinking
            if not thinking:
                # 尝试其他可能的字段名
                thinking = ""
            
            return {
                "response": full_response,
                "thinking": thinking
            }
        except Exception as e:
            self.logger.error(f"LLM生成失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "response": "",
                "thinking": ""
            }
    
    def validate_and_fix_json(self, json_str: str) -> str:
        """验证并修复JSON格式问题
        
        Args:
            json_str: 要验证和修复的JSON字符串
            
        Returns:
            修复后的JSON字符串
        """
        import json
        
        # 首先尝试直接解析
        try:
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON格式错误: {e}")
        
        # 使用 fast-json-repair 库修复JSON
        try:
            from fast_json_repair import repair_json
            fixed_json = repair_json(json_str)
            
            # 验证修复后的JSON
            json.loads(fixed_json)
            self.logger.info("JSON格式修复成功")
            return fixed_json
        except Exception as e:
            self.logger.error(f"fast-json-repair修复失败: {e}")
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
        
        # 移除JSON前面的所有非JSON文本（查找第一个{字符）
        first_brace = response.find('{')
        if first_brace > 0:
            response = response[first_brace:]
        
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
    
    async def parse_intent(self, user_input: str, tools=None) -> Dict[str, Any]:
        """解析用户意图（提取意图类型和关键实体，task类型时同时生成任务计划）"""
        system_prompt = "你是一个智能桌面系统的意图解析器，负责分析用户的自然语言输入并判断意图类型、提取关键实体，如果是task类型则同时生成任务执行计划。你必须只返回有效的JSON格式，不要包含任何其他文字、解释或markdown标记。"
        
        # 如果提供了tools，格式化工具信息
        tools_info = ""
        if tools:
            tools_info = "\n\n可用工具列表：\n"
            for tool in tools:
                tool_name = tool.name if hasattr(tool, 'name') else str(tool)
                tool_desc = tool.description if hasattr(tool, 'description') else ""
                tools_info += f"- {tool_name}: {tool_desc}\n"
        
        prompt = f"""请分析以下用户输入，判断用户的意图类型、根据工具信息提取关键实体并根据意图类型生成任务计划（如果是task类型）：

用户输入：{user_input}
工具信息：{tools_info}

重要规则：
1. 意图类型只能是以下三种：
   - "task": 任务型意图，当前可用工具可以完成的操作
   - "chat": 聊天型意图，当前可用工具无法完成的操作，包括问候、提问、闲聊、咨询等纯对话内容，不执行任何工具
   - "cannot_execute": 无法执行型意图，用户确实想调用工具执行任务，但现有工具或工具的组合步骤不能满足任务执行需要

2. 判断是否为"task"的标准：
   - 当前可用工具可以完成用户的请求（如文件操作、系统信息、文本处理、网络请求、邮件发送、天气查询、股票查询、新闻查询、快递查询等）
   - 用户明确要求执行某个操作（如"转换"、"发送"、"处理"、"生成"、"删除"、"打开"、"查询"等）
   - **重要：如果用户输入只是简单的问候语（如"你好"、"早上好"等），不要识别为task**

3. 判断是否为"chat"的标准：
   - **优先判断**：如果用户输入是问候语，直接识别为chat类型
   - 问候语包括："你好"、"早上好"、"下午好"、"晚上好"、"嗨"、"hello"、"hi"、"在吗"、"你好吗"、"在吗"等
   - 当前可用工具无法完成用户的请求
   - 用户只是问候（如"你好"、"早上好"等）
   - 用户只是提问（如"什么是"、"如何"、"为什么"等）
   - 用户只是闲聊（如"你好吗"、"在吗"等）
   - 用户没有明确要求执行任何操作

4. 判断是否为"cannot_execute"的标准：
   - 用户确实想调用工具执行任务，但现有工具或工具的组合步骤不能满足任务执行需要
   - 用户明确要求执行某个操作，但当前工具无法完成
   - 用户提到的任务需要多个步骤，但当前工具无法组合完成
   - 用户提到的功能超出了当前工具的能力范围


5. **如果意图类型是"task"，则同时生成任务执行计划**：
   - 根据提取的entities，生成详细的任务执行计划
   - 计划格式如下：
     {{
       "plan": "任务概述",
       "steps": [
         {{
           "tool": "工具名称",
           "args": {{
             "参数名": "参数值"
           }},
           "description": "步骤描述"
         }}
       ]
     }}
   - 生成任务计划的重要规则：
     * 不要使用不存在的工具，只能使用上面列出的工具
     * 根据用户输入，智能提取工具所需的参数
     * 如果用户输入包含多个操作或多个对象，生成多个步骤
     * 每个步骤只使用一个工具，完成一个明确的任务
     * 例如：如果用户输入"东京天气怎么样，长沙呢？"，应该识别出两个地点，生成两个天气查询步骤
     * 例如：如果用户输入"把桌面上的PDF转成Word，再把Word转成PDF"，应该识别出两个转换操作，生成两个转换步骤
     * 对于天气查询：
       - 区分国内和国外地点
       - 国内地点使用domestic_weather操作，需要province和city参数
       - 国外地点使用foreign_weather操作，只需要city参数
     * 对于文档转换：
       - 确保output_path包含完整的文件名和扩展名
       - 如果用户只指定了输出文件夹，根据输入文件名自动生成输出文件名

请严格按照以下JSON格式返回结果，不要添加任何其他内容：
{{
  "intent": "用户的主要意图（只能是task、chat或cannot_execute）",
  "confidence": 0.9,
  "reason": "无法执行的原因（仅当intent为cannot_execute时提供）",
  
  "plan": "任务计划概述（仅当intent为task时提供）",
  "steps": [
    {{
      "tool": "工具名称",
      "args": {{
        "参数名": "参数值"
      }},
      "description": "步骤描述"
    }}
  ]
}}

**示例**：
用户输入："把桌面上的证明、说明两个word文件转为pdf"
应返回：
{{
  "intent": "task",
  "confidence": 0.95,
  
  "plan": "将两个Word文档转换为PDF格式",
  "steps": [
    {{
      "tool": "document_converter",
      "args": {{
        "operation": "word_to_pdf",
        "input_path": "桌面/证明.docx",
        "output_path": "桌面/证明.pdf"
      }},
      "description": "将证明.docx转换为PDF"
    }},
    {{
      "tool": "document_converter",
      "args": {{
        "operation": "word_to_pdf",
        "input_path": "桌面/说明.docx",
        "output_path": "桌面/说明.pdf"
      }},
      "description": "将说明.docx转换为PDF"
    }}
  ]
}}

注意：只返回JSON，不要包含任何解释、注释或其他文字。"""
        
        response_dict = await self.generate(prompt, system_prompt)
        response = response_dict.get("response", "")
        thinking = response_dict.get("thinking", "")
        
        if thinking:
            self.logger.info(f"LLM思考过程: {thinking[:500]}...")
        
        self.logger.debug(f"LLM原始响应: {response[:200]}...")
        response = self.clean_json_response(response)
        self.logger.debug(f"修复后的响应: {response[:200]}...")
        
        try:
            result = json.loads(response)
            self.logger.debug(f"JSON解析结果: {result}")
            return result
        except json.JSONDecodeError as e:
            self.logger.error(f"解析意图响应失败: {e}, 原始响应: {response}")
            raise Exception(f"意图解析失败：无法解析LLM返回的JSON格式。错误信息：{e}")
    
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
            intent: 用户意图（包含user_input）
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
        
        # 获取用户输入
        user_input = intent.get("user_input", "")
        
        prompt = f"""请根据以下用户输入，生成详细的任务执行计划：

用户输入：{user_input}

{available_tools}

重要规则：
1. 优先使用上面列出的专用工具
2. 不要使用不存在的工具，只能使用上面列出的工具
3. 如果可用工具无法完成用户任务，请返回空的steps数组，并在plan字段说明无法完成的原因
4. 根据用户输入，智能提取工具所需的参数：
   - 仔细分析用户输入中的关键信息（如文件路径、城市名称、操作类型等）
   - 将提取的信息映射到工具参数
   - 如果用户输入包含多个操作或多个对象，生成多个步骤
   - 每个步骤只使用一个工具，完成一个明确的任务
   - 例如：如果用户输入"东京天气怎么样，长沙呢？"，应该识别出两个地点，生成两个天气查询步骤
   - 例如：如果用户输入"把桌面上的PDF转成Word，再把Word转成PDF"，应该识别出两个转换操作，生成两个转换步骤
5. 对于天气查询：
   - 区分国内和国外地点
   - 国内地点使用domestic_weather操作，需要province和city参数
   - 国外地点使用foreign_weather操作，只需要city参数
6. 对于文档转换：
   - 确保output_path包含完整的文件名和扩展名
   - 如果用户只指定了输出文件夹，根据输入文件名自动生成输出文件名

请严格按照以下JSON格式返回结果，不要添加任何其他内容：
{{
  "plan": "任务计划概述",
  "steps": [
    {{
      "tool": "工具名称",
      "args": {{
        "参数名": "参数值"
      }},
      "description": "步骤描述"
    }}
  ]
}}

注意：只返回JSON，不要包含任何解释、注释或其他文字。"""
        
        response_dict = await self.generate(prompt, system_prompt)
        response = response_dict.get("response", "")
        thinking = response_dict.get("thinking", "")
        
        if thinking:
            self.logger.info(f"LLM思考过程: {thinking[:500]}...")
        
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
        
        response_dict = await self.generate(prompt, system_prompt)
        return response_dict.get("response", "")
    
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
            response_dict = await loop.run_in_executor(None, self.generate, prompt, system_prompt)
            result = response_dict.get("response", "")
            thinking = response_dict.get("thinking", "")
            
            if thinking:
                self.logger.info(f"LLM思考过程: {thinking[:500]}...")
            
            self.logger.info(f"LLM生成代码完成，结果长度: {len(result)}")
            # 不要使用clean_json_response清理Python代码
            return result
        except Exception as e:
            self.logger.error(f"LLM生成代码异常: {e}")
            import traceback
            traceback.print_exc()
            return ""
