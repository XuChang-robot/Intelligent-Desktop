import py_trees
import logging
import asyncio
from typing import Dict, Any, Callable
from .blackboard import BehaviorTreeBlackboard

class NodeFactory:
    """节点工厂
    
    负责根据配置创建不同类型的节点。
    """
    
    def __init__(self, tool_executor: Callable, blackboard: BehaviorTreeBlackboard):
        """
        Args:
            tool_executor: 工具执行函数，签名: async def tool_executor(tool_name: str, args: Dict) -> Dict
            blackboard: 黑板实例
        """
        self.tool_executor = tool_executor
        self.blackboard = blackboard
        self.action_counter = 0
        self.condition_counter = 0
        self.logger = logging.getLogger(__name__)
    
    def create(self, node_type: str, name: str, config: Dict[str, Any]) -> py_trees.behaviour.Behaviour:
        """根据类型创建节点
        
        Args:
            node_type: 节点类型（Sequence, Selector, Action, Condition等）
            name: 节点名称
            config: 节点配置
        
        Returns:
            创建的节点实例
        """
        if node_type == "Sequence":
            return py_trees.composites.Sequence(name=name, memory=True)
        
        elif node_type == "Selector":
            return py_trees.composites.Selector(name=name, memory=False)
        
        elif node_type == "Parallel":
            return py_trees.composites.Parallel(
                name=name,
                policy=py_trees.common.ParallelPolicy.SuccessOnAll()
            )
        
        elif node_type == "Action":
            node_id = f"action_{self.action_counter}"
            self.action_counter += 1
            return MCPActionNode(
                name=name,
                config=config,
                tool_executor=self.tool_executor,
                blackboard=self.blackboard,
                node_id=node_id
            )
        
        elif node_type == "Condition":
            node_id = f"condition_{self.condition_counter}"
            self.condition_counter += 1
            return ConditionNode(
                name=name,
                config=config,
                blackboard=self.blackboard,
                node_id=node_id
            )
        
        else:
            raise ValueError(f"不支持的节点类型: {node_type}")


class MCPActionNode(py_trees.behaviour.Behaviour):
    """MCP工具调用节点
    
    负责调用MCP工具并存储结果到黑板。
    """
    
    def __init__(self, name: str, config: Dict[str, Any], tool_executor: Callable, 
                 blackboard: BehaviorTreeBlackboard, node_id: str):
        """
        Args:
            name: 节点名称
            config: 节点配置
            tool_executor: 工具执行函数（可以是同步或异步函数）
            blackboard: 黑板实例
            node_id: 节点ID（用于条件引用）
        """
        super().__init__(name)
        self.config = config
        self.tool_executor = tool_executor
        self.blackboard = blackboard
        self.node_id = node_id
        self.result = None
        self.async_task = None
        self.logger = logging.getLogger(__name__)
    
    def setup(self):
        """初始化节点（在行为树开始执行前调用）"""
        self.logger.debug(f"{self.name}.setup()")
    
    def initialise(self):
        """开始执行前调用"""
        self.result = None
        self.async_task = None
        self.logger.debug(f"{self.name}.initialise()")
    
    def update(self):
        """执行节点逻辑"""
        try:
            # 如果有异步任务在运行，返回 RUNNING
            if self.async_task is not None and not self.async_task.done():
                return py_trees.common.Status.RUNNING
            
            # 如果已经有结果，存储到黑板并返回对应状态
            if self.result is not None:
                # 存储结果到黑板
                self.blackboard.set_node_result(self.node_id, self.result)
                
                # 解析实际的工具结果
                tool_result = self.result
                if isinstance(self.result, dict) and "result" in self.result:
                    tool_result = self.result["result"]
                
                # 判断执行结果
                if isinstance(tool_result, dict):
                    success = tool_result.get("success", True)
                else:
                    success = True
                
                if success:
                    self.logger.debug(f"{self.name}.update()[SUCCESS]")
                    return py_trees.common.Status.SUCCESS
                else:
                    self.logger.debug(f"{self.name}.update()[FAILURE]")
                    return py_trees.common.Status.FAILURE
            
            # 首次执行
            tool_name = self.config["tool"]
            parameters = self.config.get("parameters", {})
            
            self.logger.info(f"调用工具: {tool_name}, 参数: {parameters}")
            
            # 调用工具执行器
            result = self.tool_executor(tool_name, parameters)
            
            # 检查返回值是否是协程
            if asyncio.iscoroutine(result):
                # 如果是协程，创建异步任务
                try:
                    loop = asyncio.get_running_loop()
                    self.async_task = loop.create_task(result)
                    return py_trees.common.Status.RUNNING
                except RuntimeError:
                    # 没有运行中的事件循环，使用 asyncio.run
                    self.result = asyncio.run(result)
            else:
                # 直接是结果
                self.result = result
            
            # 存储结果到黑板
            self.blackboard.set_node_result(self.node_id, self.result)
            
            # 判断执行结果
            if self.result.get("success", True):
                self.logger.debug(f"{self.name}.update()[SUCCESS]")
                return py_trees.common.Status.SUCCESS
            else:
                self.logger.debug(f"{self.name}.update()[FAILURE]")
                return py_trees.common.Status.FAILURE
        
        except Exception as e:
            self.logger.error(f"{self.name}.update()[FAILURE]: {e}")
            return py_trees.common.Status.FAILURE
    
    def terminate(self, new_status):
        """节点终止时调用"""
        self.logger.debug(f"{self.name}.terminate()[{self.status}->{new_status}]")


class ConditionNode(py_trees.behaviour.Behaviour):
    """条件判断节点
    
    根据条件表达式评估结果返回 SUCCESS 或 FAILURE。
    """
    
    def __init__(self, name: str, config: Dict[str, Any], 
                 blackboard: BehaviorTreeBlackboard, node_id: str):
        """
        Args:
            name: 节点名称
            config: 节点配置
            blackboard: 黑板实例
            node_id: 节点ID
        """
        super().__init__(name)
        self.config = config
        self.blackboard = blackboard
        self.node_id = node_id
        self.condition = config.get("condition", "")
        self.logger = logging.getLogger(__name__)
    
    def setup(self):
        """初始化节点"""
        self.logger.debug(f"{self.name}.setup()")
    
    def initialise(self):
        """开始执行前调用"""
        self.logger.debug(f"{self.name}.initialise()")
    
    def update(self):
        """执行条件判断"""
        try:
            # 评估条件表达式
            result = self._evaluate_condition(self.condition)
            
            self.logger.info(f"条件评估结果: {self.name} = {result}")
            
            if result:
                self.logger.debug(f"{self.name}.update()[SUCCESS]")
                return py_trees.common.Status.SUCCESS
            else:
                self.logger.debug(f"{self.name}.update()[FAILURE]")
                return py_trees.common.Status.FAILURE
        
        except Exception as e:
            self.logger.error(f"{self.name}.update()[FAILURE]: {e}")
            return py_trees.common.Status.FAILURE
    
    def terminate(self, new_status):
        """节点终止时调用"""
        self.logger.debug(f"{self.name}.terminate()[{self.status}->{new_status}]")
    
    def _evaluate_condition(self, condition: str) -> bool:
        """评估条件表达式
        
        Args:
            condition: 条件表达式
        
        Returns:
            评估结果
        """
        if not condition:
            return True
        
        # 构建求值环境
        env = self._build_evaluation_environment()
        
        try:
            # 解析表达式
            import ast
            tree = ast.parse(condition, mode='eval')
            
            # 求值
            result = eval(compile(tree, '<string>', 'eval'), env)
            
            return bool(result)
        
        except Exception as e:
            self.logger.error(f"条件表达式求值失败: {condition}, 错误: {e}")
            return False
    
    def _build_evaluation_environment(self) -> Dict[str, Any]:
        """构建条件求值环境
        
        Returns:
            包含所有可用变量和函数的字典
        """
        import operator
        
        env = {
            # 内置函数
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'abs': abs,
            'max': max,
            'min': min,
            'sum': sum,
            'any': any,
            'all': all,
            'isinstance': isinstance,
            'type': type,
            'list': list,
            'dict': dict,
            'range': range,
            
            # 运算符
            'and': lambda x, y: x and y,
            'or': lambda x, y: x or y,
            'not': lambda x: not x,
            'in': lambda x, y: x in y,
            
            # 比较运算
            'eq': operator.eq,
            'ne': operator.ne,
            'gt': operator.gt,
            'lt': operator.lt,
            'ge': operator.ge,
            'le': operator.le,
        }
        
        # 添加节点结果到环境
        for key, value in self.blackboard.get_all().items():
            # 如果是字典，创建一个支持点号访问的包装类
            if isinstance(value, dict):
                env[key] = DictWrapper(value)
            else:
                env[key] = value
        
        return env


class DictWrapper:
    """字典包装类，支持点号访问属性"""
    
    def __init__(self, data: Dict[str, Any]):
        self._data = data
    
    def __getattr__(self, name: str) -> Any:
        if name in self._data:
            value = self._data[name]
            # 如果是嵌套字典，继续包装
            if isinstance(value, dict):
                return DictWrapper(value)
            return value
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
    
    def __repr__(self) -> str:
        return repr(self._data)
