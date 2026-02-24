import py_trees
import logging
from typing import Dict, Any, Optional, Callable
from .tree_builder import TreeBuilder
from .tree_executor import TreeExecutor
from .blackboard import BehaviorTreeBlackboard
from .nodes import NodeFactory

class BehaviorTree:
    """行为树门面类
    
    统筹所有行为树组件，提供简洁的对外接口。
    """
    
    def __init__(self, tool_executor: Optional[Callable] = None):
        """
        Args:
            tool_executor: 工具执行函数，签名: async def tool_executor(tool_name: str, args: Dict) -> Dict
        """
        self.tool_executor = tool_executor
        self.logger = logging.getLogger(__name__)
        
        # 初始化内部组件
        self.blackboard = BehaviorTreeBlackboard()
        self.node_factory = NodeFactory(tool_executor, self.blackboard)
        self.tree_builder = TreeBuilder(self.node_factory)
        self.tree_executor = TreeExecutor(tool_executor, self.blackboard)
        
        # 行为树根节点
        self.root: Optional[py_trees.behaviour.Behaviour] = None
        
        self.logger.info("行为树初始化完成")
    
    def set_tool_executor(self, tool_executor: Callable):
        """设置工具执行回调
        
        Args:
            tool_executor: 工具执行函数，签名: async def tool_executor(tool_name: str, args: Dict) -> Dict
        """
        self.tool_executor = tool_executor
        self.node_factory.tool_executor = tool_executor
        self.tree_executor.tool_executor = tool_executor
        self.logger.info("工具执行器已更新")
    
    def build_from_config(self, config: Dict[str, Any]) -> py_trees.behaviour.Behaviour:
        """从JSON配置构建行为树
        
        Args:
            config: 行为树配置字典
        
        Returns:
            行为树根节点
        """
        self.logger.info("从配置构建行为树")
        self.root = self.tree_builder.build_from_config(config)
        return self.root
    
    async def execute(self, config: Optional[Dict[str, Any]] = None, 
                   entities: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行行为树
        
        Args:
            config: 行为树配置（可选，如果未提供则使用已构建的树）
            entities: 实体信息（可选）
        
        Returns:
            执行结果字典
        """
        if config:
            self.build_from_config(config)
        
        if not self.root:
            raise RuntimeError("行为树未构建，请先调用 build_from_config()")
        
        self.blackboard.clear()
        
        self.logger.info("开始执行行为树")
        result = await self.tree_executor.execute(self.root, entities)
        return result
    
    def get_tree(self) -> Optional[py_trees.behaviour.Behaviour]:
        """获取行为树根节点
        
        Returns:
            行为树根节点，如果未构建则返回 None
        """
        return self.root
    
    def get_blackboard(self) -> BehaviorTreeBlackboard:
        """获取黑板实例
        
        Returns:
            黑板实例
        """
        return self.blackboard
    
    def get_tree_info(self) -> Optional[Dict[str, Any]]:
        """获取行为树信息
        
        Returns:
            行为树信息字典，如果未构建则返回 None
        """
        if not self.root:
            return None
        
        return self.tree_builder.get_tree_info(self.root)
    
    def visualize(self, format: str = "ascii") -> str:
        """可视化行为树
        
        Args:
            format: 可视化格式（ascii, dot, html）
        
        Returns:
            可视化字符串
        
        Raises:
            ValueError: 不支持的格式
        """
        from .tree_visualizer import TreeVisualizer
        
        if not self.root:
            raise RuntimeError("行为树未构建，无法可视化")
        
        visualizer = TreeVisualizer()
        
        if format == "ascii":
            return visualizer.render_ascii(self.root)
        elif format == "dot":
            return visualizer.render_dot(self.root)
        elif format == "html":
            return visualizer.render_html(self.root)
        else:
            raise ValueError(f"不支持的格式: {format}，支持的格式: ascii, dot, html")
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"BehaviorTree(root={self.root.name if self.root else None})"
