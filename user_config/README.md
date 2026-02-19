# 用户配置说明

本文件夹包含用户可自定义的配置文件，用户可以根据自己的需求修改这些配置。

## 配置文件说明

### config.yaml
系统主配置文件，包含MCP服务器、LLM、安全、UI、日志、邮件、缓存等配置。

#### 配置项说明

##### MCP 配置
```yaml
mcp:
  server:
    host: "localhost"           # MCP服务器地址
    port: 8001                   # MCP服务器端口
    max_connections: 10          # 最大连接数
  client:
    retry_attempts: 3            # 客户端重试次数
```

**影响**：控制MCP客户端和服务器之间的连接行为

##### LLM 配置
```yaml
llm:
  model: "qwen3:8b"             # LLM默认模型名称
  base_url: "http://localhost:11434"  # LLM服务地址
  temperature: 0.6              # 温度参数（0-1，越高越随机）
  max_tokens: 4000              # 最大生成token数
  repeat_penalty: 1.1           # 重复惩罚
  top_p: 0.9                    # 核采样参数
  top_k: 40                     # Top-K采样参数
```

**影响**：控制LLM的生成质量和性能
- `temperature`: 越高生成越有创意，越低生成越确定
- `max_tokens`: 限制生成内容的长度
- `repeat_penalty`: 防止重复生成相同内容

##### 安全配置
```yaml
security:
  enable_sandbox: true          # 是否启用沙箱
  dangerous_commands: [...]     # 危险命令列表
  allow_network: true           # 是否允许网络操作
  allow_file_system: true       # 是否允许文件系统操作
```

**影响**：控制系统的安全级别
- `enable_sandbox`: 启用沙箱可以隔离危险操作
- `dangerous_commands`: 禁止执行的危险命令
- `allow_network`: 控制是否允许网络请求
- `allow_file_system`: 控制是否允许文件系统操作

##### UI 配置
```yaml
ui:
  title: "智能桌面系统"         # 窗口标题
  width: 800                    # 窗口宽度
  height: 600                   # 窗口高度
  theme: "light"                # 主题（light/dark）
```

**影响**：控制用户界面的外观和行为

##### 日志配置
```yaml
logging:
  level: "INFO"                 # 日志级别（DEBUG/INFO/WARNING/ERROR）
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

**影响**：控制日志的详细程度和格式
- `DEBUG`: 最详细的日志，用于调试
- `INFO`: 一般信息日志
- `WARNING`: 警告信息
- `ERROR`: 错误信息

##### 邮件服务配置
```yaml
email:
  smtp:
    server: "smtp.163.com"      # SMTP服务器地址
    port: 465                   # SMTP服务器端口
  imap:
    port: 993                   # IMAP服务器端口
```

**影响**：控制邮件发送和接收的服务器设置

##### 缓存配置
```yaml
cache:
  enabled: true                  # 是否启用缓存
  type: "faiss"                 # 缓存类型
  cache_dir: "cache"            # 缓存目录
  
  ttl: 604800                   # 缓存过期时间（秒），默认一周
  max_total_size_mb: 1024       # 总大小限制（1GB）
  max_db_size_mb: 512           # SQLite数据库最大512MB
  max_faiss_size_mb: 512        # FAISS索引最大512MB
  max_records: 10000            # 最多10000条记录
  
  cleanup_interval: 3600        # 清理间隔（秒），默认1小时
  cleanup_on_startup: true     # 启动时清理过期缓存
  
  similarity_threshold: 0.85    # 相似度阈值（0-1）
  embedding_model: "nomic-embed-text"  # Embedding模型
```

**影响**：控制缓存系统的行为和性能
- `enabled`: 是否启用缓存，禁用后每次都会重新生成计划
- `ttl`: 缓存过期时间，过期后缓存会被清理
- `max_total_size_mb`: 缓存总大小限制，超过后会清理旧缓存
- `similarity_threshold`: 相似度阈值，越高匹配越严格
- `embedding_model`: 用于向量搜索的模型

### config.py
配置加载器模块，提供配置读取接口。

#### 使用方法
```python
from user_config.config import get_config, load_config

# 获取配置值
model = get_config("llm.model", "default_model")
temperature = get_config("llm.temperature", 0.7)

# 加载完整配置
config = load_config()
```

## 配置修改建议

### 性能优化
1. **提高缓存命中率**：降低`similarity_threshold`（如0.8）
2. **减少缓存大小**：降低`max_total_size_mb`和`max_records`
3. **提高LLM速度**：降低`max_tokens`和`temperature`

### 安全增强
1. **启用沙箱**：设置`enable_sandbox: true`
2. **禁止网络操作**：设置`allow_network: false`
3. **禁止文件系统操作**：设置`allow_file_system: false`

### 调试模式
1. **启用详细日志**：设置`logging.level: "DEBUG"`
2. **禁用缓存**：设置`cache.enabled: false`

## 注意事项
1. 修改配置后需要重启系统才能生效
2. 建议在修改前备份原配置文件
3. 某些配置修改可能导致系统行为异常，请谨慎修改
4. 如果不确定某个配置的作用，建议不要修改
