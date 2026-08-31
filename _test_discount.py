# -*- coding: utf-8 -*-
"""验证非线性折扣曲线"""
def discount(hp, max_hp=100):
    ratio = max(0, min(1, hp / max_hp))
    return 0.1 + 0.9 * (ratio ** 1.8)

print("血量 | 折扣系数 | 降价幅度")
for hp in [100, 90, 80, 70, 60, 50, 40, 30, 20, 10, 5, 1, 0]:
    d = discount(hp)
    pct = int((1 - d) * 100)
    print(f"{hp:3d} |   {d:.2f}  | 降价{pct}%")
