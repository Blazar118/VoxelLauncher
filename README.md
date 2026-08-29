# VoxelLauncher

基于 Python 标准库 Tkinter 的 Minecraft Java 版第三方启动器（Windows 优先），
对标 HMCL / PCL2 的核心产品逻辑，独立实现，未复制任何第三方启动器源码。

## 功能一览

### 基础功能
- 账号：离线账号（自动生成离线 UUID）+ 微软 OAuth 设备码登录（含 token 刷新 / 失效处理）
- 版本下载：官方 manifest 全版本列表、version.json / 游戏 jar / libraries / assets 完整下载
  - sha1 完整性校验、损坏自动重下、断点续传
- 加载器一键安装：Fabric / Quilt / Forge，自动附带安装 Fabric API / Quilt API
- 实例管理：版本隔离（每个实例独立 mods/saves/resourcepacks/shaderpacks），复制 / 删除 / 重命名
- Java 管理：自动扫描本机 Java、按游戏版本自动推荐（1.16- 用 8，1.17-1.20.4 用 17，1.20.5+ 用 21）
- 启动核心：完整解析 version.json 拼接启动命令、native 解压、启动前文件完整性校验、子进程日志实时输出
- Modrinth：模组搜索 / 一键下载 / 依赖自动补装 / mrpack 整合包导入
- CurseForge：支持 API Key 下载，版本选择
- 资源包/数据包/光影包/整合包管理，全部支持版本选择
- 镜像源切换：官方源 <-> BMCLAPI 镜像
- 高速下载器：多线程下载、断点续传、下载管理

### 🎮 娱乐功能
- ⛏ 挖矿系统：点击矿石挖矿，获得经验升级镐子，不同镐子挖不同矿石
- 🐱 宠物系统：苦力怕和村民双宠物，点击互动，右键喂食，会随机说话和对话
- 🤖 AI 聊天：支持豆包/Deepseek/Kimi，宠物会按角色设定回复，自动检测 API 服务商
- ☀ 昼夜系统：实时昼夜交替，影响挖矿和天气
- 🌧 天气系统：雨/雪/雷暴动画，下雨天会出现流浪商人
- 🤝 交易系统：和村民/流浪商人交易，用矿石换物品
- ⚒ 合成系统：工作台合成物品，支持自定义皮肤
- 🐟 养殖系统：养鱼等动物，动物贴图从游戏提取
- 🎣 钓鱼小游戏：等待鱼上钩，把握时机拉杆，钓到各种鱼和宝藏
- 🎒 背包和箱子：物品存储和管理

### ⚔️ 战斗系统（单独页面）
- 👹 刷怪系统：夜晚自动刷僵尸和骷髅，贴图从游戏提取
- 🗡 武器系统：木剑→石剑→铁剑→钻石剑→下界合金剑，伤害递增
- ⚔ 战斗机制：点击怪物攻击，怪物会反击，玩家有血量条
- 💀 掉落物：僵尸掉腐肉/铁锭/胡萝卜，骷髅掉骨头/箭/弓
- 💬 指令系统：支持 /give /time set /gamemode /kill /heal /summon /xp 等
- 📜 战斗日志：记录所有战斗事件

### 🔗 游戏联动
- ⛏ 挖矿联动：挖到矿石实时发送到游戏背包
- ⚔ 战斗联动：击杀怪物时游戏里附近同种怪物也死亡
- 需要安装游戏联动Mod（设置页有「安装联动Mod」按钮）

## 文件结构

```
VoxelLauncher/
├── main.py              # 程序入口
├── config.py            # 全局配置（游戏目录/下载源/账号/Java/内存）
├── downloader.py        # 下载器（镜像重写/sha1/断点续传/并发池）
├── download_manager.py  # 下载管理（断点续传/任务管理）
├── version_manager.py   # 版本下载与解析（manifest/version.json/libraries/assets）
├── java_manager.py      # Java 扫描与版本识别
├── accounts.py          # 账号系统（离线 + 微软 OAuth）
├── installer.py         # 加载器安装（Fabric/Quilt/Forge + API）
├── instance.py          # 实例管理（版本隔离/复制/删除/重命名）
├── launcher.py          # 启动核心（命令拼接/校验/子进程日志）
├── modrinth.py          # Modrinth 平台（搜索/下载/依赖/mrpack）
├── curseforge.py        # CurseForge 平台
├── mod_manager.py       # 本地 mod/资源包管理
├── ai_chat.py           # AI 聊天（豆包/Deepseek/Kimi）
├── sounds.py            # 音效和游戏资源提取
├── bridge.py            # 游戏联动
├── game_assets.py       # 游戏资源提取
├── player_state.py      # 玩家状态
├── achievements.py      # 成就系统
├── ui_main.py           # Tkinter 全部界面
├── requirements.txt     # 依赖清单
├── voxellauncher-bridge/ # 游戏联动 Mod（Gradle 项目）
└── README.md            # 本文档
```

## 运行

```bash
pip install -r requirements.txt
python main.py
```

## 打包 EXE

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name VoxelLauncher ^
  --hidden-import=tkinter ^
  --hidden-import=PIL ^
  --hidden-import=PIL.Image ^
  --hidden-import=PIL.ImageTk ^
  --hidden-import=requests ^
  --hidden-import=ai_chat ^
  --hidden-import=sounds ^
  --hidden-import=config ^
  main.py
# 产物: dist\VoxelLauncher.exe
```

## 开源协议

MIT License
