# 系统配置说明

本文件夹包含系统的核心配置文件，这些配置文件由系统维护，**用户不应该修改**。

## 配置文件说明

### cache_config.json
缓存关键参数配置文件，用于控制缓存匹配行为。

#### 配置结构
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

#### 配置项说明
- **global**: 全局关键参数列表，适用于所有工具
- **tools**: 各工具特定的关键参数列表，可以覆盖全局配置

#### 关键参数的作用
关键参数用于区分不同的操作类型，确保缓存的准确性。例如：
- `operation`: 区分不同的操作类型（如"pdf_to_word" vs "word_to_pdf"）
- 当用户请求"把PDF转为Word"和"把Word转为PDF"时，虽然参数名称相同，但operation的值不同，因此会被识别为不同的意图

#### 影响范围
- 缓存匹配精度：关键参数越多，缓存匹配越精确，但可能降低缓存命中率
- 缓存命中率：关键参数越少，缓存命中率越高，但可能降低匹配精度
- 系统性能：合理的配置可以平衡缓存命中率和匹配精度

#### 修改建议
**用户不应该修改此文件**。如果需要调整关键参数，请联系系统维护人员。

## 注意事项
1. 本文件夹中的配置文件由系统维护，用户不应该修改
2. 修改系统配置可能导致缓存失效或系统行为异常
3. 如果需要调整配置，请联系系统维护人员
