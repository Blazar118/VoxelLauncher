# -*- coding: utf-8 -*-
filepath = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\docs\index.html'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 把积分兑换换成游戏状态监控（实际存在的功能）
old = '''                <!-- 物品兑换 -->
                <div class="integration-card">
                    <span class="integration-icon">🎁</span>
                    <h3>启动器积分兑换游戏物品</h3>
                    <p class="desc">用启动器里的积分、金币、成就点，直接兑换游戏内的稀有物品和资源！</p>
                    <ul class="integration-features">
                        <li>积分兑换钻石、下界合金</li>
                        <li>金币兑换附魔装备</li>
                        <li>成就点解锁特殊道具</li>
                        <li>每日签到领取游戏奖励</li>
                        <li>兑换记录可查，安全可靠</li>
                    </ul>
                </div>'''

new = '''                <!-- 游戏状态监控 -->
                <div class="integration-card">
                    <span class="integration-icon">📊</span>
                    <h3>游戏状态实时监控</h3>
                    <p class="desc">启动器实时显示游戏内状态：FPS、内存、坐标、游戏时间，不用切出游戏就能看！</p>
                    <ul class="integration-features">
                        <li>实时 FPS 显示</li>
                        <li>内存占用监控</li>
                        <li>当前坐标实时显示</li>
                        <li>游戏时长统计</li>
                        <li>当前维度和生物群系</li>
                    </ul>
                </div>'''

if old in content:
    content = content.replace(old, new, 1)
    print("积分兑换已替换为游戏状态监控")
else:
    print("未找到旧卡片")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("文件大小:", len(content))

# 验证
if '启动器积分兑换游戏物品' in content:
    print("✗ 积分兑换还在！")
else:
    print("✓ 积分兑换已删除")

if '游戏状态实时监控' in content:
    print("✓ 游戏状态监控已添加")
