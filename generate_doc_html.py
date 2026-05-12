#!/usr/bin/env python3
"""
生成墨韵完整文档单页HTML - 修复版
将所有.md文档转换为HTML并嵌入同一个文件
"""

import os
import re
from pathlib import Path

# 尝试导入markdown库
try:
    import markdown
    from markdown.extensions import tables, fenced_code
    MD_AVAILABLE = True
except ImportError:
    MD_AVAILABLE = False
    print("警告: markdown库不可用，将使用基础HTML转义")

PROJECT_ROOT = r"D:\newmoyun"

DOCUMENTS = [
    (r"CLAUDE.md", "CLAUDE.md", "claude"),
    (r"CONTEXT.md", "CONTEXT.md", "context"),
    (r"产品说明.md", "产品说明", "product"),
    (r"docs\功能清单.md", "功能清单", "features"),
    (r"docs\文件系统设计.md", "文件系统设计", "filesystem"),
    (r"docs\API契约.md", "API契约", "api"),
    (r"docs\后端架构设计.md", "后端架构设计", "backend"),
    (r"docs\Prompt模板说明.md", "Prompt模板说明", "prompts"),
    (r"docs\开发步骤.md", "开发步骤", "devsteps"),
    (r"docs\文档索引.md", "文档索引", "index"),
]

CSS = """:root {
    --bg-primary: #1a1a2e;
    --bg-secondary: #16213e;
    --bg-card: #0f3460;
    --accent-primary: #3b82f6;
    --accent-secondary: #4ade80;
    --text-primary: #e2e8f0;
    --text-secondary: #94a3b8;
    --border-color: #2a2a4a;
    --code-bg: #0d1117;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    display: flex;
    min-height: 100vh;
}

.sidebar {
    width: 280px;
    min-width: 280px;
    background: var(--bg-secondary);
    border-right: 1px solid var(--border-color);
    display: flex;
    flex-direction: column;
    position: sticky;
    top: 0;
    height: 100vh;
    overflow-y: auto;
}

.sidebar-header {
    padding: 20px;
    border-bottom: 1px solid var(--border-color);
}

.sidebar-header h1 {
    font-size: 20px;
    color: var(--accent-secondary);
}

.sidebar-header p {
    font-size: 12px;
    color: var(--text-secondary);
    margin-top: 4px;
}

.nav-section {
    padding: 12px 16px 4px;
    font-size: 11px;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 1px;
}

.nav-item {
    display: block;
    padding: 8px 16px;
    color: var(--text-primary);
    text-decoration: none;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s;
    border-left: 3px solid transparent;
}

.nav-item:hover {
    background: rgba(59, 130, 246, 0.1);
    border-left-color: var(--accent-primary);
}

.nav-item.active {
    background: rgba(59, 130, 246, 0.15);
    border-left-color: var(--accent-primary);
    color: var(--accent-primary);
}

.content {
    flex: 1;
    overflow-y: auto;
    padding: 32px;
    height: 100vh;
}

.doc-section {
    display: none;
    animation: fadeIn 0.3s;
}

.doc-section.active {
    display: block;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.md-content h1 {
    font-size: 28px;
    color: var(--accent-secondary);
    margin: 24px 0 16px;
    padding-bottom: 8px;
    border-bottom: 2px solid var(--border-color);
}

.md-content h2 {
    font-size: 22px;
    color: var(--accent-primary);
    margin: 20px 0 12px;
}

.md-content h3 {
    font-size: 18px;
    color: var(--text-primary);
    margin: 16px 0 8px;
}

.md-content p {
    line-height: 1.8;
    margin: 8px 0;
    color: var(--text-primary);
}

.md-content ul, .md-content ol {
    margin: 8px 0 8px 24px;
}

.md-content li {
    line-height: 1.8;
    margin: 4px 0;
}

.md-content code {
    background: #2d2d5e;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 13px;
    color: #fbbf24;
}

.md-content pre {
    background: var(--code-bg);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 16px;
    overflow-x: auto;
    margin: 12px 0;
}

.md-content pre code {
    background: none;
    padding: 0;
    color: var(--text-primary);
    font-size: 13px;
    line-height: 1.6;
}

.md-content table {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 14px;
}

.md-content th {
    background: var(--bg-card);
    padding: 8px 12px;
    text-align: left;
    border: 1px solid var(--border-color);
    color: var(--accent-primary);
}

.md-content td {
    padding: 8px 12px;
    border: 1px solid var(--border-color);
    color: var(--text-secondary);
}

.md-content tr:nth-child(even) {
    background: rgba(15, 52, 96, 0.3);
}

.md-content blockquote {
    border-left: 4px solid var(--accent-primary);
    padding: 8px 16px;
    margin: 12px 0;
    background: rgba(59, 130, 246, 0.05);
    color: var(--text-secondary);
}

.md-content hr {
    border: none;
    border-top: 1px solid var(--border-color);
    margin: 24px 0;
}

.md-content strong {
    color: var(--accent-secondary);
}

@media (max-width: 768px) {
    body { flex-direction: column; }
    .sidebar { width: 100%; min-width: 100%; height: auto; }
    .content { height: auto; }
}
"""

def read_md(filepath):
    full = os.path.join(PROJECT_ROOT, filepath)
    if os.path.exists(full):
        with open(full, 'r', encoding='utf-8') as f:
            return f.read()
    return f"# 错误\n\n文件不存在: {filepath}"

def md_to_html(text):
    if MD_AVAILABLE:
        try:
            extensions = ['tables', 'fenced_code', 'toc', 'nl2br']
            return markdown.markdown(text, extensions=extensions)
        except Exception as e:
            print(f"Markdown转换失败: {e}")
    # 备用简单转换
    return simple_convert(text)

def simple_convert(text):
    lines = text.split('\n')
    out = []
    in_code = False
    code_buf = []
    for line in lines:
        if line.startswith('```'):
            if in_code:
                out.append('<pre><code>' + escape_h(''.join(code_buf)) + '</code></pre>')
                code_buf = []
                in_code = False
            else:
                in_code = True
                code_buf = []
            continue
        if in_code:
            code_buf.append(line + '\n')
            continue
        if line.startswith('# '):
            out.append('<h1>' + inline_md(line[2:]) + '</h1>')
        elif line.startswith('## '):
            out.append('<h2>' + inline_md(line[3:]) + '</h2>')
        elif line.startswith('### '):
            out.append('<h3>' + inline_md(line[4:]) + '</h3>')
        elif line.startswith('#### '):
            out.append('<h4>' + inline_md(line[5:]) + '</h4>')
        elif line.strip() == '---':
            out.append('<hr>')
        elif line.strip().startswith('|'):
            out.append('<p>' + escape_h(line) + '</p>')
        elif line.strip().startswith('> '):
            out.append('<blockquote>' + inline_md(line.strip()[2:]) + '</blockquote>')
        elif line.strip() == '':
            out.append('<p></p>')
        else:
            out.append('<p>' + inline_md(line) + '</p>')
    return '\n'.join(out)

def inline_md(s):
    s = escape_h(s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'`(.+?)`', r'<code>\1</code>', s)
    return s

def escape_h(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def main():
    print("开始生成完整文档HTML...")
    
    # 读取并转换所有文档
    docs = []
    for filepath, title, docid in DOCUMENTS:
        print(f"  处理: {filepath}")
        md_text = read_md(filepath)
        html = md_to_html(md_text)
        docs.append((docid, title, html))
    
    # 生成导航
    nav_items = []
    for i, (docid, title, _) in enumerate(docs):
        cls = 'nav-item active' if i == 0 else 'nav-item'
        nav_items.append(f'<a class="{cls}" onclick="showDoc(\'{docid}\')">{title}</a>')
    
    # 生成内容区
    sections = []
    for i, (docid, _, html) in enumerate(docs):
        cls = 'doc-section active' if i == 0 else 'doc-section'
        sections.append(f'<div class="{cls}" id="doc-{docid}"><div class="md-content">{html}</div></div>')
    
    # 组合完整HTML
    html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>墨韵 - 完整项目文档</title>
    <style>{CSS}</style>
</head>
<body>
    <div class="sidebar">
        <div class="sidebar-header">
            <h1>📖 墨韵文档</h1>
            <p>AI小说创作助手 - 完整项目文档</p>
        </div>
        <div class="nav-section">项目文档</div>
        {''.join(nav_items)}
    </div>

    <div class="content" id="content">
        {''.join(sections)}
    </div>

    <script>
        function showDoc(docId) {{
            document.querySelectorAll('.doc-section').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
            const target = document.getElementById('doc-' + docId);
            if (target) {{
                target.classList.add('active');
            }}
            event.target.classList.add('active');
            location.hash = docId;
        }}
        
        window.addEventListener('DOMContentLoaded', () => {{
            if (location.hash) {{
                const docId = location.hash.slice(1);
                const el = document.querySelector(`.nav-item[onclick*="${{docId}}"]`);
                if (el) el.click();
            }}
        }});
    </script>
</body>
</html>'''
    
    # 写入文件
    output = os.path.join(PROJECT_ROOT, 'docs', '项目完整文档.html')
    with open(output, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    size_kb = len(html_content) / 1024
    print(f"\n✓ 文件已生成: {output}")
    print(f"  文件大小: {size_kb:.1f} KB")
    print(f"  文档数量: {len(docs)} 个")

if __name__ == '__main__':
    main()
