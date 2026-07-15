#!/usr/bin/env python3
"""
R1-31: 复核保留策略
检查所有文档中关于 TTL 和保留策略的一致性
"""

import re
from pathlib import Path

# 定义数据类型和对应的预期保留策略
RETENTION_POLICIES = {
    'PrivateSceneSubmission': {
        'name_zh': '私有场景提交',
        'expected_ttl': '场景结束',
        'expected_max_hours': 24,
        'expected_cleanup': '立即删除',
        'documents': [
            'docs/architecture/DATA_INVENTORY.md',
            'docs/security/THREAT_MODEL.md',
            'docs/privacy/PRIVACY_BASELINE.md',
            'docs/architecture/SCENE_STATE_MACHINE.md'
        ]
    },
    'PreferenceCapsule': {
        'name_zh': '偏好胶囊',
        'expected_ttl': '场景结束',
        'expected_max_hours': 24,
        'expected_cleanup': '立即删除',
        'documents': [
            'docs/architecture/DATA_INVENTORY.md',
            'docs/security/THREAT_MODEL.md',
            'docs/privacy/PRIVACY_BASELINE.md'
        ]
    },
    'PrivateCandidateEvaluation': {
        'name_zh': '私有候选评价',
        'expected_ttl': '场景结束',
        'expected_max_hours': 24,
        'expected_cleanup': '立即删除',
        'documents': [
            'docs/architecture/DATA_INVENTORY.md',
            'docs/security/THREAT_MODEL.md',
            'docs/privacy/PRIVACY_BASELINE.md'
        ]
    },
    'AgentRun': {
        'name_zh': 'AgentRun',
        'expected_ttl': '30天',
        'expected_max_hours': None,
        'expected_cleanup': '定时清理',
        'documents': [
            'docs/architecture/DATA_INVENTORY.md'
        ]
    },
    'AuditLog': {
        'name_zh': '审计日志',
        'expected_ttl': '90天',
        'expected_max_hours': None,
        'expected_cleanup': '定时清理',
        'documents': [
            'docs/architecture/DATA_INVENTORY.md'
        ]
    },
    'MemoryItem': {
        'name_zh': '记忆',
        'expected_ttl': '用户控制',
        'expected_max_hours': None,
        'expected_cleanup': '用户删除',
        'documents': [
            'docs/architecture/DATA_INVENTORY.md',
            'docs/privacy/PRIVACY_BASELINE.md'
        ]
    }
}

print("=" * 80)
print("R1-31: 保留策略一致性检查")
print("=" * 80)
print()

# 检查每个数据类型的保留策略
consistency_results = []

for data_type, policy in RETENTION_POLICIES.items():
    print(f"\n{'─' * 80}")
    print(f"数据类型: {data_type}（{policy['name_zh']}）")
    print(f"{'─' * 80}")

    type_results = {
        'data_type': data_type,
        'name_zh': policy['name_zh'],
        'documents': {}
    }

    for doc_path in policy['documents']:
        full_path = Path(doc_path)
        if not full_path.exists():
            print(f"  ⚠️  文档不存在: {doc_path}")
            type_results['documents'][doc_path] = {'exists': False}
            continue

        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 搜索相关段落
        relevant_sections = []

        # 搜索 TTL、保留、过期等关键词
        patterns = [
            r'.{0,100}TTL.{0,100}',
            r'.{0,100}保留.{0,100}',
            r'.{0,100}过期.{0,100}',
            r'.{0,100}expires_at.{0,100}',
            r'.{0,100}retention.{0,100}'
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if data_type.lower() in match.lower() or policy['name_zh'] in match:
                    relevant_sections.append(match.strip())

        if relevant_sections:
            print(f"\n  📄 {doc_path}:")
            for i, section in enumerate(relevant_sections[:3], 1):  # 只显示前3个匹配
                print(f"    {i}. {section[:100]}...")
            type_results['documents'][doc_path] = {
                'exists': True,
                'sections': relevant_sections
            }
        else:
            print(f"\n  ⚠️  {doc_path}: 未找到相关描述")
            type_results['documents'][doc_path] = {
                'exists': True,
                'sections': []
            }

    consistency_results.append(type_results)

print("\n" + "=" * 80)
print("一致性检查总结")
print("=" * 80)

# 检查一致性问题
issues = []

for result in consistency_results:
    data_type = result['data_type']
    policy = RETENTION_POLICIES[data_type]

    print(f"\n{data_type}（{result['name_zh']}）:")

    # 检查每个文档是否都有描述
    missing_docs = [doc for doc, info in result['documents'].items() if not info['exists'] or not info.get('sections')]
    if missing_docs:
        print(f"  ⚠️  缺少描述的文档: {', '.join(missing_docs)}")
        issues.append({
            'type': data_type,
            'issue': 'missing_docs',
            'details': missing_docs
        })
    else:
        print(f"  ✅ 所有文档都有描述")

print("\n" + "=" * 80)
print("建议")
print("=" * 80)

print("""
保留策略一致性建议：

1. **P4 数据（私有场景提交、偏好胶囊、私有候选评价）**：
   - 所有文档统一描述为"场景结束后立即删除，最长24小时兜底"
   - THREAT_MODEL.md 中 T-07 的缓解措施应与此一致

2. **AgentRun**：
   - 统一为"30天自动清理"
   - 确保清理任务配置正确

3. **AuditLog**：
   - 统一为"90天自动清理"
   - 确保清理任务配置正确

4. **MemoryItem**：
   - 统一为"用户控制，用户主动删除"
   - PRIVACY_BASELINE.md 应明确用户删除记忆的流程

5. **场景结果（SceneResult）**：
   - 统一为"永久保留，供历史查询"
   - 确保不会意外删除
""")

print("=" * 80)
print("检查完成")
print("=" * 80)
