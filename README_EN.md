# Intelligent Desktop System

An intelligent desktop assistant based on MCP (Model Context Protocol), supporting automated processing of various desktop tasks such as document conversion, file operations, email processing, and network requests.

## ✨ Features

- 🧠 **Intelligent Intent Recognition**: Automatically understands user needs, supporting three intent types (task/chat/cannot_execute)
- 📋 **Task Planning**: Behavior tree-based task planning system, supporting automatic decomposition and execution of complex tasks
- 🚀 **Efficient Caching**: FAISS vector search-based hybrid caching system, supporting hash exact matching and semantic matching
- 🔒 **Secure and Reliable**: Sandbox isolation, permission control
- 🧩 **Easy to Extend**: Modular design, supporting custom tools
- ☁️ **Weather Query**: Real-time weather information and warning notifications
- 📄 **Batch Document Processing**: Supports batch file conversion and wildcard matching
- 💭 **LLM Thinking Process**: Collapsible thinking process display

## 🚀 Quick Start

### Environment Requirements

- Python 3.13+
- Ollama service
- Required Python libraries (see requirements.txt)

### Installation Steps

```bash
# 1. Clone the repository
git clone https://github.com/XuChang-robot/Intelligent-Desktop.git
cd Intelligent-Desktop

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start Ollama service
ollama serve

# 4. Download models
ollama pull qwen3:8b
ollama pull nomic-embed-text

# 5. Start the system
python main.py
```

## 📚 Documentation

Complete documentation can be found in [docs/README.md](docs/README.md)

### User Documentation

- 📖 [User Guide](docs/USER_GUIDE.md) - System usage guide, feature descriptions, configuration guide
- 📝 [User Configuration Guide](user_config/README.md) - User configuration file instructions
- 💾 [Cache Configuration Guide](user_config/CACHE_CONFIG_GUIDE.md) - Cache system configuration guide

### Developer Documentation

- 🛠️ [Developer Guide](docs/DEVELOPER_GUIDE.md) - System architecture, API reference, extension development
- ⚙️ [System Configuration Guide](system_config/README.md) - System configuration file instructions
- 🚀 [Hybrid Cache System Guide](docs/cache_system.md) - Cache system working principle

## 🎯 Main Features

### Document Conversion
- PDF to Word
- Word to PDF
- Support for specifying output path
- **Support for batch conversion**: Use wildcards to match multiple files

### File Operations
- Create, read, write, delete files
- Move, copy files
- List directories, search files

### PDF Processing
- PDF merging
- PDF page insertion
- PDF printing
- PDF page extraction
- PDF splitting

### Text Processing
- Text-to-speech
- Text summarization
- Text formatting
- Character count

### Email Processing
- Send emails
- Receive emails

### Network Requests
- GET, POST, PUT, DELETE requests
- Support for custom request headers and parameters

### Weather Query
- **Real-time weather**: Query current weather for specified cities
- **Warning information**: Display weather warning titles and effective times
- **Date display**: Optimized date display in weather query results, supporting specific dates and relative dates

### Behavior Tree Task Planning

Behavior tree is an advanced architecture for task planning and execution, representing task execution logic through a tree structure.

#### Advantages of Behavior Tree

- **Modular Design**: Each node is an independent module that can be developed and tested separately
- **Flexible Execution Flow**: Supports complex control flows such as conditional branches, loops, and parallel execution
- **Easy to Extend**: Can easily add new node types and features
- **Visualization and Debugging**: Can intuitively view task execution flow, facilitating debugging and optimization
- **Error Handling**: Automatic rollback or retry when tasks fail to execute
- **State Management**: Real-time tracking of task execution status and progress

#### Example of Behavior Tree Execution

Suppose the user requests: "Help me organize PDF files on the desktop, convert them to Word format, and then send them to a specified email"

The behavior tree will decompose this task into the following steps:

1. **Root Node**: Start executing the task
2. **Sequence Node**: Execute the following sub-tasks in order
   - **Search Node**: Search for all PDF files in the desktop directory
   - **Loop Node**: Perform the following operations on each found PDF file
     - **Conversion Node**: Convert PDF file to Word format
   - **Collection Node**: Collect all converted Word files
   - **Send Node**: Send the collected Word files to the specified email address

Each node has its own execution logic and error handling mechanism. If a node fails to execute, the behavior tree will handle it according to preset strategies (such as retry, skip, or terminate the task).

#### Current Caching Logic

The system adopts a two-layer caching matching strategy to improve task planning efficiency:

1. **First Layer: Hash Exact Matching**
   - Exact matching based on MD5 hash of request content
   - Completely identical requests will immediately hit the cache
   - Fastest response speed (approximately 0.01 seconds)
   - Applicable to: Users repeatedly executing the same task

2. **Second Layer: FAISS Semantic Matching**
   - Semantic matching based on vector similarity
   - Requests with similar but different expressions can hit the cache
   - Faster response speed (approximately 0.05 seconds)
   - Controlled by `similarity_threshold` parameter (default 0.85)
   - Applicable to: Users executing similar tasks with different expressions

#### Benefits of Caching

- **Improve Response Speed**: Avoid repeated LLM calls to generate plans, significantly reducing response time
- **Reduce Resource Consumption**: Reduce the number of LLM API calls, saving computing resources and costs
- **Ensure Consistency**: Use the same execution plan for identical or similar tasks, improving system stability
- **Support Offline Mode**: When cache hits, tasks can be executed without connecting to the LLM service

## 📁 Project Structure

```
Intelligence_Desktop/
├── mcp_client/              # MCP client
│   ├── intent_parser.py      # Intent parser
│   ├── task_planner.py      # Task planner
│   ├── hybrid_cache.py      # Hybrid cache
│   └── llm.py            # LLM client
├── mcp_server/            # MCP server
│   └── tools/            # Tool collection
│       ├── document_converter.py
│       ├── file_operations.py
│       ├── pdf_processor.py
│       ├── text_processing.py
│       ├── email_processor.py
│       ├── network_request.py
│       └── query/          # Query tools
│           └── weather_query.py  # Weather query tool
├── system_config/         # System configuration (should not be modified by users)
├── user_config/           # User configuration
├── cache/                # Cache directory
├── docs/                 # Documentation
└── main.py              # Main program
```

## ⚙️ Configuration

### User Configuration

User configuration files are located at `user_config/config.yaml`, including of following configuration items:

- **MCP Configuration**: Server address, port, number of connections
- **LLM Configuration**: Model name, API address, temperature parameters
- **Security Configuration**: Sandbox, dangerous commands, permission control
- **UI Configuration**: Window title, size, theme
- **Logging Configuration**: Log level, format
- **Email Configuration**: SMTP/IMAP server
- **Cache Configuration**: Enable status, size limit, similarity threshold

For detailed configuration instructions, please refer to: [User Configuration Guide](user_config/README.md)

### System Configuration

System configuration files are located at `system_config/cache_config.json`, containing cache key parameter configurations.

**Note**: System configuration is maintained by the system and should not be modified by users.

For detailed configuration instructions, please refer to: [System Configuration Guide](system_config/README.md)

## 🔧 Development

### Adding New Tools

1. Create a new tool file under `mcp_server/tools/`
2. Implement the tool interface
3. Register the tool in `mcp_server/server.py`
4. Update configuration files
5. Update LLM prompts

For detailed development guide, please refer to: [Developer Guide](docs/DEVELOPER_GUIDE.md)

### Testing

```bash
# Run all tests
pytest tests/

# Test cache system
python test_cache_hit_complete.py

# Test different operations
python test_different_operations.py
```

## 📊 Performance

The hybrid cache system provides significant performance improvements:

| Scenario | Without Cache | With Cache | Performance Improvement |
|----------|---------------|------------|------------------------|
| Exact Match | 7.7s | 0.01s | **770x** |
| Semantic Similar | 7.7s | 0.05s | **154x** |

For detailed performance analysis, please refer to: [Hybrid Cache System Guide](docs/cache_system.md)

## 🤝 Contribution

Contributions, issues, and feature requests are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details

## 📞 Contact

- Project Home: [https://github.com/XuChang-robot/Intelligent-Desktop](https://github.com/XuChang-robot/Intelligent-Desktop)
- Issue Feedback: [https://github.com/XuChang-robot/Intelligent-Desktop/issues](https://github.com/XuChang-robot/Intelligent-Desktop/issues)

## 📝 Changelog

### 2026-02-24

#### Bug Fixes
- 🐛 Fixed TypeError in weather query logic
- 🐛 Fixed date display issue in weather query results
- 🐛 Fixed wind direction and force information display for foreign weather queries
- 🐛 Fixed parameter order issue in task planning function calls

#### System Optimization
- ⚡ Optimized weather query logic to support different API response formats for domestic and foreign cities
- ⚡ Optimized cache system to improve cache hit rate

#### Documentation Updates
- 📚 Updated user guide to add conceptual explanation of behavior tree task planning
- 📚 Updated developer documentation to add architecture description of behavior tree system
- 📚 Updated configuration guide to add detailed explanation of cache system

### 2026-02-21

#### New Features
- ✨ Intent recognition optimization: Support for three intent types (task/chat/cannot_execute)
- ✨ Task planning optimization: Adopt two-layer cache matching (hash exact matching + FAISS semantic matching)
- ✨ Cache configuration enhancement: Support independent control of hash matching and FAISS matching
- ✨ Cache template mechanism: Use templates to generate complete plans when cache hits
- ✨ Weather query tool: Real-time weather information and warning notifications
- ✨ Batch document processing: Support wildcard matching and batch file conversion
- ✨ LLM thinking process display: Collapsible thinking process

#### Bug Fixes
- 🐛 Fixed date display issue in weather query results
- 🐛 Fixed entity template extraction and operation type mismatch issues in hybrid cache system
- 🐛 Fixed missing line breaks between steps in chat window
- 🐛 Integrated fast-json-repair library to fix malformed JSON issues

#### System Optimization
- ⚡ Refactored intent parsing system to support three intent type judgments
- ⚡ Optimized task planning logic to support cache templates and complete plan generation
- ⚡ Optimized cache matching strategy to improve cache hit rate
- ⚡ Streamlined LLM prompts to improve response speed
- ⚡ Support entities as dictionary or list format
- ⚡ Support batch operations (num_inputs array)

#### Documentation Updates
- 📚 Updated user guide to add detailed instructions for intent recognition and task planning
- 📚 Updated developer documentation to add system architecture and API reference
- 📚 Added cache configuration guide with detailed cache disable scenarios
- 📚 Updated user configuration instructions to add cache configuration items
- 📚 Updated cache system documentation to add troubleshooting guide

### 2026-02-18

#### New Features
- ✨ Cache key parameter configuration
- ✨ Configuration file separation (system_config/user_config)
- ✨ Cache configuration optimization (SQLite/FAISS ratio optimization)
- ✨ Network request tool optimization (operation parameter)
- ✨ Complete documentation system (user documentation, developer documentation, configuration guide)

#### Bug Fixes
- 🐛 Fixed intent parsing failure issues
- 🐛 Fixed cache miss issues
- 🐛 Fixed template matching being too loose

#### Documentation Updates
- 📚 Added user guide
- 📚 Added developer documentation
- 📚 Added system configuration instructions
- 📚 Added user configuration instructions
- 📚 Added cache configuration guide
- 📚 Added documentation center

---

**Happy using!** 🎉