import markdown
import os

# 读取markdown文件
with open('KNOWN_ISSUES.md', 'r', encoding='utf-8') as f:
    md_content = f.read()

# 转换为HTML
html_content = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])

# 添加HTML头部和样式
full_html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>已知问题 - Elicitation 通信机制</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 10px;
        }
        h2 {
            color: #555;
            margin-top: 30px;
            border-bottom: 1px solid #eee;
            padding-bottom: 8px;
        }
        h3 {
            color: #666;
            margin-top: 25px;
        }
        h4 {
            color: #777;
            margin-top: 20px;
        }
        code {
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 0.9em;
        }
        pre {
            background-color: #f8f8f8;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            border-left: 4px solid #007acc;
        }
        pre code {
            background-color: transparent;
            padding: 0;
        }
        ul, ol {
            padding-left: 25px;
        }
        li {
            margin-bottom: 8px;
        }
        strong {
            color: #333;
        }
        .issue-box {
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 5px;
            padding: 15px;
            margin: 20px 0;
        }
        .issue-box h2 {
            margin-top: 0;
            color: #856404;
        }
        .flow-diagram {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            padding: 15px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 0.85em;
            overflow-x: auto;
            white-space: pre;
            line-height: 1.4;
        }
    </style>
</head>
<body>
    <div class="container">
''' + html_content + '''
    </div>
</body>
</html>'''

# 保存HTML文件
with open('KNOWN_ISSUES.html', 'w', encoding='utf-8') as f:
    f.write(full_html)

print('✅ 成功将 KNOWN_ISSUES.md 转换为 KNOWN_ISSUES.html')
