import py_trees
import logging
import asyncio
import time
from typing import Dict, Any, Optional, Callable, List
from .blackboard import BehaviorTreeBlackboard

class TreeExecutor:
    """行为树执行器
    
    负责执行行为树并管理执行状态。
    """
    
    def __init__(self, tool_executor: Callable, blackboard: BehaviorTreeBlackboard):
        """
        Args:
            tool_executor: 工具执行函数，签名: async def tool_executor(tool_name: str, args: Dict) -> Dict
            blackboard: 黑板实例
        """
        self.tool_executor = tool_executor
        self.blackboard = blackboard
        self.logger = logging.getLogger(__name__)
    
    async def execute(self, root: py_trees.behaviour.Behaviour, 
                   entities: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行行为树
        
        Args:
            root: 行为树根节点
            entities: 实体信息（可选）
        
        Returns:
            执行结果字典
        """
        self.logger.info("开始执行行为树")
        
        # 存储实体到黑板
        if entities:
            self.blackboard.set_entities(entities)
        
        try:
            # 执行行为树
            start_time = time.time()
            
            # 设置行为树
            root.setup_with_descendants()
            
            # 持续执行行为树直到完成
            tick_count = 0
            while root.status not in [py_trees.common.Status.SUCCESS, py_trees.common.Status.FAILURE]:
                # 执行一次 tick
                root.tick_once()
                tick_count += 1
                
                # 检查是否有异步任务需要等待
                async_tasks = self._get_async_tasks(root)
                if async_tasks:
                    try:
                        await asyncio.gather(*async_tasks, return_exceptions=True)
                    except Exception as e:
                        self.logger.error(f"异步任务执行失败: {e}")
                    
                    # 从任务中获取结果并设置到节点
                    self._set_async_results(root)
                
                # 防止无限循环
                if tick_count > 1000:
                    self.logger.warning("达到最大 tick 次数")
                    break
            
            # 获取最终状态
            status = root.status
            self.logger.info(f"行为树最终状态: {status}")
            
            execution_time = time.time() - start_time
            
            # 返回执行结果
            result = {
                "success": status == py_trees.common.Status.SUCCESS,
                "status": str(status),
                "execution_time": execution_time,
                "tick_count": tick_count,
                "blackboard": self.blackboard.get_all()
            }
            
            # 如果执行失败，尝试获取失败原因
            if status == py_trees.common.Status.FAILURE:
                # 从黑板中获取失败原因
                blackboard_data = self.blackboard.get_all()
                # 查找包含错误信息的节点结果（直接在黑板顶层查找）
                for node_id, node_result in blackboard_data.items():
                    # 跳过entities字段
                    if node_id == "entities":
                        continue
                    if isinstance(node_result, dict):
                        # 检查是否是工具返回的失败结果
                        tool_result = node_result
                        if isinstance(tool_result, dict) and "result" in tool_result:
                            tool_result = tool_result["result"]
                        if isinstance(tool_result, dict):
                            if not tool_result.get("success", True):
                                result["error"] = tool_result.get("message", "未知错误")
                                break
            
            self.logger.info(f"行为树执行完成: {result}")
            
            return result
        
        except Exception as e:
            self.logger.error(f"行为树执行异常: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                "success": False,
                "status": "ERROR",
                "error": str(e)
            }
        
        finally:
            # 清理
            try:
                root.terminate(py_trees.common.Status.INVALID)
            except:
                pass
    
    def _get_async_tasks(self, node: py_trees.behaviour.Behaviour) -> List[asyncio.Task]:
        """获取节点中的异步任务
        
        Args:
            node: 当前节点
        
        Returns:
            异步任务列表
        """
        tasks = []
        
        # 检查节点是否有异步任务
        if hasattr(node, 'async_task') and node.async_task is not None:
            tasks.append(node.async_task)
        
        # 递归检查子节点
        if hasattr(node, 'children'):
            for child in node.children:
                tasks.extend(self._get_async_tasks(child))
        
        return tasks
    
    def _set_async_results(self, node: py_trees.behaviour.Behaviour) -> None:
        """从异步任务中获取结果并设置到节点
        
        Args:
            node: 当前节点
        """
        # 检查节点是否有异步任务
        if hasattr(node, 'async_task') and node.async_task is not None and node.async_task.done():
            if node.result is None:
                # 结果还没有设置，从任务中获取
                if node.async_task.cancelled():
                    node.result = {"error": "Task cancelled"}
                elif node.async_task.exception():
                    node.result = {"error": str(node.async_task.exception())}
                else:
                    node.result = node.async_task.result()
            # 清除异步任务
            node.async_task = None
        
        # 递归检查子节点
        if hasattr(node, 'children'):
            for child in node.children:
                self._set_async_results(child)
