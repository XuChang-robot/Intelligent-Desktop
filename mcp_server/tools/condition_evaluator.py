# 工具创建规则：
# 1. 必须在文件最前面定义工具说明，包括工具名称、支持的操作类型、必需参数、可选参数、参数验证规则和返回格式
# 2. 必须定义操作类型配置（OPERATION_CONFIG或其他类似配置），包含各操作类型的描述、必需参数和可选参数
# 3. 必须实现validate_parameters函数，用于验证和调整参数，返回(调整后的参数字典, 配置错误信息)
# 4. 必须在工具函数开始时调用validate_parameters进行参数验证，如果存在config_error则返回包含config_error字段的错误结果
# 5. 必须统一返回字典格式结果，包含success字段和formatted_message字段
# 6. 配置错误时返回{"success": False, "config_error": "...", "formatted_message": "❌ 配置错误: ..."}
# 7. 执行失败时返回{"success": False, "error": "...", "formatted_message": "❌ 错误: ..."}
# 8. 成功时返回{"success": True, "result": "...", "formatted_message": "✅ ..."}
# 9. 必须包含operation参数，用于指定具体的操作类型
# 10. 只有当返回结果包含config_error字段时，行为树自动修复机制才会触发配置修复


# 条件评估工具

import os
from typing import Dict, Any, Optional, Tuple
from enum import Enum
from pydantic import BaseModel
from mcp.server.fastmcp import Context

# 从file_operations导入FileOperationsTool
from mcp_server.tools.file_operations import FileOperationsTool


# 工具说明：
# 工具名称：condition_evaluator
# 支持的操作类型（operation）：
#   - "evaluate": 评估条件表达式
# 必需参数：
#   - operation: 操作类型（必需）
#   - expression: 条件表达式（必需，使用{{节点ID}}格式引用节点结果）
#   - context: 上下文数据（必需，包含节点ID到结果的映射）
# 可选参数：
#   - ctx: FastMCP上下文，用于elicitation（可选）
#
# 参数验证规则：
#   - operation: 必须是支持的操作类型之一
#   - expression: 不能为空
#   - context: 不能为空
#
# 返回格式：
#   - 成功：{"success": True, "result": true/false, "formatted_message": "..."}
#   - 配置错误：{"success": False, "config_error": "..."}
#   - 执行失败：{"success": False, "error": "...", "formatted_message": "..."}


# 操作类型枚举
class ConditionOperationEnum(str, Enum):
    EVALUATE = "evaluate"

# 操作类型配置
OPERATION_CONFIG = {
    'evaluate': {
        'description': '评估条件表达式',
        'required_params': ['expression', 'context'],
        'optional_params': ['ctx']
    }
}


def validate_parameters(operation: ConditionOperationEnum, expression: str, context: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[str]]:
    """验证并调整参数
    
    Args:
        operation: 操作类型
        expression: 条件表达式
        context: 上下文数据
    
    Returns:
        (调整后的参数字典, 配置错误信息)
    """
    if not expression:
        return {}, "条件表达式不能为空"
    if not context:
        return {}, "上下文数据不能为空"
    return {"operation": operation, "expression": expression, "context": context}, None


def extract_node_references(expression: str) -> list:
    """提取表达式中的节点引用
    
    Args:
        expression: 条件表达式
    
    Returns:
        节点引用列表
    """
    import re
    # 匹配 {{节点ID}} 格式的引用
    pattern = r'\{\{([^}]+)\}\}'
    return re.findall(pattern, expression)


def resolve_node_reference(node_id: str, context: Dict[str, Any]) -> str:
    """解析节点引用，获取formatted_message
    
    Args:
        node_id: 节点ID
        context: 上下文数据
    
    Returns:
        节点的formatted_message内容
    """
    if node_id not in context:
        return ""
    
    node_result = context[node_id]
    if isinstance(node_result, dict):
        # 优先使用 result.formatted_message
        if "result" in node_result:
            result = node_result["result"]
            if isinstance(result, dict) and "formatted_message" in result:
                return result["formatted_message"]
            elif isinstance(result, str):
                return result
        # 其次使用 formatted_message
        elif "formatted_message" in node_result:
            return node_result["formatted_message"]
    elif isinstance(node_result, str):
        return node_result
    
    return ""


def evaluate_condition(expression: str, context: Dict[str, Any]) -> bool:
    """安全评估条件表达式
    
    Args:
        expression: 条件表达式
        context: 上下文数据
    
    Returns:
        评估结果
    """
    try:
        # 提取节点引用
        node_references = extract_node_references(expression)
        
        # 构建安全的求值环境
        safe_env = {
            'True': True,
            'False': False,
            'None': None,
            'len': len,
            'str': str,
            'bool': bool,
        }
        
        # 解析并替换节点引用
        resolved_expression = expression
        for node_id in node_references:
            # 解析节点引用，获取formatted_message
            node_value = resolve_node_reference(node_id, context)
            # 替换表达式中的引用
            resolved_expression = resolved_expression.replace(f"{{{{{node_id}}}}}", f"'{node_value}'")
        
        # 安全评估表达式
        import ast
        tree = ast.parse(resolved_expression, mode='eval')
        
        # 检查表达式安全性
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # 只允许内置函数调用
                if hasattr(node.func, 'id') and node.func.id not in safe_env:
                    return False
        
        result = eval(compile(tree, '<string>', 'eval'), {"__builtins__": {}}, safe_env)
        return bool(result)
        
    except Exception as e:
        return False


def condition_evaluator(operation: str, expression: str, context: Dict[str, Any], ctx: Optional[Context] = None) -> Dict[str, Any]:
    """条件评估工具主函数
    
    Args:
        operation: 操作类型
        expression: 条件表达式
        context: 上下文数据
        ctx: FastMCP上下文
    
    Returns:
        评估结果
    """
    try:
        # 验证参数
        params, config_error = validate_parameters(ConditionOperationEnum(operation), expression, context)
        if config_error:
            return {
                "success": False, 
                "config_error": config_error,
                "formatted_message": f"❌ 配置错误: {config_error}"
            }
        
        # 执行评估
        if operation == ConditionOperationEnum.EVALUATE:
            result = evaluate_condition(expression, context)
            return {
                "success": True,
                "result": result,
                "formatted_message": "True" if result else "False"
            }
        
        return {
            "success": False,
            "formatted_message": "False"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "formatted_message": f"❌ 评估失败: {str(e)}"
        }
