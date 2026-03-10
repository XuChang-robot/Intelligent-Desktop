#!/usr/bin/env python3
"""
将Markdown文件转换为HTML文件
"""

import os
import markdown
from pathlib import Path

def markdown_to_html(md_file, html_file=None):
    """
    将Markdown文件转换为HTML文件
    
    Args:
        md_file: Markdown文件路径
        html_file: HTML文件路径（可选，默认与md文件同名）
    """
    if html_file is None:
        html_file = md_file.replace('.md', '.html')
    
    # 检查文件是否存在
    if not os.path.exists(md_file):
        print(f"错误：文件不存在 {md_file}")
        return False
    
    # 读取Markdown文件
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # 转换为HTML
    html_content = markdown.markdown(
        md_content, 
        extensions=['fenced_code', 'codehilite', 'tables', 'toc'],
        extension_configs={
            'codehilite': {
                'linenums': False,
                'css_class': 'codehilite'
            },
            'toc': {
                'title': '目录'
            }
        }
    )
    
    # 添加HTML模板
    html_template = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{os.path.basename(md_file).replace('.md', '')}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-top: 30px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 5px;
        }}
        h3 {{
            color: #7f8c8d;
            margin-top: 25px;
        }}
        h4 {{
            color: #95a5a6;
            margin-top: 20px;
        }}
        a {{
            color: #3498db;
            text-decoration: none;
        }}
        a:hover {{
            color: #2980b9;
            text-decoration: underline;
        }}
        code {{
            background-color: #f8f9fa;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }}
        pre {{
            background-color: #2c3e50;
            color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            margin: 15px 0;
        }}
        pre code {{
            background-color: transparent;
            padding: 0;
            color: #ecf0f1;
        }}
        /* 代码高亮行号样式 - 内联显示 */
        .codehilite {{
            background-color: #2c3e50;
            border-radius: 5px;
            padding: 15px;
            overflow-x: auto;
        }}
        .codehilite pre {{
            margin: 0;
            padding: 0;
            background-color: transparent;
        }}
        .codehilite table {{
            width: 100%;
            border-collapse: collapse;
            background-color: transparent;
            margin: 0;
        }}
        .codehilite td {{
            border: none;
            padding: 0;
            background-color: transparent;
        }}
        .codehilite .linenos {{
            color: #7f8c8d;
            text-align: right;
            padding-right: 15px;
            width: 40px;
            user-select: none;
            vertical-align: top;
        }}
        .codehilite .code {{
            width: 100%;
        }}
        .codehilite pre {{
            margin: 0;
            line-height: 1.5;
        }}
        /* 代码语法高亮颜色 */
        .codehilite .k {{ color: #ff79c6; }} /* Keyword */
        .codehilite .n {{ color: #f8f8f2; }} /* Name */
        .codehilite .s {{ color: #f1fa8c; }} /* String */
        .codehilite .c {{ color: #6272a4; }} /* Comment */
        .codehilite .o {{ color: #ff79c6; }} /* Operator */
        .codehilite .p {{ color: #f8f8f2; }} /* Punctuation */
        .codehilite .mi {{ color: #bd93f9; }} /* Number */
        .codehilite .nb {{ color: #8be9fd; }} /* Builtin */
        .codehilite .nf {{ color: #50fa7b; }} /* Function */
        .codehilite .nc {{ color: #8be9fd; }} /* Class */
        .codehilite .nd {{ color: #50fa7b; }} /* Decorator */
        .codehilite .s1 {{ color: #f1fa8c; }} /* String.Single */
        .codehilite .s2 {{ color: #f1fa8c; }} /* String.Double */
        .codehilite .kn {{ color: #ff79c6; }} /* Keyword.Namespace */
        .codehilite .bp {{ color: #f8f8f2; }} /* Name.Builtin.Pseudo */
        .codehilite .fm {{ color: #50fa7b; }} /* Name.Function.Magic */
        .codehilite .sa {{ color: #f1fa8c; }} /* String.Affix */
        .codehilite .ow {{ color: #ff79c6; }} /* Operator.Word */
        .codehilite .ss {{ color: #f1fa8c; }} /* String.Symbol */
        .codehilite .vm {{ color: #8be9fd; }} /* Name.Variable.Magic */
        .codehilite .w {{ color: #f8f8f2; }} /* Text.Whitespace */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background-color: white;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #3498db;
            color: white;
        }}
        tr:nth-child(even) {{
            background-color: #f2f2f2;
        }}
        ul, ol {{
            background-color: white;
            padding: 15px 30px;
            border-radius: 5px;
            margin: 10px 0;
        }}
        .toc {{
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .toc ul {{
            background-color: transparent;
            padding: 0;
            margin: 0;
        }}
        .toc li {{
            margin-bottom: 8px;
        }}
        .section {{
            background-color: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .update {{
            background-color: #ecf0f1;
            padding: 15px;
            border-left: 4px solid #3498db;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    {html_content}
</body>
</html>
"""
    
    # 写入HTML文件
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_template)
    
    print(f"✓ 转换成功: {html_file}")
    return True

def convert_all_md_files(directory):
    """
    转换目录下所有Markdown文件为HTML文件
    
    Args:
        directory: 目录路径
    """
    md_files = list(Path(directory).rglob('*.md'))
    
    print(f"=== 开始转换目录: {directory} ===")
    print(f"找到 {len(md_files)} 个Markdown文件\n")
    
    success_count = 0
    for md_file in md_files:
        if markdown_to_html(str(md_file)):
            success_count += 1
        print()
    
    print(f"=== 转换完成 ===")
    print(f"成功: {success_count}/{len(md_files)}")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        # 转换指定文件
        md_file = sys.argv[1]
        markdown_to_html(md_file)
    else:
        # 转换当前目录下所有文件
        convert_all_md_files('.')
