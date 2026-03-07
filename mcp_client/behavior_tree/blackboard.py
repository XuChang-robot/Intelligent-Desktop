import py_trees
import logging
from typing import Dict, Any, Optional

class BehaviorTreeBlackboard:
    """行为树黑板包装类
    
    包装 py_trees 官方黑板，提供简化的接口。
    """
    
    def __init__(self):
        """初始化黑板"""
        self.logger = logging.getLogger(__name__)
        self.entities: Dict[str, Any] = {}
        self.logger.info("黑板初始化完成")
    
    def set_entities(self, entities: Dict[str, Any]):
        """设置实体信息
        
        Args:
            entities: 实体信息字典
        """
        self.entities = entities
        self.logger.debug(f"设置实体信息: {entities}")
    
    def get_entities(self) -> Dict[str, Any]:
        """获取实体信息
        
        Returns:
            实体信息字典
        """
        return self.entities
    
    def set_node_result(self, node_id: str, result: Dict[str, Any]):
        """存储节点结果
        
        Args:
            node_id: 节点ID
            result: 节点结果
        """
        # 直接使用 Blackboard.storage
        py_trees.blackboard.Blackboard.storage[node_id] = result
        self.logger.debug(f"存储节点结果: {node_id} = {result}")
    
    def get_node_result(self, node_id: str) -> Optional[Dict[str, Any]]:
        """获取节点结果
        
        Args:
            node_id: 节点ID
        
        Returns:
            节点结果，如果不存在则返回 None
        """
        return py_trees.blackboard.Blackboard.storage.get(node_id)
    
    def get(self, key: str) -> Any:
        """获取黑板值
        
        Args:
            key: 键名
        
        Returns:
            对应的值
        """
        return py_trees.blackboard.Blackboard.storage.get(key)
    
    def set(self, key: str, value: Any):
        """设置黑板值
        
        Args:
            key: 键名
            value: 值
        """
        py_trees.blackboard.Blackboard.storage[key] = value
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有黑板数据
        
        Returns:
            所有黑板数据的字典
        """
        data = {"entities": self.entities}
        
        # 直接从 Blackboard.storage 获取所有数据
        for key, value in py_trees.blackboard.Blackboard.storage.items():
            data[key] = value
            self.logger.debug(f"获取黑板数据: {key}")
        
        self.logger.debug(f"黑板所有数据: {data}")
        return data
    
    def clear(self):
        """清空黑板"""
        self.entities.clear()
        py_trees.blackboard.Blackboard.storage.clear()
        self.logger.debug("黑板已清空")
