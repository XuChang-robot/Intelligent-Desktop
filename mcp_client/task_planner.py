# 任务规划器模块

import logging
from typing import Dict, Any, List
from mcp_client.llm import LLMClient
from mcp_client.hybrid_cache import HybridTaskPlanCache

class TaskPlanner:
    def __init__(self, llm_client: LLMClient, cache_dir: str = "cache", cache_ttl: int = 604800, 
                 similarity_threshold: float = 0.85, max_total_size_mb: int = 1024, 
                 max_db_size_mb: int = 512, max_faiss_size_mb: int = 512, max_records: int = 10000,
                 cleanup_interval: int = 3600, cleanup_on_startup: bool = True,
                 embedding_model: str = "nomic-embed-text"):
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
        
        # 初始化混合缓存（使用Ollama embedding模型）
        self.cache = HybridTaskPlanCache(
            cache_dir=cache_dir,
            ttl=cache_ttl,
            similarity_threshold=similarity_threshold,
            max_total_size_mb=max_total_size_mb,
            max_db_size_mb=max_db_size_mb,
            max_faiss_size_mb=max_faiss_size_mb,
            max_records=max_records,
            cleanup_interval=cleanup_interval,
            cleanup_on_startup=cleanup_on_startup,
            embedding_model=embedding_model,
            llm_client=llm_client
        )
        self.logger.info(f"混合缓存系统初始化成功（embedding模型: {embedding_model}）")
    
    async def plan_task(self, intent: Dict[str, Any], tools=None) -> Dict[str, Any]:
        """规划任务步骤（不自动缓存）
        
        Args:
            intent: 用户意图
            tools: 可用工具列表（从server获取）
        
        Returns:
            {
                "plan": 任务计划,
                "from_cache": 是否来自缓存
            }
        """
        try:
            # 先尝试从缓存获取
            self.logger.info(f"开始查询缓存，intent: {intent}")
            cached_plan = self.cache.get(intent, tools)
            if cached_plan:
                self.logger.info("使用缓存的任务计划")
                # 添加from_cache标志
                cached_plan["from_cache"] = True
                return cached_plan
            
            self.logger.info("缓存未命中，调用LLM生成任务计划")
            # 缓存未命中，调用LLM生成
            plan = await self.llm_client.plan_task(intent, tools)
            
            # 注意：不自动缓存，等待执行成功后再缓存
            # self.cache.set(intent, tools, plan)  # 移除自动缓存
            
            # 添加from_cache标志
            plan["from_cache"] = False
            
            self.logger.info(f"生成任务计划成功: {plan}")
            return plan
        except Exception as e:
            self.logger.error(f"生成任务计划失败: {e}")
            return {
                "plan": "无法生成任务计划",
                "steps": [],
                "from_cache": False
            }
    
    def cache_plan(self, intent: Dict[str, Any], plan: Dict[str, Any], tools=None) -> None:
        """Cache task plan (called after successful execution)
        
        Args:
            intent: User intent
            plan: Task plan
            tools: Available tools list
        """
        try:
            self.logger.info(f"开始缓存任务计划: {plan.get('plan', 'N/A')}")
            # Store result in cache
            self.cache.set(intent, tools, plan)
            self.logger.info(f"Task plan cached: {plan.get('plan', 'N/A')}")
        except Exception as e:
            self.logger.error(f"Failed to cache task plan: {e}")
    
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
                # 如果计划无效，返回错误信息
                self.logger.warning("计划验证失败，无法执行任务")
                return {
                    "plan": "无法执行任务：没有合适的工具可用",
                    "steps": []
                }
            
            # 优化计划
            optimized_plan = await self.optimize_plan(plan)
            
            return optimized_plan
        except Exception as e:
            self.logger.error(f"规划任务失败: {e}")
            # 返回默认计划
            return {
                "plan": "无法执行任务：规划失败",
                "steps": []
            }
    
    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
        self.logger.info("任务计划缓存已清空")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return self.cache.get_stats()
    
    def cleanup_expired_cache(self) -> int:
        """清理过期缓存"""
        return self.cache.cleanup_expired()
