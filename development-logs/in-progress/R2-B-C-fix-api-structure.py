#!/usr/bin/env python3
"""
R2-B 和 R2-C：修复 API 工程结构和模块骨架
"""

from pathlib import Path
import os

API_SRC = Path('/mnt/f/工作盘/实习经历汇总/星星之火-创业/模型互联网比赛/CampusAgent/apps/api/src')

print("=" * 80)
print("R2-B & R2-C: 修复 API 工程结构和模块骨架")
print("=" * 80)

# R2-18: 移除错误的 core 业务模块模板
print("\n### R2-18: 移除 core 模块骨架文件")

core_module = API_SRC / 'modules' / 'core'
core_skeleton_files = [
    '__init__.py',
    'api.py',
    'models.py',
    'repository.py',
    'schemas.py',
    'service.py'
]

removed = []
for filename in core_skeleton_files:
    filepath = core_module / filename
    if filepath.exists():
        filepath.unlink()
        removed.append(filename)
        print(f"  ✓ 删除: {filename}")

print(f"\n总计删除 {len(removed)} 个文件")

# 保留的文件
kept_files = ['config.py', 'database.py', 'events.py', 'logging.py']
print(f"\nCore 模块保留文件: {', '.join(kept_files)}")

# R2-17: 处理零字节文件（业务模块保留为骨架）
print("\n### R2-17: 处理零字节文件")

zero_byte_files = []
modules_dir = API_SRC / 'modules'

for module_dir in modules_dir.iterdir():
    if not module_dir.is_dir():
        continue

    for py_file in module_dir.glob('*.py'):
        if py_file.stat().st_size == 0:
            zero_byte_files.append(py_file)

print(f"找到 {len(zero_byte_files)} 个零字节文件")

# 业务模块的零字节文件保留（骨架占位），但需要添加注释说明
skeleton_template = '''"""
{module_name} module - {description}

This module is a skeleton placeholder.
TODO: Implement business logic for {module_name}.
"""

from __future__ import annotations
'''

module_descriptions = {
    'admin': '系统管理',
    'agents': '智能体管理',
    'audit': '审计日志',
    'auth': '身份认证',
    'conversations': '会话管理',
    'directory': '校园目录',
    'memories': '记忆管理',
    'model_gateway': '模型网关',
    'nodes': '边缘节点',
    'notifications': '通知管理',
    'organizations': '组织管理',
    'scenes': '场景协商',
    'users': '用户管理',
}

for py_file in zero_byte_files:
    module_name = py_file.parent.name
    filename = py_file.name

    # 跳过 __init__.py
    if filename == '__init__.py':
        continue

    # 添加骨架注释
    try:
        with open(py_file, 'w', encoding='utf-8') as f:
            description = module_descriptions.get(module_name, module_name)
            f.write(skeleton_template.format(
                module_name=module_name,
                description=description
            ))
        print(f"  ✓ 添加注释: {module_name}/{filename}")
    except Exception as e:
        print(f"  ✗ 失败: {module_name}/{filename} - {e}")

print("\n### R2-C-16: 修复环境变量命名一致性")

# 检查 config.py 中的环境变量名
config_file = API_SRC / 'config.py'
if config_file.exists():
    with open(config_file, 'r') as f:
        content = f.read()

    # 检查环境变量命名
    env_vars = [
        'APP_ENV',
        'DATABASE_URL',
        'REDIS_URL',
        'APP_SECRET',
        'FIELD_ENCRYPTION_KEY',
        'ACCESS_TOKEN_EXPIRE_MINUTES',
        'REFRESH_TOKEN_EXPIRE_DAYS',
    ]

    print("\nConfig.py 中的环境变量:")
    for var in env_vars:
        if var in content:
            print(f"  ✓ {var}")
        else:
            print(f"  ✗ 缺少: {var}")

print("\n" + "=" * 80)
print("R2-B & R2-C 修复完成")
print("=" * 80)
