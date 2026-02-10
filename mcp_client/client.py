# MCP Client 主文件 - 使用官方ClientSession

import asyncio
import logging
import json
from typing import Dict, Any, Optional
from contextlib import AsyncExitStack
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import ElicitRequestParams, ElicitResult
from mcp_client.llm import LLMClient
from mcp_client.intent_parser import IntentParser
from mcp_client.task_planner import TaskPlanner
from mcp_client.elicitation import ElicitationManager
from config.config import load_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# 全局连接管理器实例
_global_session_manager = None

class SessionManager:
    """会话管理器，管理MCP会话"""
    def __init__(self, server_url):
        self.server_url = server_url
        self.stream_ctx = None
        self.read_stream = None
        self.write_stream = None
        self.session = None
        self.response_given = False
        self.connected = False
        self.elicitation_callback = None
    
    async def connect(self):
        """连接到MCP服务器"""
        if self.connected:
            logging.info("已经连接到服务器，无需重新连接")
            return
        
        logging.info(f"正在连接到服务器: {self.server_url}")

        try:
            # 创建MCP连接
            self.stream_ctx = streamable_http_client(self.server_url)
            # 手动进入上下文管理器，但不退出，保持流打开
            self.read_stream, self.write_stream, _ = await self.stream_ctx.__aenter__()

            # 创建并初始化会话
            self.session = ClientSession(self.read_stream, self.write_stream, elicitation_callback=self.handle_elicitation)
            # 手动进入上下文管理器，但不退出，保持会话打开
            await self.session.__aenter__()
            
            await self.session.initialize()
            logging.info("连接成功！")
            # 列出可用工具
            tools = await self.session.list_tools()
            logging.info(f"可用工具: {[t.name for t in tools.tools]}")
            self.connected = True
        except Exception as e:
            logging.error(f"连接失败: {str(e)}")
            # 清理资源
            await self.close()
            raise
    
    async def close(self):
        """关闭连接"""
        if not self.connected:
            return
        
        logging.info("正在关闭连接...")
        # 清理会话
        if hasattr(self, 'session') and self.session:
            try:
                await self.session.__aexit__(None, None, None)
            except:
                pass
            self.session = None
        
        # 清理流
        if hasattr(self, 'stream_ctx') and self.stream_ctx:
            try:
                await self.stream_ctx.__aexit__(None, None, None)
            except:
                pass
            self.stream_ctx = None
        
        self.read_stream = None
        self.write_stream = None
        self.connected = False
        logging.info("连接已关闭")
    
    async def handle_elicitation(
        self,
        context,
        params: ElicitRequestParams,
    ) -> ElicitResult:
        """
        处理服务器发送的 elicit 消息
        """
        logging.info("服务器需要更多信息...")
        logging.info(f"消息: {params.message}")
        logging.info(f"elicitation_callback: {self.elicitation_callback}")
        
        if self.elicitation_callback:
            try:
                # 调用UI回调获取用户确认
                user_approved = await self.elicitation_callback(params.message)
                logging.info(f"用户确认结果: {user_approved}")
                if user_approved:
                    # 使用content而不是data来返回用户输入的数据
                    result = ElicitResult(action="accept", content={"confirmed": True})
                    logging.info(f"返回accept结果: {result}")
                    return result
                else:
                    result = ElicitResult(action="decline")
                    logging.info(f"返回decline结果: {result}")
                    return result
            except Exception as e:
                logging.error(f"调用elicitation_callback时出错: {e}")
                import traceback
                traceback.print_exc()
                # 出错时默认拒绝
                result = ElicitResult(action="decline")
                logging.info(f"出错时返回decline结果: {result}")
                return result
        else:
            # 没有回调，默认拒绝
            result = ElicitResult(action="decline")
            logging.info(f"没有回调，返回decline结果: {result}")
            return result
    
    async def call_tool(self, tool_name, params):
        """调用工具"""
        if not self.connected:
            await self.connect()
        
        if not self.session:
            raise RuntimeError("会话未初始化")
        
        logging.info(f"调用工具: {tool_name}")
        logging.info(f"参数: {params}")
        
        try:
            # 直接使用session.call_tool
            result = await self.session.call_tool(tool_name, params)
            logging.info(f"工具调用成功，结果: {result}")
            return result
        except Exception as e:
            logging.error(f"工具调用失败: {e}")
            raise

async def get_session_manager(server_url="http://localhost:8000/mcp"):
    """获取全局的会话管理器实例"""
    global _global_session_manager
    if _global_session_manager is None:
        _global_session_manager = SessionManager(server_url)
    return _global_session_manager

async def initialize_global_session(server_url="http://localhost:8000/mcp"):
    """初始化全局会话"""
    manager = await get_session_manager(server_url)
    await manager.connect()
    return manager

async def close_global_session():
    """关闭全局会话"""
    global _global_session_manager
    if _global_session_manager:
        await _global_session_manager.close()
        _global_session_manager = None

class MCPClient:
    def __init__(self):
        self.config = load_config()
        self.llm_client = LLMClient()
        self.intent_parser = IntentParser(self.llm_client)
        self.task_planner = TaskPlanner(self.llm_client)
        self.elicitation_manager = ElicitationManager(self.llm_client)
        self.session_manager: Optional[SessionManager] = None
        self.logger = logging.getLogger(__name__)
        self.elicitation_callback = None
        self.ui_callback = None
    
    async def connect(self) -> bool:
        """连接到MCP Server"""
        try:
            # 获取全局会话管理器
            self.session_manager = await get_session_manager()
            # 设置elicitation_callback
            if self.elicitation_callback:
                self.session_manager.elicitation_callback = self.elicitation_callback
            # 连接到服务器
            await self.session_manager.connect()
            self.logger.info("成功连接到MCP Server")
            return True
                
        except Exception as e:
            self.logger.error(f"连接MCP Server失败: {e}")
            return False
    
    async def disconnect(self):
        """断开连接"""
        await close_global_session()
        self.session_manager = None
        self.logger.info("已断开与MCP Server的连接")
    
    def set_elicitation_callback(self, callback):
        """设置二次确认回调"""
        self.elicitation_callback = callback
    
    def set_ui_callback(self, callback):
        """设置UI回调"""
        self.ui_callback = callback

    async def send_tool_call(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """发送工具调用请求"""
        if not self.session_manager:
            await self.connect()
        
        retry_attempts = self.config["mcp"]["client"]["retry_attempts"]
        for attempt in range(retry_attempts):
            try:
                # 使用官方MCP Client API调用工具
                result = await self.session_manager.call_tool(tool_name, tool_args)
                
                # 解析结果
                if hasattr(result, 'content'):
                    # 处理官方MCP返回的结果格式
                    content = result.content
                    if content and len(content) > 0:
                        # 获取第一个内容项
                        first_item = content[0]
                        if hasattr(first_item, 'text'):
                            return {
                                "type": "tool_response",
                                "result": first_item.text
                            }
                        elif hasattr(first_item, 'data'):
                            return {
                                "type": "tool_response",
                                "result": first_item.data
                            }
                
                # 如果无法解析，返回原始结果
                return {
                    "type": "tool_response",
                    "result": str(result)
                }
                    
            except Exception as e:
                self.logger.error(f"工具调用异常 (尝试 {attempt + 1}/{retry_attempts}): {e}")
                if attempt == retry_attempts - 1:
                    raise
                if attempt < retry_attempts - 1:
                    await asyncio.sleep(1)
                else:
                    return {
                        "type": "error",
                        "error": str(e)
                    }
        
        return {
            "type": "error",
            "error": "工具调用失败"
        }
        
    def _parse_mcp_result(self, result: Dict[str, Any], plan: Optional[Dict[str, Any]] = None, prefix: Optional[str] = None) -> Dict[str, Any]:
        """解析MCP server返回的结果
        
        Args:
            result: MCP server返回的结果字典
            plan: 任务计划（可选）
            prefix: 结果前缀（可选），用于多步骤任务
            
        Returns:
            包含summary和plan的字典
        """
        result_text = result.get("result", "")
        if isinstance(result_text, str):
            try:
                execution_result = json.loads(result_text)
                output = execution_result.get("output", "")
                error = execution_result.get("error", "")
                if output:
                    summary = f"{prefix}: {output}" if prefix else output
                    return {"summary": summary, "plan": plan if plan else {}}
                elif error:
                    summary = f"{prefix} 错误: {error}" if prefix else f"执行错误: {error}"
                    return {"summary": summary, "plan": plan if plan else {}}
                else:
                    summary = f"{prefix}: 执行成功！" if prefix else "执行成功！"
                    return {"summary": summary, "plan": plan if plan else {}}
            except json.JSONDecodeError:
                summary = f"{prefix}: {result_text}" if prefix else result_text
                return {"summary": summary, "plan": plan if plan else {}}
        elif isinstance(result_text, dict):
            output = result_text.get("output", "")
            error = result_text.get("error", "")
            if output:
                summary = f"{prefix}: {output}" if prefix else output
                return {"summary": summary, "plan": plan if plan else {}}
            elif error:
                summary = f"{prefix} 错误: {error}" if prefix else f"执行错误: {error}"
                return {"summary": summary, "plan": plan if plan else {}}
            else:
                summary = f"{prefix}: 执行成功！" if prefix else "执行成功！"
                return {"summary": summary, "plan": plan if plan else {}}
        else:
            summary = f"{prefix}: {str(result)}" if prefix else str(result)
            return {"summary": summary, "plan": plan if plan else {}}

    async def process_user_query(self, query: str) -> Dict[str, Any]:
        """处理用户查询"""
        try:
            # 解析用户意图并更新UI
            if self.ui_callback:
                self.ui_callback("task_update", {"description": f"解析用户意图: {query}"})
            
            intent = await self.intent_parser.parse(query)
            
            if self.ui_callback:
                self.ui_callback("task_update", {"description": f"识别意图: {intent['type']}", "tool": intent.get("tool", "")})
            
            self.logger.info(f"解析到的意图: {intent}")
            
            # 根据意图执行相应的操作
            if intent["type"] == "tool_call":
                # 直接调用工具
                if self.ui_callback:
                    self.ui_callback("task_update", {"description": f"执行工具: {intent['tool']}"})
                
                result = await self.send_tool_call(intent["tool"], intent.get("args", {}))
                
                if self.ui_callback:
                    self.ui_callback("task_update", {"description": f"工具执行完成: {intent['tool']}", "result": result})
                
                return {
                    "type": "response",
                    "content": result
                }
            elif intent["type"] == "task":
                # 任务规划
                if self.ui_callback:
                    self.ui_callback("task_update", {"description": "生成任务计划"})
                
                plan = await self.task_planner.plan(query)
                
                if self.ui_callback:
                    self.ui_callback("task_update", {"description": f"任务计划生成完成，共{len(plan['steps'])}个步骤", "plan": plan})
                
                self.logger.info(f"生成的任务计划: {plan}")
                
                # 执行任务计划
                results = []
                for i, step in enumerate(plan["steps"]):
                    if self.ui_callback:
                        self.ui_callback("task_update", {"description": f"执行任务步骤 {i+1}/{len(plan['steps'])}: {step['tool']}"})
                    
                    result = await self.send_tool_call(step["tool"], step.get("args", {}))
                    results.append(result)
                    
                    if self.ui_callback:
                        self.ui_callback("task_update", {"description": f"任务步骤 {i+1} 完成", "result": result})
                
                return {
                    "type": "response",
                    "content": {
                        "plan": plan,
                        "results": results
                    }
                }
            else:
                # 直接使用LLM回答
                if self.ui_callback:
                    self.ui_callback("task_update", {"description": "使用LLM生成回答"})
                
                response = self.llm_client.generate(query)
                
                if self.ui_callback:
                    self.ui_callback("task_update", {"description": "LLM回答生成完成"})
                
                return {
                    "type": "response",
                    "content": response
                }
                
        except Exception as e:
            self.logger.error(f"处理用户查询时出错: {e}")
            if self.ui_callback:
                self.ui_callback("task_update", {"description": f"处理出错: {str(e)}"})
            return {
                "type": "error",
                "error": str(e)
            }
    
    async def process_user_intent(self, query: str) -> Dict[str, Any]:
        """处理用户意图（UI调用接口）
        
        工作流程：
        1. 用户输入自然语言
        2. MCP client 通过 LLM 解析用户意图
        3. 根据用户意图生成 Python 能够执行的任务
        4. 复杂的任务由 LLM 拆解
        5. 将拆解的任务按 MCP 协议发送给 MCP server 执行
        6. 将执行结果按 MCP 协议返回给 MCP client
        7. 显示在输出 UI 上
        """
        try:
            # 1. 使用 LLM 解析用户意图
            if self.ui_callback:
                self.ui_callback("task_update", {"description": f"解析用户意图: {query}"})
            
            intent = await self.intent_parser.parse(query)
            
            if self.ui_callback:
                self.ui_callback("task_update", {"description": f"识别意图: {intent['type']}", "tool": intent.get("tool", "")})
            
            self.logger.info(f"解析到的意图: {intent}")
            
            # 2. 根据用户意图生成 Python 代码
            if intent["type"] == "tool_call":
                # 直接调用工具，将用户输入作为 Python 代码
                code = intent.get("args", {}).get("code", query)
                
                # 如果代码不是有效的 Python 语法，使用 LLM 生成对应的 Python 代码
                if not self._is_valid_python(code):
                    if self.ui_callback:
                        self.ui_callback("task_update", {"description": "代码不是有效的 Python 语法，使用 LLM 生成对应的 Python 代码"})
                         # 添加UI回调，显示LLM生成代码的开始
                        self.ui_callback("task_update", {"description": f"开始生成Python代码，任务描述: {query[:50]}..."})
                        self.ui_callback("task_update", {"description": "开始调用LLM生成代码"})

                    self.logger.info(f"代码不是有效的 Python 语法，使用 LLM 生成对应的 Python 代码")
                
                    code = await self.llm_client.generate_python_code(query)
                    
                    if self.ui_callback:
                        self.ui_callback("task_update", {"description": "Python 代码生成完成", "code": code})
                else:
                    if self.ui_callback:
                        self.ui_callback("task_update", {"description": "使用用户提供的 Python 代码", "code": code})
                
                # 3. 将 Python 代码按 MCP 协议发送给 MCP server 执行
                result = await self.send_tool_call("execute_python", {"code": code})
                self.logger.info(f"send_tool_call 返回结果: {result}")
                
                # 发送代码执行结果到UI（只显示代码的print输出）
                if self.ui_callback:
                    self.ui_callback("task_update", {"result": result})
                
                # 4. 解析并返回执行结果
                return self._parse_mcp_result(result)
            elif intent["type"] == "task":
                # 复杂的任务由 LLM 拆解
                if self.ui_callback:
                    self.ui_callback("task_update", {"description": "复杂任务，使用 LLM 拆解"})
                
                self.logger.info(f"复杂任务，使用 LLM 拆解")
                
                # 使用 LLM 生成任务计划
                if self.ui_callback:
                    self.ui_callback("task_update", {"description": "生成任务计划"})
                
                plan = await self.task_planner.plan(query)
                
                if self.ui_callback:
                    self.ui_callback("task_update", {"description": f"任务计划生成完成，共{len(plan.get('steps', []))}个步骤", "plan": plan})
                
                self.logger.info(f"生成的任务计划: {plan}")
                
                # 执行任务计划中的每个步骤
                results = []
                for i, step in enumerate(plan.get("steps", [])):
                    if self.ui_callback:
                        self.ui_callback("task_update", {"description": f"执行任务步骤 {i+1}/{len(plan.get('steps', []))}: {step['tool']}"})
                    
                    # 将每个步骤按 MCP 协议发送给 MCP server 执行
                    result = await self.send_tool_call(step["tool"], step.get("args", {}))
                    results.append(result)
                    
                    if self.ui_callback:
                        self.ui_callback("task_update", {"description": f"任务步骤 {i+1} 完成", "result": result})
                
                # 提取所有步骤的执行结果
                execution_results = []
                for i, result in enumerate(results):
                    parsed = self._parse_mcp_result(result, prefix=f"步骤 {i+1}")
                    execution_results.append(parsed["summary"])
                
                # 将执行结果按 MCP 协议返回给 MCP client
                return {
                    "summary": "\n".join(execution_results),
                    "plan": plan
                }
            else:
                # 对于其他意图，使用 LLM 生成 Python 代码执行
                if self.ui_callback:
                    self.ui_callback("task_update", {"description": "其他意图，使用 LLM 生成 Python 代码"})
                
                self.logger.info(f"其他意图，使用 LLM 生成 Python 代码")
                code = await self.llm_client.generate_python_code(query)
                
                if self.ui_callback:
                    self.ui_callback("task_update", {"description": "Python 代码生成完成", "code": code})
                
                # 将 Python 代码按 MCP 协议发送给 MCP server 执行
                result = await self.send_tool_call("execute_python", {"code": code})
                
                # 发送代码执行结果到UI（只显示代码的print输出）
                if self.ui_callback:
                    self.ui_callback("task_update", {"result": result})
                
                # 解析并返回执行结果
                return self._parse_mcp_result(result)
        
        except Exception as e:
            self.logger.error(f"处理用户意图时出错: {e}")
            import traceback
            traceback.print_exc()
            
            if self.ui_callback:
                self.ui_callback("task_update", {"description": f"处理出错: {str(e)}"})
            
            return {
                "summary": f"处理失败: {str(e)}",
                "plan": {}
            }
        
        # 确保所有情况下都返回一个字典
        return {
            "summary": "处理完成",
            "plan": {}
        }
    
    def _is_valid_python(self, code: str) -> bool:
        """检查代码是否是有效的 Python 语法"""
        try:
            # 尝试直接编译代码
            compile(code, '<string>', 'exec')
            return True
        except SyntaxError as e:
            # 如果编译失败，尝试清理代码中的无关文本
            cleaned_code = self._clean_code(code)
            try:
                compile(cleaned_code, '<string>', 'exec')
                return True
            except SyntaxError:
                return False
    
    def _clean_code(self, code: str) -> str:
        """清理代码中的无关文本"""
        # 移除常见的无关文本模式
        lines = code.split('\n')
        cleaned_lines = []
        
        # 检测代码结束位置
        code_ended = False
        
        for line in lines:
            # 跳过看起来像提示词或无关文本的行
            stripped = line.strip()
            
            # 检测代码是否已经结束（遇到if __name__ == "__main__":块的结束）
            if 'if __name__ == "__main__":' in line or 'if __name__ == "__main__":' in line:
                code_ended = False
            
            # 如果代码已经结束，检查是否还有代码内容
            if code_ended:
                # 跳过所有非代码行
                if not stripped or stripped.startswith('#'):
                    continue
                # 检查是否是新的代码开始（不太可能）
                if any(keyword in stripped for keyword in ['def ', 'class ', 'import ', 'from ']):
                    code_ended = False
                else:
                    continue
            
            # 检测代码结束（空行或注释行，且之前有代码）
            if not code_ended and (not stripped or stripped.startswith('#')):
                # 检查前面是否有代码内容
                if cleaned_lines and any(c.strip() for c in cleaned_lines[-5:]):
                    # 可能是代码结束，但还不能确定
                    pass
            
            # 跳过空行（保留代码中的空行，但跳过连续的空行）
            if not stripped:
                if cleaned_lines and cleaned_lines[-1].strip():
                    cleaned_lines.append(line)
                continue
            
            # 跳过包含"你是一个"的行（可能是提示词）
            if '你是一个' in stripped:
                code_ended = True
                continue
            
            # 跳过包含"用户输入"的行
            if '用户输入' in stripped:
                code_ended = True
                continue
            
            # 跳过包含"规则"和"请"的行（可能是提示词）
            if '规则' in stripped and '请' in stripped:
                code_ended = True
                continue
            
            # 跳过包含"内容违规"的行
            if '内容违规' in stripped:
                code_ended = True
                continue
            
            # 跳过包含"请按规则回答"的行
            if '请按规则回答' in stripped:
                code_ended = True
                continue
            
            # 跳过包含"首先，用户输入是"的行
            if '首先，用户输入是' in stripped:
                code_ended = True
                continue
            
            # 跳过包含"现在，分析用户输入"的行
            if '现在，分析用户输入' in stripped:
                code_ended = True
                continue
            
            # 跳过包含"可能的响应"的行
            if '可能的响应' in stripped:
                code_ended = True
                continue
            
            # 跳过包含"例如："的行（可能是示例）
            if '例如：' in stripped and len(stripped) < 50:
                code_ended = True
                continue
            
            # 跳过包含"计算字数"的行
            if '计算字数' in stripped:
                code_ended = True
                continue
            
            # 跳过包含"确保"和"字数"的行
            if '确保' in stripped and '字数' in stripped:
                code_ended = True
                continue
            
            # 跳过包含"最终响应"的行
            if '最终响应' in stripped:
                code_ended = True
                continue
            
            # 跳过包含"现在，写响应"的行
            if '现在，写响应' in stripped:
                code_ended = True
                continue
            
            # 跳过包含"字数："的行
            if '字数：' in stripped:
                code_ended = True
                continue
            
            # 跳过以数字开头的行（可能是编号的规则）
            if stripped and stripped[0].isdigit() and '如果' in stripped and '，' in stripped:
                code_ended = True
                continue
            
            # 跳过包含"AI相关"的行
            if 'AI相关' in stripped:
                code_ended = True
                continue
            
            # 跳过包含"简洁、专业的解释"的行
            if '简洁、专业的解释' in stripped:
                code_ended = True
                continue
            
            # 跳过包含"错误或不完整的信息"的行
            if '错误或不完整的信息' in stripped:
                code_ended = True
                continue
            
            # 跳过包含"敏感词"的行
            if '敏感词' in stripped:
                code_ended = True
                continue
            
            # 跳过包含"不超过100字"的行
            if '不超过100字' in stripped:
                code_ended = True
                continue
            
            # 跳过包含"用中文回答"的行
            if '用中文回答' in stripped:
                code_ended = True
                continue
            
            # 跳过包含"请确保"的行
            if '请确保' in stripped:
                code_ended = True
                continue
            
            # 跳过包含"检查是否有错误"的行
            if '检查是否有错误' in stripped:
                code_ended = True
                continue
            
            # 跳过包含"规则中"的行
            if '规则中' in stripped:
                code_ended = True
                continue
            
            # 跳过包含"指令中"的行
            if '指令中' in stripped:
                code_ended = True
                continue
            
            # 跳过包含"描述了规则"的行
            if '描述了规则' in stripped:
                code_ended = True
                continue
            
            # 跳过包含"没有明显错误"的行
            if '没有明显错误' in stripped:
                code_ended = True
                continue
            
            # 跳过包含"所以，根据规则"的行
            if '所以，根据规则' in stripped:
                code_ended = True
                continue
            
            # 跳过包含"我应该"的行
            if '我应该' in stripped:
                code_ended = True
                continue
            
            # 跳过包含"指令说"的行
            if '指令说' in stripped:
                code_ended = True
                continue
            
            # 跳过包含"所以不能"的行
            if '所以不能' in stripped:
                code_ended = True
                continue
            
            # 跳过包含"添加额外内容"的行
            if '添加额外内容' in stripped:
                code_ended = True
                continue
            
            # 跳过包含"可能的响应"的行
            if '可能的响应' in stripped:
                code_ended = True
                continue
            
            # 跳过包含"例如"的行（可能是示例）
            if '例如' in stripped and len(stripped) < 50:
                code_ended = True
                continue
            
            cleaned_lines.append(line)
        
        # 重新组合代码
        cleaned_code = '\n'.join(cleaned_lines)
        
        # 移除末尾的空行
        cleaned_code = cleaned_code.rstrip()
        
        return cleaned_code
