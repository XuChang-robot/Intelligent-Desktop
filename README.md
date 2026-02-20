# 智能桌面系统

基于MCP（Model Context Protocol）架构的智能桌面助手，支持文档转换、文件操作、邮件处理、网络请求等多种桌面任务的自动化处理。

## ✨ 特性

- 🧠 **智能意图识别**：自动理解用户需求
- 📋 **任务规划**：自动生成执行计划
- 🚀 **高效缓存**：基于FAISS向量搜索的混合缓存系统
- 🔒 **安全可靠**：沙箱隔离、权限控制
- 🧩 **易于扩展**：模块化设计，支持自定义工具
- ☁️ **天气查询**：实时天气信息查询和预警通知
- 📄 **批量文档处理**：支持批量文件转换和通配符匹配
- 💭 **LLM思考过程**：可折叠的思考过程显示

## 🚀 快速开始

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
python main.py
```

## 📚 文档

完整的文档请查看 [docs/README.md](docs/README.md)

### 用户文档

- 📖 [用户使用说明](docs/USER_GUIDE.md) - 系统使用指南、功能说明、配置指南
- 📝 [用户配置说明](user_config/README.md) - 用户配置文件说明
- 💾 [缓存配置指南](user_config/CACHE_CONFIG_GUIDE.md) - 缓存系统配置指南

### 开发者文档

- 🛠️ [开发者文档](docs/DEVELOPER_GUIDE.md) - 系统架构、API参考、扩展开发
- ⚙️ [系统配置说明](system_config/README.md) - 系统配置文件说明
- 🚀 [混合缓存系统说明](docs/cache_system.md) - 缓存系统工作原理

## 🎯 主要功能

### 文档转换
- PDF转Word
- Word转PDF
- 支持指定输出路径
- **支持批量转换**：使用通配符匹配多个文件

### 文件操作
- 创建、读取、写入、删除文件
- 移动、复制文件
- 列出目录、搜索文件

### PDF处理
- PDF合并
- PDF插入页
- PDF打印
- PDF提取页
- PDF拆分

### 文本处理
- 文字转语音
- 文本摘要
- 文本格式化
- 统计字符数

### 邮件处理
- 发送邮件
- 接收邮件

### 网络请求
- GET、POST、PUT、DELETE请求
- 支持自定义请求头和参数

### 天气查询
- **实时天气**：查询指定城市的当前天气
- **预警信息**：显示天气预警标题和生效时间
- **日期显示**：修复天气查询结果中的日期显示问题

## 📁 项目结构

```
Intelligence_Desktop/
├── mcp_client/              # MCP客户端
│   ├── intent_parser.py      # 意图解析
│   ├── task_planner.py      # 任务规划
│   ├── hybrid_cache.py      # 混合缓存
│   └── llm.py            # LLM客户端
├── mcp_server/            # MCP服务器
│   └── tools/            # 工具集合
│       ├── document_converter.py
│       ├── file_operations.py
│       ├── pdf_processor.py
│       ├── text_processing.py
│       ├── email_processor.py
│       ├── network_request.py
│       └── query/          # 查询工具
│           └── weather_query.py  # 天气查询工具
├── system_config/         # 系统配置（用户不应该修改）
├── user_config/           # 用户配置
├── cache/                # 缓存目录
├── docs/                 # 文档
└── main.py              # 主程序
```

## ⚙️ 配置

### 用户配置

用户配置文件位于 `user_config/config.yaml`，包含以下配置项：

- **MCP配置**：服务器地址、端口、连接数
- **LLM配置**：模型名称、API地址、温度参数
- **安全配置**：沙箱、危险命令、权限控制
- **UI配置**：窗口标题、大小、主题
- **日志配置**：日志级别、格式
- **邮件配置**：SMTP/IMAP服务器
- **缓存配置**：启用状态、大小限制、相似度阈值

详细配置说明请参考：[用户配置说明](user_config/README.md)

### 系统配置

系统配置文件位于 `system_config/cache_config.json`，包含缓存关键参数配置。

**注意**：系统配置由系统维护，用户不应该修改。

详细配置说明请参考：[系统配置说明](system_config/README.md)

## 🔧 开发

### 添加新工具

1. 在 `mcp_server/tools/` 下创建新工具文件
2. 实现工具接口
3. 在 `mcp_server/server.py` 中注册工具
4. 更新配置文件
5. 更新LLM提示词

详细开发指南请参考：[开发者文档](docs/DEVELOPER_GUIDE.md)

### 测试

```bash
# 运行所有测试
pytest tests/

# 测试缓存系统
python test_cache_hit_complete.py

# 测试不同操作
python test_different_operations.py
```

## 📊 性能

混合缓存系统提供了显著的性能提升：

| 场景 | 不使用缓存 | 使用缓存 | 性能提升 |
|------|-----------|---------|---------|
| 精确匹配 | 7.7秒 | 0.01秒 | **770倍** |
| 语义相似 | 7.7秒 | 0.05秒 | **154倍** |

详细性能分析请参考：[混合缓存系统说明](docs/cache_system.md)

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 📞 联系方式

- 项目主页：[https://github.com/XuChang-robot/Intelligent-Desktop](https://github.com/XuChang-robot/Intelligent-Desktop)
- 问题反馈：[https://github.com/XuChang-robot/Intelligent-Desktop/issues](https://github.com/XuChang-robot/Intelligent-Desktop/issues)

## 📝 更新日志

### 2026-02-21

#### 新增功能
- ✨ 天气查询工具：实时天气信息和预警通知
- ✨ 批量文档处理：支持通配符匹配和批量文件转换
- ✨ LLM思考过程显示：可折叠的思考过程

#### 修复问题
- 🐛 修复天气查询结果中的日期显示问题
- 🐛 修复混合缓存系统中的实体模板提取和操作类型不匹配问题
- 🐛 修复聊天窗口步骤间缺少换行的问题
- 🐛 集成fast-json-repair库修复malformed JSON问题

#### 系统优化
- ⚡ 重构意图解析系统
- ⚡ 优化任务规划逻辑
- ⚡ 精简LLM提示词

### 2026-02-18

#### 新增功能
- ✨ 缓存关键参数配置
- ✨ 配置文件分离（system_config/user_config）
- ✨ 缓存配置优化（SQLite/FAISS比例优化）
- ✨ 网络请求工具优化（operation参数）
- ✨ 完整文档系统（用户文档、开发者文档、配置指南）

#### 修复问题
- 🐛 修复意图解析失败问题
- 🐛 修复缓存未命中问题
- 🐛 修复模板匹配过于宽松问题

#### 文档更新
- 📚 新增用户使用说明
- 📚 新增开发者文档
- 📚 新增系统配置说明
- 📚 新增用户配置说明
- 📚 新增缓存配置指南
- 📚 新增文档中心

---

**祝使用愉快！** 🎉
