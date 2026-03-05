# 行为树节点的Pydantic模型

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator


class BehaviorTreeNode(BaseModel):
    """行为树节点基类"""
    type: Literal['Sequence', 'Selector', 'Parallel', 'Action', 'Condition']
    name: str
    children: Optional[List['BehaviorTreeNode']] = None
    tool: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    condition: Optional[str] = None
    
    @field_validator('children')
    @classmethod
    def validate_children(cls, v, info):
        """验证子节点"""
        node_type = info.data.get('type')
        if node_type in ['Sequence', 'Selector', 'Parallel']:
            if not v or not isinstance(v, list):
                raise ValueError(f"{node_type} 节点必须包含 children 字段且为列表")
        else:
            if v:
                raise ValueError(f"{node_type} 节点不能包含 children 字段")
        return v
    
    @field_validator('tool', 'parameters')
    @classmethod
    def validate_action_fields(cls, v, info):
        """验证Action节点字段"""
        node_type = info.data.get('type')
        if node_type == 'Action':
            if info.field_name == 'tool' and not v:
                raise ValueError("Action 节点必须包含 tool 字段")
            if info.field_name == 'parameters' and v is None:
                raise ValueError("Action 节点必须包含 parameters 字段")
        else:
            if info.field_name == 'tool' and v:
                raise ValueError(f"{node_type} 节点不能包含 tool 字段")
            if info.field_name == 'parameters' and v:
                raise ValueError(f"{node_type} 节点不能包含 parameters 字段")
        return v
    
    @field_validator('condition')
    @classmethod
    def validate_condition_field(cls, v, info):
        """验证Condition节点字段"""
        node_type = info.data.get('type')
        if node_type == 'Condition':
            if not v:
                raise ValueError("Condition 节点必须包含 condition 字段")
        else:
            if v:
                raise ValueError(f"{node_type} 节点不能包含 condition 字段")
        return v


# 解决循环引用
BehaviorTreeNode.model_rebuild()


class BehaviorTreeConfig(BaseModel):
    """行为树配置模型"""
    type: Literal['Sequence', 'Selector', 'Parallel']
    name: str
    children: List[BehaviorTreeNode]
    
    @field_validator('children')
    @classmethod
    def validate_root_children(cls, v):
        """验证根节点子节点"""
        if not v or not isinstance(v, list):
            raise ValueError("根节点必须包含 children 字段且为列表")
        return v
