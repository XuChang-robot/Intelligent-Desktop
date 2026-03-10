# HTML生成工具模块

import uuid
from typing import Dict, Any


def generate_parameter_form(schema: Dict[str, Any]) -> str:
    """从JSON Schema生成参数表单HTML
    
    Args:
        schema: JSON Schema对象
    
    Returns:
        生成的HTML字符串
    """
    params = _parse_schema(schema)
    form_html = _generate_form_html(params)
    return form_html


def generate_parameter_fix_html(message: str, schema: Dict[str, Any]) -> tuple:
    """生成参数修正对话框的完整HTML
    
    Args:
        message: 提示消息
        schema: JSON Schema对象
    
    Returns:
        (html, element_id): 生成的完整HTML字符串和唯一标识符
    """
    # 生成唯一标识符
    element_id = f"param-fix-{uuid.uuid4().hex[:8]}"
    form_html = generate_parameter_form(schema)
    
    html = f"<div data-id='{element_id}' style='margin: 5px 0;'>"
    html += f"<div style='color: #FF9800; font-weight: bold; text-align: left; margin-bottom: 3px;'>⚠️ 参数修正:</div>"
    html += f"<div style='text-align: left; padding: 12px; background-color: #FFF3E0; border-radius: 10px; max-width: 80%; margin-right: auto; border-left: 4px solid #FF9800;'>"
    html += f"<div style='margin-bottom: 8px;'>{message}</div>"
    html += form_html
    html += f"<div style='margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap;'>"
    html += f"<a href='param:confirm' style='padding: 8px 16px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 6px; border: 2px solid #388E3C; font-weight: bold;'>✅ 确认</a>"
    html += f"<a href='param:reset' style='padding: 8px 16px; background-color: #FF9800; color: white; text-decoration: none; border-radius: 6px; border: 2px solid #F57C00; font-weight: bold;'>🔄 重置</a>"
    html += f"<a href='param:cancel' style='padding: 8px 16px; background-color: #F44336; color: white; text-decoration: none; border-radius: 6px; border: 2px solid #D32F2F; font-weight: bold;'>❌ 取消</a>"
    html += f"</div>"
    html += f"</div>"
    html += f"</div>"
    
    return html, element_id


def generate_confirm_dialog_html(message: str) -> tuple:
    """生成确认对话框的HTML
    
    Args:
        message: 确认消息
    
    Returns:
        (html, element_id): 生成的HTML字符串和唯一标识符
    """
    # 生成唯一标识符
    element_id = f"confirm-dialog-{uuid.uuid4().hex[:8]}"
    html = f"<div data-id='{element_id}' style='margin: 5px 0;'>"
    html += f"<div style='color: #FF9800; font-weight: bold; text-align: left; margin-bottom: 3px;'>⚠️ 系统确认:</div>"
    html += f"<div style='text-align: left; padding: 12px; background-color: #FFF3E0; border-radius: 10px; max-width: 80%; margin-right: auto; border-left: 4px solid #FF9800; white-space: pre-wrap;'>"
    html += f"<div style='margin-bottom: 8px;'>{message}</div>"
    html += f"<div style='margin-top: 8px;'>"
    html += f"<a href='confirm:yes' style='display: inline-block; padding: 8px 16px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 6px; margin-right: 8px; border: 2px solid #388E3C; font-weight: bold; cursor: pointer;'>✅ 确认执行</a>"
    html += f"<a href='confirm:no' style='display: inline-block; padding: 8px 16px; background-color: #F44336; color: white; text-decoration: none; border-radius: 6px; border: 2px solid #D32F2F; font-weight: bold; cursor: pointer;'>❌ 取消执行</a>"
    html += f"</div>"
    html += f"</div>"
    html += f"</div>"
    
    return html, element_id


def _parse_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """解析schema获取参数信息
    
    Args:
        schema: JSON Schema对象
    
    Returns:
        解析后的参数信息
    """
    params = {}
    
    # 处理不同类型的schema结构
    if isinstance(schema, dict):
        # 检查properties字段（OpenAPI风格）
        if 'properties' in schema:
            for param_name, param_info in schema['properties'].items():
                # 确保默认值不为None
                default_value = param_info.get('default', '')
                if default_value is None:
                    default_value = ''
                params[param_name] = {
                    'type': param_info.get('type', 'string'),
                    'description': param_info.get('description', ''),
                    'default': default_value,
                    'required': param_name in schema.get('required', [])
                }
        else:
            # 直接处理键值对
            for param_name, param_value in schema.items():
                # 确保默认值不为None
                if param_value is None:
                    param_value = ''
                params[param_name] = {
                    'type': 'string',
                    'description': '',
                    'default': param_value,
                    'required': True
                }
    
    return params


def _generate_form_html(params: Dict[str, Any]) -> str:
    """生成参数表单HTML
    
    Args:
        params: 解析后的参数信息
    
    Returns:
        生成的表单HTML字符串
    """
    form_html = "<div style='margin-bottom: 12px;'>"
    
    for param_name, param_info in params.items():
        param_type = param_info.get('type', 'string')
        description = param_info.get('description', '')
        default_value = param_info.get('default', '')
        required = param_info.get('required', False)
        
        # 构建标签
        label_html = f"<label for='param_{param_name}' style='display: block; margin-bottom: 4px; font-weight: bold;'>"
        label_html += f"{param_name}"
        if required:
            label_html += " <span style='color: #F44336;'>*</span>"
        if description:
            label_html += f" <span style='font-weight: normal; font-size: 12px; color: #757575;'>({description})</span>"
        label_html += "</label>"
        
        # 构建输入字段
        input_html = ""
        if param_type == 'boolean':
            # 布尔值使用复选框
            checked = 'checked' if str(default_value).lower() == 'true' else ''
            input_html = f"<input type='checkbox' id='param_{param_name}' name='{param_name}' {checked} style='margin-right: 8px;'>"
        elif param_type == 'number' or param_type == 'integer':
            # 数字类型使用数字输入框
            input_html = f"<input type='number' id='param_{param_name}' name='{param_name}' value='{default_value}' style='width: 100%; padding: 6px; border: 1px solid #ddd; border-radius: 4px;'>"
        else:
            # 默认使用文本输入框
            input_html = f"<input type='text' id='param_{param_name}' name='{param_name}' value='{default_value}' style='width: 100%; padding: 6px; border: 1px solid #ddd; border-radius: 4px;'>"
        
        # 组合成表单组
        form_html += f"<div style='margin-bottom: 12px;'>"
        form_html += label_html
        form_html += input_html
        form_html += "</div>"
    
    form_html += "</div>"
    return form_html