# 智能桌面系统 - 开发者文档

## 目录

- [系统概述](#系统概述)
- [快速开始](#快速开始)
- [系统架构](#系统架构)
- [核心模块](#核心模块)
- [运行逻辑](#运行逻辑)
- [API参考](#api参考)
- [配置说明](#配置说明)
- [扩展开发](#扩展开发)
- [测试指南](#测试指南)
- [部署指南](#部署指南)
- [架构设计文档](#架构设计文档)

## 系统概述

智能桌面系统是一个基于MCP（Model Context Protocol）架构的智能助手，采用模块化设计，支持多种桌面任务的自动化处理。

### 技术栈

- **后端**：Python 3.13
- **LLM**：Ollama（支持多种模型）
- **缓存**：FAISS + SQLite（混合缓存系统）
- **前端**：Vue3 + Element Plus + PyWebView
- **协议**：MCP（Model Context Protocol）

### 核心特性

- 智能意图识别
- 自动任务规划
- 执行智能系统（infer/confirm/intelligent/direct模式）
- 高效缓存系统
- 文件系统安全沙箱
- 模块化工具系统
- 行为树自动修复
- 工具专用LLM客户端

## 快速开始

### 环境要求

- Python 3.13+
- Ollama服务
- 必要的Python库（见requirements.txt）

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/XuChang-robot/Intelligent-Desktop.git
cd Intelligent-Desktop

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动Ollama服务
ollama serve

# 4. 下载模型
ollama pull qwen3:8b
ollama pull nomic-embed-text

# 5. 启动系统
python main_webview.py
```

### 项目结构

```
Intelligence_Desktop/
├── mcp_client/              # MCP客户端
│   ├── behavior_tree/       # 行为树系统
│   │   ├── behavior_tree.py    # 行为树门面类
│   │   ├── nodes.py            # 行为树节点实现
│   │   ├── tree_builder.py     # 行为树构建器
│   │   ├── tree_executor.py    # 行为树执行器
│   │   ├── tree_repair.py      # 行为树自动修复
│   │   ├── tree_cache.py       # 行为树缓存
│   │   ├── blackboard.py       # 黑板系统
│   │   ├── intelligence/       # 执行智能模块
│   │   │   ├── execution_manager.py   # 执行智能管理器
│   │   │   ├── inference_service.py   # LLM推断服务
│   │   │   ├── elicitation_service.py # Elicitation服务
│   │   │   ├── learning_system.py     # 学习系统
│   │   │   └── config.yaml            # 执行智能配置
│   │   └── visualizer/         # 行为树可视化
│   │       ├── tree_visualizer.py
│   │       └── visualize_behavior_tree.py
│   ├── intent_parser.py      # 意图解析
│   ├── hybrid_cache.py       # 混合缓存
│   ├── llm.py                # LLM客户端
│   ├── client.py             # MCP客户端主文件
│   └── elicitation.py        # Elicitation管理器
├── mcp_server/              # MCP服务器
│   └── tools/               # 工具集合
│       ├── tool_base.py          # 工具基类
│       ├── tool_llm_client.py    # 工具专用LLM客户端
│       ├── document_converter.py
│       ├── file_operations.py
│       ├── pdf_processor.py
│       ├── text_processing.py
│       ├── email_processor.py
│       ├── network_request.py
│       ├── security_sandbox.py   # 安全沙箱
│       ├── condition_evaluator.py # 条件评估器
│       └── query/                # 查询工具
│           └── weather_query.py  # 天气查询工具
├── frontend/                # Web前端（Vue3 + Vite）
│   ├── src/
│   │   ├── components/      # Vue组件
│   │   ├── composables/     # 组合式函数
│   │   └── utils/           # 工具函数
│   └── package.json
├── system_config/           # 系统配置
├── user_config/             # 用户配置
├── cache/                   # 缓存目录
└── docs/                    # 文档
```

## 系统架构

### 整体架构

```
┌─────────────────────────────────────────────────────────┐
│              用户界面（Vue3 + Element Plus）          │
│                   PyWebView 桥接层                     │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                   MCP客户端层                          │
│  ┌──────────────┬──────────────┬──────────────┬───────────┐
│  │ 意图解析器   │  任务规划器    │  混合缓存系统  │ 行为树系统  │
│  └──────────────┴──────────────┴──────────────┴───────────┘
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                   LLM层                              │
│              Ollama API Client                       │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                   MCP服务器层                          │
│  ┌──────────────┬──────────────┬──────────────┐   │
│  │ 文档转换工具   │  文件操作工具   │  PDF处理工具  │   │
│  ├──────────────┼──────────────┼──────────────┤   │
│  │ 文本处理工具   │  邮件处理工具   │  网络请求工具  │   │
│  └──────────────┴──────────────┴──────────────┘   │
└───────────────────────────────────────────────────────┘
```

### 信息流

```
用户输入
    ↓
[1] 意图解析（Intent Parser）
    - 调用LLM识别意图
    - 提取实体参数
    - 返回意图对象（包含tree_config）
    ↓
[2] 缓存查询
    - 检查缓存（哈希精确匹配 + FAISS语义匹配）
    - 缓存命中 → 使用缓存的tree_config
    - 缓存未命中 → LLM生成tree_config
    - 缓存tree_config
    ↓
[3] 行为树执行（Behavior Tree）
    - 构建行为树
    - 执行树节点
    - 调用MCP工具
    - 处理条件分支
    ↓
[4] 结果返回
    - 格式化输出
    - 显示给用户
```

## 核心模块

### 1. 意图解析器（Intent Parser）

**文件**：`mcp_client/intent_parser.py`

**功能**：
- 解析用户输入的意图类型
- 提取实体参数
- 识别操作类型
- 支持三种意图类型：task、chat、cannot_execute
- 生成行为树配置（tree_config）

**主要方法**：

```python
async def parse(self, user_input: str, tools=None) -> Dict[str, Any]:
    """
    解析用户意图（兼容旧接口）
    
    Args:
        user_input: 用户输入
        tools: 可用工具列表（从server获取）
        
    Returns:
        意图对象，包含：
        - type: 意图类型（task/chat/cannot_execute/error）
        - user_input: 用户原始输入
        - entities: 实体字典（仅task类型）
        - confidence: 置信度
        - reason: 无法执行的原因（仅cannot_execute类型）
        - tree_config: 行为树配置（仅task类型）
    """
```

**实现细节**：
- 使用LLM进行意图识别
- 支持三种意图类型判断
- task类型时LLM同时生成行为树配置
- 自动修复桌面路径（"桌面"/"Desktop"）
- 提供工具信息给LLM辅助判断

**意图类型说明**：

1. **task（任务型意图）**
   - 当前可用工具可以完成的操作
   - 用户明确要求执行某个操作
   - LLM同时生成行为树配置（tree_config）

2. **chat（聊天型意图）**
   - 当前可用工具无法完成的操作
   - 包括问候、提问、闲聊、咨询等纯对话内容
   - 不执行任何工具

3. **cannot_execute（无法执行型意图）**
   - 用户确实想调用工具执行任务，但现有工具无法完成
   - 返回无法执行的原因

### 2. 混合缓存系统（Hybrid Cache）

**文件**：`mcp_client/hybrid_cache.py`

**功能**：
- FAISS向量搜索
- SQLite元数据存储
- 智能缓存匹配
- 缓存行为树配置（tree_config）

**主要方法**：

```python
async def get(self, intent: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    查询缓存
    
    Args:
        intent: 意图对象
        
    Returns:
        缓存的tree_config，如果未命中返回None
    """

async def set(self, intent: Dict[str, Any], plan: Dict[str, Any]) -> bool:
    """
    保存缓存
    
    Args:
        intent: 意图对象
        plan: 行为树配置（tree_config）
        
    Returns:
        是否保存成功
    """
```

**实现细节**：
- 使用FAISS进行向量搜索
- 使用SQLite存储元数据
- 支持关键参数验证
- 自动清理过期缓存

### 4. 安全沙箱系统（Security Sandbox）

**文件**：`mcp_server/tools/security_sandbox.py`

**功能**：
- 文件系统操作安全边界
- 路径限制和检查
- 操作白名单管理
- 危险操作确认

**主要类**：

```python
class SecurityPolicy:
    """安全策略配置"""
    allowed_root_dirs: List[str]      # 允许的根目录
    blocked_paths: List[str]          # 禁止的路径模式
    allowed_operations: List[str]     # 允许的操作类型
    dangerous_operations: List[str]   # 危险操作类型

class SecurityChecker:
    """安全检查器"""
    def check_path(self, path: str) -> Tuple[bool, str]:
        """检查路径是否在允许范围内"""
        
    def check_operation(self, operation: str) -> Tuple[bool, str]:
        """检查操作是否允许"""
        
    def is_dangerous_operation(self, operation: str) -> bool:
        """检查是否为危险操作"""
```

**安全策略级别**：

1. **默认策略**：
   - 允许桌面、文档、下载等常用目录
   - 允许非系统盘操作
   - 禁止系统目录访问

2. **严格策略**：
   - 只允许桌面目录
   - 禁止系统盘操作
   - 只允许基本操作

3. **宽松策略**：
   - 允许所有非系统盘操作
   - 允许更多操作类型

**实现细节**：
- 路径规范化处理
- 路径遍历检测
- 符号链接检查
- 危险操作用户确认

### 5. LLM客户端（LLM Client）

**文件**：`mcp_client/llm.py`

**功能**：
- 与Ollama服务通信
- 生成文本和向量
- 管理API调用

**主要方法**：

```python
async def generate(self, prompt: str, **kwargs) -> str:
    """
    生成文本
    
    Args:
        prompt: 提示词
        **kwargs: 其他参数（temperature, max_tokens等）
        
    Returns:
        生成的文本
    """

async def get_embedding(self, text: str) -> List[float]:
    """
    获取文本的向量表示
    
    Args:
        text: 输入文本
        
    Returns:
        向量列表
    """
```

**实现细节**：
- 异步API调用
- 错误重试机制
- 性能监控

### 5. 行为树系统（Behavior Tree）

**文件**：`mcp_client/behavior_tree/`

**功能**：
- 任务执行引擎
- 支持复杂的执行逻辑
- 提供可视化支持
- 行为树缓存管理

**主要组件**：

1. **BehaviorTree**：门面类，提供统一接口
2. **TreeBuilder**：从配置构建行为树
3. **TreeExecutor**：执行行为树
4. **BehaviorTreeBlackboard**：节点间数据共享
5. **TreeVisualizer**：行为树可视化
6. **TreeCache**：行为树配置缓存

**主要方法**：

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

**实现细节**：
- 基于py_trees库构建
- 支持多种节点类型
- 提供丰富的可视化选项
- 集成缓存机制

### 6. 执行智能系统（Execution Intelligence）

**文件**：`mcp_client/behavior_tree/intelligence/`

**功能**：
- 智能处理缺失参数
- 支持四种执行策略
- LLM推断服务
- Elicitation用户交互

**执行策略**：

| 策略 | 说明 | 适用场景 |
|------|------|----------|
| **direct** | 直接执行，不启用智能 | 低风险、确定性操作 |
| **infer** | 仅推断，LLM自动填充参数 | 有充分上下文 |
| **confirm** | 仅确认，危险操作前请求用户确认 | 高风险操作 |
| **intelligent** | 混合模式，智能决策 | 大多数场景 |

**主要组件**：

1. **IntelligenceExecutionManager**：执行智能管理器，协调推断和确认
2. **LLMInferenceService**：LLM推断服务，基于上下文推断缺失参数
3. **ElicitationService**：Elicitation服务，引导用户补充信息
4. **LearningSystem**：学习系统，记录用户偏好

**配置示例**：

```yaml
execution_intelligence:
  tool_intelligent_mode:
    file_operations: "direct"
    email_processor: "confirm"
    weather_query: "infer"
    system_command: "intelligent"
  
  cost_control:
    enabled: true
    model: "qwen3:4b"
    temperature: 0.3
    max_tokens: 200
```

### 7. 工具基类（Tool Base）

**文件**：`mcp_server/tools/tool_base.py`

**功能**：
- 统一的工具接口
- 参数验证机制
- 执行智能支持
- 错误处理和重试

**主要类**：

```python
class ToolBase(ABC):
    """工具基类"""
    
    TOOL_NAME: str = ""
    OPERATION_CONFIG: Dict[str, OperationConfig] = {}
    
    @abstractmethod
    async def execute(self, ctx: Optional[Context] = None, **kwargs) -> Dict[str, Any]:
        """执行工具操作"""
        pass
    
    async def safe_execute(self, ctx: Optional[Context] = None, **kwargs) -> Dict[str, Any]:
        """安全执行，包含验证和重试"""
        pass
```

**ToolResult构建器**：

```python
result = (ToolResult.success(data)
    .with_message("操作成功")
    .with_path("/path/to/file")
    .with_extra("key", "value")
    .build())
```

### 8. 工具专用LLM客户端（Tool LLM Client）

**文件**：`mcp_server/tools/tool_llm_client.py`

**功能**：
- 为工具提供专用LLM客户端
- 支持参数推断和修正
- 成本控制（轻量级模型）

**使用场景**：
- 文件路径推断
- 参数格式修正
- 用户输入理解

**配置**：

```yaml
execution_intelligence:
  tool_llm:
    base_url: "http://localhost:11434"
  cost_control:
    model: "qwen3:4b"
    temperature: 0.3
    max_tokens: 200
```

## 运行逻辑

### 1. 系统启动流程

```python
def main():
    # 1. 加载配置
    config = load_config()
    
    # 2. 初始化LLM客户端
    llm_client = LLMClient(config)
    
    # 3. 初始化意图解析器
    intent_parser = IntentParser(llm_client)
    
    # 4. 初始化行为树系统
    behavior_tree = BehaviorTree()
    
    # 5. 初始化混合缓存系统
    cache = HybridTaskPlanCache(config)
    
    # 6. 启动MCP服务器
    mcp_server = MCPServer(config)
    mcp_server.start()
    
    # 7. 启动UI
    ui = DesktopUI(intent_parser, behavior_tree, cache, mcp_server)
    ui.run()
```

### 2. 请求处理流程

```python
async def handle_user_query(user_input: str):
    # 1. 意图解析（判断意图类型）
    intent = await intent_parser.parse(user_input, tools)
    
    # 2. 根据意图类型处理
    if intent['type'] == 'chat':
        # 聊天型意图：直接返回聊天响应
        return await handle_chat(intent)
    elif intent['type'] == 'cannot_execute':
        # 无法执行型意图：返回原因
        return intent['reason']
    elif intent['type'] == 'task':
        # 任务型意图：执行行为树
        tree_config = intent['tree_config']
        
        # 设置工具执行回调
        async def tool_executor(tool_name, parameters):
            return await execute_tool(tool_name, parameters)
        
        behavior_tree.set_tool_executor(tool_executor)
        behavior_tree.build_from_config(tree_config)
        result = await behavior_tree.execute()
        
        # 只有在行为树执行成功后才缓存
        if result.get('success', False):
            cache.set(user_input, tree_config, tools)
        
        # 返回结果
        return result
    else:
        # 错误类型
        return intent['error']
```

### 3. 意图识别流程

```python
async def parse_intent(user_input: str, tools=None):
    # 1. 调用LLM解析意图
    intent_result = await llm_client.parse_intent(user_input, tools)
    
    # 2. 检查意图类型
    if intent_result['intent'] == 'unknown':
        return {'type': 'error', 'error': '意图解析失败'}
    
    # 3. 转换为标准格式
    if intent_result['intent'] == 'chat':
        return {
            'type': 'chat',
            'user_input': user_input,
            'confidence': intent_result['confidence']
        }
    elif intent_result['intent'] == 'cannot_execute':
        return {
            'type': 'cannot_execute',
            'user_input': user_input,
            'confidence': intent_result['confidence'],
            'reason': intent_result.get('reason', '当前工具无法完成此任务')
        }
    elif intent_result['intent'] == 'task':
        return {
            'type': 'task',
            'user_input': user_input,
            'entities': intent_result.get('entities', {}),
            'confidence': intent_result['confidence'],
            'tree_config': intent_result.get('tree_config')  # LLM生成的行为树配置
        }
```

### 4. 缓存匹配流程

```python
async def get_cached_tree_config(query: str, tools):
    # 1. 查询缓存（哈希精确匹配 + FAISS语义匹配）
    cache_result = cache.get(query, tools)
    
    # 2. 检查缓存是否命中
    if cache_result and cache_result.get("from_cache"):
        tree_config = cache_result.get("tree_config")
        match_type = cache_result.get("match_type")
        similarity = cache_result.get("similarity")
        
        return {
            'tree_config': tree_config,
            'from_cache': True,
            'match_type': match_type,
            'similarity': similarity
        }
    
    # 3. 缓存未命中
    return None
```

### 5. 行为树执行流程

```python
async def execute_behavior_tree(tree_config: Dict[str, Any]):
    # 1. 设置工具执行回调
    async def tool_executor(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行MCP工具的回调函数"""
        result = await send_tool_call(tool_name, parameters)
        return result
    
    behavior_tree.set_tool_executor(tool_executor)
    
    # 2. 从配置构建行为树
    behavior_tree.build_from_config(tree_config)
    
    # 3. 执行行为树
    execution_result = await behavior_tree.execute()
    
    # 4. 检查执行结果
    if execution_result.get("success", False):
        # 执行成功，缓存tree_config
        return {
            'success': True,
            'execution_result': execution_result,
            'should_cache': True
        }
    else:
        # 执行失败，不缓存
        return {
            'success': False,
            'error': execution_result.get("error", "未知错误"),
            'should_cache': False
        }
```

### 6. 执行智能流程

```python
async def execute_with_intelligence(node, context: Dict[str, Any]):
    """执行智能步骤"""
    # 1. 检查参数完整性
    missing_params = check_missing_params(node, context)
    
    if not missing_params:
        # 无缺失参数，直接执行
        return await execute_tool(node.tool_name, node.parameters)
    
    # 2. 根据策略执行
    strategy = node.intelligence_config.get('strategy', 'direct')
    
    if strategy == 'infer':
        # 纯推断模式：LLM推断缺失参数
        inference_result = await llm_inference_service.infer(
            node_type=type(node).__name__,
            tool_name=node.tool_name,
            missing_params=missing_params,
            context=context
        )
        # 使用推断的参数执行
        parameters = {**node.parameters, **inference_result.inferred_params}
        return await execute_tool(node.tool_name, parameters)
    
    elif strategy == 'confirm':
        # 纯确认模式：请求用户确认
        elicitation_request = create_elicitation_request(
            node_id=node.node_id,
            missing_params=missing_params
        )
        user_response = await elicitation_service.elicit(
            elicitation_request,
            user_callback
        )
        if user_response.action == 'confirm':
            parameters = {**node.parameters, **user_response.user_input}
            return await execute_tool(node.tool_name, parameters)
        else:
            return {'success': False, 'error': '用户取消操作'}
    
    elif strategy == 'intelligent':
        # 混合模式：先推断，根据置信度决定是否确认
        inference_result = await llm_inference_service.infer(...)
        
        if inference_result.confidence >= auto_execute_threshold:
            # 高置信度，自动执行
            parameters = {**node.parameters, **inference_result.inferred_params}
            return await execute_tool(node.tool_name, parameters)
        elif inference_result.confidence >= confirm_threshold:
            # 中等置信度，请求用户确认
            elicitation_request = create_confirmation_request(
                inferred_params=inference_result.inferred_params,
                confidence=inference_result.confidence
            )
            user_response = await elicitation_service.elicit(...)
            # ...
        else:
            # 低置信度，请求用户输入
            elicitation_request = create_parameter_elicitation(...)
            user_response = await elicitation_service.elicit(...)
            # ...
```

### 7. 行为树自动修复流程

```python
async def repair_behavior_tree(tree_config: Dict[str, Any], execution_result: Dict[str, Any]):
    """自动修复行为树配置"""
    # 1. 检查是否需要修复
    if execution_result.get("success", False):
        return None  # 执行成功，无需修复
    
    # 2. 分析错误
    error = execution_result.get("error", "")
    error_node = execution_result.get("error_node", "")
    
    # 3. 调用LLM分析并修复
    repair_prompt = f"""
    行为树执行失败，请分析错误并修复配置：
    
    原始配置：
    {json.dumps(tree_config, indent=2, ensure_ascii=False)}
    
    错误信息：{error}
    错误节点：{error_node}
    
    请输出修复后的行为树配置（JSON格式）。
    """
    
    repaired_config = await llm_client.generate(repair_prompt)
    
    # 4. 验证修复后的配置
    try:
        parsed_config = json.loads(repaired_config)
        return parsed_config
    except json.JSONDecodeError:
        return None  # 修复失败
```

## API参考

### MCP工具API

所有MCP工具都遵循以下接口：

```python
@mcp.tool()
async def tool_name(
    operation: str,
    param1: type,
    param2: type,
    ...
) -> Dict[str, Any]:
    """
    工具描述
    
    Args:
        operation: 操作类型
        param1: 参数1描述
        param2: 参数2描述
        
    Returns:
        {
            "success": True/False,
            "result": 操作结果,
            "error": 错误信息（如果失败）
        }
    """
```

### 文档转换工具

**文件**：`mcp_server/tools/document_converter.py`

**操作类型**：
- `pdf_to_word`: PDF转Word
- `word_to_pdf`: Word转PDF

**参数**：
- `operation`: 操作类型
- `input_path`: 输入文件路径
- `output_path`: 输出文件路径

**示例**：

```python
result = await document_converter(
    operation="pdf_to_word",
    input_path="桌面/xxx.pdf",
    output_path="桌面/xxx.docx"
)
```

### 文件操作工具

**文件**：`mcp_server/tools/file_operations.py`

**操作类型**：
- `create`: 创建文件/文件夹
- `read`: 读取文件内容
- `write`: 写入文件内容
- `delete`: 删除文件/文件夹
- `move`: 移动文件/文件夹
- `copy`: 复制文件/文件夹
- `list`: 列出目录内容
- `search`: 搜索文件

**参数**：
- `operation`: 操作类型
- `path`: 文件/文件夹路径
- `content`: 文件内容（用于write操作）
- `pattern`: 搜索模式（用于search操作）

**示例**：

```python
result = await file_operations(
    operation="create",
    path="桌面/test.txt",
    content="hello world"
)
```

### PDF处理工具

**文件**：`mcp_server/tools/pdf_processor.py`

**操作类型**：
- `merge`: PDF合并
- `insert`: PDF插入页
- `print`: PDF打印
- `extract`: PDF提取页
- `split`: PDF拆分

**参数**：
- `operation`: 操作类型
- `input_path`: 输入文件路径
- `output_path`: 输出文件路径
- `insert_position`: 插入位置（仅用于insert操作）
- `pages`: 页面范围（仅用于extract和split操作）

**示例**：

```python
result = await pdf_processor(
    operation="merge",
    input_path="桌面/file1.pdf;桌面/file2.pdf",
    output_path="桌面/merged.pdf"
)
```

### 文本处理工具

**文件**：`mcp_server/tools/text_processing.py`

**操作类型**：
- `to_audio`: 文字转语音
- `summarize`: 文本摘要
- `format`: 文本格式化
- `count`: 统计字符数

**参数**：
- `operation`: 操作类型
- `text`: 输入文本
- `input_file`: 输入文件路径（可选）
- `lang`: 语言代码（用于to_audio）
- `format_type`: 格式化类型（用于format）
- `output_path`: 输出文件路径（用于to_audio）

**示例**：

```python
result = await text_processing(
    operation="to_audio",
    text="hello world",
    output_path="桌面/audio.mp3"
)
```

### 邮件处理工具

**文件**：`mcp_server/tools/email_processor.py`

**操作类型**：
- `send`: 发送邮件
- `receive`: 接收邮件

**参数**：
- `operation`: 操作类型
- `recipient`: 收件人邮箱地址（用于send）
- `sender`: 发件人邮箱地址（用于receive）
- `subject`: 邮件主题（用于send）
- `body`: 邮件正文（用于send）
- `attachments`: 附件路径（用于send）

**示例**：

```python
result = await email_processor(
    operation="send",
    recipient="test@example.com",
    subject="测试",
    body="hello"
)
```

### 网络请求工具

**文件**：`mcp_server/tools/network_request.py`

**操作类型**：
- `GET`: 获取数据
- `POST`: 提交数据
- `PUT`: 更新数据
- `DELETE`: 删除数据

**参数**：
- `operation`: 操作类型
- `url`: 请求URL
- `data`: 请求体数据（用于POST、PUT等）
- `headers`: 请求头
- `params`: URL参数

**示例**：

```python
result = await network_request(
    operation="GET",
    url="https://api.example.com/data"
)
```

## 配置说明

### 配置文件结构

```
Intelligence_Desktop/
├── system_config/           # 系统配置（用户不应该修改）
│   ├── cache_config.json    # 缓存关键参数配置
│   └── README.md          # 系统配置说明
├── user_config/            # 用户配置
│   ├── config.yaml         # 用户配置文件
│   ├── config.py          # 配置加载器
│   ├── README.md          # 用户配置说明
│   └── CACHE_CONFIG_GUIDE.md  # 缓存配置指南
```

### 缓存配置

**文件**：`system_config/cache_config.json`

```json
{
  "cache_key_params": {
    "global": ["operation"],
    "tools": {
      "document_converter": ["operation"],
      "file_operations": ["operation"],
      "pdf_processor": ["operation"],
      "text_processing": ["operation"],
      "email_processor": ["operation"],
      "network_request": ["operation"]
    }
  }
}
```

**说明**：
- `global`: 全局关键参数列表
- `tools`: 各工具特定的关键参数列表

**作用**：
- 区分不同的操作类型
- 确保缓存匹配的准确性
- 避免错误的缓存命中

### 用户配置

**文件**：`user_config/config.yaml`

详细配置说明请参考：[用户配置说明](../user_config/README.md)

## 扩展开发

### 添加新工具

1. **创建工具文件**

在`mcp_server/tools/`下创建新文件：

```python
# my_tool.py
from typing import Dict, Any
from mcp.server.fastmcp import Context

def register_my_tool(mcp):
    """注册自定义工具到MCP服务器"""
    
    @mcp.tool()
    async def my_tool(
        operation: str,
        param1: str,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """自定义工具
        
        Args:
            operation: 操作类型
            param1: 参数1描述
            ctx: FastMCP上下文，用于elicitation（可选）
            
        Returns:
            {
                "success": True/False,
                "result": 操作结果,
                "error": 错误信息（如果失败）
            }
        """
        try:
            # 实现工具逻辑
            result = do_something(operation, param1)
            
            return {
                "success": True,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
```

2. **注册工具**

在`mcp_server/server.py`中注册：

```python
from mcp_server.tools.my_tool import register_my_tool

def create_mcp_server():
    mcp = FastMCP("intelligent-desktop")
    
    # 注册工具
    register_my_tool(mcp)
    
    return mcp
```

3. **更新配置**

在`system_config/cache_config.json`中添加关键参数：

```json
{
  "cache_key_params": {
    "global": ["operation"],
    "tools": {
      "my_tool": ["operation"]
    }
  }
}
```

4. **更新LLM提示词**

在`mcp_client/llm.py`中更新工具描述：

```python
tools_info = """
...
my_tool:
  operation: 操作类型
  param1: 参数1描述
...
"""
```

### 添加新操作类型

1. **定义操作类型**

在工具文件中定义新的操作类型：

```python
@mcp.tool()
async def my_tool(
    operation: str,
    ...
) -> Dict[str, Any]:
    """自定义工具
    
    Args:
        operation: 操作类型，可选值：
            - "op1": 操作1描述
            - "op2": 操作2描述
        ...
    """
```

2. **更新配置**

在`system_config/cache_config.json`中添加关键参数：

```json
{
  "cache_key_params": {
    "tools": {
      "my_tool": ["operation"]
    }
  }
}
```

## 测试指南

### 单元测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_intent_parser.py

# 查看测试覆盖率
pytest --cov=mcp_client tests/
```

### 集成测试

```bash
# 测试缓存系统
python test_cache_hit_complete.py

# 测试不同操作
python test_different_operations.py

# 测试意图解析
python test_intent_parsing.py
```

### 性能测试

```bash
# 测试缓存性能
python test_cache_performance.py

# 测试LLM性能
python test_llm_performance.py
```

## 部署指南

### 本地部署

```bash
# 1. 克隆仓库
git clone https://github.com/XuChang-robot/Intelligent-Desktop.git
cd Intelligent-Desktop

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置系统
cp user_config/config.example.yaml user_config/config.yaml
# 编辑config.yaml

# 4. 启动Ollama服务
ollama serve

# 5. 下载模型
ollama pull qwen3:8b
ollama pull nomic-embed-text

# 6. 启动系统
python main.py
```

### Docker部署

```bash
# 1. 构建镜像
docker build -t intelligent-desktop .

# 2. 运行容器
docker run -d \
  -p 8001:8001 \
  -v $(pwd)/user_config:/app/user_config \
  -v $(pwd)/cache:/app/cache \
  intelligent-desktop
```

### 生产环境部署

1. **配置优化**
   - 调整缓存大小
   - 优化LLM参数
   - 配置日志级别

2. **监控**
   - 监控系统性能
   - 监控缓存命中率
   - 监控错误日志

3. **备份**
   - 定期备份配置
   - 定期备份缓存
   - 定期备份日志

## 架构设计文档

- [LLM生成行为树架构的优势](./LLM生成行为树架构的优势.md) - 详细阐述系统核心架构的设计理念、优势分析、最佳实践和技术实现

## 相关文档

- [用户使用说明](./USER_GUIDE.md)
- [系统配置说明](../system_config/README.md)
- [用户配置说明](../user_config/README.md)
- [缓存配置指南](../user_config/CACHE_CONFIG_GUIDE.md)
- [混合缓存系统说明](./cache_system.md)
