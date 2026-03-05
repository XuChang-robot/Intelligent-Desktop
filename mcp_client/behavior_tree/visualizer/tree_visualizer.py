import py_trees
import logging
from typing import Optional, List

class TreeVisualizer:
    """行为树可视化工具
    
    提供多种格式的行为树可视化输出。
    
    注意：
    - ASCII 和 DOT 格式的可视化已被 py-trees 自带功能替换，
      建议使用 py_trees.display.ascii_tree() 和 py_trees.display.dot_tree()
    - 本工具保留 HTML 格式和执行路径渲染功能
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def render_ascii(self, root: py_trees.behaviour.Behaviour, 
                  execution_path: Optional[List[str]] = None) -> str:
        """渲染 ASCII 格式的行为树（使用 py-trees 自带功能）
        
        Args:
            root: 行为树根节点
            execution_path: 执行路径（用于高亮）
        
        Returns:
            ASCII 格式的树字符串
        """
        self.logger.info("渲染 ASCII 格式的行为树（使用 py-trees 自带功能）")
        try:
            return py_trees.display.ascii_tree(root)
        except Exception as e:
            self.logger.error(f"使用 py-trees 渲染 ASCII 失败: {e}")
            # 回退到简单的文本表示
            return self._render_simple_text(root)
    
    def render_dot(self, root: py_trees.behaviour.Behaviour,
                 execution_path: Optional[List[str]] = None) -> str:
        """渲染 Graphviz DOT 格式的行为树（使用 py-trees 自带功能）
        
        Args:
            root: 行为树根节点
            execution_path: 执行路径（用于高亮）
        
        Returns:
            DOT 格式的字符串
        """
        self.logger.info("渲染 DOT 格式的行为树（使用 py-trees 自带功能）")
        try:
            # 使用 dot_tree 函数生成 DOT 对象
            dot_content = py_trees.display.dot_tree(root)
            self.logger.info("使用 py_trees.display.dot_tree()  生成 DOT 对象")
            
            # 确保返回的是字符串
            if isinstance(dot_content, str):
                dot_source = dot_content
            elif hasattr(dot_content, 'to_string'):
                # 使用 to_string() 方法获取字符串表示
                dot_source = dot_content.to_string()
            elif hasattr(dot_content, 'source'):
                dot_source = dot_content.source
            elif hasattr(dot_content, '__str__'):
                dot_source = str(dot_content)
            else:
                raise ValueError("无法获取 DOT 源代码")
            
            # 只添加字体配置，不修改其他内容
            lines = dot_source.split('\n')
            modified_lines = []
            font_config_added = False
            
            for line in lines:
                # 跳过原有的字体配置行
                if not (('fontname' in line) and ('[' in line)):
                    modified_lines.append(line)
                    # 只在 graph 定义后添加一次字体配置
                    if not font_config_added and (line.strip().startswith('digraph') or line.strip().startswith('graph')):
                        # 添加字体配置，使用多种中文字体作为备选
                        modified_lines.append('    graph [fontname="SimHei,Microsoft YaHei,Heiti TC,WenQuanYi Micro Hei,sans-serif"];')
                        modified_lines.append('    node [fontname="SimHei,Microsoft YaHei,Heiti TC,WenQuanYi Micro Hei,sans-serif"];')
                        modified_lines.append('    edge [fontname="SimHei,Microsoft YaHei,Heiti TC,WenQuanYi Micro Hei,sans-serif"];')
                        font_config_added = True
            
            dot_source = '\n'.join(modified_lines)
            
            return dot_source
        except Exception as e:
            self.logger.error(f"使用 py-trees 渲染 DOT 失败: {e}")
            # 回退到简单的 DOT 表示
            return self._render_simple_dot(root)
    
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
            "        * {",
            "            margin: 0;",
            "            padding: 0;",
            "            box-sizing: border-box;",
            "        }",
            "        body {",
            "            font-family: Arial, sans-serif;",
            "            font-size: 14px;",
            "            line-height: 1.5;",
            "            background-color: #f5f5f5;",
            "            padding: 20px;",
            "        }",
            "        .tree {",
            "            display: flex;",
            "            flex-direction: column;",
            "            align-items: center;",
            "            padding: 20px;",
            "        }",
            "        .node-container {",
            "            display: flex;",
            "            flex-direction: column;",
            "            align-items: center;",
            "            margin: 10px 0;",
            "        }",
            "        .node {",
            "            display: inline-block;",
            "            border: 1px solid #ccc;",
            "            border-radius: 8px;",
            "            padding: 10px 15px;",
            "            margin: 10px;",
            "            background-color: #ffffff;",
            "            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);",
            "            min-width: 180px;",
            "            text-align: center;",
            "            position: relative;",
            "        }",
            "        .node.executed {",
            "            background-color: #e8f5e8;",
            "            border-color: #4caf50;",
            "            box-shadow: 0 2px 4px rgba(76, 175, 80, 0.2);",
            "        }",
            "        .node-name {",
            "            font-weight: bold;",
            "            margin-bottom: 5px;",
            "            word-wrap: break-word;",
            "        }",
            "        .node-type {",
            "            font-size: 12px;",
            "            color: #666;",
            "        }",
            "        .children-container {",
            "            display: flex;",
            "            flex-direction: column;",
            "            align-items: center;",
            "            margin-top: 5px;",
            "            width: 100%;",
            "        }",
            "        .children {",
            "            display: flex;",
            "            flex-direction: row;",
            "            justify-content: center;",
            "            align-items: flex-start;",
            "            margin-top: 5px;",
            "            flex-wrap: nowrap;",
            "        }",
            "        .child {",
            "            display: flex;",
            "            flex-direction: column;",
            "            align-items: center;",
            "            margin: 0 15px;",
            "            position: relative;",
            "        }",
            "        .edge {",
            "            width: 2px;",
            "            height: 20px;",
            "            background-color: #ccc;",
            "            margin: 0 auto;",
            "        }",
            "        .edge-horizontal {",
            "            width: 100%;",
            "            height: 2px;",
            "            background-color: #ccc;",
            "            margin: 0;",
            "        }",
            "        .child-edge {",
            "            width: 2px;",
            "            height: 20px;",
            "            background-color: #ccc;",
            "            margin: 0 auto;",
            "        }",
            "        .children-line {",
            "            display: flex;",
            "            align-items: center;",
            "            margin-top: 10px;",
            "        }",
            "        @media (max-width: 1200px) {",
            "            .children {",
            "                flex-wrap: wrap;",
            "            }",
            "            .child {",
            "                margin: 10px;",
            "            }",
            "        }",
            "        @media (max-width: 768px) {",
            "            .node {",
            "                min-width: 150px;",
            "                padding: 8px 12px;",
            "            }",
            "            .children {",
            "                flex-direction: column;",
            "                align-items: center;",
            "            }",
            "            .child {",
            "                margin: 10px 0;",
            "            }",
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
        lines.append("        <div class='node-container'>")
        lines.append(f"            <div class='node {executed_class}'>")
        lines.append(f"                <div class='node-name'>{node.name}</div>")
        lines.append(f"                <div class='node-type'>{node_type}</div>")
        lines.append("            </div>")
        
        # 递归渲染子节点
        if hasattr(node, 'children') and node.children:
            lines.append("            <div class='children-container'>")
            lines.append("                <div class='edge'></div>")
            lines.append("                <div class='edge-horizontal'></div>")
            lines.append("                <div class='children'>")
            for child in node.children:
                lines.append("                    <div class='child'>")
                lines.append("                        <div class='child-edge'></div>")
                self._render_node_html(child, lines, execution_path)
                lines.append("                    </div>")
            lines.append("                </div>")
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
    
    def _render_simple_text(self, node: py_trees.behaviour.Behaviour, indent: int = 0) -> str:
        """简单的文本表示（回退方案）
        
        Args:
            node: 当前节点
            indent: 缩进级别
        
        Returns:
            文本表示字符串
        """
        lines = []
        prefix = "  " * indent
        lines.append(f"{prefix}{node.name} ({type(node).__name__})")
        
        if hasattr(node, 'children') and node.children:
            for child in node.children:
                lines.append(self._render_simple_text(child, indent + 1))
        
        return "\n".join(lines)
    
    def _render_simple_dot(self, node: py_trees.behaviour.Behaviour) -> str:
        """简单的 DOT 表示（回退方案）
        
        Args:
            node: 当前节点
        
        Returns:
            DOT 格式字符串
        """
        lines = [
            "digraph BehaviorTree {",
            "    rankdir=TB;",
            "    graph [fontname=\"SimHei,Microsoft YaHei,Heiti TC,WenQuanYi Micro Hei,sans-serif\"];",
            "    node [fontname=\"SimHei,Microsoft YaHei,Heiti TC,WenQuanYi Micro Hei,sans-serif\"];",
            "    edge [fontname=\"SimHei,Microsoft YaHei,Heiti TC,WenQuanYi Micro Hei,sans-serif\"];",
            ""
        ]
        
        self._render_simple_dot_node(node, lines)
        
        lines.append("}")
        return "\n".join(lines)
    
    def _render_simple_dot_node(self, node: py_trees.behaviour.Behaviour,
                              lines: List[str],
                              parent_id: Optional[str] = None):
        """递归渲染简单的 DOT 节点
        
        Args:
            node: 当前节点
            lines: 输出行列表
            parent_id: 父节点 ID
        """
        node_id = node.name.replace(" ", "_")
        
        # 根据节点类型设置不同的形状
        node_type = type(node).__name__
        shape = "ellipse"  # 默认形状
        
        if "Sequence" in node_type:
            shape = "ellipse"  # 顺序节点使用椭圆
        elif "Selector" in node_type:
            shape = "diamond"  # 选择节点使用菱形
        elif "Parallel" in node_type:
            shape = "parallelogram"  # 并行节点使用平行四边形
        
        # 添加节点定义
        lines.append(f'    "{node_id}" [label="{node.name}", shape={shape}];')
        
        # 添加边
        if parent_id:
            lines.append(f'    "{parent_id}" -> "{node_id}";')
        
        # 递归渲染子节点
        if hasattr(node, 'children') and node.children:
            for child in node.children:
                self._render_simple_dot_node(child, lines, node_id)
