# MCP Client 主文件 - 使用官方ClientSession

import asyncio
import logging
import json
import sqlite3
import hashlib
import os
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
from mcp_client.behavior_tree.tree_repair import BehaviorTreeRepair
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
            logging.info(f"[SessionManager.call_tool] 未连接，正在连接...")
            await self.connect()
        
        if not self.session:
            logging.error(f"[SessionManager.call_tool] 会话未初始化")
            raise RuntimeError("会话未初始化")
        
        try:
            # 使用 asyncio.wait_for 添加超时
            import asyncio
            
            result = await asyncio.wait_for(
                self.session.call_tool(tool_name, params),
                timeout=120.0  # 120秒超时
            )

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
        
        # 获取日志目录配置
        log_config = self.config.get('logging', {})
        self.log_dir = log_config.get('log_dir', 'logs')
        # 确保日志目录存在
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 获取开发模式配置
        self.dev_mode = log_config.get('dev_mode', False)
        
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
        
        # 初始化行为树自动修复模块
        bt_config = self.config.get('behavior_tree', {}).get('auto_repair', {})
        self.auto_repair_enabled = bt_config.get('enabled', True)
        self.max_repair_attempts = bt_config.get('max_repair_attempts', 3)
        
        if self.auto_repair_enabled:
            self.behavior_tree_repair = BehaviorTreeRepair(
                llm=self.llm_client,
                max_repair_attempts=self.max_repair_attempts
            )
            self.logger.info(f"行为树自动修复模块初始化完成，最大尝试次数: {self.max_repair_attempts}")
        else:
            self.behavior_tree_repair = None
            self.logger.info("行为树自动修复模块已禁用")
        
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
            
            # 更新行为树修复模块的工具信息
            if self.auto_repair_enabled and self.behavior_tree_repair:
                self.behavior_tree_repair.tools = self.tools
                self.logger.info("行为树修复模块工具信息更新完成")
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
        
        if not self.session_manager:
            self.logger.info("[send_tool_call] 连接 session_manager")
            await self.connect()
        
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
                        # 尝试解析JSON格式的返回值
                        text = first_item.text
                        try:
                            import json
                            parsed = json.loads(text)
                            if isinstance(parsed, dict):
                                # 如果是字典，直接返回
                                self.logger.debug(f"[send_tool_call] 返回 JSON 结果")
                                return {
                                    "type": "tool_response",
                                    "result": parsed
                                }
                        except (json.JSONDecodeError, ValueError):
                            # 如果不是JSON，直接返回文本
                            pass
                        self.logger.debug(f"[send_tool_call] 返回文本结果")
                        return {
                            "type": "tool_response",
                            "result": text
                        }
                    elif hasattr(first_item, 'data'):
                        self.logger.debug(f"[send_tool_call] 返回数据结果")
                        return {
                            "type": "tool_response",
                            "result": first_item.data
                        }
            
            # 如果无法解析，返回原始结果
            self.logger.debug(f"[send_tool_call] 返回原始结果")
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
                    
                    # 自动保存行为树配置到日志目录
                    self._save_tree_config(tree_config, query)
                    
                    if self.ui_callback:
                        if match_type == "exact":
                            self.ui_callback("task_update", {"description": "✅ 缓存精确命中"})
                        else:
                            self.ui_callback("task_update", {"description": f"✅ 缓存语义命中（相似度: {similarity:.2f}）"})
                    
                    # 执行行为树
                    try:
                        if self.ui_callback:
                            self.ui_callback("loading", True, "行为树配置生成完成...")
                            self.ui_callback("progress", True, 30)
                        
                        # 定义工具执行回调（异步）
                        async def async_tool_executor(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
                            """执行MCP工具的回调函数"""
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
                self.logger.debug(f"使用行为树配置: {tree_config}")
                
                # 自动保存行为树配置到日志目录
                self._save_tree_config(tree_config, query)
                
                if self.ui_callback:
                    self.ui_callback("task_update", {"description": f"行为树配置生成完成"})
                    self.ui_callback("loading", True, "行为树配置生成完成...")
                    self.ui_callback("progress", True, 30)
                
                # 定义工具执行回调（异步）
                async def async_tool_executor(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
                    """执行MCP工具的回调函数"""
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
                        
                        # 格式化执行结果
                        summary = self._format_tree_execution_result(execution_result)
                        
                        return {
                            "summary": summary,
                            "tree_config": tree_config,
                            "execution_result": execution_result
                        }
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
                    
                    # 捕获到异常，尝试自动修复
                    if self.auto_repair_enabled and self.behavior_tree_repair:
                        self.logger.info(f"捕获到异常，尝试自动修复...")
                        
                        # 重置修复计数
                        self.behavior_tree_repair.reset_repair_count()
                        
                        # 循环尝试修复，最多尝试3次
                        for attempt in range(self.max_repair_attempts):
                            self.logger.info(f"自动修复尝试 {attempt + 1}/{self.max_repair_attempts}...")
                            
                            # 尝试修复
                            repaired_config = await self.behavior_tree_repair.repair_behavior_tree(
                                tree_config, 
                                str(e)
                            )
                            
                            if repaired_config:
                                self.logger.info("行为树修复成功，尝试重新执行...")
                                
                                # 重新执行修复后的行为树
                                try:
                                    if self.ui_callback:
                                        self.ui_callback("task_update", {"description": f"行为树修复成功，重新执行... (尝试 {attempt + 1}/{self.max_repair_attempts})"})
                                        self.ui_callback("loading", True, "行为树修复成功，重新执行...")
                                        self.ui_callback("progress", True, 40)
                                    
                                    # 从修复后的配置构建树
                                    self.behavior_tree.build_from_config(repaired_config)
                                    
                                    # 执行行为树
                                    execution_result = await self.behavior_tree.execute()
                                    
                                    if self.ui_callback:
                                        self.ui_callback("loading", True, "修复后任务执行完成...")
                                        self.ui_callback("progress", True, 100)
                                        self.ui_callback("task_update", {"description": "🎉 修复后任务执行完成！", "status": "完成"})
                                    
                                    # 检查行为树执行是否成功
                                    if execution_result.get("success", False):
                                        # 只有在行为树执行成功后才缓存修复后的tree_config
                                        if self.cache is not None:
                                            self.logger.info(f"修复后行为树执行成功，缓存修复后的tree_config: {query}")
                                            self.cache.set(query, repaired_config, self.tools)
                                        
                                        # 格式化执行结果
                                        summary = self._format_tree_execution_result(execution_result)
                                        
                                        return {
                                            "summary": summary,
                                            "tree_config": repaired_config,
                                            "execution_result": execution_result,
                                            "repaired": True,
                                            "repair_attempts": attempt + 1
                                        }
                                    else:
                                        self.logger.warning(f"修复后行为树执行失败，尝试再次修复...")
                                        # 更新错误信息
                                        error_str = execution_result.get("error", str(e))
                                except Exception as repair_exec_error:
                                    self.logger.error(f"修复后行为树执行失败: {repair_exec_error}")
                                    # 更新错误信息
                                    error_str = str(repair_exec_error)
                            else:
                                self.logger.error("行为树修复失败，尝试再次修复...")
                        
                        self.logger.warning(f"已达到最大修复尝试次数 ({self.max_repair_attempts})，修复失败")
                    
                    # 如果无法修复或修复失败，返回原始错误
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

    def _save_tree_config(self, tree_config: Dict[str, Any], query: str):
        """保存行为树配置到日志目录（仅在开发者模式下）
        
        Args:
            tree_config: 行为树配置
            query: 用户查询（用于生成文件名）
        """
        from datetime import datetime
        # 生成文件名（基于时间戳和查询的MD5哈希）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        query_hash = hashlib.md5(query.encode('utf-8')).hexdigest()[:8]
        filename = f"behavior_tree_{timestamp}_{query_hash}.json"
        
        # 使用llm_client的_save_debug_file方法保存
        self.llm_client._save_debug_file(filename, tree_config, "行为树配置")

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
    
       
