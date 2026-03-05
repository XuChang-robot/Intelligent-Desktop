"""
DOT文件解析器 - 将Graphviz DOT格式解析为HTML可视化
"""

import re
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import json

@dataclass
class DOTNode:
    """DOT节点"""
    id: str
    label: str
    shape: str = "box"
    color: str = "black"
    style: str = "filled"
    fillcolor: str = "white"
    fontsize: str = "12"
    fontcolor: str = "black"
    fontname: str = ""
    node_type: str = ""
    node_icon: str = ""  # 节点类型（Sequence, Action等）

@dataclass
class DOTEdge:
    """DOT边"""
    from_node: str
    to_node: str
    label: str = ""
    color: str = "black"

@dataclass
class DOTGraph:
    """DOT图"""
    name: str
    nodes: Dict[str, DOTNode]
    edges: List[DOTEdge]
    rankdir: str = "TB"
    ordering: str = ""
    fontname: str = ""

class DOTParser:
    """DOT文件解析器"""
    
    def __init__(self):
        self.nodes = {}
        self.edges = []
        self.graph_name = "G"
        self.rankdir = "TB"
        self.ordering = ""
        self.fontname = ""
    
    def parse(self, dot_content: str) -> DOTGraph:
        """解析DOT内容
        
        Args:
            dot_content: DOT文件内容
            
        Returns:
            DOTGraph对象
        """
        # 移除注释
        dot_content = re.sub(r'//.*', '', dot_content)
        dot_content = re.sub(r'/\*.*?\*/', '', dot_content, flags=re.DOTALL)
        
        # 解析图名称
        graph_match = re.search(r'digraph\s+(\w+)\s*\{', dot_content)
        if graph_match:
            self.graph_name = graph_match.group(1)
        
        # 解析 rankdir
        rankdir_match = re.search(r'rankdir\s*=\s*(\w+)', dot_content)
        if rankdir_match:
            self.rankdir = rankdir_match.group(1)
        
        # 解析 ordering
        ordering_match = re.search(r'ordering\s*=\s*(\w+)', dot_content)
        if ordering_match:
            self.ordering = ordering_match.group(1)
        
        # 解析 fontname
        fontname_match = re.search(r'fontname\s*=\s*"([^"]+)"', dot_content)
        if fontname_match:
            self.fontname = fontname_match.group(1)
        
        # 解析节点
        self._parse_nodes(dot_content)
        
        # 解析边
        self._parse_edges(dot_content)
        
        return DOTGraph(
            name=self.graph_name,
            nodes=self.nodes,
            edges=self.edges,
            rankdir=self.rankdir,
            ordering=self.ordering,
            fontname=self.fontname
        )
    
    def _parse_nodes(self, dot_content: str):
        """解析节点定义"""
        # 匹配节点定义: node_id [label="label", shape="shape", ...];
        # 支持中文节点ID和带空格的节点ID
        # 匹配规则：
        # 1. 带引号的节点ID："..."
        # 2. 不带引号的节点ID：由字母、数字、中文、下划线、空格等组成，直到遇到 [ 或 ;
        node_pattern = r'("[^"]*"|[^\[;]+?)\s*\[\s*label\s*=\s*("[^"]*"|[^\s,\[\]]+)(.*?)\];'
        
        for match in re.finditer(node_pattern, dot_content, re.DOTALL):
            node_id = match.group(1).strip()
            label = match.group(2)
            attributes = match.group(3)
            
            # 去除引号
            if node_id.startswith('"') and node_id.endswith('"'):
                node_id = node_id[1:-1]
            if label.startswith('"') and label.endswith('"'):
                label = label[1:-1]
            
            # 处理转义字符（如 \\n -> \n）
            label = label.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"').replace('\\\\', '\\')
            
            # 解析属性
            shape = self._parse_attribute(attributes, 'shape', 'box')
            color = self._parse_attribute(attributes, 'color', 'black')
            style = self._parse_attribute(attributes, 'style', 'filled')
            fillcolor = self._parse_attribute(attributes, 'fillcolor', 'white')
            fontsize = self._parse_attribute(attributes, 'fontsize', '12')
            fontcolor = self._parse_attribute(attributes, 'fontcolor', 'black')
            fontname = self._parse_attribute(attributes, 'fontname', '')
            
            # 提取节点图标和类型（从label中）
            node_icon = ""
            node_type = ""
            
            # 检查是否有图标标记（如 Ⓜ, ⚡, 等）
            icon_match = re.search(r'^([^\w\s])\s*', label)
            if icon_match:
                node_icon = icon_match.group(1)
            
            # 检查是否有类型信息（如 SuccessOnAll）
            type_match = re.search(r'\n([A-Za-z]+)$', label)
            if type_match:
                node_type = type_match.group(1)
            
            self.nodes[node_id] = DOTNode(
                id=node_id,
                label=label,
                shape=shape,
                color=color,
                style=style,
                fillcolor=fillcolor,
                fontsize=fontsize,
                fontcolor=fontcolor,
                fontname=fontname,
                node_type=node_type,
                node_icon=node_icon
            )
    
    def _parse_edges(self, dot_content: str):
        """解析边定义"""
        # 匹配边定义: from_node -> to_node [label="label", ...];
        # 支持中文节点ID和带引号的节点ID
        # 匹配边定义: from_node -> to_node [label="label", ...];
        # 支持中文节点ID和带空格的节点ID
        # 匹配规则：
        # 1. 带引号的节点ID："..."
        # 2. 不带引号的节点ID：由字母、数字、中文、下划线、空格等组成，直到遇到 -> 或 ;
        edge_pattern = r'("[^"]*"|[^->;]+?)\s*->\s*("[^"]*"|[^->;]+?)(\[.*?\])?;'
        
        for match in re.finditer(edge_pattern, dot_content, re.DOTALL):
            from_node = match.group(1).strip()
            to_node = match.group(2).strip()
            attributes = match.group(3) or ""
            
            # 去除引号
            if from_node.startswith('"') and from_node.endswith('"'):
                from_node = from_node[1:-1]
            if to_node.startswith('"') and to_node.endswith('"'):
                to_node = to_node[1:-1]
            
            # 解析属性
            label = self._parse_attribute(attributes, 'label', '')
            color = self._parse_attribute(attributes, 'color', 'black')
            
            self.edges.append(DOTEdge(
                from_node=from_node,
                to_node=to_node,
                label=label,
                color=color
            ))
    
    def _parse_attribute(self, attributes: str, attr_name: str, default: str) -> str:
        """解析属性值"""
        # 支持带引号和不带引号的属性值
        pattern = rf'{attr_name}\s*=\s*("([^"]*)"|([^\s,]+))'
        match = re.search(pattern, attributes)
        if match:
            # 返回带引号的值或不带引号的值
            return match.group(2) if match.group(2) else match.group(3)
        return default

class DOTHTMLRenderer:
    """DOT HTML渲染器"""
    
    def __init__(self, dot_graph: DOTGraph):
        self.graph = dot_graph
    
    def render(self) -> str:
        """渲染为HTML
        
        Returns:
            HTML字符串
        """
        # 构建树结构
        tree = self._build_tree()
        
        # 生成HTML
        html = self._generate_html(tree)
        
        return html
    
    def _build_tree(self) -> Dict:
        """构建树结构
        
        Returns:
            树结构的字典
        """
        # 找到根节点（没有入边的节点）
        in_degree = {node_id: 0 for node_id in self.graph.nodes}
        for edge in self.graph.edges:
            in_degree[edge.to_node] += 1
        
        root_nodes = [node_id for node_id, degree in in_degree.items() if degree == 0]
        
        if not root_nodes:
            # 如果没有根节点，使用第一个节点
            root_nodes = [list(self.graph.nodes.keys())[0]]
        
        # 构建树
        tree = {
            "root_id": root_nodes[0],
            "nodes": self.graph.nodes,
            "edges": self.graph.edges,
            "children": {}
        }
        
        # 构建子节点映射
        for edge in self.graph.edges:
            if edge.from_node not in tree["children"]:
                tree["children"][edge.from_node] = []
            tree["children"][edge.from_node].append(edge.to_node)
        
        return tree
    
    def _get_node_style(self, node: DOTNode) -> str:
        """获取节点的内联样式
        
        Args:
            node: DOT节点对象
            
        Returns:
            CSS样式字符串
        """
        styles = []
        
        # 应用填充颜色
        if node.fillcolor and node.fillcolor != "white":
            color_map = {
                "orange": "#f97316",
                "gold": "#fbbf24",
                "gray": "#6b7280",
                "green": "#22c55e",
                "red": "#ef4444",
                "blue": "#3b82f6",
                "purple": "#a855f7",
                "pink": "#ec4899"
            }
            bg_color = color_map.get(node.fillcolor.lower(), node.fillcolor)
            styles.append(f"background: {bg_color}")
        
        # 应用字体颜色
        if node.fontcolor and node.fontcolor != "black":
            styles.append(f"color: {node.fontcolor}")
        
        # 应用字体大小
        if node.fontsize and node.fontsize != "12":
            styles.append(f"font-size: {node.fontsize}px")
        
        # 应用字体名称
        if node.fontname:
            styles.append(f"font-family: {node.fontname}")
        
        return "; ".join(styles)
    
    def _generate_html(self, tree: Dict) -> str:
        """生成HTML
        
        Args:
            tree: 树结构
            
        Returns:
            HTML字符串
        """
        # 获取字体名称
        font_family = self.graph.fontname if self.graph.fontname else "'Microsoft YaHei', 'SimHei', Arial, sans-serif"
        
        html = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "    <meta charset='utf-8'>",
            "    <title>行为树可视化 (DOT解析)</title>",
            "    <link rel='stylesheet' href='styles.css'>",
            "    <script src='script.js'></script>",
            "</head>",
            "<body>",
            "    <div class='container'>",
            "        <div class='title'>🌳 行为树可视化</div>",
            "        <div class='tree'>"
        ]
        
        # 递归渲染树
        self._render_node_html(tree["root_id"], tree, html)
        
        html.extend([
            "        </div>",
            "    </div>",
            "</body>",
            "</html>"
        ])
        
        return "\n".join(html)
    
    def _render_node_html(self, node_id: str, tree: Dict, html: List[str]):
        """递归渲染节点HTML
        
        Args:
            node_id: 节点ID
            tree: 树结构
            html: HTML行列表
        """
        if node_id not in tree["nodes"]:
            return
        
        node = tree["nodes"][node_id]
        
        # 添加节点
        html.append("            <div class='node-container'>")
        
        # 根据节点属性设置样式
        node_style = self._get_node_style(node)
        html.append(f"                <div class='node' style='{node_style}'>")
        
        # 解析节点名称、图标和类型
        label = node.label
        node_icon = node.node_icon
        node_type = node.node_type
        
        # 清理label中的图标和类型信息
        display_label = label
        if node_icon:
            display_label = display_label.replace(node_icon, '', 1).strip()
        if node_type:
            display_label = display_label.replace(f'\n{node_type}', '').strip()
        
        # 显示图标和节点名称在同一行
        html.append("                    <div class='node-content'>")
        if node_icon:
            html.append(f"                        <span class='node-icon'>{node_icon}</span>")
        html.append(f"                        <span class='node-name'>{display_label}</span>")
        html.append("                    </div>")
        
        # 显示节点类型
        if node_type:
            html.append(f"                    <div class='node-type'>{node_type}</div>")
        
        html.append("                </div>")
        
        # 递归渲染子节点
        if node_id in tree["children"] and tree["children"][node_id]:
            html.append("                <div class='children-container'>")
            html.append("                    <div class='edge-curve'></div>")
            html.append("                    <div class='edge-horizontal'></div>")
            html.append("                    <div class='children'>")
            
            for child_id in tree["children"][node_id]:
                html.append("                        <div class='child'>")
                html.append("                            <div class='child-edge-curve'></div>")
                self._render_node_html(child_id, tree, html)
                html.append("                        </div>")
            
            html.append("                    </div>")
            html.append("                </div>")
        
        html.append("            </div>")

def parse_dot_file(dot_file_path: str) -> DOTGraph:
    """解析DOT文件
    
    Args:
        dot_file_path: DOT文件路径
        
    Returns:
        DOTGraph对象
    """
    with open(dot_file_path, 'r', encoding='utf-8') as f:
        dot_content = f.read()
    
    parser = DOTParser()
    return parser.parse(dot_content)

def render_dot_to_html(dot_file_path: str, output_html_path: str = None) -> str:
    """将DOT文件渲染为HTML
    
    Args:
        dot_file_path: DOT文件路径
        output_html_path: 输出HTML文件路径（可选）
        
    Returns:
        HTML字符串
    """
    # 解析DOT文件
    dot_graph = parse_dot_file(dot_file_path)
    
    # 渲染为HTML
    renderer = DOTHTMLRenderer(dot_graph)
    html = renderer.render()
    
    # 保存到文件
    if output_html_path:
        # 复制CSS和JavaScript文件到输出目录
        output_dir = os.path.dirname(output_html_path)
        
        # 复制CSS文件
        css_source = os.path.join(os.path.dirname(__file__), 'styles.css')
        css_target = os.path.join(output_dir, 'styles.css')
        if os.path.exists(css_source):
            with open(css_source, 'r', encoding='utf-8') as f:
                css_content = f.read()
            with open(css_target, 'w', encoding='utf-8') as f:
                f.write(css_content)
        
        # 复制JavaScript文件
        js_source = os.path.join(os.path.dirname(__file__), 'script.js')
        js_target = os.path.join(output_dir, 'script.js')
        if os.path.exists(js_source):
            with open(js_source, 'r', encoding='utf-8') as f:
                js_content = f.read()
            with open(js_target, 'w', encoding='utf-8') as f:
                f.write(js_content)
        
        # 保存HTML文件
        with open(output_html_path, 'w', encoding='utf-8') as f:
            f.write(html)
    
    return html

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python dot_parser.py <dot_file> [output_html]")
        sys.exit(1)
    
    dot_file = sys.argv[1]
    output_html = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(dot_file):
        print(f"错误: 文件不存在: {dot_file}")
        sys.exit(1)
    
    html = render_dot_to_html(dot_file, output_html)
    
    if output_html:
        print(f"HTML已保存到: {output_html}")
    else:
        print(html)