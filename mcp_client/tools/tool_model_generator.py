# 基于MCP工具的inputSchema自动生成Pydantic模型

from typing import Dict, Any, Optional, Type
from pydantic import BaseModel, create_model
from pydantic.fields import Field


def create_tool_model_from_schema(tool_name: str, input_schema: Dict[str, Any]) -> Optional[Type[BaseModel]]:
    """基于工具的inputSchema创建Pydantic模型
    
    Args:
        tool_name: 工具名称
        input_schema: 工具的inputSchema
        
    Returns:
        创建的Pydantic模型类，如果schema无效则返回None
    """
    if not input_schema or 'properties' not in input_schema:
        return None
    
    properties = input_schema.get('properties', {})
    required = input_schema.get('required', [])
    
    # 构建模型字段
    model_fields = {}
    
    for param_name, param_info in properties.items():
        # 获取参数类型
        param_type = param_info.get('type', 'string')
        python_type = _json_type_to_python_type(param_type)
        
        # 获取参数描述
        param_desc = param_info.get('description', '')
        
        # 检查是否为必需参数
        is_required = param_name in required
        
        # 创建字段
        if is_required:
            model_fields[param_name] = (python_type, Field(..., description=param_desc))
        else:
            model_fields[param_name] = (Optional[python_type], Field(None, description=param_desc))
    
    # 创建并返回模型类
    model_name = f"{tool_name.capitalize()}Model"
    return create_model(model_name, **model_fields)


def _json_type_to_python_type(json_type: str) -> Type:
    """将JSON类型映射到Python类型
    
    Args:
        json_type: JSON类型字符串
        
    Returns:
        对应的Python类型
    """
    type_mapping = {
        'string': str,
        'integer': int,
        'number': float,
        'boolean': bool,
        'array': list,
        'object': dict
    }
    
    return type_mapping.get(json_type, Any)


def validate_tool_parameters(tool_name: str, input_schema: Dict[str, Any], parameters: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """验证工具参数
    
    Args:
        tool_name: 工具名称
        input_schema: 工具的inputSchema
        parameters: 要验证的参数字典
        
    Returns:
        (验证是否成功, 错误信息, 验证后的参数字典)
    """
    # 创建模型
    model = create_tool_model_from_schema(tool_name, input_schema)
    
    if not model:
        return True, None, parameters
    
    try:
        # 验证参数
        validated = model(**parameters)
        return True, None, validated.model_dump()
    except Exception as e:
        return False, str(e), None
