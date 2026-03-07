import py_trees
import logging
import asyncio
from typing import Dict, Any, Callable, Optional
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
            node_id = config["id"]
            return MCPActionNode(
                name=name,
                config=config,
                tool_executor=self.tool_executor,
                blackboard=self.blackboard,
                node_id=node_id
            )
        
        elif node_type == "Condition":
            node_id = config["id"]
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
                    # 检查是否存在config_error字段
                    config_error = tool_result.get("config_error")
                    if config_error:
                        # 存储配置错误信息到黑板
                        self.blackboard.set_node_result(self.node_id, {
                            "type": "tool_response",
                            "result": tool_result,
                            "config_error": config_error
                        })
                        self.logger.error(f"{self.name} 配置错误: {config_error}")
                else:
                    # 非字典结果默认为失败
                    success = False
                
                if success:
                    self.logger.debug(f"{self.name}.update()[SUCCESS]")
                    return py_trees.common.Status.SUCCESS
                else:
                    self.logger.debug(f"{self.name}.update()[FAILURE]")
                    return py_trees.common.Status.FAILURE
            
            # 首次执行
            tool_name = self.config["tool"]
            parameters = self.config.get("parameters", {})
            
            # 解析参数引用
            parameters = self._resolve_parameters(parameters)
            
            self.logger.debug(f"调用工具: {tool_name}, 参数: {parameters}")
            
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
            if isinstance(self.result, dict):
                success = self.result.get("success", True)
                
                # 收集所有错误信息
                error_messages = []
                if self.result.get("config_error"):
                    error_messages.append(f"配置错误: {self.result['config_error']}")
                if self.result.get("error"):
                    error_messages.append(f"执行错误: {self.result['error']}")
                
                if error_messages:
                    # 合并所有错误信息
                    full_error = "; ".join(error_messages)
                    
                    # 将错误信息写入 self.result，确保UI能获取到
                    self.result["error"] = full_error
                    
                    # 存储错误信息到黑板
                    self.blackboard.set_node_result(self.node_id, {
                        "type": "tool_response",
                        "result": self.result,
                        "config_error": self.result.get("config_error"),
                        "execution_error": self.result.get("error")
                    })
                    self.logger.error(f"{self.name} 错误: {full_error}")
            else:
                # 非字典结果默认为失败
                success = False
            
            if success:
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
    
    def _resolve_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """解析参数引用
        
        Args:
            parameters: 原始参数字典
        
        Returns:
            解析后的参数字典
        """
        import re
        
        def resolve_value(value):
            """递归解析值"""
            if isinstance(value, str):
                # 查找引用模式，如 {{weatherBeijing.result.formatted_message}}
                pattern = r'\{\{([^}]+)\}\}'
                matches = re.findall(pattern, value)
                
                if not matches:
                    return value
                
                # 替换所有引用
                # 先收集所有需要替换的内容，然后一次性替换
                replacements = {}
                for match in matches:
                    # 解析引用路径，如 weatherBeijing.result.formatted_message
                    ref_path = match.split('.')
                    
                    if len(ref_path) < 2:
                        self.logger.warning(f"引用格式不正确，需要至少2个部分: {match}")
                        # 保持原始引用，不替换
                        continue
                    
                    # 从黑板获取数据
                    node_id = ref_path[0]
                    
                    node_result = self.blackboard.get_node_result(node_id)
                    
                    if node_result is None:
                        self.logger.warning(f"无法找到节点结果: {node_id}")
                        # 保持原始引用，不替换
                    else:
                        # 直接获取formatted_message字段，这是标准的工具执行结果
                        if isinstance(node_result, dict) and "result" in node_result:
                            result = node_result["result"]
                            if isinstance(result, dict) and "formatted_message" in result:
                                data = result["formatted_message"]
                                # 存储替换内容
                                replacements[f'{{{{{match}}}}}'] = str(data)
                            else:
                                self.logger.warning(f"无法找到formatted_message字段: {match}")
                                # 保持原始引用，不替换
                        else:
                            self.logger.warning(f"无法找到result字段: {match}")
                            # 保持原始引用，不替换
                
                # 执行替换
                resolved_value = value
                for old, new in replacements.items():
                    count = resolved_value.count(old)
                    resolved_value = resolved_value.replace(old, new)
                
                return resolved_value
            elif isinstance(value, dict):
                # 递归处理字典
                return {k: resolve_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                # 递归处理列表
                return [resolve_value(item) for item in value]
            else:
                return value
        
        resolved_params = resolve_value(parameters)
        return resolved_params

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
            
            self.logger.debug(f"条件评估结果: {self.name} = {result}")
            
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
        
        try:
            # 预处理条件表达式，处理直接使用节点ID的情况
            preprocessed_condition = self._preprocess_condition(condition)
            
            # 提取并替换{{节点ID}}格式的引用
            resolved_condition = self._resolve_node_references(preprocessed_condition)
            
            # 构建求值环境
            env = self._build_evaluation_environment()
            
            # 解析表达式
            import ast
            tree = ast.parse(resolved_condition, mode='eval')
            
            # 求值
            result = eval(compile(tree, '<string>', 'eval'), env)
            
            # 如果是==比较且结果为False，尝试使用contains比较
            if not result and '==' in resolved_condition:
                # 尝试两种contains比较方式：A in B 和 B in A
                result = self._try_contains_comparison(resolved_condition, condition, env)
            
            return bool(result)
        
        except Exception as e:
            self.logger.error(f"条件表达式求值失败: {condition}, 错误: {e}")
            return False
    
    def _try_contains_comparison(self, resolved_condition: str, original_condition: str, env: Dict[str, Any]) -> bool:
        """尝试使用contains比较
        
        Args:
            resolved_condition: 解析后的条件表达式
            original_condition: 原始条件表达式
            env: 求值环境
        
        Returns:
            如果contains比较成功返回True，否则返回False
        """
        import ast
        
        try:
            # 提取比较的两个值
            tree = ast.parse(resolved_condition, mode='eval')
            if isinstance(tree.body, ast.Compare) and len(tree.body.ops) == 1 and isinstance(tree.body.ops[0], ast.Eq):
                # 获取左右两个表达式
                left_expr = tree.body.left
                right_expr = tree.body.comparators[0]
                
                # 计算左右两个表达式的值
                left_value = eval(compile(ast.Expression(left_expr), '<string>', 'eval'), env)
                right_value = eval(compile(ast.Expression(right_expr), '<string>', 'eval'), env)
                
                # 尝试两种contains比较
                if str(right_value) in str(left_value):
                    self.logger.debug(f"==比较失败，使用 {right_value!r} in {left_value!r} 比较成功: {original_condition}")
                    return True
                if str(left_value) in str(right_value):
                    self.logger.debug(f"==比较失败，使用 {left_value!r} in {right_value!r} 比较成功: {original_condition}")
                    return True

        except Exception as e:
            self.logger.debug(f"AST解析失败，跳过contains比较: {e}")
        
        return False
    
    def _preprocess_condition(self, condition: str) -> str:
        """预处理条件表达式，处理直接使用节点ID的情况
        
        Args:
            condition: 条件表达式
        
        Returns:
            处理后的条件表达式
        """
        import re
        
        # 处理直接使用节点ID的情况（如 actionQueryBeijingWeather.result['current']['weather']）
        def replace_direct_references(match):
            node_id = match.group(1)
            # 从黑板获取节点结果
            node_result = self.blackboard.get_node_result(node_id)
            # 提取formatted_message
            node_value = self._get_formatted_message(node_result)
            # 转义字符串中的特殊字符
            node_value = node_value.replace('\\', '\\\\')  # 转义反斜杠
            node_value = node_value.replace('\n', '\\n')    # 转义换行符
            node_value = node_value.replace('\r', '\\r')    # 转义回车符
            node_value = node_value.replace('\t', '\\t')    # 转义制表符
            node_value = node_value.replace("'", "\\'")     # 转义单引号
            node_value = node_value.replace('"', '\\"')     # 转义双引号
            return f"'{node_value}'"
        
        # 替换直接使用节点ID的引用（如 nodeID.result.xxx 或 nodeID.xxx）
        # 使用更精确的正则表达式，避免匹配到字符串内部的内容
        condition = re.sub(r'\b([a-zA-Z][a-zA-Z0-9_]*)\.\w+(?:\[\'[^\']*\'\])*', replace_direct_references, condition)
        
        return condition
    
    def _resolve_node_references(self, condition: str) -> str:
        """解析条件表达式中的节点引用
        
        Args:
            condition: 条件表达式
        
        Returns:
            解析后的表达式
        """
        import re
        
        # 匹配 {{节点ID}} 格式的引用
        pattern = r'\{\{([^}]+)\}\}'
        matches = re.findall(pattern, condition)
        
        resolved_condition = condition
        for ref in matches:
            # 提取节点ID（只取第一个字段）
            node_id = ref.split('.')[0].strip()
            
            # 从黑板获取节点结果
            node_result = self.blackboard.get_node_result(node_id)
            
            # 强制使用 .result.formatted_message
            node_value = self._get_formatted_message(node_result)
            
            # 转义字符串中的特殊字符
            node_value = node_value.replace('\\', '\\\\')  # 转义反斜杠
            node_value = node_value.replace('\n', '\\n')    # 转义换行符
            node_value = node_value.replace('\r', '\\r')    # 转义回车符
            node_value = node_value.replace('\t', '\\t')    # 转义制表符
            node_value = node_value.replace("'", "\\'")     # 转义单引号
            node_value = node_value.replace('"', '\\"')     # 转义双引号
            
            # 替换表达式中的引用
            resolved_condition = resolved_condition.replace(f"{{{{{ref}}}}}", f"'{node_value}'")
        
        return resolved_condition
    
    def _get_formatted_message(self, node_result: Any) -> str:
        """从节点结果中提取formatted_message
        
        Args:
            node_result: 节点结果
        
        Returns:
            formatted_message内容
        """
        if node_result is None:
            return ""
        
        if isinstance(node_result, dict):
            # 强制使用 result.formatted_message
            if "result" in node_result:
                result = node_result["result"]
                if isinstance(result, dict) and "formatted_message" in result:
                    return result["formatted_message"]
        
        return ""
    
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


# ==================== 装饰器节点 ====================

class InverterNode(py_trees.decorators.Inverter):
    """反转装饰器节点
    
    反转子节点的返回状态：
    - SUCCESS → FAILURE
    - FAILURE → SUCCESS
    - RUNNING → RUNNING（保持不变）
    """
    
    def __init__(self, name: str, child: py_trees.behaviour.Behaviour):
        """
        Args:
            name: 节点名称
            child: 子节点
        """
        super().__init__(name=name, child=child)
        self.logger = logging.getLogger(__name__)
    
    def update(self):
        """执行并反转子节点状态"""
        self.logger.debug(f"{self.name}.update() [Inverter]")
        
        # 调用父类的update方法（会自动处理子节点并反转状态）
        status = super().update()
        
        self.logger.info(f"反转器 {self.name}: 子节点状态反转后为 {status}")
        return status


class TimeoutNode(py_trees.decorators.Timeout):
    """超时装饰器节点
    
    限制子节点的执行时间，如果超时则返回FAILURE。
    """
    
    def __init__(self, name: str, child: py_trees.behaviour.Behaviour, 
                 duration: float = 30.0):
        """
        Args:
            name: 节点名称
            child: 子节点
            duration: 超时时间（秒），默认30秒
        """
        super().__init__(name=name, child=child, duration=duration)
        self.logger = logging.getLogger(__name__)
        self.duration = duration
    
    def update(self):
        """执行子节点并检查是否超时"""
        self.logger.debug(f"{self.name}.update() [Timeout: {self.duration}s]")
        
        # 调用父类的update方法
        status = super().update()
        
        if status == py_trees.common.Status.FAILURE:
            self.logger.warning(f"超时节点 {self.name}: 子节点执行超时 ({self.duration}s)")
        else:
            self.logger.debug(f"超时节点 {self.name}: 子节点状态 {status}")
        
        return status


class RepeatNode(py_trees.decorators.Repeat):
    """重复装饰器节点
    
    重复执行子节点指定次数，直到子节点返回FAILURE或达到重复次数。
    """
    
    def __init__(self, name: str, child: py_trees.behaviour.Behaviour, 
                 num_success: int = 3):
        """
        Args:
            name: 节点名称
            child: 子节点
            num_success: 重复次数，默认3次
        """
        super().__init__(name=name, child=child, num_success=num_success)
        self.logger = logging.getLogger(__name__)
        self.num_success = num_success
        self.current_iteration = 0
    
    def initialise(self):
        """初始化重复计数器"""
        super().initialise()
        self.current_iteration = 0
        self.logger.debug(f"重复节点 {self.name}: 开始执行，目标重复 {self.num_success} 次")
    
    def update(self):
        """执行子节点并计数"""
        self.logger.debug(f"{self.name}.update() [Repeat: {self.current_iteration}/{self.num_success}]")
        
        # 调用父类的update方法
        status = super().update()
        
        if status == py_trees.common.Status.SUCCESS:
            self.current_iteration += 1
            self.logger.debug(f"重复节点 {self.name}: 第 {self.current_iteration}/{self.num_success} 次成功")
        elif status == py_trees.common.Status.FAILURE:
            self.logger.warning(f"重复节点 {self.name}: 子节点失败，停止重复")
        
        return status
