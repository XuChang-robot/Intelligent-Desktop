# 参数修正组件模块

from typing import Dict, Any, Callable
from PyQt6.QtWidgets import QTextEdit
from ui.utils.html_generator import generate_parameter_fix_html, generate_confirm_dialog_html
from ui.utils.html_processor import remove_interactive_elements, remove_interactive_element_by_id
from bs4 import BeautifulSoup

class ParameterFixComponent:
    """参数修正组件"""
    
    def __init__(self, chat_area: QTextEdit):
        """初始化参数修正组件
        
        Args:
            chat_area: 聊天区域文本编辑框
        """
        self.chat_area = chat_area
        self.current_schema = None
        self.original_params = None
        self.current_element_id = None  # 记录当前交互元素的唯一标识符
    
    def show_parameter_fix_dialog(self, message: str, schema: Dict[str, Any]):
        """显示参数修正对话框
        
        Args:
            message: 提示消息
            schema: JSON Schema对象
        """
        # 保存参数信息
        self.current_schema = schema
        
        # 生成参数修正HTML和唯一标识符
        html, element_id = generate_parameter_fix_html(message, schema)
        self.current_element_id = element_id
        
        # 将HTML添加到聊天区域
        self._add_html_to_chat_area(html)
    
    def show_confirm_dialog(self, message: str):
        """显示确认对话框
        
        Args:
            message: 确认消息
        """
        # 生成确认对话框HTML和唯一标识符
        html, element_id = generate_confirm_dialog_html(message)
        self.current_element_id = element_id
        
        # 将HTML添加到聊天区域
        self._add_html_to_chat_area(html)
    
    def extract_form_data(self, html: str) -> dict:
        """从HTML表单中提取数据
        
        Args:
            html: 包含表单的HTML字符串
        
        Returns:
            提取的表单数据
        """
        
        soup = BeautifulSoup(html, 'lxml')
        form_data = {}
        
        # 查找所有输入元素
        for input_elem in soup.find_all('input'):
            name = input_elem.get('name')
            if name:
                if input_elem.get('type') == 'checkbox':
                    form_data[name] = input_elem.get('checked') is not None
                else:
                    form_data[name] = input_elem.get('value', '')
        
        return form_data
    
    def refresh_chat_area(self):
        """刷新聊天区域，移除已处理的交互元素"""
        current_html = self.chat_area.toHtml()
        # 使用增强版的remove_interactive_elements函数移除所有交互元素
        new_html = remove_interactive_elements(current_html)
        self.chat_area.setHtml(new_html)
        
        # 确保滚动到底部
        cursor = self.chat_area.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.chat_area.setTextCursor(cursor)
        
        # 重置当前元素ID
        self.current_element_id = None
    
    def _add_html_to_chat_area(self, html: str):
        """将HTML添加到聊天区域
        
        Args:
            html: 要添加的HTML字符串
        """
        current_html = self.chat_area.toHtml()
        
        # 确保HTML结构正确
        if "</body>" not in current_html:
            current_html = "<html><body style='font-family: Arial, sans-serif; font-size: 14px;'></body></html>"
        
        # 将新HTML插入到现有HTML中
        new_html = current_html.replace("</body>", html + "</body>")
        
        # 更新聊天区域
        self.chat_area.setHtml(new_html)
        
        # 确保滚动到底部
        cursor = self.chat_area.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.chat_area.setTextCursor(cursor)