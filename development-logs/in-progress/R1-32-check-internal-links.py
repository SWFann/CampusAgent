#!/usr/bin/env python3
"""
R1-32: 修复全部内部链接
检查所有 Markdown 文档中的内部链接，验证是否存在
"""

import re
from pathlib import Path
from collections import defaultdict

# 定义需要检查的文档目录
DOCS_DIR = Path('/mnt/f/工作盘/实习经历汇总/星星之火-创业/模型互联网比赛/CampusAgent/docs')

# 收集所有 Markdown 文件
md_files = list(DOCS_DIR.rglob('*.md'))

print(f"找到 {len(md_files)} 个 Markdown 文件")
print()

# 统计内部链接
link_stats = {
    'total_links': 0,
    'valid_links': 0,
    'broken_links': 0,
    'external_links': 0
}

broken_links = []
valid_links_by_doc = defaultdict(list)

# 检查每个文件
for md_file in sorted(md_files):
    try:
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 查找所有 Markdown 链接 [text](url)
        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)

        rel_path = md_file.relative_to(DOCS_DIR.parent)

        for text, url in links:
            link_stats['total_links'] += 1

            # 跳过外部链接
            if url.startswith('http://') or url.startswith('https://'):
                link_stats['external_links'] += 1
                continue

            # 跳过锚点链接（#xxx）
            if url.startswith('#'):
                link_stats['valid_links'] += 1
                valid_links_by_doc[str(rel_path)].append((text, url))
                continue

            # 解析内部链接路径
            if url.startswith('/'):
                # 绝对路径（从根目录开始）
                target_path = DOCS_DIR.parent / url.lstrip('/')
            else:
                # 相对路径
                target_path = (md_file.parent / url).resolve()

                # 移除锚点
                if '#' in str(target_path):
                    target_path = Path(str(target_path).split('#')[0])

            # 检查目标文件是否存在
            if target_path.exists():
                link_stats['valid_links'] += 1
                valid_links_by_doc[str(rel_path)].append((text, url))
            else:
                link_stats['broken_links'] += 1
                broken_links.append({
                    'source': str(rel_path),
                    'text': text,
                    'url': url,
                    'target': str(target_path)
                })

    except Exception as e:
        print(f"⚠️  读取文件失败 {md_file}: {e}")

print("=" * 80)
print("内部链接检查报告")
print("=" * 80)
print(f"总链接数: {link_stats['total_links']}")
print(f"有效链接: {link_stats['valid_links']} ({link_stats['valid_links'] / link_stats['total_links'] * 100:.1f}%)")
print(f"损坏链接: {link_stats['broken_links']} ({link_stats['broken_links'] / link_stats['total_links'] * 100:.1f}%)")
print(f"外部链接: {link_stats['external_links']}")
print()

if broken_links:
    print("=" * 80)
    print(f"损坏的链接 ({len(broken_links)} 个)")
    print("=" * 80)
    for i, link in enumerate(broken_links, 1):
        print(f"\n{i}. 源文件: {link['source']}")
        print(f"   链接文本: {link['text']}")
        print(f"   链接地址: {link['url']}")
        print(f"   目标路径: {link['target']}")
else:
    print("✅ 所有内部链接都有效！")

print()
print("=" * 80)
print("按文档统计（前 10 个）")
print("=" * 80)

sorted_docs = sorted(valid_links_by_doc.items(), key=lambda x: len(x[1]), reverse=True)
for doc_path, links in sorted_docs[:10]:
    print(f"\n{doc_path}: {len(links)} 个链接")
    for text, url in links[:3]:
        print(f"  - [{text}]({url})")
    if len(links) > 3:
        print(f"  ... 还有 {len(links) - 3} 个链接")
