# 任务规划器模块

import json
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
        """规划任务步骤（基于entities）
        
        Args:
            intent: 用户意图（包含entities）
            tools: 可用工具列表（从server获取）
        
        Returns:
            {
                "plan": 任务计划,
                "from_cache": 是否来自缓存
            }
        """
        try:
            # 获取entities
            entities = intent.get("entities", {})
            
            # 先尝试从缓存获取（语义匹配）
            self.logger.info(f"开始查询缓存，intent: {intent}")
            
            # 查询缓存（只进行语义匹配，哈希精确匹配已在client.py中完成）
            cached_plan = self.cache.get(intent, tools)
            if cached_plan:
                self.logger.info("缓存命中，使用缓存的模板")
                
                # 获取缓存的模板（只包含 tool + operation）
                template = cached_plan.get("template", {})
                
                # 根据entities生成完整计划（用具体参数替换模板）
                complete_plan = self._generate_plan_from_template(template, entities)
                
                # 添加from_cache标志和相似度
                complete_plan["from_cache"] = True
                complete_plan["similarity"] = cached_plan.get("similarity", 0.0)
                complete_plan["match_type"] = "semantic"
                
                self.logger.info(f"使用缓存模板生成的完整计划: {complete_plan}")
                
                return complete_plan
            
            self.logger.info("缓存未命中，通过LLM生成任务计划")
            # 缓存未命中，通过LLM根据entities生成任务计划
            plan = await self._generate_plan_from_entities(entities, tools)
            
            # 添加from_cache标志
            plan["from_cache"] = False
            
            self.logger.info(f"生成任务计划成功: {plan}")
            
            return plan
        except Exception as e:
            self.logger.error(f"生成任务计划失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "plan": "无法生成任务计划",
                "steps": [],
                "from_cache": False
            }
    
    async def _generate_plan_from_entities(self, entities: Dict[str, Any], tools=None) -> Dict[str, Any]:
        """通过LLM根据entities生成任务计划
        
        Args:
            entities: 从意图中提取的实体信息
            tools: 可用工具列表
        
        Returns:
            完整任务计划
        """
        # 格式化工具信息
        tools_info = ""
        if tools:
            tools_info = "\n\n可用工具列表：\n"
            for tool in tools:
                tool_name = tool.name if hasattr(tool, 'name') else str(tool)
                tool_desc = tool.description if hasattr(tool, 'description') else ""
                tools_info += f"- {tool_name}: {tool_desc}\n"
        
        # 构建entities描述
        entities_str = json.dumps(entities, ensure_ascii=False, indent=2)
        
        system_prompt = "你是一个智能任务规划器，负责根据实体信息和可用工具生成任务执行计划。你必须只返回有效的JSON格式，不要包含任何其他文字、解释或markdown标记。"
        
        prompt = f"""请根据以下实体信息和可用工具，生成任务执行计划：

实体信息：
{entities_str}{tools_info}

请按照以下JSON格式返回任务计划：
{{
  "plan": "任务概述",
  "steps": [
    {{
      "tool": "工具名称",
      "args": {{
        "参数名": "参数值"
      }},
      "description": "步骤描述"
    }}
  ]
}}

重要规则：
1. 根据entities中的信息，选择合适的工具和参数
2. 根据工具的参数类型决定如何生成步骤：
   - 如果工具支持批量处理（如支持输入数组或列表），可以一次调用处理多个输入
   - 如果工具只支持单个输入，需要为每个输入生成一个步骤
3. 确保每个步骤的参数都完整且正确
4. 步骤描述应该清晰简洁

注意：只返回JSON，不要包含任何解释、注释或其他文字。"""
        
        response_dict = await self.llm_client.generate(prompt, system_prompt)
        response = response_dict.get("response", "")
        thinking = response_dict.get("thinking", "")
        
        if thinking:
            self.logger.info(f"LLM思考过程: {thinking[:500]}...")
        
        response = self.llm_client.clean_json_response(response)
        
        try:
            plan = json.loads(response)
            self.logger.info(f"LLM生成的任务计划: {plan}")
            return plan
        except json.JSONDecodeError as e:
            self.logger.error(f"解析任务计划失败: {e}, 原始响应: {response}")
            return {
                "plan": "无法生成任务计划",
                "steps": []
            }
    
    def _generate_plan_from_template(self, template: Dict[str, Any], entities: Any) -> Dict[str, Any]:
        """根据模板和entities生成完整计划
        
        Args:
            template: 缓存的模板（只包含 tool + operation）
            entities: 从意图中提取的实体信息（可以是字典或列表）
        
        Returns:
            完整任务计划
        """
        # 获取模板中的步骤
        template_steps = template.get("steps", [])
        if not template_steps:
            return {
                "plan": "无法生成任务计划",
                "steps": []
            }
        
        # 只使用第一个模板步骤（模板步骤是抽象的，不包含具体参数）
        template_step = template_steps[0]
        tool = template_step.get("tool", "")
        template_args = template_step.get("args", {})
        
        # 生成完整步骤
        steps = []
        
        # 如果entities是列表，为每个元素生成一个步骤
        if isinstance(entities, list):
            for entity in entities:
                # 获取entity的operation（优先使用entity自己的operation）
                entity_operation = entity.get("operation", "")
                
                # 检查是否有多个输入（num_inputs数组）
                if "num_inputs" in entity and isinstance(entity["num_inputs"], list):
                    # 多个输入的情况：为每个输入生成一个步骤
                    for input_info in entity["num_inputs"]:
                        # 合并模板参数和输入参数
                        args = template_args.copy()
                        # 如果entity有自己的operation，使用entity的operation
                        if entity_operation:
                            args["operation"] = entity_operation
                        args.update(input_info)
                        
                        step = {
                            "tool": tool,
                            "args": args,
                            "description": f"执行{tool}操作"
                        }
                        steps.append(step)
                else:
                    # 单个输入或单个参数的情况：直接使用模板步骤
                    # 合并模板参数和entities参数
                    args = template_args.copy()
                    # 如果entity有自己的operation，使用entity的operation
                    if entity_operation:
                        args["operation"] = entity_operation
                    for key, value in entity.items():
                        if key not in ["tool", "operation", "num_inputs"]:  # 排除tool、operation和num_inputs
                            args[key] = value
                    
                    step = {
                        "tool": tool,
                        "args": args,
                        "description": f"执行{tool}操作"
                    }
                    steps.append(step)
        else:
            # entities是字典的情况
            # 获取entities的operation（优先使用entities自己的operation）
            entities_operation = entities.get("operation", "")
            
            # 检查是否有多个输入（num_inputs数组）
            if "num_inputs" in entities and isinstance(entities["num_inputs"], list):
                # 多个输入的情况：为每个输入生成一个步骤
                for input_info in entities["num_inputs"]:
                    # 合并模板参数和输入参数
                    args = template_args.copy()
                    # 如果entities有自己的operation，使用entities的operation
                    if entities_operation:
                        args["operation"] = entities_operation
                    args.update(input_info)
                    
                    step = {
                        "tool": tool,
                        "args": args,
                        "description": f"执行{tool}操作"
                    }
                    steps.append(step)
            else:
                # 单个输入或单个参数的情况：直接使用模板步骤
                # 合并模板参数和entities参数
                args = template_args.copy()
                # 如果entities有自己的operation，使用entities的operation
                if entities_operation:
                    args["operation"] = entities_operation
                for key, value in entities.items():
                    if key not in ["tool", "operation", "num_inputs"]:  # 排除tool、operation和num_inputs
                        args[key] = value
                
                step = {
                    "tool": tool,
                    "args": args,
                    "description": f"执行{tool}操作"
                }
                steps.append(step)
        
        # 生成计划概述
        plan = self._generate_plan_description(steps, entities)
        
        return {
            "plan": plan,
            "steps": steps
        }
    
    def _generate_plan_description(self, steps: List[Dict[str, Any]], entities: Dict[str, Any]) -> str:
        """生成计划描述
        
        Args:
            steps: 步骤列表
            entities: 实体信息
        
        Returns:
            计划描述
        """
        if not steps:
            return "无法生成任务计划"
        
        descriptions = [step.get("description", "") for step in steps if step.get("description")]
        
        if descriptions:
            return "\n".join(descriptions)
        else:
            return "执行任务"
    
    def cache_plan(self, intent: Dict[str, Any], plan: Dict[str, Any], tools=None) -> None:
        """Cache task plan (called after successful execution)
        
        Args:
            intent: User intent (must contain user_input for hash matching)
            plan: Task plan
            tools: Available tools list
        """
        try:
            # 只有当意图类型为task时才缓存
            intent_type = intent.get("intent") or intent.get("type", "")
            if intent_type != "task":
                self.logger.info(f"意图类型为 {intent_type}，不是task类型，不缓存")
                return
            
            self.logger.info(f"开始缓存任务计划: {plan.get('plan', 'N/A')}")
            
            # 获取用户原始输入
            user_input = intent.get("user_input", "")
            if not user_input:
                self.logger.warning("intent中缺少user_input，无法进行哈希精确匹配")
            
            # Store result in cache (with user_input for exact hash matching)
            self.cache.set(intent, tools, plan, user_input)
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
