"""
文档PDF编译脚本

将Markdown文档编译成PDF格式，支持超链接和目录
"""

import os
from pathlib import Path

try:
    import pypandoc
except ImportError:
    print("错误：未安装pypandoc")
    print("请安装pypandoc：")
    print("  pip install pypandoc")
    exit(1)

def compile_markdown_to_pdf(md_file: str, pdf_file: str = None):
    """
    将Markdown文件编译成PDF
    
    Args:
        md_file: Markdown文件路径
        pdf_file: PDF文件路径（可选，默认与md文件同名）
    """
    if pdf_file is None:
        pdf_file = md_file.replace('.md', '.pdf')
    
    # 检查文件是否存在
    if not os.path.exists(md_file):
        print(f"错误：文件不存在 {md_file}")
        return False
    
    # 检查pypandoc是否可用
    try:
        pypandoc.get_pandoc_version()
    except Exception as e:
        print(f"错误：pypandoc不可用 - {e}")
        print("尝试下载pandoc...")
        try:
            pypandoc.download_pandoc()
            print("✓ pandoc下载成功")
        except Exception as download_error:
            print(f"✗ pandoc下载失败: {download_error}")
            return False
    
    # 编译参数
    extra_args = [
        '--pdf-engine=xelatex',
        '-V', 'geometry:margin=1in',
        '-V', 'colorlinks=true',
        '-V', 'linkcolor=blue',
        '-V', 'urlcolor=blue',
        '-V', 'toc',
        '-V', 'toc-depth=3',
        '--highlight-style', 'pygments'
    ]
    
    try:
        print(f"正在编译: {md_file} -> {pdf_file}")
        pypandoc.convert_file(
            md_file,
            'pdf',
            outputfile=pdf_file,
            extra_args=extra_args
        )
        print(f"✓ 编译成功: {pdf_file}")
        return True
    except Exception as e:
        print(f"✗ 编译失败: {e}")
        return False

def compile_all_docs():
    """编译所有文档"""
    docs_dir = Path(__file__).parent
    md_files = [
        'README.md',
        'USER_GUIDE.md',
        'DEVELOPER_GUIDE.md',
        'cache_system.md'
    ]
    
    print("=== 开始编译文档 ===\n")
    
    success_count = 0
    for md_file in md_files:
        md_path = os.path.join(docs_dir, md_file)
        if os.path.exists(md_path):
            if compile_markdown_to_pdf(md_path):
                success_count += 1
        print()
    
    print(f"=== 编译完成 ===")
    print(f"成功: {success_count}/{len(md_files)}")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        # 编译指定文件
        md_file = sys.argv[1]
        compile_markdown_to_pdf(md_file)
    else:
        # 编译所有文档
        compile_all_docs()
