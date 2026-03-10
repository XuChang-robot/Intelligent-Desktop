import py_trees
import logging
from typing import Dict, Any, Optional, Callable
from .tree_builder import TreeBuilder
from .tree_executor import TreeExecutor
from .blackboard import BehaviorTreeBlackboard
from .nodes import NodeFactory
from user_config.config import get_config

# 内部配置缓存
_internal_config = None

def _load_internal_config() -> Dict[str, Any]:
    """加载内部执行智能配置"""
    global _internal_config
    if _internal_config is None:
        import yaml
        import os
        internal_config_path = os.path.join(os.path.dirname(__file__), 'intelligence', 'config.yaml')
        try:
            with open(internal_config_path, 'r', encoding='utf-8') as f:
                _internal_config = yaml.safe_load(f)
        except Exception as e:
            # 加载失败时使用默认配置
            _internal_config = {
                'global': {
                    'default_strategy': 'hybrid',
                    'thresholds': {
                        'auto_execute': 0.85,
                        'confirm': 0.60
                    }
                }
            }
    return _internal_config

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
        
        # 保存处理后的配置
        self._config: Optional[Dict[str, Any]] = None
    
    def set_tool_executor(self, tool_executor: Callable):
        """设置工具执行回调
        
        Args:
            tool_executor: 工具执行函数，签名: async def tool_executor(tool_name: str, args: Dict) -> Dict
        """
        self.tool_executor = tool_executor
        self.node_factory.tool_executor = tool_executor
        self.tree_executor.tool_executor = tool_executor
    
    def build_from_config(self, config: Dict[str, Any]) -> py_trees.behaviour.Behaviour:
        """从JSON配置构建行为树
        
        Args:
            config: 行为树配置字典
        
        Returns:
            行为树根节点
        """
        
        # 标准化行为树配置，确保有根节点
        normalized_config = self._normalize_behavior_tree(config)
        
        # 预处理配置，为Action节点添加intelligence_config
        processed_config = self._preprocess_config(normalized_config)
        
        # 保存处理后的配置
        self._config = processed_config
        
        self.root = self.tree_builder.build_from_config(processed_config)
        return self.root
    
    def get_config(self) -> Optional[Dict[str, Any]]:
        """获取行为树配置
        
        Returns:
            返回行为树配置
        """
        return self._config
    
    def _normalize_behavior_tree(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """标准化行为树配置，确保有根节点
        
        Args:
            config: 原始行为树配置
        
        Returns:
            标准化后的行为树配置
        """
        # 如果是单个Action节点，包装为Sequence
        if isinstance(config, dict) and config.get("type") == "Action":
            self.logger.debug("检测到单个Action节点，自动包装为Sequence根节点")
            return {
                "type": "Sequence",
                "name": "Root",
                "children": [config]
            }
        
        return config
    
    def _preprocess_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """预处理配置，为Action节点添加intelligence_config
        
        Args:
            config: 行为树配置
        
        Returns:
            处理后的配置
        """
        # 从用户配置读取工具执行模式
        user_config = get_config('execution_intelligence', {})
        tool_modes = user_config.get('tool_intelligent_mode', {})
        
        # 从内部配置读取默认值和阈值
        internal_config = _load_internal_config()
        global_config = internal_config.get('global', {})
        thresholds = global_config.get('thresholds', {})
        
        if isinstance(config, dict):
            if config.get('type') == 'Action':
                tool_name = config.get('tool', '')
                
                # 1. LLM生成的execution_mode优先级最高
                execution_mode = config.get('execution_mode')
                
                # 2. 否则，使用工具配置
                if not execution_mode:
                    execution_mode = tool_modes.get(tool_name, 'intelligent')
                
                # 3. 转换为intelligence_config
                config['intelligence_config'] = {
                    'enabled': execution_mode != 'direct',
                    'strategy': execution_mode,  # 直接使用用户配置的execution_mode作为strategy
                    'auto_execute_threshold': thresholds.get('auto_execute', 0.85),
                    'confirm_threshold': thresholds.get('confirm', 0.60)
                }
                
                self.logger.debug(f"为节点 {config.get('name')} 添加执行智能配置: {config['intelligence_config']}")
            
            # 递归处理子节点
            if 'children' in config:
                config['children'] = [
                    self._preprocess_config(child)
                    for child in config['children']
                ]
        
        return config
    
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
        from .visualizer.tree_visualizer import TreeVisualizer
        
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
    
    def build_node_schema(self, tools=None):
        """动态构建行为树节点的JSON schema
        
        Args:
            tools: MCP工具列表，用于获取工具的inputSchema
            
        Returns:
            行为树节点的JSON schema
        """
        
        # 首先创建一个带有$defs的基础schema结构
        behavior_tree_node_schema = {
            "$defs": {
                "behaviorTreeNode": {
                    "oneOf": []
                }
            }
        }
        
        # 创建所有可能的节点类型schema
        all_branches = []
        
        # Sequence节点
        sequence_schema = {
            "type": "object",
            "properties": {
                "type": {"const": "Sequence"},
                "name": {"type": "string"},
                "id": {"type": "string"},
                "children": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/behaviorTreeNode"}
                }
            },
            "required": ["type", "name", "id", "children"],
            "additionalProperties": False
        }
        
        # Selector节点
        selector_schema = {
            "type": "object",
            "properties": {
                "type": {"const": "Selector"},
                "name": {"type": "string"},
                "id": {"type": "string"},
                "children": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/behaviorTreeNode"}
                }
            },
            "required": ["type", "name", "id", "children"],
            "additionalProperties": False
        }
        
        # Parallel节点
        parallel_schema = {
            "type": "object",
            "properties": {
                "type": {"const": "Parallel"},
                "name": {"type": "string"},
                "id": {"type": "string"},
                "children": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/behaviorTreeNode"}
                }
            },
            "required": ["type", "name", "id", "children"],
            "additionalProperties": False
        }
        
        # Condition节点
        condition_schema = {
            "type": "object",
            "properties": {
                "type": {"const": "Condition"},
                "name": {"type": "string"},
                "id": {"type": "string"},
                "condition": {"type": "string"}
            },
            "required": ["type", "name", "id", "condition"],
            "additionalProperties": False
        }
        
        # Inverter装饰器节点
        inverter_schema = {
            "type": "object",
            "properties": {
                "type": {"const": "Inverter"},
                "name": {"type": "string"},
                "id": {"type": "string"},
                "child": {"$ref": "#/$defs/behaviorTreeNode"}
            },
            "required": ["type", "name", "id", "child"],
            "additionalProperties": False
        }
        
        # Timeout装饰器节点
        timeout_schema = {
            "type": "object",
            "properties": {
                "type": {"const": "Timeout"},
                "name": {"type": "string"},
                "id": {"type": "string"},
                "child": {"$ref": "#/$defs/behaviorTreeNode"},
                "duration": {"type": "number", "default": 10.0}
            },
            "required": ["type", "name", "id", "child"],
            "additionalProperties": False
        }
        
        # Repeat装饰器节点
        repeat_schema = {
            "type": "object",
            "properties": {
                "type": {"const": "Repeat"},
                "name": {"type": "string"},
                "id": {"type": "string"},
                "child": {"$ref": "#/$defs/behaviorTreeNode"},
                "num_success": {"type": "integer", "default": 1}
            },
            "required": ["type", "name", "id", "child"],
            "additionalProperties": False
        }
        
        all_branches.extend([sequence_schema, selector_schema, parallel_schema, condition_schema, inverter_schema, timeout_schema, repeat_schema])
        
        # 如果有工具信息，为每种工具创建独立的Action节点schema
        if tools:
            for tool in tools:
                if hasattr(tool, 'name'):
                    tool_name = tool.name
                    
                    # 创建工具参数schema
                    parameters_schema = {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False
                    }
                    
                    # 从工具的inputSchema获取参数
                    required_params = []
                    if hasattr(tool, 'inputSchema') and tool.inputSchema:
                        input_schema = tool.inputSchema
                        
                        # 尝试不同的方式获取properties
                        properties = None
                        defs = None
                        if isinstance(input_schema, dict):
                            if 'properties' in input_schema:
                                properties = input_schema['properties']
                            if '$defs' in input_schema:
                                defs = input_schema['$defs']
                        elif hasattr(input_schema, 'properties'):
                            properties = input_schema.properties
                            if hasattr(input_schema, '$defs'):
                                defs = getattr(input_schema, '$defs')
                        
                        # 尝试不同的方式获取required
                        if isinstance(input_schema, dict) and 'required' in input_schema:
                            required_params = input_schema['required']
                        elif hasattr(input_schema, 'required'):
                            required_params = input_schema.required
                        
                        if properties:
                            for param_name, param_info in properties.items():
                                # 尝试不同的方式获取参数类型
                                param_type = 'string'
                                param_enum = None
                                
                                # 处理字典类型的param_info
                                if isinstance(param_info, dict):
                                    # 检查是否有type
                                    if 'type' in param_info:
                                        param_type = param_info['type']
                                    # 检查是否有enum
                                    if 'enum' in param_info:
                                        param_enum = param_info['enum']
                                    # 检查是否有$ref引用
                                    elif '$ref' in param_info and defs:
                                        ref_path = param_info['$ref']
                                        # 提取$defs中的引用名称（例如从#/$defs/WeatherOperationEnum提取WeatherOperationEnum）
                                        ref_name = ref_path.split('/')[-1]
                                        if ref_name in defs:
                                            ref_def = defs[ref_name]
                                            if 'enum' in ref_def:
                                                param_enum = ref_def['enum']
                                            if 'type' in ref_def:
                                                param_type = ref_def['type']
                                # 处理其他类型的param_info
                                elif hasattr(param_info, 'get'):
                                    param_type = param_info.get('type', 'string')
                                    if 'enum' in param_info:
                                        param_enum = param_info['enum']
                                elif hasattr(param_info, 'type'):
                                    param_type = getattr(param_info, 'type', 'string')
                                    if hasattr(param_info, 'enum'):
                                        param_enum = getattr(param_info, 'enum')
                                
                                # 创建参数schema
                                if param_enum:
                                    parameters_schema["properties"][param_name] = {
                                        "type": param_type,
                                        "enum": param_enum
                                    }
                                else:
                                    parameters_schema["properties"][param_name] = {
                                        "type": param_type
                                    }
                    
                    # 添加必需参数
                    if required_params:
                        parameters_schema["required"] = required_params
                    
                    # 创建工具的Action节点schema
                    tool_action_schema = {
                        "type": "object",
                        "properties": {
                            "type": {"const": "Action"},
                            "name": {"type": "string"},
                            "id": {"type": "string"},
                            "tool": {"const": tool_name},
                            "parameters": parameters_schema
                        },
                        "required": ["type", "name", "id", "tool", "parameters"],
                        "additionalProperties": False
                    }
                    
                    all_branches.append(tool_action_schema)
        
        # 将所有分支添加到behaviorTreeNode的oneOf属性中
        behavior_tree_node_schema["$defs"]["behaviorTreeNode"]["oneOf"] = all_branches
        
        # 最终的schema应该直接引用behaviorTreeNode定义
        final_schema = {
            "$ref": "#/$defs/behaviorTreeNode",
            "$defs": behavior_tree_node_schema["$defs"]
        }
        
        self.logger.debug(f"行为树节点schema构建完成，包含{len(all_branches)}个分支")
        return final_schema
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"BehaviorTree(root={self.root.name if self.root else None})"
