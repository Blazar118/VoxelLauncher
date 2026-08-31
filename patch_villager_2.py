# -*- coding: utf-8 -*-
"""村民交易修复 + 生气机制 补丁 第2部分"""
import ast

p = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\ui_main.py'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# ========== A. _build_trade_row: 支持涨价(生气) ==========
old_build = '''    def _build_trade_row(self, parent, trade, index, bg_color="#c8a878", is_wandering=False):
        """构建一行交易选项(含血量折扣)"""
        give_items = trade["give"]
        get_items = trade["get"]
        # 血量折扣(仅普通村民)
        discount = 1.0
        if not is_wandering and hasattr(self, '_villager_hp'):
            discount = self._get_villager_discount()
        discounted_give = {}
        for k, v in give_items.items():
            discounted_give[k] = max(1, int(v * discount + 0.99))
        trade["_discounted_give"] = discounted_give
        give_text = " + ".join(
            f"{v} {self._DROP_NAMES.get(k, k)}" for k, v in discounted_give.items()
        )
        get_text = " + ".join(
            f"{v} {self._DROP_NAMES.get(k, k)}" for k, v in get_items.items()
        )

        row = tk.Frame(parent, bg=bg_color, relief="solid", borderwidth=1,
                        padx=8, pady=4)
        row.pack(fill="x", pady=3)

        text_color = "#ffffff" if is_wandering else "#333"
        discount_text = ""
        if discount < 0.99 and not is_wandering:
            discount_text = f"  (降价{int((1-discount)*100)}%)"
        tk.Label(row, text=f"{give_text}  →  {get_text}{discount_text}",
                 bg=bg_color, font=("Arial", 9), fg=text_color).pack(side="left")'''

new_build = '''    def _build_trade_row(self, parent, trade, index, bg_color="#c8a878", is_wandering=False):
        """构建一行交易选项(含血量折扣 + 生气涨价)"""
        give_items = trade["give"]
        get_items = trade["get"]
        # 价格系数: 血量折扣 * 生气涨价
        discount = 1.0
        if not is_wandering and hasattr(self, '_villager_hp'):
            discount = self._get_villager_discount()
        # 生气机制: 村民生气会涨价(原版MC行为)
        angry_mult = 1.0
        if not is_wandering:
            angry_level = getattr(self, '_villager_angry', 0)
            if angry_level == 1:
                angry_mult = 1.5   # 生气: 涨价50%
            elif angry_level >= 2:
                angry_mult = 2.0   # 暴怒: 涨价100%
        price_factor = discount * angry_mult
        discounted_give = {}
        for k, v in give_items.items():
            discounted_give[k] = max(1, int(v * price_factor + 0.99))
        trade["_discounted_give"] = discounted_give
        trade["_price_factor"] = price_factor
        give_text = " + ".join(
            f"{v} {self._DROP_NAMES.get(k, k)}" for k, v in discounted_give.items()
        )
        get_text = " + ".join(
            f"{v} {self._DROP_NAMES.get(k, k)}" for k, v in get_items.items()
        )

        row = tk.Frame(parent, bg=bg_color, relief="solid", borderwidth=1,
                        padx=8, pady=4)
        row.pack(fill="x", pady=3)

        text_color = "#ffffff" if is_wandering else "#333"
        price_text = ""
        angry_level = getattr(self, '_villager_angry', 0) if not is_wandering else 0
        if angry_level == 1:
            price_text = "  (😠 生气了, 涨价50%!)"
        elif angry_level >= 2:
            price_text = "  (🤬 暴怒, 涨价100%!)"
        elif discount < 0.99 and not is_wandering:
            price_text = f"  (降价{int((1-discount)*100)}%)"
        tk.Label(row, text=f"{give_text}  →  {get_text}{price_text}",
                 bg=bg_color, font=("Arial", 9), fg=text_color).pack(side="left")'''

if old_build in c:
    c = c.replace(old_build, new_build, 1)
    print('OK: _build_trade_row 支持生气涨价')
else:
    print('FAIL: _build_trade_row 锚点未找到')

# ========== B. _attack_villager: 加生气机制 ==========
old_attack = '''    def _attack_villager(self, win):
        """攻击村民: 扣血, 显示伤害, 降低交易价格"""
        if self._villager_hp <= 0:
            self._creeper_say("村民已经晕倒了, 换一个吧", 2000)
            return
        # 计算伤害(铁斧基础9点, 有小浮动)
        base_damage = self._axe["damage"]
        damage = base_damage + random.randint(-2, 2)
        damage = max(1, damage)
        self._villager_hp -= damage

        # 显示伤害数字
        self._damage_label.config(text=f"-{damage} 伤害!")
        self.root.after(800, lambda: self._damage_label.config(text=""))

        # 更新血量条
        self._update_villager_hp_bar()

        # 村民被打说话
        hurt_quotes = ["哎呦！", "别打了！", "饶命啊！", "我降价还不行吗！", "救命啊！", "我错了！"]
        self._villager_quote_label.config(text=random.choice(hurt_quotes), fg="#ffaaaa")

        # 血量为0: 村民晕倒
        if self._villager_hp <= 0:
            self._villager_hp = 0
            self._update_villager_hp_bar()
            self._damage_label.config(text="💀 村民晕倒了!", fg="#ff0000")
            self._villager_quote_label.config(text="...(晕倒了)", fg="#888")
            # 禁用所有交易按钮
            for btn, trade in self._trade_buttons:
                btn.config(state="disabled")
            self._creeper_say("村民被你打晕了! 换一个吧", 3000)
        else:
            # 刷新交易按钮(价格降低)
            discount = self._get_villager_discount()
            discount_pct = int((1 - discount) * 100)
            if discount_pct > 0:
                self._creeper_say(f"村民降价了! 便宜{discount_pct}%", 2000)
            # 重新构建交易列表
            self._rebuild_trade_list(win)'''

new_attack = '''    def _attack_villager(self, win):
        """攻击村民: 扣血, 显示伤害, 有概率生气涨价(原版MC行为)"""
        if self._villager_hp <= 0:
            self._creeper_say("村民已经晕倒了, 换一个吧", 2000)
            return
        # 计算伤害(铁斧基础9点, 有小浮动)
        base_damage = self._axe["damage"]
        damage = base_damage + random.randint(-2, 2)
        damage = max(1, damage)
        self._villager_hp -= damage

        # 显示伤害数字
        self._damage_label.config(text=f"-{damage} 伤害!")
        self.root.after(800, lambda: self._damage_label.config(text=""))

        # 更新血量条
        self._update_villager_hp_bar()

        # ===== 生气机制: 有概率被打后涨价 =====
        angry_level = getattr(self, '_villager_angry', 0)
        roll = random.random()
        if angry_level < 1 and roll < 0.30:
            self._villager_angry = 1   # 30% 概率生气
        elif angry_level == 1 and roll < 0.45:
            self._villager_angry = 2   # 已生气时 45% 概率升级为暴怒
        if angry_level == 0 and self._villager_angry == 1:
            self._creeper_say("😠 村民生气了! 交易要涨价50%!", 2200)
        elif self._villager_angry == 2 and angry_level < 2:
            self._creeper_say("🤬 村民暴怒了! 价格翻倍!", 2200)

        # 村民被打说话(生气时说气话)
        if self._villager_angry >= 1:
            angry_quotes = ["气死我了！", "你等着！", "涨价了！", "哼！不给你便宜！", "我记住你了！"]
            self._villager_quote_label.config(text=random.choice(angry_quotes), fg="#ff5555")
        else:
            hurt_quotes = ["哎呦！", "别打了！", "饶命啊！", "我降价还不行吗！", "救命啊！", "我错了！"]
            self._villager_quote_label.config(text=random.choice(hurt_quotes), fg="#ffaaaa")

        # 血量为0: 村民晕倒
        if self._villager_hp <= 0:
            self._villager_hp = 0
            self._update_villager_hp_bar()
            self._damage_label.config(text="💀 村民晕倒了!", fg="#ff0000")
            self._villager_quote_label.config(text="...(晕倒了)", fg="#888")
            # 禁用所有交易按钮
            for btn, trade in self._trade_buttons:
                btn.config(state="disabled")
            self._creeper_say("村民被你打晕了! 换一个吧", 3000)
        else:
            # 重新构建交易列表(价格可能降价或涨价)
            self._rebuild_trade_list(win)'''

if old_attack in c:
    c = c.replace(old_attack, new_attack, 1)
    print('OK: _attack_villager 加入生气机制')
else:
    print('FAIL: _attack_villager 锚点未找到')

# ========== C. 修复 _rebuild_trade_list: 用保存的引用 ==========
old_rebuild = '''    def _rebuild_trade_list(self, win):
        """重新构建交易列表(价格变化后)"""
        try:
            # 找到交易列表frame并清空
            for widget in win.winfo_children():
                if isinstance(widget, tk.Frame) and widget.cget("bg") == win.cget("bg"):
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Frame):
                            child.destroy()
            # 重新构建
            is_wandering = getattr(self, '_wandering_trader_active', False)
            bg_color = "#4a6a8a" if is_wandering else "#c8a878"
            self._trade_buttons = []
            list_frame = None
            for widget in win.winfo_children():
                if isinstance(widget, tk.Frame) and widget.cget("bg") == bg_color:
                    list_frame = widget
                    break
            if list_frame:
                for i, trade in enumerate(self._current_villager["trades"]):
                    self._build_trade_row(list_frame, trade, i, bg_color, is_wandering)
        except Exception:
            pass'''

new_rebuild = '''    def _rebuild_trade_list(self, win):
        """重新构建交易列表(价格变化后), 使用保存的 list_frame 引用, 不会丢列表"""
        try:
            # 用保存的引用直接清空重建(不再靠 bg 猜测, 修复交易项消失的 bug)
            list_frame = getattr(self, '_trade_list_frame', None)
            if list_frame is None or not list_frame.winfo_exists():
                # 兜底: 按背景色查找
                is_wandering = getattr(self, '_wandering_trader_active', False)
                bg_color = "#4a6a8a" if is_wandering else "#c8a878"
                for widget in win.winfo_children():
                    if isinstance(widget, tk.Frame) and widget.cget("bg") == bg_color:
                        list_frame = widget
                        break
            if list_frame is None:
                return
            # 清空交易行(保留"交易选项:"标签)
            for child in list_frame.winfo_children():
                if isinstance(child, tk.Frame):
                    child.destroy()
            # 重新构建
            is_wandering = getattr(self, '_wandering_trader_active', False)
            bg_color = "#4a6a8a" if is_wandering else "#c8a878"
            self._trade_buttons = []
            for i, trade in enumerate(self._current_villager["trades"]):
                self._build_trade_row(list_frame, trade, i, bg_color, is_wandering)
        except Exception:
            import traceback
            traceback.print_exc()'''

if old_rebuild in c:
    c = c.replace(old_rebuild, new_rebuild, 1)
    print('OK: _rebuild_trade_list 修复(用引用重建)')
else:
    print('FAIL: _rebuild_trade_list 锚点未找到')

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
ast.parse(c)
print('语法检查通过')
