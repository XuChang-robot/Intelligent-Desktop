# MCP Client 主文件 - 使用官方ClientSession

import asyncio
import logging
import json
import sqlite3
import hashlib
from typing import Dict, Any, Optional, Callable
from contextlib import AsyncExitStack
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import ElicitRequestParams, ElicitResult
from mcp_client.llm import LLMClient
from mcp_client.intent_parser import IntentParser
from mcp_client.hybrid_cache import HybridTaskPlanCache
from mcp_client.elicitation import ElicitationManager
from mcp_client.behavior_tree import BehaviorTree
from user_config.config import load_config

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
        self.tools = None  # 保存工具列表
    
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
            self.tools = tools.tools  # 保存工具列表
            logging.info(f"可用工具: {[t.name for t in self.tools]}")
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
        logging.info(f"[SessionManager.call_tool] 开始调用工具: {tool_name}")
        
        if not self.connected:
            logging.info(f"[SessionManager.call_tool] 未连接，正在连接...")
            await self.connect()
        
        if not self.session:
            logging.error(f"[SessionManager.call_tool] 会话未初始化")
            raise RuntimeError("会话未初始化")
        
        logging.info(f"调用工具: {tool_name}")
        logging.info(f"参数: {params}")
        
        try:
            # 使用 asyncio.wait_for 添加超时
            import asyncio
            logging.info(f"[SessionManager.call_tool] 开始调用 session.call_tool")
            logging.info(f"[SessionManager.call_tool] session 对象: {self.session}")
            logging.info(f"[SessionManager.call_tool] session 类型: {type(self.session)}")
            
            result = await asyncio.wait_for(
                self.session.call_tool(tool_name, params),
                timeout=30.0  # 30秒超时
            )
            logging.info(f"工具调用成功，结果: {result}")
            return result
        except asyncio.TimeoutError:
            logging.error(f"工具调用超时: {tool_name}")
            raise TimeoutError(f"Tool call timeout: {tool_name}")
        except Exception as e:
            logging.error(f"工具调用失败: {e}")
            import traceback
            logging.error(f"错误详情:\n{traceback.format_exc()}")
            raise

async def get_session_manager(server_url=None):
    """获取全局的会话管理器实例"""
    global _global_session_manager
    if _global_session_manager is None:
        # 如果没有指定server_url，从配置文件读取
        if server_url is None:
            config = load_config()
            host = config["mcp"]["server"]["host"]
            port = config["mcp"]["server"]["port"]
            server_url = f"http://{host}:{port}/mcp"
        _global_session_manager = SessionManager(server_url)
    return _global_session_manager

async def initialize_global_session(server_url=None):
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
        
        # 初始化行为树系统
        self.behavior_tree = BehaviorTree()
        
        # 从config中读取缓存配置
        cache_config = self.config.get('cache', {})
        self.enable_hash_match = cache_config.get('enable_hash_match', True)
        self.enable_faiss_match = cache_config.get('enable_faiss_match', True)

        if cache_config.get('enabled', True):
            self.cache = HybridTaskPlanCache(
                cache_dir=cache_config.get('cache_dir', 'cache'),
                ttl=cache_config.get('ttl', 604800),
                similarity_threshold=cache_config.get('similarity_threshold', 0.85),
                max_total_size_mb=cache_config.get('max_total_size_mb', 1024),
                max_db_size_mb=cache_config.get('max_db_size_mb', 512),
                max_faiss_size_mb=cache_config.get('max_faiss_size_mb', 512),
                max_records=cache_config.get('max_records', 10000),
                cleanup_interval=cache_config.get('cleanup_interval', 3600),
                cleanup_on_startup=cache_config.get('cleanup_on_startup', True),
                embedding_model=cache_config.get('embedding_model', 'nomic-embed-text'),
                llm_client=self.llm_client,
                enable_hash_match=self.enable_hash_match,
                enable_faiss_match=self.enable_faiss_match
            )
        else:
            self.cache = None
        self.elicitation_manager = ElicitationManager(self.llm_client)
        self.session_manager: Optional[SessionManager] = None
        self.logger = logging.getLogger(__name__)
        self.elicitation_callback = None
        self.ui_callback = None
        self.tools = None  # 保存工具列表
        self.interrupted = False  # 中断标志
    
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
            # 获取工具列表
            self.tools = self.session_manager.tools
            self.logger.info(f"成功连接到MCP Server，获取到{len(self.tools) if self.tools else 0}个工具")
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
    
    def interrupt(self):
        """中断执行"""
        self.logger.info("收到中断请求")
        self.interrupted = True
        if self.ui_callback:
            self.ui_callback("task_update", {"description": "任务已被用户中断"})

    async def send_tool_call(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """发送工具调用请求"""
        self.logger.info(f"[send_tool_call] 开始执行工具: {tool_name}")
        
        if not self.session_manager:
            self.logger.info("[send_tool_call] 连接 session_manager")
            await self.connect()
        
        try:
            # 使用官方MCP Client API调用工具
            self.logger.info(f"[send_tool_call] 调用 session_manager.call_tool")
            result = await self.session_manager.call_tool(tool_name, tool_args)
            self.logger.info(f"[send_tool_call] call_tool 返回: {result}")
            
            # 解析结果
            if hasattr(result, 'content'):
                self.logger.info(f"[send_tool_call] 解析结果 content")
                # 处理官方MCP返回的结果格式
                content = result.content
                if content and len(content) > 0:
                    # 获取第一个内容项
                    first_item = content[0]
                    if hasattr(first_item, 'text'):
                        # 尝试解析JSON格式的返回值
                        text = first_item.text
                        try:
                            import json
                            parsed = json.loads(text)
                            if isinstance(parsed, dict):
                                # 如果是字典，直接返回
                                self.logger.info(f"[send_tool_call] 返回 JSON 结果")
                                return {
                                    "type": "tool_response",
                                    "result": parsed
                                }
                        except (json.JSONDecodeError, ValueError):
                            # 如果不是JSON，直接返回文本
                            pass
                        self.logger.info(f"[send_tool_call] 返回文本结果")
                        return {
                            "type": "tool_response",
                            "result": text
                        }
                    elif hasattr(first_item, 'data'):
                        self.logger.info(f"[send_tool_call] 返回数据结果")
                        return {
                            "type": "tool_response",
                            "result": first_item.data
                        }
            
            # 如果无法解析，返回原始结果
            self.logger.info(f"[send_tool_call] 返回原始结果")
            return {
                "type": "tool_response",
                "result": str(result)
            }
                
        except Exception as e:
            self.logger.error(f"工具调用失败: {e}")
            raise
    
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
        
        # 处理有formatted_message的结果（如天气查询）
        if isinstance(result, dict):
            # 检查result.result中的formatted_message
            if result.get("type") == "tool_response":
                tool_result = result.get("result", {})
                if isinstance(tool_result, dict):
                    formatted_message = tool_result.get("formatted_message")
                    if formatted_message:
                        summary = f"{prefix}: {formatted_message}" if prefix else formatted_message
                        return {"summary": summary, "plan": plan if plan else {}}
            # 也检查直接在result中的formatted_message
            formatted_message = result.get("formatted_message")
            if formatted_message:
                summary = f"{prefix}: {formatted_message}" if prefix else formatted_message
                return {"summary": summary, "plan": plan if plan else {}}
        
        # 处理file_operations等工具的返回格式：{"success": True, "result": "...", "path": "..."}
        if isinstance(result_text, dict):
            success = result_text.get("success", False)
            tool_result = result_text.get("result", "")
            error = result_text.get("error", "")
            path = result_text.get("path", "")
            
            # 检查是否是文件夹已存在的情况
            is_folder_exists = "文件夹已存在" in tool_result or "文件夹已存在" in error
            
            if success or is_folder_exists:
                if is_folder_exists:
                    # 文件夹已存在视为成功
                    summary = f"{prefix}: 文件夹已存在" if prefix else "文件夹已存在"
                else:
                    summary = f"{prefix}: {tool_result}" if prefix else tool_result
                if path:
                    summary += f" (路径: {path})"
                return {"summary": summary, "plan": plan if plan else {}}
            else:
                summary = f"{prefix} 错误: {error}" if prefix else f"执行错误: {error}"
                return {"summary": summary, "plan": plan if plan else {}}
        
        else:
            summary = f"{prefix}: {str(result)}" if prefix else str(result)
            return {"summary": summary, "plan": plan if plan else {}}
    
    async def process_user_intent(self, query: str, stream_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """处理用户意图（UI调用接口）
        
        工作流程：
        1. 用户输入自然语言
        2. 优先进行缓存查询（精确匹配 + 语义匹配）
        3. 如果缓存命中，直接使用缓存的tree_config执行行为树
        4. 如果缓存未命中，调用LLM解析意图并生成tree_config
        5. 执行行为树
        6. 显示在输出 UI 上
        """
        try:
            # 重置中断标志
            self.interrupted = False
            
            # 第一步：缓存查询（精确匹配 + 语义匹配）
            if self.cache is not None:
                if self.ui_callback:
                    self.ui_callback("task_update", {"description": f"检查缓存: {query}"})
                
                # 查询缓存
                cache_result = self.cache.get(query, self.tools)
                
                if cache_result and cache_result.get("from_cache"):
                    tree_config = cache_result.get("tree_config")
                    match_type = cache_result.get("match_type")
                    similarity = cache_result.get("similarity")
                    
                    self.logger.info(f"缓存命中（{match_type}），直接使用缓存的tree_config")
                    
                    if self.ui_callback:
                        if match_type == "exact":
                            self.ui_callback("task_update", {"description": "✅ 缓存精确命中"})
                        else:
                            self.ui_callback("task_update", {"description": f"✅ 缓存语义命中（相似度: {similarity:.2f}）"})
                    
                    # 执行行为树
                    try:
                        if self.ui_callback:
                            self.ui_callback("task_update", {"description": "行为树配置生成完成"})
                            self.ui_callback("loading", True, "行为树配置生成完成...")
                            self.ui_callback("progress", True, 30)
                        
                        # 定义工具执行回调（异步）
                        async def async_tool_executor(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
                            """执行MCP工具的回调函数"""
                            self.logger.info(f"执行工具: {tool_name}, 参数: {parameters}")
                            result = await self.send_tool_call(tool_name, parameters)
                            return result
                        
                        # 设置工具执行回调
                        self.behavior_tree.set_tool_executor(async_tool_executor)
                        
                        # 从tree_config构建行为树
                        self.behavior_tree.build_from_config(tree_config)
                        
                        # 执行行为树
                        execution_result = await self.behavior_tree.execute()
                        
                        if self.ui_callback:
                            self.ui_callback("loading", True, "任务执行完成...")
                            self.ui_callback("progress", True, 100)
                            self.ui_callback("task_update", {"description": "🎉 任务执行完成！", "status": "完成"})
                        
                        # 格式化执行结果
                        summary = self._format_tree_execution_result(execution_result)
                        
                        return {
                            "summary": summary,
                            "tree_config": tree_config,
                            "execution_result": execution_result,
                            "from_cache": True,
                            "match_type": match_type,
                            "similarity": similarity
                        }
                    except Exception as e:
                        self.logger.error(f"行为树执行失败: {e}")
                        import traceback
                        traceback.print_exc()
                        return {
                            "summary": f"任务执行失败: {str(e)}",
                            "tree_config": tree_config,
                            "error": str(e)
                        }
                else:
                    self.logger.info("缓存未命中，继续LLM解析")
            else:
                self.logger.info("缓存已禁用")
            
            # 第二步：使用 LLM 解析用户意图   
            # 检查是否中断
            if self.interrupted:
                return {"summary": "任务已被用户中断", "plan": {}}
            
            intent = await self.intent_parser.parse(query, self.tools)
            
            self.logger.debug(f"解析到的意图: {intent}")
            
            # 根据用户意图执行相应的操作
            if intent["type"] == "chat":
                # 聊天型意图，直接使用LLM回答       
                # 流式生成回答
                def llm_stream_callback(chunk):
                    """LLM流式回调（同步函数）"""
                    if stream_callback:
                        stream_callback({
                            "type": "stream",
                            "response": chunk.get("response", ""),
                            "thinking": chunk.get("thinking", ""),
                            "done": chunk.get("done", False)
                        })
                
                response_dict = await self.llm_client.generate(query, stream_callback=llm_stream_callback)
                response = response_dict.get("response", "")
                thinking = response_dict.get("thinking", "")
                
                return {
                    "summary": response,
                    "thinking": thinking,
                    "plan": {}
                }
            elif intent["type"] == "task":        
                # 使用行为树系统执行任务
                
                # 检查intent中是否包含行为树配置
                if "tree_config" not in intent:
                    self.ui_callback("task_update", True, "行为树配置生成失败！")
                    self.logger.error("行为树配置生成失败！")
                    return
                
                tree_config = intent["tree_config"]
                self.logger.info(f"使用行为树配置: {tree_config}")
                
                if self.ui_callback:
                    self.ui_callback("task_update", {"description": f"行为树配置生成完成"})
                    self.ui_callback("loading", True, "行为树配置生成完成...")
                    self.ui_callback("progress", True, 30)
                
                # 定义工具执行回调（异步）
                async def async_tool_executor(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
                    """执行MCP工具的回调函数"""
                    self.logger.info(f"执行工具: {tool_name}, 参数: {parameters}")
                    result = await self.send_tool_call(tool_name, parameters)
                    return result
                
                # 设置工具执行回调（直接传递异步函数）
                self.behavior_tree.set_tool_executor(async_tool_executor)
                
                # 执行行为树
                try:
                    # 从行为树配置构建树
                    self.behavior_tree.build_from_config(tree_config)
                    
                    # 执行行为树（同步方式）
                    execution_result = await self.behavior_tree.execute()
                    
                    if self.ui_callback:
                        self.ui_callback("loading", True, "任务执行完成...")
                        self.ui_callback("progress", True, 100)
                        self.ui_callback("task_update", {"description": "🎉 任务执行完成！", "status": "完成"})
                    
                    # 检查行为树执行是否成功
                    if execution_result.get("success", False):
                        # 只有在行为树执行成功后才缓存tree_config
                        if self.cache is not None:
                            self.logger.info(f"行为树执行成功，缓存tree_config: {query}")
                            self.cache.set(query, tree_config, self.tools)
                    else:
                        self.logger.warning(f"行为树执行失败，不缓存tree_config: {query}")
                    
                    # 格式化执行结果
                    summary = self._format_tree_execution_result(execution_result)
                    
                    return {
                        "summary": summary,
                        "tree_config": tree_config,
                        "execution_result": execution_result
                    }
                except Exception as e:
                    self.logger.error(f"行为树执行失败: {e}")
                    import traceback
                    traceback.print_exc()
                    return {
                        "summary": f"任务执行失败: {str(e)}",
                        "tree_config": tree_config,
                        "error": str(e)
                    }
            elif intent["type"] == "cannot_execute":
                return {
                    "summary": intent.get("reason", ""),
                    "plan": {}
                }
            elif intent["type"] == "error":
                # 错误类型，返回错误信息
                error_msg = intent.get("error", "处理失败")
                self.logger.error(f"意图解析错误: {error_msg}")
                
                if self.ui_callback:
                    self.ui_callback("loading", False)
                    self.ui_callback("task_update", {"description": f"❌ {error_msg}"})
                
                return {
                    "summary": f"❌ {error_msg}",
                    "plan": {}
                }
        
        except Exception as e:
            self.logger.error(f"处理用户意图时出错: {e}")
            import traceback
            traceback.print_exc()
            
            if self.ui_callback:
                self.ui_callback("loading", False)
                self.ui_callback("task_update", {"description": f"❌ 处理出错: {str(e)}"})
            
            return {
                "summary": f"❌ 处理失败: {str(e)}",
                "plan": {}
            }
        
        # 确保所有情况下都返回一个字典
        return {
            "summary": "处理完成",
            "plan": {}
        }

    def _format_tree_execution_result(self, execution_result: Dict[str, Any]) -> str:
        """格式化行为树执行结果
        
        Args:
            execution_result: 行为树执行结果
        
        Returns:
            格式化后的结果字符串
        """
        if not execution_result:
            return "行为树执行完成，无结果"
        
        success = execution_result.get("success", False)
        blackboard = execution_result.get("blackboard", {})
        
        # 如果执行失败，返回错误信息
        if not success:
            error = execution_result.get("error", "未知错误")
            return f"❌ 任务执行失败: {error}"
        
        # 收集所有工具的 formatted_message
        formatted_messages = []
        
        for key, value in blackboard.items():
            if key != "entities" and isinstance(value, dict):
                # 检查是否有 formatted_message
                if "formatted_message" in value:
                    formatted_messages.append(value["formatted_message"])
                # 如果没有 formatted_message，但有 result 字段
                elif "result" in value:
                    result = value["result"]
                    # 如果 result 是字典，检查其中是否有 formatted_message
                    if isinstance(result, dict) and "formatted_message" in result:
                        formatted_messages.append(result["formatted_message"])
                    # 否则使用 result 字符串
                    elif isinstance(result, str):
                        formatted_messages.append(result)
        
        # 如果没有找到 formatted_message，返回默认消息
        if not formatted_messages:
            return "✅ 任务执行完成"
        
        # 将所有 formatted_message 用换行符连接
        return "\n\n".join(formatted_messages)
    
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
