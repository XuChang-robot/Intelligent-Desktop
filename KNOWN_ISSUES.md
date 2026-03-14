# 已知问题

## 1. Elicitation 取消操作响应速度慢

### 问题描述
当用户在 elicitation 确认对话框中点击取消按钮时，系统响应速度较慢，需要等待较长时间才能完成取消操作。而点击确认按钮时，系统能够秒响应。

### 根本原因分析

经过深入代码分析，发现问题主要出在**行为树执行机制**上：

#### 1.1 行为树执行流程

**TreeExecutor.execute 方法**（`mcp_client/behavior_tree/tree_executor.py`）:
```python
async def execute(self, root: py_trees.behaviour.Behaviour, 
               entities: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    # ...
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
```

**问题所在**：
- 行为树使用 `while` 循环持续执行 `tick_once()`
- 每次 tick 后会检查异步任务并等待 `asyncio.gather(*async_tasks)`
- **没有中断机制**：一旦开始执行，就无法在 tick 之间中断

#### 1.2 MCPActionNode 执行机制

**MCPActionNode.update 方法**（`mcp_client/behavior_tree/nodes.py`）:
```python
def update(self):
    # 如果有异步任务在运行，返回 RUNNING
    if self.async_task is not None and not self.async_task.done():
        return py_trees.common.Status.RUNNING
    
    # 首次执行
    result = self.tool_executor(tool_name, final_params)
    
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
```

**问题所在**：
- 工具调用创建异步任务后，节点返回 `RUNNING` 状态
- 行为树会继续 tick，等待异步任务完成
- **没有取消机制**：异步任务一旦创建，就无法取消

#### 1.3 执行智能管理器

**IntelligenceExecutionManager.execute_intelligent_step 方法**（`mcp_client/behavior_tree/intelligence/execution_manager.py`）:
```python
async def execute_intelligent_step(
    self,
    node,
    context: Dict[str, Any]
) -> IntelligenceExecutionResult:
    # 1. 检查参数完整性
    missing_params = self._check_missing_params(node, context)
    
    if not missing_params:
        # 无缺失参数，直接执行
        return IntelligenceExecutionResult(...)
    
    # 2. 根据策略执行
    if self.strategy == ExecutionStrategy.INFER:
        result = await self._execute_inference_only(...)
    elif self.strategy == ExecutionStrategy.INTELLIGENT:
        result = await self._execute_hybrid(...)
```

**问题所在**：
- 执行智能步骤是异步的，需要等待 LLM 推断
- **没有中断检查**：在推断过程中没有检查是否应该取消

### 具体原因总结

1. **行为树执行循环无法中断**：
   - `TreeExecutor.execute` 使用 `while` 循环持续执行
   - 没有提供中断机制来停止执行

2. **异步任务无法取消**：
   - `MCPActionNode` 创建异步任务后，任务会一直运行到完成
   - 即使取消了操作，异步任务仍在后台运行

3. **工具调用阻塞**：
   - 工具调用（如发送邮件）可能涉及网络请求
   - 网络请求有超时时间（如 30 秒）
   - 在超时前，操作无法被取消

4. **缺少取消检查点**：
   - 在行为树执行的关键路径上没有检查取消状态
   - 无法及时响应取消请求

### 影响范围
- 所有使用行为树执行的工具
- 特别是涉及异步操作的工具（如发送邮件、天气查询等）
- 执行智能模式下的参数推断

### 优化建议

#### 1. 添加中断机制
在 `TreeExecutor.execute` 中添加中断检查：
```python
async def execute(self, root: py_trees.behaviour.Behaviour, 
               entities: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    # ...
    while root.status not in [py_trees.common.Status.SUCCESS, py_trees.common.Status.FAILURE]:
        # 检查是否被取消
        if self._is_cancelled():
            self.logger.info("行为树执行被取消")
            return {"success": False, "status": "CANCELLED", "error": "用户取消执行"}
        
        # 执行一次 tick
        root.tick_once()
        # ...
```

#### 2. 支持异步任务取消
在 `MCPActionNode` 中添加任务取消支持：
```python
def cancel(self):
    """取消节点执行"""
    if self.async_task and not self.async_task.done():
        self.async_task.cancel()
        self.logger.info(f"节点 {self.name} 的异步任务已取消")
```

#### 3. 在工具调用中添加取消检查
在工具执行过程中定期检查取消状态：
```python
async def _execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    # 检查是否被取消
    if self._is_cancelled():
        return {"success": False, "error": "用户取消执行"}
    
    result = self.tool_executor(tool_name, final_params)
    # ...
```

#### 4. 使用超时机制
为工具调用设置合理的超时时间：
```python
result = await asyncio.wait_for(
    self.tool_executor(tool_name, final_params),
    timeout=10.0  # 设置较短的超时时间
)
```

#### 5. 立即响应取消请求
当用户点击取消时，立即返回取消结果，不等待行为树执行完成：
```python
async def confirm_elicitation(self, message: str, content: any, confirmed: bool) -> Dict[str, Any]:
    if not confirmed:
        # 立即返回取消结果
        return {"success": True, "cancelled": True, "message": "用户取消执行"}
    # ...
```

## 2. Elicitation 通信机制

### 完整流程

#### 2.1 Elicitation 请求发起
1. **后端触发**：当 MCP Server 需要用户确认时，会发送 `elicit` 消息
2. **客户端处理**：`SessionManager.handle_elicitation` 方法接收到请求
3. **回调触发**：调用 `elicitation_callback`（即 `MCPWorker._elicitation_callback`）
4. **前端通知**：通过 `_emit_event` 发送 `elicitation_request` 事件到前端
5. **前端显示**：前端显示确认对话框，等待用户操作

#### 2.2 用户操作处理

##### 2.2.1 用户点击确认
1. **前端处理**：调用 `handleElicitationResponse(true)`
2. **发送请求**：调用 `window.pywebview.api.confirm_elicitation` 发送确认请求到后端
3. **后端主线程处理**：
   - `confirm_elicitation` 方法立即处理确认请求
   - 设置 `elicitation_future` 的结果为 `{"action": "accept", "content": content}`
   - 重置 `elicitation_future` 为 None
   - 立即返回 `{"success": True}`
4. **工作线程处理**：
   - 从 `await asyncio.wait_for(self.elicitation_future, timeout=60.0)` 中恢复
   - 收到用户响应 `{"action": "accept", "content": content}`
   - 继续执行工具调用
   - 后端 Server 执行工具操作
   - 返回执行结果
5. **前端显示**：显示 "✅ 用户确认：允许执行" 消息

##### 2.2.2 用户点击取消
1. **前端处理**：调用 `handleElicitationResponse(false)`
2. **发送请求**：调用 `window.pywebview.api.confirm_elicitation` 发送取消请求到后端
3. **后端主线程处理**：
   - `confirm_elicitation` 方法立即处理取消请求
   - 设置 `elicitation_future` 的结果为 `{"action": "decline", "content": content}`
   - 重置 `elicitation_future` 为 None
   - 立即返回 `{"success": True}`
4. **工作线程处理**：
   - 从 `await asyncio.wait_for(self.elicitation_future, timeout=60.0)` 中恢复
   - 收到用户响应 `{"action": "decline", "content": content}`
   - **问题**：行为树已经在执行中，无法立即停止
   - 需要等待当前 tick 完成
   - 如果正在执行异步任务，需要等待任务完成或超时
   - 返回取消结果
5. **前端显示**：显示 "❌ 用户取消：拒绝执行" 消息（但可能有延迟）

### 关键代码位置

#### 客户端代码
- **mcp_client/behavior_tree/tree_executor.py**：`TreeExecutor.execute` 方法，行为树执行主循环
- **mcp_client/behavior_tree/nodes.py**：`MCPActionNode.update` 方法，节点执行逻辑
- **mcp_client/behavior_tree/intelligence/execution_manager.py**：`IntelligenceExecutionManager.execute_intelligent_step` 方法，执行智能逻辑
- **mcp_client/client.py**：`SessionManager.handle_elicitation` 方法处理服务器发送的 elicit 消息
- **main_webview.py**：`MCPWorker._elicitation_callback` 方法触发前端确认对话框
- **main_webview.py**：`confirm_elicitation` 方法处理用户的确认和取消操作

#### 前端代码
- **frontend/src/composables/useChat.ts**：`handleElicitationRequest` 方法处理后端发送的 elicitation 请求
- **frontend/src/composables/useChat.ts**：`handleElicitationResponse` 方法处理用户的确认和取消操作

#### 后端代码
- **mcp_server/tools/tool_base.py**：`_trigger_elicitation` 方法触发用户确认
- **mcp_server/tools/email_processor.py**：发送邮件工具的确认机制示例

### 通信流程图

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    前端     │     │   客户端    │     │  MCP Server │     │    工具     │
└─────┬──────┘     └─────┬──────┘     └─────┬──────┘     └─────┬──────┘
      │                  │                  │                  │
      │                  │                  │  需要用户确认     │
      │                  │                  │─────────────────>│
      │                  │                  │                  │
      │                  │  触发elicitation  │                  │
      │                  │<─────────────────│                  │
      │                  │                  │                  │
      │  显示确认对话框  │                  │                  │
      │<─────────────────│                  │                  │
      │                  │                  │                  │
      │  用户点击取消    │                  │                  │
      │─────────────────>│                  │                  │
      │                  │                  │                  │
      │                  │  处理取消请求    │                  │
      │                  │─────────────────>│                  │
      │                  │                  │                  │
      │                  │                  │  通知工具取消    │
      │                  │                  │─────────────────>│
      │                  │                  │                  │
      │                  │                  │  [问题] 行为树   │
      │                  │                  │  无法立即停止    │
      │                  │                  │                  │
      │                  │                  │  等待当前执行完成 │
      │                  │                  │<─────────────────│
      │                  │                  │                  │
      │                  │  返回取消结果    │                  │
      │                  │<─────────────────│                  │
      │                  │                  │                  │
      │  显示取消消息    │                  │                  │
      │<─────────────────│                  │                  │
┌─────┴──────┐     ┌─────┴──────┐     ┌─────┴──────┐     ┌─────┴──────┐
│    前端     │     │   客户端    │     │  MCP Server │     │    工具     │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

### 问题总结

**核心问题**：行为树执行机制缺乏中断支持

1. **行为树执行循环**：`TreeExecutor.execute` 使用 `while` 循环持续执行，没有提供中断机制
2. **异步任务管理**：`MCPActionNode` 创建异步任务后，任务会一直运行到完成，无法取消
3. **工具调用阻塞**：工具调用可能涉及网络请求，在超时前无法取消
4. **缺少取消检查点**：在行为树执行的关键路径上没有检查取消状态

**解决方案**：
1. 在行为树执行循环中添加中断检查
2. 支持异步任务取消
3. 在工具调用中添加取消检查
4. 使用超时机制
5. 立即响应取消请求，不等待行为树执行完成
