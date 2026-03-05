#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
行为树可视化脚本
用于将已生成的行为树配置文件可视化

用法:
    python visualize_behavior_tree.py [options]

选项:
    -h, --help              显示帮助信息
    -f CONFIG, --file CONFIG
                            行为树配置文件路径 (默认: test_behavior_tree_config.json)
    -c FORMATS, --formats FORMATS
                            输出格式，多个格式用逗号分隔 (默认: ascii,dot,png)
                            支持的格式: ascii, dot, png, svg
    -o OUTPUT_DIR, --output-dir OUTPUT_DIR
                            输出文件目录 (默认: 当前目录)
"""

import argparse
import json
import logging
import os
import py_trees
import subprocess
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from mcp_client.behavior_tree import BehaviorTree
from user_config.config import get_config
from utils.logging_config import get_logger

# 获取配置
visualization_dir = get_config("logging.visualization_dir", "logs/visualizations")

# 配置日志
logger = get_logger(__name__, "visualize")

def visualize_behavior_tree(config_file, output_formats, output_dir):
    """
    可视化行为树配置文件
    
    Args:
        config_file: 行为树配置文件路径
        output_formats: 输出格式列表
        output_dir: 输出文件目录
    """
    logger.info(f"开始可视化行为树配置文件: {config_file}")
    
    # 从输入文件路径提取基础文件名（不含扩展名）
    base_name = os.path.splitext(os.path.basename(config_file))[0]
    logger.info(f"输出文件基础名: {base_name}")
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"输出目录: {output_dir}")
    
    # 加载配置文件
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            tree_config = json.load(f)
        logger.info("配置文件加载成功")
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return False
    
    # 初始化行为树
    behavior_tree = BehaviorTree()
    
    # 从配置构建行为树
    try:
        behavior_tree.build_from_config(tree_config)
        logger.info("行为树构建成功")
    except Exception as e:
        logger.error(f"行为树构建失败: {e}")
        return False
    
    # 获取行为树根节点
    root = behavior_tree.get_tree()
    if not root:
        logger.error("无法获取行为树根节点")
        return False
    
    # 生成可视化结果
    success = True
    
    # 导入 TreeVisualizer 类
    from mcp_client.behavior_tree.visualizer.tree_visualizer import TreeVisualizer
    visualizer = TreeVisualizer()
    
    # 处理 ASCII 格式（使用 TreeVisualizer）
    if "ascii" in output_formats:
        try:
            logger.info("生成 ascii 格式的可视化结果（使用 TreeVisualizer）")
            ascii_tree = visualizer.render_ascii(root)
            output_file = os.path.join(output_dir, f"{base_name}.ascii")
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(ascii_tree)
            logger.info(f"ascii 格式的可视化结果已保存到: {output_file}")
        except Exception as e:
            logger.error(f"生成 ascii 格式失败: {e}")
            success = False
    
    # 处理 DOT 格式和图片格式
    if any(fmt in output_formats for fmt in ["dot", "png", "svg"]):
        try:
            logger.info("生成 DOT 格式的行为树（使用 TreeVisualizer）")
            # 使用 TreeVisualizer.render_dot() 方法生成 DOT 格式
            dot_source = visualizer.render_dot(root)
            
            # 直接使用 TreeVisualizer 生成的 DOT 格式，它已经包含了中文字体配置
            if not dot_source:
                raise ValueError("无法获取 DOT 源代码")
            
            if dot_source is None:
                raise ValueError("无法获取 DOT 源代码")
            
            # 如果需要保存 DOT 文件
            if "dot" in output_formats:
                output_file = os.path.join(output_dir, f"{base_name}.dot")
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(dot_source)
                logger.info(f"DOT 格式的可视化结果已保存到: {output_file}")
            
            # 处理图片格式
            for fmt in ["png", "svg"]:
                if fmt in output_formats:
                    try:
                        logger.info(f"生成 {fmt} 格式的可视化结果")
                        
                        # 保存 DOT 文件，以便用户可以手动使用 Graphviz 转换
                        dot_file = os.path.join(output_dir, f"{base_name}.dot")
                        if not os.path.exists(dot_file):
                            with open(dot_file, "w", encoding="utf-8") as f:
                                f.write(dot_source)
                        
                        # 尝试使用 graphviz 库
                        try:
                            import graphviz
                            source = graphviz.Source(dot_source)
                            output_file = os.path.join(output_dir, f"{base_name}.{fmt}")
                            source.render(filename=base_name, directory=output_dir, format=fmt, cleanup=True)
                            logger.info(f"{fmt} 格式的可视化结果已保存到: {output_file}")
                        except Exception as e:
                            logger.warning(f"使用 graphviz 库渲染失败: {e}")
                            logger.info(f"已保存 DOT 文件，请手动使用 Graphviz 转换为 {fmt} 格式:")
                            logger.info(f"dot -T{fmt} {dot_file} -o {base_name}.{fmt}")
                            
                            # 尝试其他常见的 Graphviz 安装路径
                            common_paths = [
                                "C:\\Program Files\\Graphviz\\bin\\dot.exe",
                                "C:\\Program Files (x86)\\Graphviz\\bin\\dot.exe",
                                "D:\\Program Files\\Graphviz\\bin\\dot.exe",
                                "D:\\Program Files (x86)\\Graphviz\\bin\\dot.exe"
                            ]
                            
                            for dot_path in common_paths:
                                if os.path.exists(dot_path):
                                    try:
                                        output_file = os.path.join(output_dir, f"{base_name}.{fmt}")
                                        subprocess.run(
                                            [dot_path, '-T' + fmt, dot_file, '-o', output_file],
                                            check=True,
                                            capture_output=True,
                                            text=True
                                        )
                                        logger.info(f"使用找到的 Graphviz 执行文件成功生成 {fmt} 格式:")
                                        logger.info(f"{fmt} 格式的可视化结果已保存到: {output_file}")
                                        break
                                    except Exception as e:
                                        logger.warning(f"使用路径 {dot_path} 失败: {e}")
                    except Exception as e:
                        logger.warning(f"生成 {fmt} 格式失败: {e}")
                        logger.info(f"已保存 DOT 文件，请手动使用 Graphviz 转换为 {fmt} 格式")
        except Exception as e:
            logger.error(f"生成 DOT 格式失败: {e}")
            success = False
    
    if success:
        logger.info("行为树可视化完成！")
    else:
        logger.warning("行为树可视化部分失败！")
    
    return success

def main():
    """
    主函数
    """
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="行为树可视化脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 使用默认配置文件和输出格式
    python visualize_behavior_tree.py
    
    # 指定配置文件（相对路径基于 logs 目录）
    python visualize_behavior_tree.py -f my_behavior_tree.json
    
    # 指定输出格式
    python visualize_behavior_tree.py -c png
    
    # 指定输出目录
    python visualize_behavior_tree.py -o visualization_output
    """
    )
    
    parser.add_argument(
        "-f", "--file",
        required=True,
        help="行为树配置文件路径（相对路径基于 logs 目录）"
    )
    
    parser.add_argument(
        "-c", "--formats",
        default="ascii,dot,png",
        help="输出格式，多个格式用逗号分隔 (默认: ascii,dot,png)"
    )
    
    parser.add_argument(
        "-o", "--output-dir",
        default=visualization_dir,
        help=f"输出文件目录 (默认: {visualization_dir})"
    )
    
    args = parser.parse_args()
    
    # 处理输出格式
    output_formats = [fmt.strip() for fmt in args.formats.split(",")]
    
    # 验证输出格式
    supported_formats = ["ascii", "dot", "png", "svg"]
    invalid_formats = [fmt for fmt in output_formats if fmt not in supported_formats]
    if invalid_formats:
        logger.error(f"不支持的格式: {', '.join(invalid_formats)}")
        logger.error(f"支持的格式: {', '.join(supported_formats)}")
        return
    
    # 处理配置文件路径：如果是相对路径，基于 logs 目录解析
    config_file = args.file
    if not os.path.isabs(config_file):
        logs_dir = os.path.join(str(project_root), "logs")
        config_file = os.path.join(logs_dir, config_file)
    
    # 处理输出目录路径：如果是相对路径，基于项目根目录解析
    output_dir = args.output_dir
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(str(project_root), output_dir)
    
    # 运行可视化
    success = visualize_behavior_tree(config_file, output_formats, output_dir)
    
    if success:
        logger.info("\n查看结果:")
        logger.info("- ASCII 格式: 在文本编辑器中打开查看")
        logger.info("- DOT 格式: 使用 Graphviz 工具转换为图片")
        logger.info("- PNG/SVG 格式: 直接查看生成的图片文件")

if __name__ == "__main__":
    main()