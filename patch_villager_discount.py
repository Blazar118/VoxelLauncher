# -*- coding: utf-8 -*-
"""村民交易: 血量越低降价越狠(非线性, 最低约1折)"""
import ast

p = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\ui_main.py'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

old = '''    def _get_villager_discount(self):
        """获取村民交易折扣: 血量越低折扣越大"""
        ratio = max(0, self._villager_hp / self._villager_max_hp)
        # 血量100%=原价, 血量0%=5折
        return 0.5 + 0.5 * ratio'''

new = '''    def _get_villager_discount(self):
        """获取村民交易折扣: 血量越低降价越便宜(非线性, 最低约1折)"""
        ratio = max(0, min(1, self._villager_hp / self._villager_max_hp))
        # 非线性曲线: 血量100%=原价(1.0), 血量0%=约1折(0.1)
        # 前期掉血降价温和, 快没血时价格极低, 体现"生命越低越便宜"
        return 0.1 + 0.9 * (ratio ** 1.8)'''

if old in c:
    c = c.replace(old, new, 1)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(c)
    ast.parse(c)
    print('OK: 折扣改为非线性(最低约1折)')
else:
    print('FAIL: 未找到折扣函数')
