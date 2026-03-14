# LLM Client 模块

import ollama
import logging
import json
import asyncio
import os
from typing import Dict, Any, Optional, Callable
from user_config.config import load_config, get_config
from mcp_client.behavior_tree.prompt.config_prompts import BEHAVIOR_TREE_CONFIG_PRINCIPLES
from mcp_client.prompt.intent_prompts import INTENT_PARSE_PROMPT
from .behavior_tree import BehaviorTree

class LLMClient:
    def __init__(self):
        self.config = load_config()
        self.model = self.config["llm"]["model"]
        self.base_url = self.config["llm"]["base_url"]
        self.temperature = self.config["llm"].get("temperature", 0.6)
        self.max_tokens = self.config["llm"].get("max_tokens", 100000)
        self.repeat_penalty = self.config["llm"].get("repeat_penalty", 1.1)
        self.top_p = self.config["llm"].get("top_p", 0.9)
        self.top_k = self.config["llm"].get("top_k", 40)
        self.logger = logging.getLogger(__name__)
        
        # 获取日志目录配置
        self.log_dir = get_config("logging.log_dir", "logs")
        # 获取开发模式配置（嵌套结构）
        self.dev_mode = get_config("logging.dev_mode.enabled", False)
        # 获取思考模式开关（仅在dev_mode启用时有效）
        self.enable_thinking = get_config("logging.dev_mode.enable_thinking", False)
        # 确保日志目录存在
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 移除BehaviorTree实例，直接使用静态方法
        pass
        
        # Ollama默认连接到http://localhost:11434
        # 注意：如果需要自定义Ollama服务地址，请设置环境变量 OLLAMA_HOST
        # 例如：set OLLAMA_HOST=http://localhost:11434
    
    def update_model(self, model_name: str):
        """更新模型名称"""
        self.model = model_name
        self.logger.info(f"模型已更新为: {model_name}")
    
    def set_model(self, model):
        """设置模型"""
        self.update_model(model)
    
    def get_current_model(self):
        """获取当前模型名称"""
        return self.model
    
    def _save_debug_file(self, filename: str, content: Any, description: str = "调试文件"):
        """保存调试文件到logs目录（仅在开发者模式下）
        
        Args:
            filename: 文件名
            content: 文件内容（字符串或可序列化的对象）
            description: 文件描述
        """
        if not self.dev_mode:
            return
        
        try:
            file_path = os.path.join(self.log_dir, filename)
            if isinstance(content, str):
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
            else:
                import json
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(content, f, ensure_ascii=False, indent=2)
            self.logger.debug(f"{description}已保存到 {file_path}")
        except Exception as e:
            self.logger.error(f"保存调试文件失败: {e}")
    
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
                return []
        except Exception as e:
            self.logger.error(f"获取模型列表异常: {e}")
            return []
    
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, stream_callback: Optional[Callable] = None, bool_think_content: Optional[bool] = True) -> Dict[str, Any]:
        """生成LLM响应
        
        Args:
            prompt: 提示词
            system_prompt: 系统提示词
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
                "top_k": self.top_k,
                "num_ctx": 8192,
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
                    # 尝试启用思考功能
                    try:
                        for chunk in ollama.generate(
                            model=self.model,
                            prompt=prompt,
                            system=system_prompt,
                            options=options,
                            stream=True,
                            keep_alive=0,  # 不保留上下文
                            context=None,  # 明确不传递上下文
                            think=True  # 启用思考功能
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

                            # 累加到完整响应
                            full_response += chunk_response
                            if chunk_thinking:
                                full_thinking += chunk_thinking
                            
                            # 调用回调函数（同步调用）
                            if stream_callback:
                                stream_callback({
                                    "response": chunk_response,
                                    "thinking": chunk_thinking if bool_think_content else "",
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
                        # 处理模型不支持思考功能的情况
                        if "does not support thinking" in str(e):
                            self.logger.warning(f"模型 {self.model} 不支持思考功能，将禁用思考模式重新尝试")
                            # 重新尝试不使用思考模式
                            chunk_count = 0
                            full_response = ""
                            full_thinking = ""
                            for chunk in ollama.generate(
                                model=self.model,
                                prompt=prompt,
                                system=system_prompt,
                                options=options,
                                stream=True,
                                context=None,  # 明确不传递上下文
                                think=False  # 禁用思考功能
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
                            
                            # 完成时调用回调
                            if stream_callback:
                                stream_callback({
                                    "response": "",
                                    "thinking": "",
                                    "done": True
                                })
                        else:
                            # 其他错误，抛出异常
                            raise
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
                "thinking": thinking if bool_think_content else ""
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
        
        # 格式化工具信息（包含参数）
        tools_info = ""
        if tools:
            tools_info = "\n\n" + self.format_tools_for_llm(tools)
        
        # 动态构建行为树节点的JSON schema

        behavior_tree_node_schema = BehaviorTree.build_node_schema(tools)
        
        # 构建完整的JSON schema，包含所有配置字段
        intent_schema = {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "enum": ["task", "chat", "cannot_execute"]
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0
                },
                "reason": {
                    "type": "string"
                },
                "tree_config": {
                    "$ref": "#/$defs/behaviorTreeNode"
                }
            },
            "required": ["intent"],
            "$defs": {
                "behaviorTreeNode": behavior_tree_node_schema["$defs"]["behaviorTreeNode"]
            }
        }
        
        # 保存schema文件用于调试（仅在开发者模式下）
        self._save_debug_file("behavior_tree_schema.json", behavior_tree_node_schema, "行为树schema")
        self._save_debug_file("intent_schema.json", intent_schema, "完整的schema")
        
        system_prompt = INTENT_PARSE_PROMPT.format(
            tools_info=tools_info,
            BEHAVIOR_TREE_CONFIG_PRINCIPLES=BEHAVIOR_TREE_CONFIG_PRINCIPLES,
            user_input=user_input
        )
        #对于提到的具体文件名或路径，无需额外添加验证或搜索子任务。
        user_prompt =f"""
        用户输入：
        {user_input}。"""

        try:
            # 仅调试输出思考才用，当前版本的format与think参数同时使用会相互影响导致think不能正常输出
            # 思考模式需要同时满足：dev_mode=true 且 enable_thinking=true
            if self.dev_mode and self.enable_thinking:
                try:
                    response = ollama.generate(
                        model=self.model,
                        prompt=user_prompt,
                        system=system_prompt,
                        options={
                            "temperature": self.temperature,
                            "repeat_penalty": self.repeat_penalty,
                            "top_p": self.top_p,
                            "top_k": self.top_k,
                            "num_ctx": 8192,
                        },
                        think=True  # 启用思考功能
                    )
                    thinking_content = response.get("thinking", "")
                    if thinking_content:
                        self.logger.debug(f"LLM思考: {thinking_content[:500]}...")
                        # 保存思考内容到文件
                        self._save_debug_file("llm_thinking.txt", thinking_content, "LLM思考内容")
                except Exception as e:
                    # 处理模型不支持思考功能的情况
                    if "does not support thinking" in str(e):
                        self.logger.warning(f"模型 {self.model} 不支持思考功能，跳过思考输出")
                    else:
                        self.logger.error(f"获取思考内容失败: {e}")

            # 使用ollama.generate API，启用结构化输出
            import time
            start_time = time.time()
            response = ollama.generate(
                model=self.model,
                prompt=user_prompt,
                system=system_prompt,
                format=intent_schema,  # 传递完整的JSON schema对象
                options={
                    "temperature": self.temperature,
                    "repeat_penalty": self.repeat_penalty,
                    "top_p": self.top_p,
                    "top_k": self.top_k,
                    "num_ctx": 8192,
                },
                think=False  # 禁用思考功能
            )
            end_time = time.time()
            elapsed_time = end_time - start_time
            self.logger.info(f"LLM解析意图耗时: {elapsed_time:.2f}秒")
            
            # 获取响应内容
            response_content = response.get("response", "")
            
            # 调试：记录原始响应
            self.logger.debug(f"LLM原始响应: {response_content}...")
            # 保存到文件
            self._save_debug_file("llm_response_raw.txt", response_content, "LLM原始响应")
            
            # 解析JSON响应
            result = json.loads(response_content)
            self.logger.debug(f"JSON解析结果: {result}")
            return result
        except json.JSONDecodeError as e:
            self.logger.error(f"解析意图响应失败: {e}, 原始响应: {response_content}")
            raise Exception(f"意图解析失败：无法解析LLM返回的JSON格式。错误信息：{e}")
        except Exception as e:
            self.logger.error(f"意图解析失败: {e}")
            import traceback
            traceback.print_exc()
            raise
    
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
        
        for tool in tools:
            tool_name = tool.name if hasattr(tool, 'name') else str(tool)
            tool_desc = tool.description if hasattr(tool, 'description') else ""       
            tool_descriptions.append(f"- {tool_name}: {tool_desc}")

            # 处理参数信息
            if hasattr(tool, 'inputSchema') and tool.inputSchema:
                properties = tool.inputSchema.get('properties', {})
                required = tool.inputSchema.get('required', [])
                defs = tool.inputSchema.get('$defs', {})
                if properties:
                    tool_descriptions.append("  参数：")
                    for param_name, param_info in properties.items():
                        param_desc = param_info.get('description', '')
                        param_type = param_info.get('type', 'unknown')
                        # 处理$ref引用的枚举类型
                        if '$ref' in param_info:
                            ref = param_info['$ref']
                            if ref.startswith('#/$defs/'):
                                enum_name = ref.split('#/$defs/')[1]
                                if enum_name in defs:
                                    enum_def = defs[enum_name]
                                    if 'enum' in enum_def:
                                        enum_values = enum_def['enum']
                                        param_type = f"({', '.join(enum_values)})"
                        is_required = param_name in required
                        required_mark = " (必需)" if is_required else " (可选)"
                        tool_descriptions.append(f"    - {param_name}: {param_type}{required_mark}")
                        if param_desc:
                            tool_descriptions.append(f"     {param_desc}")
                    tool_descriptions.append("")
        
        return "\n".join(tool_descriptions)
