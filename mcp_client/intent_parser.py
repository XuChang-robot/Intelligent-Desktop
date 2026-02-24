# 意图解析器模块

import json
import logging
import os
import platform
from typing import Dict, Any
from mcp_client.llm import LLMClient

class IntentParser:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
    
    def _get_desktop_path(self) -> str:
        """获取当前系统的桌面路径"""
        system = platform.system()
        
        if system == "Windows":
            # Windows: C:\Users\<username>\Desktop
            return os.path.join(os.path.expanduser("~"), "Desktop")
        elif system == "Darwin":
            # macOS: /Users/<username>/Desktop
            return os.path.join(os.path.expanduser("~"), "Desktop")
        else:
            # Linux: /home/<username>/Desktop
            return os.path.join(os.path.expanduser("~"), "Desktop")
    
    def _fix_desktop_path(self, path: str) -> str:
        """修复路径中的"桌面"或"Desktop"为实际的桌面路径
        
        Args:
            path: 原始路径
        
        Returns:
            修复后的路径
        """
        if not path:
            return path
        
        # 检查路径中是否包含"桌面"或"Desktop"
        import re
        
        # 匹配模式：/桌面/、/Desktop/、桌面/、Desktop/ 等
        if "桌面" in path or "Desktop" in path or "desktop" in path:
            # 替换为实际的桌面路径
            desktop_path = self._get_desktop_path()
            self.logger.info(f"检测到桌面路径，准备替换: {path} -> {desktop_path}")
            
            # 使用正则表达式替换（只替换第一个匹配）
            # 匹配：桌面/、Desktop/、\桌面\、\Desktop\ 等
            pattern = r'[/\\]?(?:桌面|Desktop|desktop)[/\\]?'
            
            # 查找第一个匹配
            match = re.search(pattern, path, flags=re.IGNORECASE)
            if match:
                # 获取匹配后的部分
                rest_of_path = path[match.end():]
                
                # 构建新路径
                if rest_of_path:
                    new_path = os.path.join(desktop_path, rest_of_path)
                else:
                    new_path = desktop_path
                
                self.logger.info(f"桌面路径已替换: {new_path}")
                return new_path
        
        return path
    
    async def parse_intent(self, user_input: str, tools=None) -> Dict[str, Any]:
        """解析用户意图（提取意图类型和关键实体）"""
        try:
            # 使用LLM解析意图
            intent = await self.llm_client.parse_intent(user_input, tools)
            self.logger.info(f"解析意图成功: {intent}")
            return intent
        except ConnectionError as e:
            # LLM连接错误
            error_msg = str(e)
            self.logger.error(f"LLM连接失败: {error_msg}")
            return {
                "intent": "error",
                "error": error_msg,
                "confidence": 0.0
            }
        except Exception as e:
            self.logger.error(f"解析意图失败: {e}")
            return {
                "intent": "unknown",
                "confidence": 0.5
            }
    
    def validate_intent(self, intent: Dict[str, Any]) -> bool:
        """验证意图是否有效"""
        if not intent:
            return False
        
        if intent.get("confidence", 0) < 0.7:
            self.logger.warning(f"意图置信度低: {intent.get('confidence')}")
            return False
        
        if intent.get("intent") == "unknown":
            self.logger.warning("未知意图")
            return False
        
        return True
    
    async def parse(self, user_input: str, tools=None) -> Dict[str, Any]:
        """解析用户意图（兼容旧接口）
        
        Args:
            user_input: 用户输入
            tools: 可用工具列表（从server获取）
        """
        self.logger.info(f"开始解析用户意图: {user_input[:50]}...")
        try:
            # 调用parse_intent，获取意图类型和entities
            intent_result = await self.parse_intent(user_input, tools)
            
            # 检查意图是否有效
            if intent_result.get("intent") == "unknown":
                # 解析失败，返回错误信息
                self.logger.error("意图解析失败：LLM返回了未知意图")
                return {
                    "type": "error",
                    "user_input": user_input,
                    "error": "意图解析失败：无法理解您的输入，请重新表述"
                }
            
            # 检查是否是连接错误
            if intent_result.get("intent") == "error":
                error_msg = intent_result.get("error", "无法与LLM服务通信")
                self.logger.error(f"LLM连接错误: {error_msg}")
                return {
                    "type": "error",
                    "user_input": user_input,
                    "error": error_msg
                }
            
            # 转换为client.py期望的格式
            if intent_result.get("intent") == "chat":
                # 聊天型意图，直接返回
                return {
                    "type": "chat",
                    "user_input": user_input,
                    "confidence": intent_result.get("confidence", 0.5)
                }
            elif intent_result.get("intent") == "cannot_execute":
                # 无法执行型意图，返回原因
                return {
                    "type": "cannot_execute",
                    "user_input": user_input,
                    "confidence": intent_result.get("confidence", 0.5),
                    "reason": intent_result.get("reason", "当前工具无法完成此任务")
                }
            elif intent_result.get("intent") == "task":
                # 任务型意图，直接使用tree_config
                tree_config = intent_result.get("tree_config")
                
                if not tree_config:
                    self.logger.error("意图解析失败：LLM未返回tree_config")
                    return {
                        "type": "error",
                        "user_input": user_input,
                        "error": "意图解析失败：LLM未返回行为树配置"
                    }
                
                result = {
                    "type": "task",
                    "user_input": user_input,
                    "entities": intent_result.get("entities", {}),
                    "confidence": intent_result.get("confidence", 0.5),
                    "tree_config": tree_config
                }
                return result
            else:
                # 未知意图，返回错误信息
                self.logger.error(f"未知意图: {intent_result.get('intent')}")
                return {
                    "type": "error",
                    "user_input": user_input,
                    "error": f"意图解析失败：未知的意图类型 {intent_result.get('intent')}"
                }
        except Exception as e:
            self.logger.error(f"解析用户意图时出错: {e}")
            import traceback
            traceback.print_exc()
            # 出错时返回错误信息
            return {
                "type": "error",
                "user_input": user_input,
                "error": f"意图解析失败：{str(e)}"
            }
    
    # @deprecated: 此方法已废弃，功能已整合到parse_intent方法中
    # 为了向后兼容保留此方法，但不应再调用
    async def _generate_tree_config(self, user_input: str, intent_result: Dict[str, Any], tools=None) -> Dict[str, Any]:
        """生成行为树配置
        
        Args:
            user_input: 用户输入
            intent_result: 意图解析结果
            tools: 可用工具列表
        
        Returns:
            行为树配置字典
        """
        # 此方法已废弃，不应再调用
        # 直接抛出异常，提示调用者使用新的parse_intent方法
        raise NotImplementedError("_generate_tree_config方法已废弃，请使用parse_intent方法，tree_config已整合到parse_intent的返回值中")
