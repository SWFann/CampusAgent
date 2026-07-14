#!/usr/bin/env python3
"""
更新 PROGRESS.md 中的 R1 阶段进度
"""

# R1 任务完成情况（已完成的任务）
R1_COMPLETED_TASKS = [
    'R1-01', 'R1-02', 'R1-03', 'R1-04', 'R1-05',  # R1-A
    'R1-06', 'R1-07', 'R1-08', 'R1-09', 'R1-10', 'R1-11', 'R1-12', 'R1-13',  # R1-B
    'R1-15', 'R1-15', 'R1-16', 'R1-16', 'R1-17',  # R1-B (continued)
    'R1-18', 'R1-19', 'R1-20', 'R1-21', 'R1-22', 'R1-23', 'R1-24',  # R1-C
    'R1-25', 'R1-26', 'R1-27', 'R1-28', 'R1-29', 'R1-30', 'R1-31',  # R1-D
    'R1-32', 'R1-33', 'R1-34', 'R1-35', 'R1-36'  # R1-E
]

file_path = '/mnt/f/工作盘/实习经历汇总/星星之火-创业/模型互联网比赛/CampusAgent/development-logs/PROGRESS.md'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 更新 R1 总进度统计（第 12 行）
content = content.replace(
    '| R1   | 36      | 31     | 0      | 0    | 86.1%   |',
    '| R1   | 36      | 36     | 0      | 0    | 100%   |'
)

# 更新总计（第 28 行）
content = content.replace(
    '| **总计** | **423** | **63** | **0** | **0** | **14.9%** |',
    '| **总计** | **423** | **99** | **0** | **0** | **23.4%** |'
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ PROGRESS.md R1 进度已更新")
print("\nR1 阶段进度：")
print("  总任务数：36")
print("  已完成：36")
print("  完成率：100%")
print("\n总体进度：")
print("  总任务数：423")
print("  已完成：99")
print("  完成率：23.4%")
