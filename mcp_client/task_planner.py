# 任务规划器模块

import logging
from typing import Dict, Any, List
from mcp_client.llm import LLMClient

class TaskPlanner:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
    
    async def plan_task(self, intent: Dict[str, Any], tools=None) -> Dict[str, Any]:
        """规划任务步骤
        
        Args:
            intent: 用户意图
            tools: 可用工具列表（从server获取）
        """
        try:
            # 使用LLM生成任务计划，传入工具列表
            plan = await self.llm_client.plan_task(intent, tools)
            self.logger.info(f"生成任务计划成功: {plan}")
            return plan
        except Exception as e:
            self.logger.error(f"生成任务计划失败: {e}")
            return {
                "plan": "无法生成任务计划",
                "steps": []
            }
    
    def validate_plan(self, plan: Dict[str, Any]) -> bool:
        """验证任务计划是否有效"""
        if not plan:
            return False
        
        steps = plan.get("steps", [])
        if not steps:
            self.logger.warning("任务计划为空")
            return False
        
        for step in steps:
            if not step.get("tool"):
                self.logger.warning(f"步骤缺少工具名称: {step}")
                return False
            
        return True
    
    async def optimize_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """优化任务计划"""
        # 这里可以添加任务计划优化逻辑
        # 例如：合并相同的工具调用、调整执行顺序等
        return plan
    
    async def plan(self, query: str, tools=None) -> Dict[str, Any]:
        """规划任务步骤（兼容旧接口）
        
        Args:
            query: 用户查询
            tools: 可用工具列表（从server获取）
        """
        try:
            # 构建意图字典
            intent = {
                "intent": "task",
                "entities": {"query": query},
                "confidence": 0.9
            }
            
            # 调用现有的plan_task方法，传入工具列表
            plan = await self.plan_task(intent, tools)
            
            # 验证计划
            if not self.validate_plan(plan):
                # 如果计划无效，使用LLM生成Python代码
                from mcp_client.llm import LLMClient
                llm_client = LLMClient()
                code = await llm_client.generate_python_code(query)
                
                # 构建简单的计划
                return {
                    "plan": f"执行Python代码: {query}",
                    "steps": [
                        {
                            "tool": "execute_python",
                            "args": {"code": code},
                            "description": "执行生成的Python代码"
                        }
                    ]
                }
            
            # 优化计划
            optimized_plan = await self.optimize_plan(plan)
            
            return optimized_plan
        except Exception as e:
            self.logger.error(f"规划任务失败: {e}")
            # 返回默认计划
            return {
                "plan": f"执行Python代码: {query}",
                "steps": [
                    {
                        "tool": "execute_python",
                        "args": {"code": query},
                        "description": "执行Python代码"
                    }
                ]
            }
