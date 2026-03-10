# HTML处理工具模块

from bs4 import BeautifulSoup


def remove_interactive_elements(html: str) -> str:
    """移除HTML中的所有交互元素
    
    Args:
        html: 原始HTML字符串
    
    Returns:
        移除交互元素后的HTML字符串
    """
    soup = BeautifulSoup(html, 'lxml')
    
    # 方法1：根据data-id属性移除所有交互元素
    for element in soup.find_all(attrs={'data-id': True}):
        element.decompose()
    
    # 方法2：根据文本内容移除参数修正和确认对话框
    for div in soup.find_all('div'):
        # 检查是否包含参数修正或系统确认标题
        if div.find(string=lambda text: text and ('参数修正:' in text or '系统确认:' in text)):
            # 查找包含这个div的最外层容器
            container = div.find_parent('div')
            if container:
                container.decompose()
    
    # 方法3：根据链接href属性移除交互元素
    for a in soup.find_all('a', href=True):
        href = a.get('href', '')
        if href.startswith('param:') or href.startswith('confirm:'):
            # 查找包含这个链接的最外层容器
            container = a.find_parent('div')
            while container and not container.get('style', '').startswith('margin: 5px 0;'):
                parent = container.find_parent('div')
                if not parent:
                    break
                container = parent
            if container:
                container.decompose()
    
    return str(soup)


def remove_interactive_element_by_id(html: str, element_id: str) -> str:
    """根据唯一标识符移除交互元素
    
    Args:
        html: 原始HTML字符串
        element_id: 要移除的元素的唯一标识符
    
    Returns:
        移除交互元素后的HTML字符串
    """
    soup = BeautifulSoup(html, 'lxml')
    
    # 根据data-id属性精确查找元素
    element = soup.find(attrs={'data-id': element_id})
    if element:
        element.decompose()
    
    return str(soup)


def _remove_parameter_fix_elements(soup: BeautifulSoup) -> None:
    """移除参数修正区域
    
    Args:
        soup: BeautifulSoup对象
    """
    # 查找所有可能的参数修正区域
    for div in soup.find_all('div'):
        # 检查是否包含参数修正标题
        if div.find(string=lambda text: text and '参数修正:' in text):
            # 查找包含这个div的最外层容器
            container = div.find_parent('div')
            if container:
                # 检查容器是否有合适的样式
                style = container.get('style', '')
                if 'margin: 5px 0;' in style:
                    container.decompose()
                else:
                    # 尝试查找上一级容器
                    grandparent = container.find_parent('div')
                    if grandparent and 'margin: 5px 0;' in grandparent.get('style', ''):
                        grandparent.decompose()


def _remove_confirm_dialog_elements(soup: BeautifulSoup) -> None:
    """移除确认对话框区域
    
    Args:
        soup: BeautifulSoup对象
    """
    # 查找所有可能的确认对话框区域
    for div in soup.find_all('div'):
        # 检查是否包含系统确认标题
        if div.find(string=lambda text: text and '系统确认:' in text):
            # 查找包含这个div的最外层容器
            container = div.find_parent('div')
            if container:
                # 检查容器是否有合适的样式
                style = container.get('style', '')
                if 'margin: 5px 0;' in style:
                    container.decompose()
                else:
                    # 尝试查找上一级容器
                    grandparent = container.find_parent('div')
                    if grandparent and 'margin: 5px 0;' in grandparent.get('style', ''):
                        grandparent.decompose()


def extract_form_data(html: str) -> dict:
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