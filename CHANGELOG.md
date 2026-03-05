# 更新日志

## [2026-03-05] 修复行为树条件节点与单节点bug

### 行为树系统改进

1. **条件节点评估优化（mcp_client/behavior_tree/nodes.py）**
   - 修复条件表达式求值逻辑，支持 `==` 比较失败时自动尝试 `contains` 比较
   - 添加双向包含验证（A in B 和 B in A）
   - 优化字符串处理，正确处理多行字符串和特殊字符
   - 修复变量名错误（left_str/right_str → left_value/right_value）
   - 删除重复的比较逻辑，简化代码结构

2. **单Action节点自动包装（mcp_client/behavior_tree/behavior_tree.py）**
   - 添加 `_normalize_behavior_tree` 方法，自动将单个Action节点包装为Sequence根节点
   - 在 `build_from_config` 中自动调用标准化方法
   - 解决LLM生成单个Action节点时缺少根节点的问题
   - 添加日志记录，便于调试和监控

3. **参数引用解析优化**
   - 强制使用 `.result.formatted_message` 格式解析参数引用
   - 修复 `{{节点ID}}` 格式的引用解析
   - 优化字符串转义处理，支持反斜杠、换行符、回车符、制表符等

4. **代码清理**
   - 删除 `client.py` 中冗余的Pydantic验证
   - 简化 `client.py` 中的调用逻辑，直接调用 `build_from_config`
   - 删除未使用的 `BehaviorTreeConfig` 导入

### 缓存系统改进

1. **TTL配置优化（user_config/config.yaml）**
   - 将缓存过期时间从120秒调整为604800秒（7天）
   - 提高缓存命中率，减少重复请求

2. **缓存命中更新逻辑（mcp_client/hybrid_cache.py）**
   - 修复缓存命中时只更新 `last_accessed` 的问题
   - 同时更新 `last_accessed` 和 `timestamp` 字段，延长缓存有效期

### 文件管理改进

1. **行为树JSON文件名（mcp_client/client.py）**
   - 文件名中加入时间戳（格式：`behavior_tree_YYYYMMDD_HHMMSS_hash.json`）
   - 便于区分不同时间生成的行为树配置

2. **可视化脚本优化（mcp_client/behavior_tree/visualizer/visualize_behavior_tree.py）**
   - 修改 `-f` 参数的相对路径基准为 `logs` 文件夹
   - 移除默认值，要求必须指定文件
   - 生成的可视化文件名与输入文件名保持一致

### 新增功能

1. **条件评估工具（mcp_server/tools/condition_evaluator.py）**
   - 新增条件评估工具，支持安全地评估条件表达式
   - 支持基本比较、逻辑运算、字符串操作等

2. **行为树修复模块（mcp_client/behavior_tree/tree_repair.py）**
   - 添加行为树自动修复功能
   - 通过LLM分析错误并修复配置
   - 支持最大修复尝试次数配置（默认2次）

3. **行为树可视化工具（mcp_client/behavior_tree/visualizer/）**
   - 添加DOT格式解析器
   - 支持ASCII、DOT、HTML多种可视化格式
   - 添加可视化脚本 `visualize_behavior_tree.py`

4. **工具模型生成器（mcp_client/tools/tool_model_generator.py）**
   - 动态生成工具的Pydantic模型
   - 支持参数验证和类型转换

### 配置清理

1. **删除未使用的配置（user_config/config.yaml）**
   - 删除 `type: "faiss"` 未使用的配置项

2. **修复次数可配置**
   - 行为树最大修复尝试次数可在配置文件中控制
   - 默认值为2次

### 测试文件

1. **添加测试文件（test_selector_conditions.py）**
   - 专门测试Selector节点和条件节点的测试文件
   - 查询天气并根据天气创建不同文档
   - 验证条件表达式评估逻辑

---

## [2026-02-21] 意图识别、规划、缓存性能更新

### 文档改进

1. **用户使用文档更新（docs/USER_GUIDE.md）**
   - 添加缓存配置详细说明
   - 新增缓存禁用场景说明
   - 添加缓存匹配策略说明
   - 详细说明三个缓存开关的作用和影响
   - 更新系统架构图，展示意图类型判断流程
   - 新增意图识别说明（task/chat/cannot_execute三种类型）
   - 新增任务规划说明（两层缓存匹配、缓存命中/未命中流程）

2. **缓存配置指南更新（user_config/CACHE_CONFIG_GUIDE.md）**
   - 重构文档结构，添加概述部分
   - 新增缓存配置项详细说明
   - 添加缓存禁用场景详细说明
   - 提供配置示例和使用建议

3. **用户配置说明更新（user_config/README.md）**
   - 更新缓存配置项说明
   - 添加缓存禁用场景简要说明
   - 添加缓存配置指南的引用链接

4. **缓存系统文档更新（docs/cache_system.md）**
   - 添加缓存配置项详细说明
   - 添加缓存禁用场景详细说明
   - 更新故障排除部分
   - 添加缓存匹配策略说明

5. **开发者文档更新（docs/DEVELOPER_GUIDE.md）**
   - 更新意图解析器说明（支持三种意图类型）
   - 更新任务规划器说明（支持缓存模板和完整计划生成）
   - 新增意图识别流程说明
   - 新增任务规划流程说明
   - 新增模板生成完整计划流程说明
   - 更新系统启动流程和请求处理流程

### 缓存配置说明

**新增内容**：
- **总开关（enabled）**：控制缓存系统的启用/禁用
- **哈希精确匹配（enable_hash_match）**：控制基于MD5哈希的精确匹配
- **FAISS语义匹配（enable_faiss_match）**：控制基于向量相似度的语义匹配

**禁用场景说明**：
1. **禁用FAISS语义匹配**：资源受限、精确性要求高、调试测试、Embedding模型不可用
2. **禁用哈希精确匹配**：仅依赖语义匹配、特殊测试场景、避免重复请求
3. **全局禁用缓存**：调试开发、测试新功能、缓存问题排查、存储空间不足

**缓存匹配策略**：
- 第一层：哈希精确匹配（响应速度约0.01秒）
- 第二层：FAISS语义匹配（响应速度约0.05秒）

### 意图识别和任务规划更新

**意图识别变化**：
- 支持三种意图类型：task、chat、cannot_execute
- task类型时LLM同时生成任务计划
- 自动修复桌面路径（"桌面"/"Desktop"）
- 提供工具信息给LLM辅助判断

**任务规划变化**：
- 采用两层缓存匹配（哈希精确匹配 + FAISS语义匹配）
- 缓存命中时使用模板生成完整计划
- 缓存未命中时通过LLM生成计划
- 支持entities为字典或列表格式
- 支持批量操作（num_inputs数组）
- 自动缓存成功执行的计划

**缓存策略优化**：
- 第一层：哈希精确匹配（基于MD5哈希，响应速度约0.01秒）
- 第二层：FAISS语义匹配（基于向量相似度，响应速度约0.05秒）
- 缓存命中：从缓存获取模板，根据entities生成完整计划
- 缓存未命中：通过LLM生成计划，缓存模板

### 文件变更统计

- 修改文件：5个
- 新增内容：约500行

### 主要修改文件

- `docs/USER_GUIDE.md` - 用户使用说明
- `user_config/CACHE_CONFIG_GUIDE.md` - 缓存配置指南
- `user_config/README.md` - 用户配置说明
- `docs/cache_system.md` - 缓存系统文档
- `docs/DEVELOPER_GUIDE.md` - 开发者文档

## [2026-02-20] 功能增强与修复

### 新增功能

1. **文档转换工具增强**
   - 添加批量文件转换支持，支持通配符匹配（如 `*.docx`）
   - 支持输出路径为文件夹时自动生成输出文件名
   - 修复通配符匹配时的"输入文件不存在"错误

2. **天气查询工具优化**
   - 修改预警信息显示，仅显示标题和生效时间
   - 统一术语：将"有效时间"改为"生效时间"
   - 修复未来7天预报日期显示问题（空括号问题）
   - 修复日出日落时间日期显示问题

3. **LLM思考过程显示**
   - 修改LLM generate方法返回结构，包含response和thinking
   - UI界面添加可折叠的思考过程显示
   - 思考过程使用小字体和灰色背景，默认折叠
   - 仅用于显示，不影响其他功能

### 修复问题

1. **JSON解析修复**
   - 集成fast-json-repair库修复 malformed JSON
   - 增强JSON清理和验证逻辑
   - 添加详细的日志记录用于调试

2. **混合缓存系统优化**
   - 修复实体模板提取，正确处理列表实体
   - 修复操作类型不匹配问题（缓存中的operation与实际执行不一致）
   - 增强相似度阈值比较的日志记录

3. **UI界面修复**
   - 修复聊天窗口步骤间缺少换行的问题
   - 修复重复消息显示问题
   - 添加思考过程显示支持

4. **缓存相似度问题**
   - 添加精确的日志记录来诊断浮点数精度问题
   - 改进相似度比较逻辑

### 技术改进

1. **代码结构优化**
   - 重构LLM客户端，统一返回格式
   - 改进错误处理和日志记录
   - 增强类型提示和文档

2. **工具注册优化**
   - 改进MCP服务器工具注册机制
   - 添加天气查询工具支持

3. **配置更新**
   - 更新用户配置文件
   - 添加新的模型和工具配置

### 文件变更统计

- 修改文件：18个
- 新增代码：1758行
- 删除代码：595行
- 新增目录：mcp_server/tools/query/（天气查询工具）

### 主要修改文件

- `mcp_client/llm.py` - LLM客户端核心逻辑
- `mcp_client/client.py` - MCP客户端主逻辑
- `mcp_client/task_planner.py` - 任务规划器
- `mcp_client/hybrid_cache.py` - 混合缓存系统
- `mcp_client/intent_parser.py` - 意图解析器
- `ui/pyqt_main_window.py` - 主窗口UI
- `ui/pyqt_app.py` - 应用程序主逻辑
- `mcp_server/tools/document_converter.py` - 文档转换工具
- `mcp_server/tools/query/weather_query.py` - 天气查询工具（新增）

### 待解决问题

1. **LLM思考过程显示**
   - 当前Ollama API返回结构中未找到thinking字段
   - 需要进一步研究Ollama API文档
   - 可能需要使用不同的参数或配置

2. **JSON解析返回None**
   - 即使JSON修复成功，意图解析仍返回None
   - 需要进一步调试和修复