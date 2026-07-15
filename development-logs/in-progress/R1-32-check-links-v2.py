#!/usr/bin/env python3
"""
R1-32: 修复全部内部链接 - 修订版（正确处理锚点）
"""

import re
from pathlib import Path
from collections import defaultdict

DOCS_DIR = Path('/mnt/f/工作盘/实习经历汇总/星星之火-创业/模型互联网比赛/CampusAgent/docs')
ROOT_DIR = DOCS_DIR.parent

md_files = list(DOCS_DIR.rglob('*.md'))

print(f"找到 {len(md_files)} 个 Markdown 文件")
print()

link_stats = {
    'total_links': 0,
    'valid_links': 0,
    'broken_links': 0,
    'external_links': 0
}

broken_links = []

for md_file in sorted(md_files):
    try:
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()

        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
        rel_path = md_file.relative_to(ROOT_DIR)

        for text, url in links:
            link_stats['total_links'] += 1

            # 跳过外部链接
            if url.startswith('http://') or url.startswith('https://'):
                link_stats['external_links'] += 1
                continue

            # 跳过纯锚点链接
            if url.startswith('#'):
                link_stats['valid_links'] += 1
                continue

            # 分离路径和锚点
            path_part = url
            anchor_part = None

            if '#' in url:
                path_part, anchor_part = url.split('#', 1)

            # 解析路径
            if path_part.startswith('/'):
                target_path = ROOT_DIR / path_part.lstrip('/')
            else:
                target_path = (md_file.parent / path_part).resolve()

            # 检查文件是否存在
            if target_path.exists():
                link_stats['valid_links'] += 1
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
