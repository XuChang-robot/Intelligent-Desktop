import py_trees
import logging
from typing import Optional, List

class TreeVisualizer:
    """行为树可视化工具
    
    提供多种格式的行为树可视化输出。
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def render_ascii(self, root: py_trees.behaviour.Behaviour, 
                  execution_path: Optional[List[str]] = None) -> str:
        """渲染 ASCII 格式的行为树
        
        Args:
            root: 行为树根节点
            execution_path: 执行路径（用于高亮）
        
        Returns:
            ASCII 格式的树字符串
        """
        self.logger.info("渲染 ASCII 格式的行为树")
        lines = []
        self._render_node_ascii(root, lines, "", execution_path)
        return "\n".join(lines)
    
    def _render_node_ascii(self, node: py_trees.behaviour.Behaviour, 
                         lines: List[str], prefix: str,
                         execution_path: Optional[List[str]] = None):
        """递归渲染节点
        
        Args:
            node: 当前节点
            lines: 输出行列表
            prefix: 前缀字符串
            execution_path: 执行路径
        """
        # 判断是否在执行路径中
        is_executed = execution_path and (node.id in execution_path if hasattr(node, 'id') else node.name in execution_path)
        
        # 构建节点标识
        node_type = type(node).__name__
        status_marker = "✓" if is_executed else " "
        
        # 添加节点行
        lines.append(f"{prefix}[{status_marker}] {node.name} ({node_type})")
        
        # 递归渲染子节点
        if hasattr(node, 'children') and node.children:
            for i, child in enumerate(node.children):
                is_last = i == len(node.children) - 1
                child_prefix = prefix + ("    " if is_last else "│   ")
                connector = "└── " if is_last else "├── "
                self._render_node_ascii(child, lines, prefix + connector, execution_path)
    
    def render_dot(self, root: py_trees.behaviour.Behaviour,
                 execution_path: Optional[List[str]] = None) -> str:
        """渲染 Graphviz DOT 格式的行为树
        
        Args:
            root: 行为树根节点
            execution_path: 执行路径（用于高亮）
        
        Returns:
            DOT 格式的字符串
        """
        self.logger.info("渲染 DOT 格式的行为树")
        
        lines = [
            "digraph BehaviorTree {",
            "    rankdir=TB;",
            "    node [shape=box, style=rounded];",
            ""
        ]
        
        self._render_node_dot(root, lines, execution_path)
        
        lines.append("}")
        return "\n".join(lines)
    
    def _render_node_dot(self, node: py_trees.behaviour.Behaviour,
                       lines: List[str],
                       execution_path: Optional[List[str]] = None):
        """递归渲染 DOT 节点
        
        Args:
            node: 当前节点
            lines: 输出行列表
            execution_path: 执行路径
        """
        node_id = node.id if hasattr(node, 'id') else node.name.replace(" ", "_")
        node_type = type(node).__name__
        
        # 判断是否在执行路径中
        is_executed = execution_path and (node_id in execution_path)
        
        # 设置节点样式
        color = "lightgreen" if is_executed else "lightblue"
        style = "filled,rounded"
        
        # 添加节点定义
        lines.append(f'    "{node_id}" [label="{node.name}\\n({node_type})", fillcolor={color}, style={style}];')
        
        # 递归渲染子节点
        if hasattr(node, 'children') and node.children:
            for child in node.children:
                child_id = child.id if hasattr(child, 'id') else child.name.replace(" ", "_")
                lines.append(f'    "{node_id}" -> "{child_id}";')
                self._render_node_dot(child, lines, execution_path)
    
    def render_html(self, root: py_trees.behaviour.Behaviour,
                   execution_path: Optional[List[str]] = None) -> str:
        """渲染 HTML 格式的行为树
        
        Args:
            root: 行为树根节点
            execution_path: 执行路径（用于高亮）
        
        Returns:
            HTML 格式的字符串
        """
        self.logger.info("渲染 HTML 格式的行为树")
        
        html = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "    <meta charset='utf-8'>",
            "    <title>行为树可视化</title>",
            "    <style>",
            "        .tree {",
            "            font-family: Arial, sans-serif;",
            "            font-size: 14px;",
            "            line-height: 1.5;",
            "        }",
            "        .node {",
            "            display: inline-block;",
            "            border: 1px solid #ccc;",
            "            border-radius: 5px;",
            "            padding: 8px 12px;",
            "            margin: 5px;",
            "            background-color: #f0f0f0;",
            "        }",
            "        .node.executed {",
            "            background-color: #90EE90;",
            "            border-color: #228B22;",
            "        }",
            "        .node-type {",
            "            font-size: 12px;",
            "            color: #666;",
            "            margin-top: 4px;",
            "        }",
            "        .children {",
            "            display: flex;",
            "            flex-direction: row;",
            "            justify-content: center;",
            "            margin-top: 20px;",
            "        }",
            "        .child {",
            "            margin: 0 10px;",
            "        }",
            "        .edge {",
            "            border-left: 1px solid #ccc;",
            "            height: 20px;",
            "            margin: 0 auto;",
            "        }",
            "    </style>",
            "</head>",
            "<body>",
            "    <div class='tree'>",
            ""
        ]
        
        self._render_node_html(root, html, execution_path)
        
        html.extend([
            "    </div>",
            "</body>",
            "</html>"
        ])
        
        return "\n".join(html)
    
    def _render_node_html(self, node: py_trees.behaviour.Behaviour,
                        lines: List[str],
                        execution_path: Optional[List[str]] = None):
        """递归渲染 HTML 节点
        
        Args:
            node: 当前节点
            lines: 输出行列表
            execution_path: 执行路径
        """
        node_id = node.id if hasattr(node, 'id') else node.name.replace(" ", "_")
        node_type = type(node).__name__
        
        # 判断是否在执行路径中
        is_executed = execution_path and (node_id in execution_path)
        
        # 添加节点
        executed_class = "executed" if is_executed else ""
        lines.append(f"        <div class='node {executed_class}'>")
        lines.append(f"            <strong>{node.name}</strong>")
        lines.append(f"            <div class='node-type'>{node_type}</div>")
        lines.append("        </div>")
        
        # 递归渲染子节点
        if hasattr(node, 'children') and node.children:
            lines.append("        <div class='children'>")
            for child in node.children:
                lines.append("            <div class='child'>")
                lines.append("                <div class='edge'></div>")
                self._render_node_html(child, lines, execution_path)
                lines.append("            </div>")
            lines.append("        </div>")
    
    def render_execution_path(self, execution_path: List[str], 
                           results: List[dict]) -> str:
        """渲染执行路径
        
        Args:
            execution_path: 执行路径
            results: 执行结果列表
        
        Returns:
            执行路径字符串
        """
        self.logger.info("渲染执行路径")
        
        lines = ["执行路径：", ""]
        
        for i, node_id in enumerate(execution_path):
            # 查找对应的结果
            result = next((r for r in results if r.get("node_id") == node_id), None)
            
            # 添加步骤
            lines.append(f"{i+1}. {node_id}")
            
            if result:
                node_name = result.get("node_name", "")
                node_result = result.get("result", {})
                success = node_result.get("success", True)
                status = "✓ 成功" if success else "✗ 失败"
                
                lines.append(f"   节点: {node_name}")
                lines.append(f"   状态: {status}")
                
                if not success:
                    error = node_result.get("error", "未知错误")
                    lines.append(f"   错误: {error}")
                
                lines.append("")
        
        return "\n".join(lines)
