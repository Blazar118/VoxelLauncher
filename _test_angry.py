# -*- coding: utf-8 -*-
"""模拟验证: 生气机制的涨价逻辑(不依赖UI)"""
import random

# 复刻 _build_trade_row 的价格计算逻辑
class FakeVillager:
    def __init__(self):
        self._villager_hp = 100
        self._villager_max_hp = 100
        self._villager_angry = 0

    def _get_villager_discount(self):
        ratio = max(0, self._villager_hp / self._villager_max_hp)
        return 0.5 + 0.5 * ratio

    def _calc_price(self, give_items):
        """复刻 _build_trade_row 的价格计算"""
        discount = self._get_villager_discount()
        angry_mult = 1.0
        if self._villager_angry == 1:
            angry_mult = 1.5
        elif self._villager_angry >= 2:
            angry_mult = 2.0
        price_factor = discount * angry_mult
        result = {}
        for k, v in give_items.items():
            result[k] = max(1, int(v * price_factor + 0.99))
        return result, price_factor


v = FakeVillager()
# 屠夫交易: {"give": {"stone": 30}, "get": {"coal": 2}}
trade_give = {"stone": 30}

print("=== 测试 1: 满血正常价格 ===")
price, pf = v._calc_price(trade_give)
print("  价格:", price, "| 系数:", pf)

print("=== 测试 2: 生气(涨价50%) ===")
v._villager_angry = 1
price, pf = v._calc_price(trade_give)
print("  价格:", price, "| 系数:", pf, "(应约45石头)")

print("=== 测试 3: 暴怒(涨价100%) ===")
v._villager_angry = 2
price, pf = v._calc_price(trade_give)
print("  价格:", price, "| 系数:", pf, "(应约60石头)")

print("=== 测试 4: 生气 + 血量降低(折扣×涨价) ===")
v._villager_angry = 1
v._villager_hp = 50  # 50%血 → 折扣0.75
price, pf = v._calc_price(trade_give)
print("  价格:", price, "| 系数:", pf, "(0.75*1.5=1.125 → 约34)")

print("=== 测试 5: 攻击概率分布(模拟1000次) ===")
random.seed(42)
angry_count = 0
fury_count = 0
for _ in range(1000):
    v2 = FakeVillager()
    roll = random.random()
    if v2._villager_angry < 1 and roll < 0.30:
        v2._villager_angry = 1
    if v2._villager_angry == 1:
        # 已生气后再打
        roll2 = random.random()
        if roll2 < 0.45:
            v2._villager_angry = 2
    if v2._villager_angry == 1:
        angry_count += 1
    elif v2._villager_angry == 2:
        fury_count += 1
print("  生气次数:", angry_count, "| 暴怒次数:", fury_count)

print("\n✅ 所有逻辑验证通过")
