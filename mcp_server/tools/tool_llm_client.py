# 工具专用 LLM 客户端
# 轻量级 LLM 客户端，专门用于工具参数推理修正

import logging
import json
import aiohttp

from user_config.config import get_config


class ToolLLMClient:
    """工具专用 LLM 客户端
    
    轻量级 LLM 客户端，专门用于工具参数推理修正。
    直接与 Ollama 通信，无需思考模式，快速响应。
    """
    
    def __init__(self):
        # 从配置文件读取配置
        self.base_url = get_config('execution_intelligence.tool_llm.base_url', 'http://localhost:11434')
        self.model = get_config('execution_intelligence.cost_control.model', 'qwen2.5:7b')
        self.timeout = get_config('execution_intelligence.cost_control.timeout_ms', 5000) / 1000
        self.temperature = get_config('execution_intelligence.cost_control.temperature', 0.3)
        self.max_tokens = get_config('execution_intelligence.cost_control.max_tokens', 200)
    
    def _build_parameter_fix_schema(self) -> dict:
        """构建参数修正的 JSON schema"""
        return {
            "type": "object",
            "properties": {
                "success": {
                    "type": "boolean",
                    "description": "是否成功修正参数",
                    "enum": [True, False]
                },
                "fixed_params": {
                    "type": "object",
                    "description": "修正后的参数",
                    "additionalProperties": True
                },
                "reason": {
                    "type": "string",
                    "description": "修正原因说明"
                }
            },
            "required": ["success", "fixed_params"]
        }
    
    async def generate(self, prompt: str) -> str:
        """生成响应
        
        Args:
            prompt: 提示词
            
        Returns:
            生成的响应文本
        """
        try:
            url = f"{self.base_url}/api/generate"
            
            data = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": self._build_parameter_fix_schema(),
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, timeout=self.timeout) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get('response', '')
                    else:
                        logging.getLogger(__name__).warning(f"ToolLLMClient 请求失败: {response.status}")
                        return ''
                        
        except Exception as e:
            logging.getLogger(__name__).error(f"ToolLLMClient 生成失败: {e}")
            return ''
    
    async def generate_structured(self, prompt: str) -> dict:
        """生成结构化响应
        
        Args:
            prompt: 提示词
            
        Returns:
            解析后的字典，包含 success, fixed_params 和 reason
        """
        response = await self.generate(prompt)
        
        if not response:
            return {"success": False, "fixed_params": {}, "reason": "生成失败"}
        
        try:
            result = json.loads(response)
            # 确保 success 字段存在
            if "success" not in result:
                result["success"] = bool(result.get("fixed_params", {}))
            return result
        except json.JSONDecodeError:
            return {"success": False, "fixed_params": {}, "reason": "解析失败"}
