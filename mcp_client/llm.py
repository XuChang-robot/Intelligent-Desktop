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
            stream_error = None
            
            def stream_handler():
                nonlocal full_response, full_thinking, stream_error
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
                    stream_error = e
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
            
            # 检查是否发生错误
            if stream_error:
                raise stream_error
            
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
            
            # 检查是否是连接错误
            error_str = str(e)
            if "10061" in error_str or "10054" in error_str or "拒绝" in error_str or "refused" in error_str.lower() or "connection" in error_str.lower():
                raise ConnectionError(f"无法与LLM服务通信，请确保Ollama已启动并正常运行") from e
            
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
        """解析用户意图（提取意图类型和关键实体，task类型时同时生成行为树配置）"""
        system_prompt = "你是一个智能桌面系统的意图解析器，负责分析用户的自然语言输入并判断意图类型、提取关键实体，如果意图是task类型则同时生成行为树配置。你必须只返回有效的JSON格式，不要包含任何其他文字、解释或markdown标记。"
        
        # 格式化工具信息（包含参数）
        tools_info = ""
        if tools:
            tools_info = "\n\n可用工具列表：\n"
            for tool in tools:
                tool_name = tool.name if hasattr(tool, 'name') else str(tool)
                tool_desc = tool.description if hasattr(tool, 'description') else ""
                tools_info += f"- {tool_name}: {tool_desc}\n"
                
                # 添加工具参数信息
                if hasattr(tool, 'inputSchema') and tool.inputSchema:
                    tools_info += f"  参数：\n"
                    properties = tool.inputSchema.get('properties', {})
                    required = tool.inputSchema.get('required', [])
                    for param_name, param_info in properties.items():
                        param_desc = param_info.get('description', '')
                        param_type = param_info.get('type', 'unknown')
                        is_required = param_name in required
                        required_mark = " (必需)" if is_required else " (可选)"
                        tools_info += f"    - {param_name}: {param_type}{required_mark}"
                        if param_desc:
                            tools_info += f" - {param_desc}"
                        tools_info += "\n"
                    tools_info += "\n"
        
        prompt = f"""请分析以下用户输入，判断用户的意图类型、根据工具信息提取关键实体并根据意图类型生成任务计划（如果是task类型）：



工具信息：
{tools_info}

重要规则：
1. 意图类型只能是以下三种：
   - "task": 任务型意图，当前可用工具可以完成的操作
   - "chat": 聊天型意图，当前可用工具无法完成的操作，包括问候、提问、闲聊、咨询等纯对话内容，不执行任何工具
   - "cannot_execute": 无法执行型意图，用户确实想调用工具执行任务，但现有工具或工具的组合步骤不能满足任务执行需要

意图类型说明：
- task: 任务型意图，当前可用工具可以完成的操作
- chat: 聊天型意图，当前可用工具无法完成的操作，包括问候、提问、闲聊、咨询等纯对话内容，不执行任何工具
- cannot_execute: 无法执行型意图，用户确实想调用工具执行任务，但现有工具或工具的组合步骤不能满足任务执行需要

判断是否为"task"的标准：
- 当前可用工具可以完成用户的请求（如文件操作、系统信息、文本处理、网络请求、邮件发送、天气查询、股票查询、新闻查询、快递查询等）
- 用户明确要求执行某个操作（如"转换"、"发送"、"处理"、"生成"、"删除"、"打开"、"查询"等）
- **重要：如果用户输入只是简单的问候语（如"你好"、"早上好"等），不要识别为task**

判断是否为"chat"的标准：
- **优先判断**：如果用户输入是问候语，直接识别为chat类型
- 问候语包括："你好"、"早上好"、"下午好"、"晚上好"、"嗨"、"hello"、"hi"、"在吗"、"你好吗"、"在吗"等
- 当前可用工具无法完成用户的请求
- 用户只是问候（如"你好"、"早上好"等）
- 用户只是提问（如"什么是"、"如何"、"为什么"等）
- 用户只是闲聊（如"你好吗"、"在吗"等）
- 用户没有明确要求执行任何操作

判断是否为"cannot_execute"的标准：
- 用户确实想调用工具执行任务，但现有工具或工具的组合步骤不能满足任务执行需要
- 用户明确要求执行某个操作，但当前工具无法完成
- 用户提到的任务需要多个步骤，但当前工具无法组合完成
- 用户提到的功能超出了当前工具的能力范围

2. 行为树生成（如果是task类型意图）
如果是task类型意图，根据意图生成行为树配置。

行为树节点类型：
- Sequence: 序列节点（所有子节点按顺序执行，全部成功才返回成功）
- Selector: 选择器节点（依次执行子节点，直到有一个成功）
- Parallel: 并行节点（同时执行所有子节点，提高执行效率）
- Action: 动作节点（调用MCP工具）
- Condition: 条件节点（检查条件）

节点配置格式：
{{
  "type": "节点类型",
  "name": "节点名称",
  "children": [子节点列表],
  "tool": "工具名称",  // Action节点
  "parameters": {{}},     // Action节点参数
  "condition": "条件表达式"  // Condition节点
}}

条件表达式语法：
- 支持比较运算: ==, !=, >, <, >=, <=
- 支持逻辑运算: and, or, not
- 支持成员运算: in
- 支持函数调用: len(), str(), int()
- 引用前面结果: action_0.success, action_0.result.path
- 引用实体: entities.path, entities.keyword

条件表达式示例：
- "action_0.success == true"
- "len(action_0.result.files) > 5"
- "'error' in action_0.result.message"
- "action_0.result.status in ['completed', 'success']"

参数引用语法：
- 支持引用前面节点的结果: {{action_0.result.path}}
- 支持引用实体: {{entities.path}}

重要规则：
1. 根据用户输入和实体信息，生成合理的任务执行流程
2. 使用合适的节点类型（Sequence、Selector、Parallel等），**优先使用Parallel节点**：当多个任务相互独立、没有依赖关系时，使用Parallel节点同时执行，提高效率
3. 使用Sequence节点：当任务有先后顺序依赖时使用
4. Action节点必须指定tool和parameters， parameters必须是一个字典，包含工具需要的所有参数
5. Condition节点必须指定condition
6. 确保节点间的引用关系正确
7. 根据需要使用条件节点实现分支逻辑
8. 不要使用不存在的工具

请严格按照以下JSON格式返回结果，不要添加任何其他内容：
{{
  "intent": "用户的主要意图（只能是task、chat或cannot_execute）",
  "entities": {{}},
  "confidence": 0.0-1.0,
  "reason": "无法执行的原因（仅当intent为cannot_execute时提供）",
  "tree_config": {{  // 仅当intent为task时提供
    "type": "节点类型",
    "name": "节点名称",
    "children": [...],
    "tool": "工具名称",
    "parameters": {{}},
    "condition": "条件表达式"
  }}
}}

**示例开始**：
"你好"->
{{
  "intent": "chat",
  "entities": {{}},
  "confidence": 0.9
}}

"今天天气如何"->
{{
  "intent": "task",
  "entities": {{
    "operation": "ip_weather"
  }},
  "confidence": 0.95,
  "tree_config": {{
    "type": "Action",
    "name": "查询天气",
    "tool": "weather_query",
    "parameters": {{
      "operation": "ip_weather",
      "detail_level": "simple"
    }}
  }}
}}

"帮我让天上下雨"->
{{
  "intent": "cannot_execute",
  "entities": {{}},
  "confidence": 0.99,
  "reason": "当前工具无法完成天气控制"
}}
**示例结束**

用户输入：{user_input}。

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
