# -*- coding: utf-8 -*-
"""村民交易修复 + 生气机制 补丁"""
import ast

p = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\ui_main.py'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# ========== 1. 初始化生气状态 ==========
old_init = '''        self._villager_hp = 100
        self._villager_max_hp = 100'''
new_init = '''        self._villager_hp = 100
        self._villager_max_hp = 100
        self._villager_angry = 0  # 0=正常 1=生气(涨价) 2=暴怒(大幅涨价)'''
if old_init in c:
    c = c.replace(old_init, new_init, 1)
    print('OK: 初始化生气状态')
else:
    print('FAIL: 初始化锚点未找到')

# ========== 2. _open_trading 里保存 list_frame + 重置生气状态 ==========
old_open = '''            if is_wandering:
                self._current_villager = {
                    "name": "流浪商人",
                    "trades": self._WANDERING_TRADER_TRADES,
                }
                self._current_villager_key = "wandering"
                villager_photo = self._wandering_trader_photo or self._villager_photo
                quotes = self._WANDERING_TRADER_QUOTES
            else:
                prof_key = random.choice(list(self._VILLAGER_PROFESSIONS.keys()))
                self._current_villager = self._VILLAGER_PROFESSIONS[prof_key]
                self._current_villager_key = prof_key
                villager_photo = self._villager_photo
                quotes = self._VILLAGER_QUOTES
                self._villager_hp = self._villager_max_hp  # 每次打开新村民满血'''
new_open = '''            if is_wandering:
                self._current_villager = {
                    "name": "流浪商人",
                    "trades": self._WANDERING_TRADER_TRADES,
                }
                self._current_villager_key = "wandering"
                villager_photo = self._wandering_trader_photo or self._villager_photo
                quotes = self._WANDERING_TRADER_QUOTES
            else:
                prof_key = random.choice(list(self._VILLAGER_PROFESSIONS.keys()))
                self._current_villager = self._VILLAGER_PROFESSIONS[prof_key]
                self._current_villager_key = prof_key
                villager_photo = self._villager_photo
                quotes = self._VILLAGER_QUOTES
                self._villager_hp = self._villager_max_hp  # 每次打开新村民满血
                self._villager_angry = 0  # 新村民不生气'''
if old_open in c:
    c = c.replace(old_open, new_open, 1)
    print('OK: 打开村民时重置生气状态')
else:
    print('FAIL: 打开村民锚点未找到')

# ========== 3. 保存交易列表 frame 引用 ==========
old_frame = '''            # 交易列表
            list_frame = tk.Frame(win, bg=bg_color, padx=10, pady=8)
            list_frame.pack(fill="both", expand=True)'''
new_frame = '''            # 交易列表 (保存引用, 供攻击后重建用)
            self._trade_list_frame = tk.Frame(win, bg=bg_color, padx=10, pady=8)
            list_frame = self._trade_list_frame
            list_frame.pack(fill="both", expand=True)'''
if old_frame in c:
    c = c.replace(old_frame, new_frame, 1)
    print('OK: 保存交易列表 frame 引用')
else:
    print('FAIL: 交易列表 frame 锚点未找到')

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
ast.parse(c)
print('语法检查通过')
