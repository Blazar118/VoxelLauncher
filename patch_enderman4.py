# -*- coding: utf-8 -*-
filepath = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\ui_main.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 在天气更新函数里添加末影人受伤逻辑
old = '''        # 雷暴天: 苦力怕变闪电苦力怕
        if self._weather == "thunder" and not self._creeper_is_charged:
            self._creeper_is_charged = True
            self._update_creeper_display()
            self._creeper_say("⚡ 雷暴让我充满力量！⚡", 3000)'''

new = '''        # 雷暴天: 苦力怕变闪电苦力怕
        if self._weather == "thunder" and not self._creeper_is_charged:
            self._creeper_is_charged = True
            self._update_creeper_display()
            self._creeper_say("⚡ 雷暴让我充满力量！⚡", 3000)
        # 雨天/雷暴天: 末影人受伤(瞬移躲避)
        if self._weather in ("rain", "thunder") and self._current_pet == "enderman":
            if random.random() < 0.3:
                self._enderman_say("啊啊啊！水！我怕水！", 2000)
                self._enderman_teleport()'''

if old in content:
    content = content.replace(old, new, 1)
    print("末影人雨天受伤逻辑添加成功")
else:
    print("未找到天气更新代码")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("保存完成")
