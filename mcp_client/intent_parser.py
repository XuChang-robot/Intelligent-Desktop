# 意图解析器模块

import logging
from typing import Dict, Any
from mcp_client.llm import LLMClient

class IntentParser:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
    
    async def parse_intent(self, user_input: str) -> Dict[str, Any]:
        """解析用户意图"""
        try:
            # 使用LLM解析意图
            intent = await self.llm_client.parse_intent(user_input)
            self.logger.info(f"解析意图成功: {intent}")
            return intent
        except Exception as e:
            self.logger.error(f"解析意图失败: {e}")
            return {
                "intent": "unknown",
                "entities": {},
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
    
    async def parse(self, user_input: str) -> Dict[str, Any]:
        """解析用户意图（兼容旧接口）"""
        self.logger.info(f"开始解析用户意图: {user_input[:50]}...")
        try:
            # 调用现有的parse_intent方法
            intent_result = await self.parse_intent(user_input)
            self.logger.info(f"parse_intent返回: {intent_result}")
            
            # 如果意图解析失败，使用简单的fallback逻辑
            if intent_result.get("intent") == "unknown" or intent_result.get("confidence", 0) < 0.5:
                self.logger.warning(f"意图解析失败，使用fallback逻辑")
                # 使用简单的规则来解析用户意图
                # 默认使用tool_call类型，让LLM生成Python代码
                return {
                    "type": "tool_call",
                    "tool": "execute_python",
                    "args": {"code": user_input},
                    "confidence": 0.5
                }
            
            # 转换为client.py期望的格式
            if intent_result.get("intent") == "execute_code":
                # 生成Python代码而不是直接使用用户输入
                self.logger.info("意图是execute_code，开始生成Python代码")
                code = await self.llm_client.generate_python_code(user_input)
                self.logger.info("Python代码生成完成")
                return {
                    "type": "tool_call",
                    "tool": "execute_python",
                    "args": {"code": code},
                    "confidence": intent_result.get("confidence", 0.5)
                }
            elif intent_result.get("intent") == "task":
                self.logger.info("意图是task")
                return {
                    "type": "task",
                    "entities": intent_result.get("entities", {}),
                    "confidence": intent_result.get("confidence", 0.5)
                }
            else:
                # 对于其他意图，也转换为tool_call类型，使用Python代码执行
                # 生成Python代码而不是直接使用用户输入
                self.logger.info(f"其他意图: {intent_result.get('intent')}, 开始生成Python代码")
                code = await self.llm_client.generate_python_code(user_input)
                self.logger.info(f"Python代码生成完成")
                return {
                    "type": "tool_call",
                    "tool": "execute_python",
                    "args": {"code": code},
                    "confidence": intent_result.get("confidence", 0.5)
                }
        except Exception as e:
            self.logger.error(f"解析意图失败: {e}")
            import traceback
            traceback.print_exc()
            # 即使出现异常，也尝试生成Python代码
            try:
                self.logger.info("尝试生成Python代码（fallback）")
                code = await self.llm_client.generate_python_code(user_input)
            except Exception as e2:
                self.logger.error(f"生成Python代码失败: {e2}")
                code = user_input
            return {
                "type": "tool_call",
                "tool": "execute_python",
                "args": {"code": code},
                "confidence": 0.5
            }
