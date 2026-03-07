import py_trees
import logging
from typing import Dict, Any, List
from .nodes import NodeFactory

class TreeBuilder:
    """行为树构建器
    
    负责将JSON配置转换为py_trees节点对象。
    支持递归构建复杂的树结构。
    """
    
    def __init__(self, node_factory: NodeFactory):
        """
        Args:
            node_factory: 节点工厂实例
        """
        self.node_factory = node_factory
        self.logger = logging.getLogger(__name__)
    
    def build_from_config(self, config: Dict[str, Any]) -> py_trees.behaviour.Behaviour:
        """从JSON配置构建行为树
        
        Args:
            config: 行为树配置字典
        
        Returns:
            行为树根节点
        
        Raises:
            ValueError: 配置无效时
        """
        
        # 验证配置
        self._validate_config(config)
        
        # 递归构建节点
        root_node = self._build_node(config)
        
        self.logger.info(f"行为树已构建")
        
        return root_node
    
    def _build_node(self, config: Dict[str, Any]) -> py_trees.behaviour.Behaviour:
        """递归构建节点
        
        Args:
            config: 节点配置
        
        Returns:
            构建的节点
        """
        node_type = config.get("type")
        node_name = config.get("name", node_type)
        
        self.logger.debug(f"构建节点: {node_name} (类型: {node_type})")
        
        # 处理装饰器节点（只有一个子节点）
        if node_type in ["Inverter", "Timeout", "Repeat"]:
            return self._build_decorator_node(config)
        
        # 使用工厂创建节点
        node = self.node_factory.create(node_type, node_name, config)
        
        # 递归构建子节点
        if "children" in config:
            children_config = config["children"]
            
            if not isinstance(children_config, list):
                raise ValueError(f"children 必须是列表: {node_name}")
            
            for child_config in children_config:
                child_node = self._build_node(child_config)
                node.add_child(child_node)
        
        return node
    
    def _build_decorator_node(self, config: Dict[str, Any]) -> py_trees.behaviour.Behaviour:
        """构建装饰器节点
        
        装饰器节点只有一个子节点（child），不是多个子节点（children）。
        
        Args:
            config: 装饰器节点配置
        
        Returns:
            构建的装饰器节点
        """
        node_type = config.get("type")
        node_name = config.get("name", node_type)
        
        self.logger.debug(f"构建装饰器节点: {node_name} (类型: {node_type})")
        
        # 检查是否有子节点配置
        if "child" not in config:
            raise ValueError(f"装饰器节点 {node_name} 必须包含 child 字段")
        
        child_config = config["child"]
        
        # 递归构建子节点
        child_node = self._build_node(child_config)
        
        # 根据类型创建对应的装饰器节点
        if node_type == "Inverter":
            from .nodes import InverterNode
            return InverterNode(name=node_name, child=child_node)
        
        elif node_type == "Timeout":
            from .nodes import TimeoutNode
            duration = config.get("duration", 30.0)
            return TimeoutNode(name=node_name, child=child_node, duration=duration)
        
        elif node_type == "Repeat":
            from .nodes import RepeatNode
            num_success = config.get("num_success", 3)
            return RepeatNode(name=node_name, child=child_node, num_success=num_success)
        
        else:
            raise ValueError(f"不支持的装饰器节点类型: {node_type}")
    
    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置有效性
        
        Args:
            config: 配置字典
        
        Returns:
            验证通过返回 True
        
        Raises:
            ValueError: 配置无效时
        """
        if not isinstance(config, dict):
            raise ValueError("配置必须是字典")
        
        if "type" not in config:
            raise ValueError("配置必须包含 type 字段")
        
        node_type = config["type"]
        
        # 验证节点类型
        valid_types = ["Sequence", "Selector", "Parallel", "Action", "Condition", "Inverter", "Timeout", "Repeat"]
        if node_type not in valid_types:
            raise ValueError(f"不支持的节点类型: {node_type}, 支持的类型: {valid_types}")
        
        # 验证必需字段
        if node_type == "Action":
            if "tool" not in config:
                raise ValueError("Action 节点必须包含 tool 字段")
        
        elif node_type == "Condition":
            if "condition" not in config:
                raise ValueError("Condition 节点必须包含 condition 字段")
        
        # 验证装饰器节点
        elif node_type in ["Inverter", "Timeout", "Repeat"]:
            if "child" not in config:
                raise ValueError(f"{node_type} 装饰器节点必须包含 child 字段")
            # 递归验证子节点
            self._validate_config(config["child"])
        
        # 递归验证子节点（复合节点）
        if "children" in config:
            children_config = config["children"]
            if not isinstance(children_config, list):
                raise ValueError("children 必须是列表")
            
            for child_config in children_config:
                self._validate_config(child_config)
        
        return True
    
    def optimize_tree(self, root: py_trees.behaviour.Behaviour) -> py_trees.behaviour.Behaviour:
        """优化行为树结构
        
        可以合并不必要的节点、调整执行顺序等。
        
        Args:
            root: 行为树根节点
        
        Returns:
            优化后的根节点
        """
        self.logger.info("优化行为树结构")
        
        # 这里可以添加优化逻辑
        # 例如：合并连续的 Sequence 节点
        # 移除无用的 Condition 节点等
        
        return root
    
    def get_tree_info(self, root: py_trees.behaviour.Behaviour) -> Dict[str, Any]:
        """获取行为树信息
        
        Args:
            root: 行为树根节点
        
        Returns:
            包含树信息的字典
        """
        info = {
            "root_name": root.name,
            "root_type": type(root).__name__,
            "total_nodes": 0,
            "node_types": {},
            "max_depth": 0
        }
        
        def count_nodes(node: py_trees.behaviour.Behaviour, depth: int = 0):
            info["total_nodes"] += 1
            info["max_depth"] = max(info["max_depth"], depth)
            
            node_type = type(node).__name__
            info["node_types"][node_type] = info["node_types"].get(node_type, 0) + 1
            
            if hasattr(node, 'children'):
                for child in node.children:
                    count_nodes(child, depth + 1)
        
        count_nodes(root)
        
        return info
