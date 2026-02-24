# 行为树系统开发文档

## 目录
1. [概述](#概述)
2. [架构设计](#架构设计)
3. [核心组件](#核心组件)
4. [节点类型](#节点类型)
5. [使用指南](#使用指南)
6. [API参考](#api参考)
7. [示例](#示例)
8. [最佳实践](#最佳实践)

## 概述

行为树系统是智能桌面系统的核心任务执行引擎，基于行为树模式实现灵活的任务规划和执行。系统使用 py_trees 库构建，支持复杂的条件逻辑和并行执行。

### 主要特性

- **模块化设计**: 各组件职责清晰，易于扩展和维护
- **灵活的任务规划**: 支持序列、选择、并行等多种执行模式
- **条件执行**: 支持基于运行时结果的动态分支
- **数据共享**: 通过 Blackboard 实现节点间的数据传递
- **可视化支持**: 提供多种可视化格式（ASCII、DOT、HTML）
- **缓存机制**: 支持行为树配置的缓存和复用

## 架构设计

### 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     BehaviorTree (Facade)                   │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              TreeBuilder                          │  │
│  │  - JSON配置解析                                   │  │
│  │  - 节点创建                                     │  │
│  │  - 树结构构建                                   │  │
│  └─────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │             TreeExecutor                          │  │
│  │  - 树执行管理                                     │  │
│  │  - 节点调度                                     │  │
│  │  - 结果收集                                     │  │
│  └─────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │         BehaviorTreeBlackboard                   │  │
│  │  - 数据存储                                       │  │
│  │  - 节点间通信                                     │  │
│  └─────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │             NodeFactory                         │  │
│  │  - 节点创建工厂                                   │  │
│  │  - 节点类型映射                                   │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 数据流

```
用户输入 → IntentParser → LLM生成行为树配置 → TreeBuilder构建树
                                                          ↓
                                              TreeExecutor执行树
                                                          ↓
                                              Blackboard存储结果
                                                          ↓
                                              返回执行结果
```

## 核心组件

### 1. BehaviorTree (Facade)

行为树的门面类，提供统一的接口。

**主要职责**:
- 统筹所有行为树组件
- 提供简洁的API
- 管理树的生命周期

**关键方法**:
```python
class BehaviorTree:
    def __init__(self):
        """初始化行为树系统"""
        
    def set_tool_executor(self, executor: Callable):
        """设置工具执行回调"""
        
    def build_from_config(self, config: Dict[str, Any]):
        """从JSON配置构建行为树"""
        
    async def execute(self) -> Dict[str, Any]:
        """执行行为树"""
        
    def visualize(self, format: str = "ascii") -> str:
        """可视化行为树"""
```

### 2. TreeBuilder

负责将JSON配置转换为py_trees对象。

**主要职责**:
- 解析JSON配置
- 创建节点实例
- 构建树结构

**配置格式**:
```json
{
  "type": "Sequence",
  "name": "任务流程",
  "children": [
    {
      "type": "Action",
      "name": "执行工具",
      "tool": "tool_name",
      "parameters": {}
    }
  ]
}
```

### 3. TreeExecutor

管理行为树的执行过程。

**主要职责**:
- 执行行为树
- 管理执行状态
- 收集执行结果

**执行流程**:
1. 初始化Blackboard
2. 设置工具执行回调
3. 执行根节点
4. 收集所有节点结果
5. 返回执行结果

### 4. BehaviorTreeBlackboard

节点间数据共享的存储系统。

**主要职责**:
- 存储节点执行结果
- 支持节点间数据引用
- 提供数据访问接口

**数据结构**:
```python
{
  "action_0": {
    "success": True,
    "result": {...}
  },
  "entities": {
    "path": "/path/to/file"
  }
}
```

### 5. NodeFactory

节点创建工厂，负责创建各种类型的节点。

**支持的节点类型**:
- Sequence: 序列节点
- Selector: 选择器节点
- Parallel: 并行节点
- Action: 动作节点
- Condition: 条件节点

### 6. TreeVisualizer

提供行为树的可视化功能。

**支持格式**:
- ASCII: 文本树形图
- DOT: Graphviz格式
- HTML: 交互式网页

### 7. TreeCache

行为树配置缓存系统。

**主要功能**:
- 缓存行为树配置
- 支持配置复用
- 提高执行效率

## 节点类型

### 1. Sequence (序列节点)

按顺序执行所有子节点，全部成功才返回成功。

**使用场景**:
- 需要按顺序执行的任务
- 后续步骤依赖前面步骤的结果

**示例**:
```json
{
  "type": "Sequence",
  "name": "文件处理流程",
  "children": [
    {
      "type": "Action",
      "name": "读取文件",
      "tool": "file_reader",
      "parameters": {"path": "/path/to/file"}
    },
    {
      "type": "Action",
      "name": "处理文件",
      "tool": "file_processor",
      "parameters": {"content": "{{action_0.result.content}}"}
    }
  ]
}
```

### 2. Selector (选择器节点)

依次执行子节点，直到有一个成功就返回成功。

**使用场景**:
- 尝试多种方法完成任务
- 提供备选方案

**示例**:
```json
{
  "type": "Selector",
  "name": "尝试多种方法",
  "children": [
    {
      "type": "Action",
      "name": "方法1",
      "tool": "method1",
      "parameters": {}
    },
    {
      "type": "Action",
      "name": "方法2",
      "tool": "method2",
      "parameters": {}
    }
  ]
}
```

### 3. Parallel (并行节点)

同时执行所有子节点。

**使用场景**:
- 独立任务并行执行
- 提高执行效率

**示例**:
```json
{
  "type": "Parallel",
  "name": "并行处理",
  "children": [
    {
      "type": "Action",
      "name": "任务1",
      "tool": "task1",
      "parameters": {}
    },
    {
      "type": "Action",
      "name": "任务2",
      "tool": "task2",
      "parameters": {}
    }
  ]
}
```

### 4. Action (动作节点)

调用MCP工具执行具体操作。

**配置参数**:
- `tool`: 工具名称（必需）
- `parameters`: 工具参数（可选）

**示例**:
```json
{
  "type": "Action",
  "name": "转换文档",
  "tool": "document_converter",
  "parameters": {
    "operation": "pdf_to_word",
    "input_path": "/path/to/file.pdf",
    "output_path": "/path/to/file.docx"
  }
}
```

### 5. Condition (条件节点)

检查条件，根据结果决定执行路径。

**条件表达式语法**:
- 比较运算: `==`, `!=`, `>`, `<`, `>=`, `<=`
- 逻辑运算: `and`, `or`, `not`
- 成员运算: `in`
- 函数调用: `len()`, `str()`, `int()`

**数据引用**:
- 前面节点结果: `action_0.success`, `action_0.result.path`
- 实体数据: `entities.path`, `entities.keyword`

**示例**:
```json
{
  "type": "Sequence",
  "name": "条件执行",
  "children": [
    {
      "type": "Action",
      "name": "检查文件",
      "tool": "file_checker",
      "parameters": {"path": "/path/to/file"}
    },
    {
      "type": "Selector",
      "name": "根据结果选择",
      "children": [
        {
          "type": "Sequence",
          "name": "文件存在时的处理",
          "children": [
            {
              "type": "Condition",
              "name": "检查文件是否存在",
              "condition": "action_0.success == true"
            },
            {
              "type": "Action",
              "name": "处理文件",
              "tool": "file_processor",
              "parameters": {"path": "{{action_0.result.path}}"}
            }
          ]
        },
        {
          "type": "Action",
          "name": "文件不存在时的处理",
          "tool": "file_creator",
          "parameters": {"path": "/path/to/file"}
        }
      ]
    }
  ]
}
```

## 使用指南

### 基本使用

```python
from mcp_client.behavior_tree import BehaviorTree

# 创建行为树实例
tree = BehaviorTree()

# 设置工具执行回调
async def tool_executor(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """执行MCP工具"""
    # 调用工具并返回结果
    return {"success": True, "result": {...}}

tree.set_tool_executor(tool_executor)

# 从JSON配置构建树
config = {
    "type": "Sequence",
    "name": "任务流程",
    "children": [...]
}
tree.build_from_config(config)

# 执行行为树
result = await tree.execute()
print(result)
```

### 与MCPClient集成

```python
class MCPClient:
    def __init__(self):
        self.behavior_tree = BehaviorTree()
        
    async def process_user_intent(self, query: str):
        # 解析意图，获取行为树配置
        intent = await self.intent_parser.parse(query, self.tools)
        
        if intent["type"] == "task":
            # 设置工具执行回调
            async def tool_executor(tool_name, parameters):
                return await self.send_tool_call(tool_name, parameters)
            
            self.behavior_tree.set_tool_executor(tool_executor)
            
            # 构建并执行行为树
            self.behavior_tree.build_from_config(intent["tree_config"])
            result = await self.behavior_tree.execute()
            
            return result
```

### 可视化行为树

```python
# ASCII格式可视化
ascii_tree = tree.visualize("ascii")
print(ascii_tree)

# DOT格式可视化（可用于Graphviz）
dot_tree = tree.visualize("dot")
with open("tree.dot", "w") as f:
    f.write(dot_tree)

# HTML格式可视化
html_tree = tree.visualize("html")
with open("tree.html", "w") as f:
    f.write(html_tree)
```

## API参考

### BehaviorTree

#### `__init__()`

初始化行为树系统。

```python
def __init__(self):
    """初始化行为树系统"""
```

#### `set_tool_executor(executor)`

设置工具执行回调函数。

```python
def set_tool_executor(self, executor: Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]]):
    """
    设置工具执行回调
    
    Args:
        executor: 工具执行回调函数
                   参数: (tool_name: str, parameters: Dict[str, Any])
                   返回: Dict[str, Any] - 工具执行结果
    """
```

#### `build_from_config(config)`

从JSON配置构建行为树。

```python
def build_from_config(self, config: Dict[str, Any]):
    """
    从JSON配置构建行为树
    
    Args:
        config: 行为树配置字典
        
    Raises:
        ValueError: 配置格式错误
    """
```

#### `execute()`

执行行为树。

```python
async def execute(self) -> Dict[str, Any]:
    """
    执行行为树
    
    Returns:
        Dict[str, Any]: 执行结果
        {
            "status": "success|failure|running",
            "results": [...],
            "error": "错误信息（如果失败）"
        }
    """
```

#### `visualize(format)`

可视化行为树。

```python
def visualize(self, format: str = "ascii") -> str:
    """
    可视化行为树
    
    Args:
        format: 可视化格式 ("ascii", "dot", "html")
        
    Returns:
        str: 可视化结果字符串
    """
```

## 示例

### 示例1: 简单的文件转换

```json
{
  "type": "Sequence",
  "name": "PDF转Word",
  "children": [
    {
      "type": "Action",
      "name": "转换文档",
      "tool": "document_converter",
      "parameters": {
        "operation": "pdf_to_word",
        "input_path": "/path/to/file.pdf",
        "output_path": "/path/to/file.docx"
      }
    }
  ]
}
```

### 示例2: 条件执行

```json
{
  "type": "Sequence",
  "name": "智能文件处理",
  "children": [
    {
      "type": "Action",
      "name": "检查文件类型",
      "tool": "file_checker",
      "parameters": {"path": "/path/to/file"}
    },
    {
      "type": "Selector",
      "name": "根据类型选择处理方式",
      "children": [
        {
          "type": "Sequence",
          "name": "PDF处理",
          "children": [
            {
              "type": "Condition",
              "name": "检查是否为PDF",
              "condition": "action_0.result.type == 'pdf'"
            },
            {
              "type": "Action",
              "name": "转换PDF",
              "tool": "pdf_converter",
              "parameters": {"path": "{{action_0.result.path}}"}
            }
          ]
        },
        {
          "type": "Sequence",
          "name": "Word处理",
          "children": [
            {
              "type": "Condition",
              "name": "检查是否为Word",
              "condition": "action_0.result.type == 'docx'"
            },
            {
              "type": "Action",
              "name": "转换Word",
              "tool": "word_converter",
              "parameters": {"path": "{{action_0.result.path}}"}
            }
          ]
        }
      ]
    }
  ]
}
```

### 示例3: 并行处理

```json
{
  "type": "Parallel",
  "name": "批量文件处理",
  "children": [
    {
      "type": "Action",
      "name": "处理文件1",
      "tool": "file_processor",
      "parameters": {"path": "/path/to/file1.pdf"}
    },
    {
      "type": "Action",
      "name": "处理文件2",
      "tool": "file_processor",
      "parameters": {"path": "/path/to/file2.pdf"}
    },
    {
      "type": "Action",
      "name": "处理文件3",
      "tool": "file_processor",
      "parameters": {"path": "/path/to/file3.pdf"}
    }
  ]
}
```

## 最佳实践

### 1. 节点命名

- 使用清晰、描述性的名称
- 名称应反映节点的功能
- 避免使用过于简短的名称

**推荐**:
```json
{
  "name": "转换PDF为Word格式"
}
```

**不推荐**:
```json
{
  "name": "转换"
}
```

### 2. 条件表达式

- 保持条件表达式简单明了
- 避免复杂的嵌套条件
- 使用有意义的变量名

**推荐**:
```json
{
  "condition": "action_0.success == true and action_0.result.size > 0"
}
```

**不推荐**:
```json
{
  "condition": "action_0.success == true and (action_0.result.size > 0 or action_0.result.type == 'pdf') and not action_0.result.error"
}
```

### 3. 参数引用

- 使用双大括号引用参数
- 确保引用的节点已执行
- 验证引用路径的正确性

**推荐**:
```json
{
  "parameters": {
    "input_path": "{{action_0.result.output_path}}"
  }
}
```

### 4. 错误处理

- 使用Selector节点提供备选方案
- 在关键节点后添加条件检查
- 记录错误信息到Blackboard

### 5. 性能优化

- 使用Parallel节点并行执行独立任务
- 缓存常用的行为树配置
- 避免不必要的条件检查

### 6. 调试技巧

- 使用可视化工具查看树结构
- 在Blackboard中记录中间结果
- 逐步执行节点进行调试

## 扩展开发

### 添加新的节点类型

1. 在 `NodeFactory` 中添加节点创建逻辑
2. 实现节点类（继承自 `py_trees.behaviour.Behaviour`）
3. 在 `TreeBuilder` 中添加配置解析逻辑

**示例**:
```python
class CustomNode(py_trees.behaviour.Behaviour):
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name)
        self.config = config
        
    def update(self):
        # 实现节点逻辑
        return py_trees.common.Status.SUCCESS
```

### 添加新的可视化格式

在 `TreeVisualizer` 中添加新的可视化方法。

**示例**:
```python
def visualize_custom(self, tree) -> str:
    """自定义可视化格式"""
    # 实现可视化逻辑
    return visualization_string
```

## 常见问题

### Q1: 如何处理节点执行失败？

A: 使用Selector节点提供备选方案，或在Condition节点中检查执行结果。

### Q2: 如何在节点间传递数据？

A: 使用Blackboard存储和访问数据，通过 `action_N.result` 引用前面节点的结果。

### Q3: 如何调试行为树？

A: 使用可视化工具查看树结构，在Blackboard中记录中间结果，逐步执行节点。

### Q4: 如何优化行为树性能？

A: 使用Parallel节点并行执行独立任务，缓存常用配置，避免不必要的条件检查。

## 总结

行为树系统提供了灵活、强大的任务执行框架。通过合理使用各种节点类型和组合方式，可以实现复杂的任务逻辑。遵循最佳实践，可以构建高效、可维护的行为树。

## 参考资料

- [py_trees官方文档](https://py-trees.readthedocs.io/)
- [行为树模式介绍](https://en.wikipedia.org/wiki/Behavior_tree)
- [MCP协议规范](https://modelcontextprotocol.io/)
