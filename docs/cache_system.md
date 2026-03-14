# 混合缓存系统使用说明

## 概述

混合缓存系统结合了GPTCache的语义匹配能力和文件持久化存储的优势，为智能桌面系统提供高效的任务计划缓存功能。

## 架构设计

```
用户请求
    ↓
GPTCache (语义匹配)
    ↓ 缓存命中
返回结果
    ↓ 缓存未命中
调用LLM
    ↓
GPTCache + 文件持久化 (双重存储)
    ↓
返回结果
```

## 核心特性

### 1. 三层缓存机制

- **第一层**：GPTCache语义匹配（内存缓存）
- **第二层**：文件精确匹配（磁盘缓存）
- **第三层**：文件语义匹配（磁盘缓存）

### 2. 智能匹配策略

- **精确匹配**：基于MD5哈希的精确匹配
- **语义匹配**：基于向量相似度的语义匹配
- **输入归一化**：自动处理标点、空格等细微差异

### 3. 持久化存储

- **文件存储**：所有缓存都保存到磁盘
- **重启有效**：系统重启后缓存仍然有效
- **自动过期**：支持TTL（Time To Live）自动清理

## 配置说明

在`config/config.yaml`中配置缓存系统：

```yaml
# 缓存配置
cache:
  enabled: true                  # 是否启用缓存（总开关）
  enable_hash_match: true         # 哈希精确匹配开关
  enable_faiss_match: false       # FAISS语义匹配开关
  type: "faiss"                 # 缓存类型
  cache_dir: "cache"            # 缓存目录
  ttl: 3600  # 缓存过期时间（秒）
  similarity_threshold: 0.85  # 语义相似度阈值
  
  # GPTCache配置
  gptcache:
    enabled: true
    embedding_model: "onnx"  # 使用ONNX模型生成向量
    data_manager: "map"  # 内存管理器
    
  # 文件缓存配置
  file_cache:
    enabled: true
    auto_cleanup: true  # 自动清理过期缓存
    cleanup_interval: 3600  # 清理间隔（秒）
```

### 缓存配置项说明

**总开关（enabled）**：
- `true`：启用缓存系统（推荐）
- `false`：完全禁用缓存，每次请求都会重新生成计划

**哈希精确匹配（enable_hash_match）**：
- `true`：启用哈希精确匹配（推荐）
- `false`：禁用哈希精确匹配

**FAISS语义匹配（enable_faiss_match）**：
- `true`：启用FAISS语义匹配
- `false`：禁用FAISS语义匹配（默认）

### 缓存禁用场景说明

#### 1. 何时禁用FAISS语义匹配（enable_faiss_match: false）

**推荐禁用FAISS语义匹配的场景**：

- **资源受限环境**：系统内存或CPU资源有限，FAISS向量搜索消耗较多资源
- **精确性要求高**：需要确保每次请求都精确匹配，不接受语义相似的结果
- **调试和测试**：开发调试阶段需要精确控制每次请求的行为
- **Embedding模型不可用**：Ollama embedding模型未安装或加载失败
- **缓存数据量小**：缓存记录数量很少，语义匹配意义不大

**影响**：
- 禁用后只能通过哈希精确匹配命中缓存
- 相似但表述不同的请求无法命中缓存
- 缓存命中率降低，但精确性提高
- 减少内存和CPU消耗

#### 2. 何时禁用哈希精确匹配（enable_hash_match: false）

**推荐禁用哈希精确匹配的场景**：

- **仅依赖语义匹配**：希望完全依赖FAISS语义匹配，不使用精确匹配
- **特殊测试场景**：需要测试纯语义匹配的效果
- **避免重复请求**：防止完全相同的请求命中缓存

**影响**：
- 禁用后只能通过FAISS语义匹配命中缓存
- 完全相同的请求也无法命中缓存
- 缓存命中率大幅降低
- 通常不建议单独禁用

#### 3. 何时全局禁用缓存（enabled: false）

**推荐全局禁用缓存的场景**：

- **调试和开发**：需要每次都重新生成计划以验证LLM输出
- **测试新功能**：测试新的意图识别或任务规划逻辑
- **缓存问题排查**：怀疑缓存导致错误结果时临时禁用
- **频繁变化的任务**：任务参数或内容经常变化，缓存效果差
- **存储空间不足**：磁盘空间紧张，无法存储缓存数据
- **性能测试**：需要测试无缓存情况下的系统性能

**影响**：
- 每次请求都会调用LLM生成计划
- 响应时间显著增加（从0.01秒增加到7秒以上）
- LLM API调用次数大幅增加
- 不占用磁盘空间

### 缓存匹配策略

系统采用两层匹配策略：

1. **第一层：哈希精确匹配**
   - 基于请求内容的MD5哈希
   - 完全相同的请求会立即命中
   - 响应速度最快（约0.01秒）

2. **第二层：FAISS语义匹配**
   - 基于向量相似度的语义匹配
   - 相似但表述不同的请求可以命中
   - 响应速度较快（约0.05秒）
   - 受`similarity_threshold`控制

## 使用方法

### 1. 初始化TaskPlanner

```python
from mcp_client.task_planner import TaskPlanner
from mcp_client.llm import LLMClient
from config.config import load_config

# 加载配置
config = load_config()

# 初始化LLM客户端
llm_client = LLMClient()

# 初始化任务规划器（带混合缓存）
cache_config = config.get('cache', {})
task_planner = TaskPlanner(
    llm_client=llm_client,
    cache_dir=cache_config.get('cache_dir', 'cache'),
    cache_ttl=cache_config.get('ttl', 3600),
    similarity_threshold=cache_config.get('similarity_threshold', 0.85)
)
```

### 2. 使用缓存的任务规划

```python
# 规划任务（自动使用缓存）
intent = {
    "intent": "task",
    "entities": {
        "收件人邮箱": "457911161@qq.com",
        "邮件主题": "演示",
        "邮件内容": "hello，项目地址是：https://github.com/XuChang-robot/Intelligent-Desktop.git"
    },
    "confidence": 0.9
}

plan = await task_planner.plan_task(intent)
```

### 3. 缓存管理

```python
# 获取缓存统计信息
stats = task_planner.get_cache_stats()
print(f"总文件数: {stats['total_files']}")
print(f"有效文件数: {stats['valid_files']}")
print(f"过期文件数: {stats['expired_files']}")
print(f"总大小: {stats['total_size_mb']} MB")

# 清理过期缓存
cleaned = task_planner.cleanup_expired_cache()
print(f"清理了 {cleaned} 个过期缓存文件")

# 清空所有缓存
task_planner.clear_cache()
```

## 性能对比

### 测试场景：用户多次发送相同内容的邮件

| 场景 | 不使用缓存 | 使用混合缓存 | 性能提升 |
|------|-----------|-------------|---------|
| 第一次请求 | 7.7秒 | 7.7秒 | 无（需要生成） |
| 第二次请求（精确匹配） | 7.7秒 | 0.01秒 | **770倍** |
| 第三次请求（语义相似） | 7.7秒 | 0.05秒 | **154倍** |
| 第四次请求（不同请求） | 7.7秒 | 7.7秒 | 无（需要生成） |

## 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖：
- `gptcache`：语义缓存库
- `sentence-transformers`：文本嵌入模型
- `scipy`：向量相似度计算

## 测试

运行测试脚本：

```bash
python test_hybrid_cache.py
```

测试内容包括：
1. 精确匹配测试
2. 语义相似测试
3. 不同请求测试
4. 缓存统计信息
5. 过期缓存清理

## 缓存文件格式

缓存文件存储在`cache/`目录下，文件名格式为`{md5_hash}.json`：

```json
{
  "plan": {
    "plan": "发送包含特定内容和合并PDF附件的邮件",
    "steps": [...]
  },
  "timestamp": "2026-02-12T23:00:09.123456",
  "intent": {
    "intent": "task",
    "entities": {...},
    "confidence": 0.9
  },
  "intent_str": "intent:task entities:收件人邮箱:457911161@qq.com ...",
  "tools": "none"
}
```

## 高级配置

### 调整相似度阈值

```yaml
cache:
  similarity_threshold: 0.90  # 更严格的匹配
```

- **0.80-0.85**：宽松匹配，更多缓存命中
- **0.85-0.90**：平衡匹配（推荐）
- **0.90-0.95**：严格匹配，更少误匹配

### 调整缓存过期时间

```yaml
cache:
  ttl: 7200  # 2小时
```

- **1800**：30分钟（适合频繁更新的内容）
- **3600**：1小时（推荐）
- **7200**：2小时（适合稳定的内容）
- **86400**：24小时（适合很少更新的内容）

### 禁用缓存

如果需要禁用缓存，可以设置：

```yaml
cache:
  enabled: false  # 全局禁用缓存
```

或者只禁用特定匹配方式：

```yaml
cache:
  enabled: true
  enable_hash_match: true   # 启用哈希精确匹配
  enable_faiss_match: false  # 禁用FAISS语义匹配
```

详细配置指南请参考：[缓存配置指南](../user_config/CACHE_CONFIG_GUIDE.md)

## 故障排除

### FAISS初始化失败

**问题**：日志显示"FAISS索引初始化失败"

**解决方案**：
1. 检查是否安装了`faiss`：`pip install faiss-cpu`
2. 检查缓存目录权限
3. 系统会自动创建新的FAISS索引

### 嵌入模型加载失败

**问题**：日志显示"嵌入模型加载失败"

**解决方案**：
1. 检查Ollama是否运行：`ollama list`
2. 检查embedding模型是否可用：`ollama pull nomic-embed-text`
3. 系统会自动降级到哈希精确匹配

### 缓存未命中

**问题**：缓存命中率低

**解决方案**：
1. 检查`enable_hash_match`和`enable_faiss_match`是否启用
2. 降低相似度阈值（如从0.85降到0.80）
3. 增加缓存过期时间
4. 查看日志了解缓存状态

### 缓存文件过大

**问题**：缓存目录占用过多磁盘空间

**解决方案**：
1. 定期清理过期缓存：`task_planner.cleanup_expired_cache()`
2. 减少TTL时间
3. 清空所有缓存：`task_planner.clear_cache()`
4. 调整`max_total_size_mb`和`max_records`

### FAISS语义匹配导致错误结果

**问题**：语义匹配返回了不相关的结果

**解决方案**：
1. 提高相似度阈值（如从0.85提高到0.90）
2. 禁用FAISS语义匹配：`enable_faiss_match: false`
3. 只使用哈希精确匹配：`enable_hash_match: true, enable_faiss_match: false`

## 最佳实践

1. **定期清理**：设置自动清理过期缓存
2. **监控统计**：定期查看缓存统计信息
3. **调整参数**：根据实际使用情况调整相似度阈值和TTL
4. **测试验证**：使用测试脚本验证缓存效果

## 总结

混合缓存系统为智能桌面系统提供了：

- **770倍性能提升**（精确匹配）
- **154倍性能提升**（语义相似）
- **持久化存储**（重启后仍然有效）
- **智能匹配**（理解语义，不只是文字）
- **自动管理**（过期清理、统计监控）

这是一个高效、可靠、易用的缓存解决方案！