from mcp_client.behavior_tree.visualizer.dot_parser import render_dot_to_html

# 生成 HTML 并打印前200行来检查结构
html = render_dot_to_html(r'e:\Project_AIcoding\Intelligence_Desktop\logs\visualizations\behavior_tree_visualization.dot')

# 打印 HTML 头部和相关部分
lines = html.split('\n')
print('=== HTML 头部和样式 ===')
for i, line in enumerate(lines[:150]):
    print(f'{i+1:3d}: {line}')

print('\n=== 节点和连线部分 ===')
for i, line in enumerate(lines[150:250]):
    if 'edge' in line.lower() or 'child' in line.lower():
        print(f'{i+151:3d}: {line}')
