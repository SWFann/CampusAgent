#!/usr/bin/env python3
"""
R2-14：测试应用工厂是否能创建多个隔离实例
"""

import sys
sys.path.insert(0, 'apps/api')

from src.main import create_app

# 创建第一个实例
app1 = create_app()
print(f"✓ App instance 1 created: {id(app1)}")

# 创建第二个实例
app2 = create_app()
print(f"✓ App instance 2 created: {id(app2)}")

# 验证隔离性
if id(app1) != id(app2):
    print("✓ Instances are isolated (different object IDs)")
else:
    print("✗ Instances are NOT isolated (same object ID)")
    sys.exit(1)

# 验证状态独立
app1.state.test_value = "instance1"
app2.state.test_value = "instance2"

if app1.state.test_value == "instance1" and app2.state.test_value == "instance2":
    print("✓ Instance states are independent")
else:
    print("✗ Instance states are NOT independent")
    sys.exit(1)

print("\n✓ R2-14: 应用工厂测试通过")
