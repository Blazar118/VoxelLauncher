# -*- coding: utf-8 -*-
"""
VoxelLauncher - Tkinter 图形界面主模块
包含: 主界面(启动)/版本下载/Modrinth模组/实例设置/日志/全局设置
后台任务通过线程 + 队列 + root.after 轮询与界面安全交互。
"""
import os
import queue
import random
import shutil
import sys
import tempfile
import threading
import time
import webbrowser
import winsound
import zipfile
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from pathlib import Path

from config import CONFIG
import accounts
import achievements
import player_state
import bridge
import instance as instance_mod
import java_manager
import launcher
import version
import version_manager
import themes
import updater
import installer as installer_mod
import modrinth
import mod_manager
import curseforge
import sounds
import skin_editor
import multiplayer
from PIL import Image, ImageTk

# 尝试加载可选拖拽支持(第三方, 非必须)
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except Exception:
    HAS_DND = False

# Pillow: 用于 mod 图标显示(系统已装; 缺省时图标降级为色块)
try:
    from PIL import Image, ImageTk
    import io as _io
    HAS_PIL = True
except Exception:
    HAS_PIL = False


class ForgeLoadingScreen:
    """
    Forge 风格启动加载窗口:
    - 顶部 Canvas: 锤子打铁动画(铁砧 + 锤子 + 火花)
    - 中部: 进度条
    - 底部: 随机废话文学提示, 每隔几秒换一条
    游戏启动完成后调用 close() 关闭。
    """
    # 超级无厘头提示列表(废话文学 + MC 梗 + 纯扯淡)
    _TIPS = [
        # 纯扯淡
        "据研究，每呼吸 60 秒，就会减少 1 分钟寿命。",
        "如果你现在正在看这条提示，说明你现在正在看这条提示。",
        "这条提示的作用是告诉你这是一条提示。",
        "如果你看到了这条提示，说明你没瞎。",
        "本条提示由 0 个 AI 生成，全靠人工瞎编。",
        "本条提示字数为 0，但你还是读完了。",
        "如果你看到了这里，说明你真的很无聊。",
        "启动器正在思考人生，请稍候。",
        "正在加载你的智商... 加载失败，智商为 0。",
        "正在连接 Herobrine 的服务器... 连接失败，他不想理你。",
        "正在向 Notch 祈祷... 祈祷失败，他在打麻将。",
        "正在召唤苦力怕... 召唤成功，它在你身后。",
        "正在检查你的背包... 发现你很穷。",
        "正在检查你的成就... 发现你一个都没有。",
        "正在检查你的好友列表... 发现你没有朋友。",
        "正在加载游戏... 但游戏不想被加载。",
        "正在启动 Minecraft... 但 Minecraft 还在睡觉。",
        "正在唤醒史蒂夫... 但史蒂夫不想上班。",
        "正在叫醒爱丽克丝... 但她在赖床。",
        # MC 生物扯淡
        "苦力怕的真实身份是你失散多年的远房表哥。",
        "村民不看你是因为它害羞。",
        "村民的绿宝石都是从你身上骗来的。",
        "铁砧砸到头上不会掉血，只会掉智商。",
        "床炸末影龙是 Notch 默许的外挂。",
        "红石比较器的发明者至今下落不明。",
        "下界之星其实是凋灵的胆结石。",
        "鞘翅是末影龙的头皮屑做的。",
        "烟花火箭是苦力怕的骨灰做的。",
        "附魔金苹果的配方被 Notch 吃了。",
        "Notch 其实是 Herobrine 的小号。",
        "实体 303 是 404 的弟弟。",
        "404 种子是假的，但你的恐惧是真的。",
        "如果你在游戏里看到了 Herobrine，请截图，我帮你删游戏。",
        "僵尸的真实身份是熬夜的程序员。",
        "骷髅的箭都是从你的库存里偷的。",
        "蜘蛛在白天不攻击你是因为它要上班。",
        "女巫的药水配方是从抖音学的。",
        "史莱姆的弹性来自于它每天做 1000 个俯卧撑。",
        "恶魂的哭声是因为它想家了，但它没有家。",
        "凋灵骷髅的头是它自己砍下来的。",
        "猪灵的金粒都是从你这里抢的。",
        "循声守卫的耳朵是它的弱点，但它没有弱点。",
        "悦灵是 Notch 派来的卧底。",
        "青蛙的真实身份是村民的远房亲戚。",
        "蝌蚪长大后会变成什么？答案是：大蝌蚪。",
        "骆驼的驼峰里装的是你的希望。",
        "嗅探兽的鼻子可以闻到 1.17 版本的味道。",
        # 方块扯淡
        "方块的真实身份是被压缩的空气。",
        "钻石的真实身份是被压缩的煤炭，但煤炭不承认。",
        "红石的真实身份是被压缩的魔法，但魔法不承认。",
        "下界岩的真实身份是被压缩的地狱，但地狱不承认。",
        "末地石的真实身份是被压缩的外太空，但外太空不承认。",
        "羊毛的真实身份是你的头发做的。",
        "皮革的真实身份是你的皮做的。",
        "猪肉的真实身份是你做的。",
        # 作死指南
        "如果你把 TNT 放在家旁边，你的家就不在了。",
        "如果你把床放在下界，下界就不在了。",
        "如果你把水桶放在末地，末地就不在了。",
        "如果你把岩浆放在手上，你就不在了。",
        "如果你在现实中挖到钻石，请立刻就医。",
        "Minecraft 的世界是方的，但你的脑洞是圆的。",
        "史蒂夫的右手是无限耐久的，因为他从来不洗手。",
        "爱丽克丝的背包里有什么？连她自己都不知道。",
        # 启动器自黑
        "正在给苦力怕做心理辅导... 它还是想炸你。",
        "正在给村民做眼部护理... 它还是不想看你。",
        "正在给村民做反诈骗培训... 它们还是想骗你。",
        "正在给铁砧做保养... 它还是想砸你。",
        "正在给床做清洁... 它还是想炸你。",
        "正在给 TNT 做安检... 它还是想炸你。",
        "正在给钻石做鉴定... 发现是玻璃做的。",
        "正在给红石做检测... 发现是面条做的。",
        "正在给下界岩做化验... 发现是巧克力做的。",
        "正在给末地石做检测... 发现是芝士做的。",
        "VoxelLauncher，你值得拥有，但你已经拥有了。",
        "VoxelLauncher，比 PCL2 差一点，但比没有强。",
        "VoxelLauncher，启动器中的战斗机，但战斗机是纸糊的。",
        "如果你喜欢这个启动器，请给五星好评。",
        "如果你不喜欢这个启动器，请假装喜欢。",
    ]

    def __init__(self, master, version_name=""):
        self.master = master
        self._closed = False
        self._progress = 0
        self._anim_frame = 0
        self._anim_frames = []

        self.win = tk.Toplevel(master)
        self.win.title("Minecraft Forge")
        self.win.geometry("520x460")
        self.win.resizable(False, False)
        self.win.configure(bg="#1a1a1a")
        # 居中
        self.win.transient(master)
        self.win.grab_set()
        self.win.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() - 520) // 2
        y = master.winfo_y() + (master.winfo_height() - 460) // 2
        self.win.geometry("+{}+{}".format(max(0, x), max(0, y)))

        # 顶部留白
        tk.Frame(self.win, bg="#1a1a1a", height=30).pack()

        # Forge 官方 Logo
        self._forge_logo_img = None
        try:
            # 从多个位置找 logo
            logo_paths = []
            # 1. EXE 所在目录(打包后)
            if getattr(sys, 'frozen', False):
                logo_paths.append(os.path.join(os.path.dirname(sys.executable), "forge_logo.png"))
            # 2. 源码目录
            logo_paths.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "forge_logo.png"))
            # 3. APPDATA 目录
            logo_paths.append(os.path.join(os.environ.get("APPDATA", "."), "VoxelLauncher", "forge_logo.png"))

            logo_path = None
            for p in logo_paths:
                if os.path.exists(p):
                    logo_path = p
                    break

            # 找不到就自动下载
            if not logo_path:
                try:
                    import requests
                    save_dir = os.path.join(os.environ.get("APPDATA", "."), "VoxelLauncher")
                    os.makedirs(save_dir, exist_ok=True)
                    save_path = os.path.join(save_dir, "forge_logo.png")
                    r = requests.get("https://cdn.jsdelivr.net/gh/MinecraftForge/MinecraftForge@1.20.1/forge_installer_logo.png", timeout=10)
                    if r.status_code == 200:
                        with open(save_path, 'wb') as f:
                            f.write(r.content)
                        logo_path = save_path
                except Exception:
                    pass

            if logo_path and os.path.exists(logo_path):
                from PIL import Image, ImageTk
                img = Image.open(logo_path).convert("RGBA")
                # 放大到 384x96
                img = img.resize((384, 96), Image.NEAREST)
                self._forge_logo_img = ImageTk.PhotoImage(img)
                tk.Label(self.win, image=self._forge_logo_img, bg="#1a1a1a").pack(pady=(0, 10))
        except Exception:
            # 回退: 文字 logo
            tk.Label(self.win, text="Minecraft Forge",
                     font=("Arial", 24, "bold"), fg="#ffffff",
                     bg="#1a1a1a").pack(pady=(0, 10))

        # 版本信息
        tk.Label(self.win, text="Loading Minecraft {} ...".format(version_name or ""),
                 font=("Arial", 10), fg="#888888",
                 bg="#1a1a1a").pack(pady=(0, 4))

        # Forge 官方锻造动画(从 forge_anim.png 雪碧图加载, 32帧)
        self._anim_label = None
        try:
            anim_paths = []
            if getattr(sys, 'frozen', False):
                anim_paths.append(os.path.join(os.path.dirname(sys.executable), "forge_anim.png"))
            anim_paths.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "forge_anim.png"))
            anim_paths.append(os.path.join(os.environ.get("APPDATA", "."), "VoxelLauncher", "forge_anim.png"))

            anim_path = None
            for p in anim_paths:
                if os.path.exists(p):
                    anim_path = p
                    break

            # 找不到就自动下载
            if not anim_path:
                try:
                    import requests
                    save_dir = os.path.join(os.environ.get("APPDATA", "."), "VoxelLauncher")
                    os.makedirs(save_dir, exist_ok=True)
                    save_path = os.path.join(save_dir, "forge_anim.png")
                    # 从 Forge 1.12.2 universal jar 提取
                    jar_url = "https://maven.minecraftforge.net/net/minecraftforge/forge/1.12.2-14.23.5.2860/forge-1.12.2-14.23.5.2860-universal.jar"
                    r = requests.get(jar_url, timeout=30)
                    if r.status_code == 200:
                        import zipfile, io
                        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                            if 'assets/fml/textures/gui/forge.png' in z.namelist():
                                with open(save_path, 'wb') as f:
                                    f.write(z.read('assets/fml/textures/gui/forge.png'))
                                anim_path = save_path
                except Exception:
                    pass

            if anim_path and os.path.exists(anim_path):
                from PIL import Image, ImageTk
                sprite = Image.open(anim_path).convert("RGBA")
                # 128x4096, 每帧128x128, 共32帧
                for i in range(32):
                    frame = sprite.crop((0, i * 128, 128, (i + 1) * 128))
                    frame = frame.resize((192, 192), Image.NEAREST)
                    self._anim_frames.append(ImageTk.PhotoImage(frame))
                if self._anim_frames:
                    self._anim_label = tk.Label(self.win, image=self._anim_frames[0],
                                                 bg="#1a1a1a")
                    self._anim_label.pack(pady=(2, 4))
                    self._animate_forge()
        except Exception:
            pass

        # 进度条(Forge 风格: 深色背景 + 白色进度)
        self.progress_canvas = tk.Canvas(self.win, width=400, height=20,
                                          bg="#2a2a2a", highlightthickness=1,
                                          highlightbackground="#444444")
        self.progress_canvas.pack(pady=4)
        self.progress_bar = self.progress_canvas.create_rectangle(
            0, 0, 0, 20, fill="#dddddd", outline="")
        self.progress_label = self.progress_canvas.create_text(
            200, 10, text="0%", fill="#333333", font=("Arial", 9, "bold"))

        # 阶段提示
        self.stage_var = tk.StringVar(value="Preparing...")
        tk.Label(self.win, textvariable=self.stage_var,
                 font=("Arial", 9), fg="#aaaaaa", bg="#1a1a1a").pack(
            pady=(2, 4))

        # 废话提示(Forge 风格的黄色提示)
        self.tip_var = tk.StringVar(value=random.choice(self._TIPS))
        tk.Label(self.win, textvariable=self.tip_var,
                 font=("Arial", 9), fg="#ffd700", bg="#1a1a1a",
                 wraplength=460, justify="center").pack(
            side="bottom", pady=(0, 12))

        # 启动提示轮换
        self._rotate_tip()

    def _animate_forge(self):
        """Forge 官方锻造动画: 32帧循环, 每帧80ms"""
        if self._closed or not self._anim_frames or not self._anim_label:
            return
        self._anim_frame = (self._anim_frame + 1) % len(self._anim_frames)
        self._anim_label.config(image=self._anim_frames[self._anim_frame])
        self.win.after(80, self._animate_forge)

    def _rotate_tip(self):
        """每隔 5 秒换一条废话提示"""
        if self._closed:
            return
        self.tip_var.set(random.choice(self._TIPS))
        self.win.after(5000, self._rotate_tip)

    def set_stage(self, text):
        """设置当前阶段提示文字"""
        if not self._closed:
            self.stage_var.set(text)

    def _update_progress(self):
        w = int(400 * self._progress / 100)
        self.progress_canvas.coords(self.progress_bar, 0, 0, w, 20)
        self.progress_canvas.itemconfig(self.progress_label,
                                         text="{}%".format(int(self._progress)))

    def set_progress(self, value):
        """外部设置进度(0-100)"""
        self._progress = max(0, min(100, value))
        self._update_progress()

    def close(self):
        """关闭加载窗口(进度拉满后延迟关闭)"""
        if self._closed:
            return
        self._closed = True
        self._progress = 100
        self._update_progress()
        self.tip_var.set("加载完成！游戏即将启动...")
        self.win.after(600, self._destroy)

    def _destroy(self):
        try:
            self.win.destroy()
        except Exception:
            pass


class VoxelApp:
    """主应用"""

    def __init__(self, root):
        self.root = root
        root.title("VoxelLauncher - Minecraft 第三方启动器")
        root.geometry("960x640")
        root.minsize(860, 560)

        self.ui_queue = queue.Queue()
        self.game_proc = None
        self.accounts = []
        self.instances = []
        self.java_paths = []
        self.manifest_versions = []
        self.modrinth_results = []
        self.curseforge_results = []
        self.pk_results = []
        self.current_instance = None
        self.ach_mgr = achievements.get_manager()
        self._ach_popups = []  # 成就弹窗列表
        # 玩家状态: 经验/等级/背包
        self.player = player_state.get_player()

        self._build_ui()
        self._poll_queue()

        # 初始化下载管理器(断点续传)
        import download_manager
        self.dl_mgr = download_manager.manager
        save_dir = str(Path.home() / "AppData" / "Roaming" / ".voxellauncher")
        self.dl_mgr.init(save_dir)
        # 清理无效任务(之前bug创建的 temp 任务, 或 URL 为空的任务)
        try:
            to_remove = []
            for tid, task in self.dl_mgr.tasks.items():
                if (task.file_name == "temp" or not task.url or
                    task.dest_path.endswith("\temp") or
                    task.dest_path.endswith("/temp")):
                    to_remove.append(tid)
            for tid in to_remove:
                self.dl_mgr.remove_task(tid, delete_file=False)
        except Exception:
            pass
        self.dl_mgr.register_callback(self._on_download_task_changed)
        self._refresh_download_list()

        # 应用日志窗口可见性设置
        show_log = CONFIG.get("show_log_window", "true").lower() != "false"
        self._apply_log_visibility(show_log)

        # 初始加载
        self.modrinth_results = []
        self.mr_selected_idx = -1
        self._reload_accounts()
        self._reload_instances()
        self.refresh_java()
        self.refresh_version_list()

    # ============================================================
    # 界面构建
    # ============================================================
    def _build_ui(self):
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=6, pady=6)

        self.tab_launch = ttk.Frame(self.nb)
        self.tab_versions = ttk.Frame(self.nb)
        self.tab_modrinth = ttk.Frame(self.nb)
        self.tab_instance = ttk.Frame(self.nb)
        self.tab_settings = ttk.Frame(self.nb)
        # CurseForge 页: 默认不 add, 由 _apply_cf_tab 按密钥显隐
        self.tab_curseforge = ttk.Frame(self.nb)
        # 资源管理页
        self.tab_resourcepacks = ttk.Frame(self.nb)
        self.tab_datapacks = ttk.Frame(self.nb)
        self.tab_shaders = ttk.Frame(self.nb)
        self.tab_packs = ttk.Frame(self.nb)
        self.tab_fun = ttk.Frame(self.nb)  # 娱乐页: 挖矿/苦力怕/昼夜天气
        self.tab_combat = ttk.Frame(self.nb)  # 战斗页: 怪物/武器/指令
        self.tab_downloader = ttk.Frame(self.nb)  # 高速下载器页
        self.tab_tools = ttk.Frame(self.nb)  # 工具页
        self.tab_multiplayer = ttk.Frame(self.nb)  # 联机页
        self.tab_server = ttk.Frame(self.nb)  # 开服器页
        self.tab_about = ttk.Frame(self.nb)  # 关于页
        self.tab_friends = ttk.Frame(self.nb)  # 好友页

        self.nb.add(self.tab_launch, text=" 启动 ")
        self.nb.add(self.tab_versions, text=" 版本下载 ")
        self.nb.add(self.tab_modrinth, text=" Modrinth ")
        self.nb.add(self.tab_instance, text=" 实例设置 ")
        self.nb.add(self.tab_settings, text=" 设置 ")
        self.nb.add(self.tab_resourcepacks, text=" 资源包 ")
        self.nb.add(self.tab_datapacks, text=" 数据包 ")
        self.nb.add(self.tab_shaders, text=" 光影包 ")
        self.nb.add(self.tab_packs, text=" 整合包 ")
        self.nb.add(self.tab_fun, text=" 🎮 娱乐 ")
        self.nb.add(self.tab_combat, text=" ⚔️ 战斗 ")
        self.nb.add(self.tab_downloader, text=" ⚡ 高速下载 ")
        self.nb.add(self.tab_tools, text=" 🔧 工具 ")
        self.nb.add(self.tab_multiplayer, text=" 🌐 联机 ")
        self.nb.add(self.tab_server, text=" 🖥 开服器 ")
        self.nb.add(self.tab_about, text=" ℹ 关于 ")
        self.nb.add(self.tab_friends, text=" 👥 好友 ")

        self._build_launch_tab()
        self._build_versions_tab()
        self._build_modrinth_tab()
        self._build_curseforge_tab()
        self._build_fun_tab()
        self._build_combat_tab()
        self._build_instance_tab()
        self._build_settings_tab()
        # 资源管理页
        self._build_resource_tab(self.tab_resourcepacks, "resourcepack",
                                 "resourcepacks")
        self._build_resource_tab(self.tab_datapacks, "datapack", "datapacks")
        self._build_resource_tab(self.tab_shaders, "shader", "shaderpacks")
        self._build_packs_tab()
        self._build_downloader_tab()
        self._build_tools_tab()
        self._build_multiplayer_tab()
        self._build_server_tab()
        self._build_services_tab()
        self._build_about_tab()
        self._build_friends_tab()

        # 刷新积分显示
        self.root.after(1000, self._refresh_points)

        # 启动后后台检查更新
        self.root.after(3000, self._maybe_auto_check)

        # 根据是否配置 CurseForge 密钥决定该页是否显示
        self._apply_cf_tab()

    # ---------------- 主启动页 ----------------
    def _apply_launch_background(self):
        """应用启动页背景/主题壁纸"""
        # 主题色
        theme_key = CONFIG.get("theme", "default")
        theme = themes.get_theme(theme_key)
        # 优先自定义背景图片
        bg_path = CONFIG.get("background_image")
        if not bg_path or not os.path.exists(bg_path):
            # 用主题壁纸
            wpath = themes.generate_wallpaper(theme_key, 1600, 900)
            if wpath and os.path.exists(wpath):
                bg_path = wpath
            else:
                self._launch_canvas.configure(bg=theme["bg"])
                self._launch_bg_img = None
                return
        try:
            from PIL import Image, ImageTk
            img = Image.open(bg_path).convert("RGBA")
            # 缩放到 Canvas 大小
            cw = self._launch_canvas.winfo_width() or 800
            ch = self._launch_canvas.winfo_height() or 600
            img = img.resize((cw, ch), Image.LANCZOS)
            self._launch_bg_img = ImageTk.PhotoImage(img)
            self._launch_canvas.delete("bg")
            self._launch_canvas.create_image(0, 0, anchor="nw",
                image=self._launch_bg_img, tags="bg")
            self._launch_canvas.tag_lower("bg")
        except Exception:
            self._launch_canvas.configure(bg=theme["bg"])
            self._launch_bg_img = None

    def _on_launch_resize(self, event):
        """启动页大小变化时重新定位背景和内容"""
        self._apply_launch_background()
        # 内容面板居中
        cw = event.width
        self._launch_canvas.coords("content", cw // 2, 10)
        self._launch_canvas.itemconfig("content", anchor="n")

    def _build_launch_tab(self):
        # 背景层: Canvas 显示自定义背景图片
        self._launch_canvas = tk.Canvas(self.tab_launch, highlightthickness=0)
        self._launch_canvas.pack(fill="both", expand=True)
        self._launch_bg_img = None
        self._apply_launch_background()
        # 内容面板: 所有控件放在这里, 浮动在背景之上
        self._launch_content = tk.Frame(self._launch_canvas, bg="#2b2b2b")
        self._launch_canvas.create_window(
            0, 0, anchor="nw", window=self._launch_content,
            tags="content")
        self._launch_canvas.bind("<Configure>", self._on_launch_resize)
        f = self._launch_content

        # 玩家状态栏: 等级 + 经验条 + 背包按钮
        player_bar = tk.Frame(f, bg="#2b2b2b")
        player_bar.pack(fill="x", padx=8, pady=(6, 2))
        self._player_level_label = tk.Label(player_bar, text="Lv.1",
            bg="#2b2b2b", fg="#ffd700", font=("Arial", 11, "bold"))
        self._player_level_label.pack(side="left", padx=(4, 6))
        # 经验条背景
        self._xp_bar_bg = tk.Frame(player_bar, bg="#444", height=14, width=200)
        self._xp_bar_bg.pack(side="left", padx=4)
        self._xp_bar_bg.pack_propagate(False)
        self._xp_bar_fg = tk.Frame(self._xp_bar_bg, bg="#4CAF50", height=14)
        self._xp_bar_fg.pack(side="left")
        self._xp_text_label = tk.Label(player_bar, text="0/150 EXP",
            bg="#2b2b2b", fg="#aaa", font=("Arial", 8))
        self._xp_text_label.pack(side="left", padx=4)
        ttk.Button(player_bar, text="🎒 背包", command=self._open_backpack,
                   width=8).pack(side="right", padx=2)
        ttk.Button(player_bar, text="🏆 成就", command=self._open_achievements,
                   width=8).pack(side="right", padx=2)
        self._update_player_level_display()

        # 账号区
        box = ttk.LabelFrame(f, text="账号")
        box.pack(fill="x", padx=8, pady=4)
        self.acct_combo = ttk.Combobox(box, state="readonly", width=30)
        self.acct_combo.pack(side="left", padx=6, pady=4)
        ttk.Button(box, text="+离线", command=self._add_offline).pack(
            side="left", padx=3)
        ttk.Button(box, text="微软登录", command=self._ms_login).pack(
            side="left", padx=3)
        ttk.Button(box, text="刷新", command=self._refresh_selected_acct).pack(
            side="left", padx=3)
        ttk.Button(box, text="删除", command=self._delete_acct).pack(
            side="left", padx=3)

        # 实例区
        box2 = ttk.LabelFrame(f, text="实例 / 版本")
        box2.pack(fill="x", padx=8, pady=4)
        self.inst_combo = ttk.Combobox(box2, state="readonly", width=30)
        self.inst_combo.pack(side="left", padx=6, pady=4)
        ttk.Button(box2, text="新建实例", command=self._new_instance).pack(
            side="left", padx=3)
        ttk.Button(box2, text="刷新", command=self._reload_instances).pack(
            side="left", padx=3)
        self.inst_detail = ttk.Label(box2, text="")
        self.inst_detail.pack(side="left", padx=8)

        # Java / 内存区
        box3 = ttk.LabelFrame(f, text="Java 与内存")
        box3.pack(fill="x", padx=8, pady=4)
        self.java_combo = ttk.Combobox(box3, state="readonly", width=42)
        self.java_combo.pack(side="left", padx=6, pady=4)
        ttk.Button(box3, text="扫描Java", command=self.refresh_java).pack(
            side="left", padx=3)
        ttk.Button(box3, text="浏览...", command=self._browse_java).pack(
            side="left", padx=3)
        ttk.Label(box3, text="最小内存(MB):").pack(side="left", padx=(12, 2))
        self.min_mem = tk.Spinbox(box3, from_=256, to=16384, increment=256,
                                  width=6)
        self.min_mem.pack(side="left")
        ttk.Label(box3, text="最大内存(MB):").pack(side="left", padx=(12, 2))
        self.max_mem = tk.Spinbox(box3, from_=512, to=65536, increment=512,
                                  width=7)
        self.max_mem.pack(side="left")

        # 自动加入服务器
        box_server = ttk.LabelFrame(f, text="自动加入服务器 (不填则正常启动)")
        box_server.pack(fill="x", padx=8, pady=(0, 4))
        server_row = ttk.Frame(box_server)
        server_row.pack(fill="x", padx=6, pady=4)
        ttk.Label(server_row, text="服务器地址:").pack(side="left")
        self.auto_join_server_var = tk.StringVar()
        self.auto_join_server_entry = ttk.Entry(server_row,
            textvariable=self.auto_join_server_var, width=30)
        self.auto_join_server_entry.pack(side="left", padx=5)
        ttk.Label(server_row, text="(格式: IP 或 IP:端口, 如 mc.hypixel.net)",
                  foreground="#888").pack(side="left")
        ttk.Button(server_row, text="清除",
                   command=lambda: self.auto_join_server_var.set("")).pack(side="left", padx=5)

        # 启动区
        box4 = ttk.Frame(f)
        box4.pack(fill="x", padx=8, pady=6)
        self.launch_btn = ttk.Button(box4, text="启动游戏",
                                     command=self._launch, width=16)
        self.launch_btn.pack(side="left")
        ttk.Button(box4, text="导出启动脚本",
                   command=self._export_script).pack(side="left", padx=6)
        ttk.Button(box4, text="📁 打开实例文件夹",
                   command=self._open_instance_folder).pack(side="left", padx=6)
        ttk.Button(box4, text="🏆 成就",
                   command=self._show_achievements, width=8).pack(side="left", padx=2)
        self.stop_btn = ttk.Button(box4, text="停止", command=self._stop_game,
                                   state="disabled")
        self.stop_btn.pack(side="left", padx=6)
        self.status_lbl = ttk.Label(box4, text="就绪")
        self.status_lbl.pack(side="left", padx=10)

        # 日志区
        self.log_box = ttk.LabelFrame(f, text="游戏日志")
        self.log_box.pack(fill="both", expand=True, padx=8, pady=6)
        self.log_text = tk.Text(self.log_box, height=14, wrap="word",
                                state="disabled", bg="#101418",
                                fg="#d8dee9")
        self.log_text.pack(side="left", fill="both", expand=True, padx=4,
                           pady=4)
        sb = ttk.Scrollbar(self.log_box, command=self.log_text.yview)
        sb.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=sb.set)

    # ---------------- 娱乐页(挖矿/苦力怕/昼夜天气) ----------------
    def _build_fun_tab(self):
        f = self.tab_fun

        # 顶部: 昼夜/天气/镐子状态栏
        self._fun_status_bar = tk.Frame(f, bg="#e0e0e0")
        self._fun_status_bar.pack(fill="x", padx=8, pady=(8, 4))
        # 第一行: 状态信息
        status_row = tk.Frame(self._fun_status_bar, bg="#e0e0e0")
        status_row.pack(fill="x")
        self._time_label = tk.Label(status_row, text="☀ 白天", bg="#e0e0e0",
                                     font=("Arial", 11, "bold"))
        self._time_label.pack(side="left", padx=10)
        self._weather_label = tk.Label(status_row, text="🌤 晴天", bg="#e0e0e0",
                                        font=("Arial", 11, "bold"))
        self._weather_label.pack(side="left", padx=10)
        self._pickaxe_label = tk.Label(status_row, text="⛏ 木镐", bg="#e0e0e0",
                                        font=("Arial", 11, "bold"))
        self._pickaxe_label.pack(side="left", padx=10)
        self._axe_label = tk.Label(status_row, text="🪓 铁斧", bg="#e0e0e0",
                                    font=("Arial", 11, "bold"), fg="#aa5500")
        self._axe_label.pack(side="left", padx=10)
        self._xp_label = tk.Label(status_row, text="⭐ Lv.0 (0/10)", bg="#e0e0e0",
                                   font=("Arial", 10, "bold"), fg="#00aa00")
        self._xp_label.pack(side="left", padx=10)
        self._points_label = tk.Label(status_row, text="💰 0 积分", bg="#e0e0e0",
                                       font=("Arial", 10, "bold"), fg="#ff8800")
        self._points_label.pack(side="left", padx=10)
        # 第二行: 功能按钮
        btn_row = tk.Frame(self._fun_status_bar, bg="#e0e0e0")
        btn_row.pack(fill="x", pady=(2, 4))
        ttk.Button(btn_row, text="🤝 交易",
                   command=self._open_trading).pack(side="left", padx=3)
        ttk.Button(btn_row, text="⚒ 锻造台",
                   command=self._open_smithing_table).pack(side="left", padx=3)
        ttk.Button(btn_row, text="🔨 合成镐",
                   command=self._open_pickaxe_craft).pack(side="left", padx=3)
        ttk.Button(btn_row, text="🔥 熔炉",
                   command=lambda: self._open_furnace("normal")).pack(side="left", padx=3)
        ttk.Button(btn_row, text="🏭 高炉",
                   command=lambda: self._open_furnace("blast")).pack(side="left", padx=3)
        ttk.Button(btn_row, text="✨ 附魔",
                   command=self._open_enchanting).pack(side="left", padx=3)
        ttk.Button(btn_row, text="🎣 钓鱼",
                   command=self._open_fishing).pack(side="left", padx=3)
        ttk.Button(btn_row, text="🐄 养殖",
                   command=self._open_farming).pack(side="left", padx=3)
        ttk.Button(btn_row, text="⚒ 合成",
                   command=self._open_crafting).pack(side="left", padx=3)
        ttk.Button(btn_row, text="🎨 皮肤编辑器",
                   command=self._open_skin_editor).pack(side="left", padx=3)
        ttk.Button(btn_row, text="🎁 积分兑换",
                   command=self._open_points_shop).pack(side="left", padx=3)

        # 天气效果 Canvas(雨/雪/闪电动画)
        self._weather_canvas = tk.Canvas(f, height=80, bg="#87ceeb",
                                          highlightthickness=0)
        self._weather_canvas.pack(fill="x", padx=8, pady=(0, 4))
        self._weather_drops = []  # 雨滴/雪花列表
        self._weather_animating = False
        # 预加载雨雪纹理
        self._rain_tex = None
        self._snow_tex = None
        self.root.after(500, self._preload_weather_textures)

        # 流浪商人显示区(下雨天出现, 像苦力怕一样可点击交易)
        self._trader_frame = tk.Frame(f, bg="#f0f0f0", height=170)
        self._trader_frame.pack(fill="x", padx=8, pady=(0, 4))
        self._trader_label = tk.Label(self._trader_frame, bg="#f0f0f0",
                                       cursor="hand2")
        self._trader_label.place(x=20, y=5)
        self._trader_bubble = tk.Label(self._trader_frame, text="",
                                        bg="#ffffcc", fg="#333",
                                        font=("Arial", 9), padx=6, pady=2,
                                        relief="solid", borderwidth=1)
        self._trader_label.bind("<Button-1>", lambda e: self._open_trading())
        self._trader_wandering = False
        self.root.after(800, self._trader_wander)

        # 挖矿区域
        self._build_mining_area(f)

        # 宠物区域: 苦力怕和村民同时显示
        self._pet_frame = tk.Frame(f, bg="#f0f0f0", height=140)
        self._pet_frame.pack(fill="x", side="bottom", padx=8, pady=4)
        self._pet_frame.pack_propagate(False)
        # 宠物工具栏
        pet_toolbar = tk.Frame(self._pet_frame, bg="#f0f0f0")
        pet_toolbar.pack(fill="x", padx=4, pady=2)
        tk.Label(pet_toolbar, text="🐾 宠物区", bg="#f0f0f0",
                 font=("Arial", 9, "bold")).pack(side="left", padx=4)
        ttk.Button(pet_toolbar, text="💬 随机对话",
                   command=self._start_pet_dialogue).pack(side="left", padx=2)
        ttk.Button(pet_toolbar, text="🤖 AI 聊天",
                   command=self._open_ai_chat).pack(side="left", padx=2)
        self._pet_dialogue_status = tk.Label(pet_toolbar, text="",
                                              bg="#f0f0f0", fg="#666",
                                              font=("Arial", 8))
        self._pet_dialogue_status.pack(side="left", padx=10)
        # 苦力怕(左边)
        self._creeper_label = tk.Label(self._pet_frame, bg="#f0f0f0", cursor="hand2")
        self._creeper_label.place(x=20, y=35)
        self._creeper_bubble = tk.Label(self._pet_frame, text="",
                                         bg="#ffffcc", fg="#333",
                                         font=("Arial", 9), padx=6, pady=2,
                                         relief="solid", borderwidth=1)
        self._creeper_exploded = False
        self._creeper_photo = None
        self._creeper_photo_white = None
        self._creeper_original_img = None
        self._creeper_scale = 3.0
        self._creeper_feed_count = 0
        self._creeper_is_charged = False
        self._load_creeper_texture()
        self._creeper_label.bind("<Button-1>", lambda e: self._creeper_click())
        self._creeper_label.bind("<Button-3>", lambda e: self._feed_creeper())
        self._creeper_wander()
        self._creeper_talk_random()

        # 村民(右边)
        self._villager_label = tk.Label(self._pet_frame, bg="#f0f0f0", cursor="hand2")
        self._villager_label.place(x=600, y=35)
        self._villager_bubble = tk.Label(self._pet_frame, text="",
                                          bg="#ffffcc", fg="#333",
                                          font=("Arial", 9), padx=6, pady=2,
                                          relief="solid", borderwidth=1)
        self._villager_photo = None
        self._villager_original_img = None
        self._load_villager_texture()
        self._villager_label.bind("<Button-1>", lambda e: self._villager_click())
        self._villager_label.bind("<Button-3>", lambda e: self._feed_villager())
        self._villager_wander_loop()
        self._villager_talk_random()

        # 宠物对话系统
        self._pet_dialogue_active = False
        self._pet_dialogue_loop()

        # 初始化昼夜/天气/镐子
        self._init_day_night_weather()

        # 启动夜晚刷怪检查
        self.root.after(5000, self._check_night_spawn)

    # ---------------- 昼夜系统 ----------------
    def _init_day_night_weather(self):
        """初始化昼夜、天气、镐子系统"""
        # 预加载镐子贴图
        self._pickaxe_photos = {}
        self._item_photos = {}  # 物品贴图(下界合金锭等)
        try:
            game_dir = CONFIG.get("game_dir")
            for key, info in self._PICKAXE_TYPES.items():
                tex_path = sounds.get_item_texture(game_dir, info["tex"], scale=2)
                if tex_path and os.path.exists(tex_path):
                    img = Image.open(tex_path).convert("RGBA")
                    self._pickaxe_photos[key] = ImageTk.PhotoImage(img)
            # 预加载物品贴图
            for item_name in ["netherite_ingot", "smithing_table", "chest"]:
                tex_path = sounds.get_item_texture(game_dir, item_name, scale=3)
                if tex_path and os.path.exists(tex_path):
                    img = Image.open(tex_path).convert("RGBA")
                    self._item_photos[item_name] = ImageTk.PhotoImage(img)
            # 预加载村民纹理(头+身体正面, 不只是脸)
            self._villager_photo = None
            self._wandering_trader_photo = None
            try:
                import zipfile
                jar_path = os.path.join(game_dir, "versions", "1.21.1", "1.21.1.jar")
                if not os.path.exists(jar_path):
                    versions_dir = os.path.join(game_dir, "versions")
                    if os.path.exists(versions_dir):
                        for v in os.listdir(versions_dir):
                            j = os.path.join(versions_dir, v, v + ".jar")
                            if os.path.exists(j):
                                jar_path = j
                                break

                def extract_villager_body(tex_path_in_jar, scale=8):
                    """提取村民/流浪商人的头+身体正面"""
                    with zipfile.ZipFile(jar_path, "r") as z:
                        with z.open(tex_path_in_jar) as f:
                            vimg = Image.open(f).convert("RGBA")
                    # 头正面: (8,8) 8x8, 身体正面: (20,20) 8x12
                    head = vimg.crop((8, 8, 16, 16))
                    body = vimg.crop((20, 20, 28, 32))
                    # 拼成 8x20 的上半身
                    full = Image.new("RGBA", (8, 20), (0, 0, 0, 0))
                    full.paste(head, (0, 0))
                    full.paste(body, (0, 8))
                    # 放大(NEAREST保持像素风清晰)
                    full_big = full.resize((8 * scale, 20 * scale), Image.NEAREST)
                    return ImageTk.PhotoImage(full_big)

                self._villager_photo = extract_villager_body(
                    "assets/minecraft/textures/entity/villager/villager.png")
                try:
                    self._wandering_trader_photo = extract_villager_body(
                        "assets/minecraft/textures/entity/wandering_trader.png")
                except Exception:
                    pass
            except Exception:
                pass
        except Exception:
            pass

        # 镐子数据
        self._pickaxe = self._load_pickaxe()
        self._update_pickaxe_label()

        # 流浪商人状态(必须在天气更新前初始化)
        self._wandering_trader_active = False

        # 天气: 启动时随机
        self._weather = random.choice(["sunny", "rain", "snow", "thunder"])
        self._weather_change_time = time.time() + random.randint(600, 900)
        self._update_weather_label()

        # 启动时如果是下雨天, 30%概率直接出现流浪商人
        if self._weather in ("rain", "thunder") and random.random() < 0.3:
            self._wandering_trader_active = True
            if self._wandering_trader_photo:
                self._trader_label.config(image=self._wandering_trader_photo)
            self._trader_say("下雨天我又来了~", 3000)

        # 启动昼夜循环(每30秒检查)
        self._update_day_night()
        self.root.after(30000, self._day_night_loop)
        # 天气循环(每60秒检查是否该换天气)
        self.root.after(60000, self._weather_loop)

    def _update_day_night(self):
        """根据真实时间更新昼夜状态"""
        hour = datetime.now().hour
        if 5 <= hour < 7:
            phase = "dawn"
            text = "🌅 黎明"
            bg = "#ffd4a3"
        elif 7 <= hour < 17:
            phase = "day"
            text = "☀ 白天"
            bg = "#87ceeb"
        elif 17 <= hour < 19:
            phase = "dusk"
            text = "🌇 黄昏"
            bg = "#ff9966"
        else:
            phase = "night"
            text = "🌙 夜晚"
            bg = "#2c3e50"
        self._day_phase = phase
        try:
            self._time_label.config(text=text)
            # 状态栏背景随昼夜变化
            self._fun_status_bar.configure(bg=bg)
            self._time_label.configure(bg=bg)
            self._weather_label.configure(bg=bg)
            self._pickaxe_label.configure(bg=bg)
        except Exception:
            pass

    def _day_night_loop(self):
        """昼夜循环: 每30秒检查一次"""
        self._update_day_night()
        self.root.after(30000, self._day_night_loop)

    # ---------------- 天气系统 ----------------
    _WEATHER_INFO = {
        "sunny": {"text": "🌤 晴天", "mining_bonus": 1.0},
        "rain": {"text": "🌧 雨天", "mining_bonus": 1.2},
        "snow": {"text": "❄ 雪天", "mining_bonus": 1.0},
        "thunder": {"text": "⛈ 雷暴", "mining_bonus": 1.3},
    }

    def _update_weather_label(self):
        """更新天气显示并重启动画"""
        info = self._WEATHER_INFO.get(self._weather, self._WEATHER_INFO["sunny"])
        try:
            self._weather_label.config(text=info["text"])
        except Exception:
            pass
        # 雷暴天: 苦力怕变闪电苦力怕
        if self._weather == "thunder" and not self._creeper_is_charged:
            self._creeper_is_charged = True
            self._update_creeper_display()
            self._creeper_say("⚡ 雷暴让我充满力量！⚡", 3000)
        # 下雨天/雷暴天: 30%概率出现流浪商人
        trader_active = getattr(self, '_wandering_trader_active', False)
        if self._weather in ("rain", "thunder"):
            if not trader_active and random.random() < 0.3:
                self._wandering_trader_active = True
                self._creeper_say("🧳 流浪商人出现了！点他交易！", 3500)
                # 显示流浪商人图像
                if getattr(self, '_wandering_trader_photo', None):
                    self._trader_label.config(image=self._wandering_trader_photo)
                self._trader_say(random.choice(["只在下雨天出现哦", "机会难得", "看看我的货吧", "嘿嘿，划算吧"]))
        else:
            # 晴天/雪天: 流浪商人离开
            if trader_active:
                self._wandering_trader_active = False
                self._trader_display_override = None  # 重置切换状态
                self._creeper_say("流浪商人走了...", 2000)
                if hasattr(self, '_trader_label'):
                    self._trader_label.config(image="")
                    self._trader_bubble.place_forget()
        # 重启天气动画
        if hasattr(self, "_weather_canvas"):
            self._start_weather_animation()

    def _weather_loop(self):
        """天气循环: 每60秒检查是否该换天气"""
        if time.time() >= self._weather_change_time:
            # 换天气, 但不要连续一样
            new_weather = random.choice(["sunny", "rain", "snow", "thunder"])
            if new_weather != self._weather:
                self._weather = new_weather
                self._update_weather_label()
                self._creeper_say(f"天气变成了{self._WEATHER_INFO[new_weather]['text']}", 2000)
            self._weather_change_time = time.time() + random.randint(600, 900)
        self.root.after(60000, self._weather_loop)

    def _preload_weather_textures(self):
        """预加载雨/雪纹理(从游戏提取)"""
        try:
            game_dir = CONFIG.get("game_dir")
            rain_path = sounds.get_environment_texture(game_dir, "rain", scale=2)
            snow_path = sounds.get_environment_texture(game_dir, "snow", scale=2)
            if rain_path and os.path.exists(rain_path):
                self._rain_tex = Image.open(rain_path).convert("RGBA")
            if snow_path and os.path.exists(snow_path):
                self._snow_tex = Image.open(snow_path).convert("RGBA")
        except Exception:
            pass
        # 启动当前天气的动画
        self._start_weather_animation()

    def _start_weather_animation(self):
        """根据当前天气启动动画"""
        self._stop_weather_animation()
        self._weather_canvas.delete("all")
        self._weather_drops = []

        if self._weather == "sunny":
            # 晴天: 显示太阳
            self._weather_canvas.configure(bg="#87ceeb")
            self._weather_canvas.create_oval(50, 10, 90, 50, fill="#ffdd00",
                                              outline="#ffaa00", width=2)
            return

        if self._weather in ("rain", "thunder"):
            # 雨天/雷暴: 蓝色背景 + 雨滴
            self._weather_canvas.configure(bg="#5a6a7a")
            for _ in range(60):
                x = random.randint(0, 800)
                y = random.randint(0, 80)
                speed = random.randint(8, 15)
                length = random.randint(8, 16)
                drop_id = self._weather_canvas.create_line(
                    x, y, x - 2, y + length, fill="#aaccff", width=1)
                self._weather_drops.append({"id": drop_id, "x": x, "y": y,
                                             "speed": speed, "type": "rain"})
        elif self._weather == "snow":
            # 雪天: 灰蓝背景 + 雪花
            self._weather_canvas.configure(bg="#b0c4de")
            for _ in range(40):
                x = random.randint(0, 800)
                y = random.randint(0, 80)
                speed = random.randint(2, 5)
                size = random.randint(2, 4)
                drift = random.uniform(-1, 1)
                drop_id = self._weather_canvas.create_oval(
                    x, y, x + size, y + size, fill="#ffffff", outline="")
                self._weather_drops.append({"id": drop_id, "x": x, "y": y,
                                             "speed": speed, "size": size,
                                             "drift": drift, "type": "snow"})

        self._weather_animating = True
        self._weather_animation_step()

    def _stop_weather_animation(self):
        """停止天气动画"""
        self._weather_animating = False

    def _weather_animation_step(self):
        """天气动画: 雨滴/雪花下落"""
        if not self._weather_animating:
            return
        try:
            canvas_w = self._weather_canvas.winfo_width() or 800
            canvas_h = 80
            for drop in self._weather_drops:
                drop["y"] += drop["speed"]
                if drop["type"] == "snow":
                    drop["x"] += drop["drift"]
                # 超出底部则回到顶部
                if drop["y"] > canvas_h:
                    drop["y"] = -10
                    drop["x"] = random.randint(0, canvas_w)
                # 移动
                if drop["type"] == "rain":
                    self._weather_canvas.coords(drop["id"], drop["x"], drop["y"],
                                                 drop["x"] - 2, drop["y"] + 12)
                else:
                    s = drop["size"]
                    self._weather_canvas.coords(drop["id"], drop["x"], drop["y"],
                                                 drop["x"] + s, drop["y"] + s)

            # 雷暴: 随机闪电
            if self._weather == "thunder" and random.random() < 0.02:
                self._weather_canvas.configure(bg="#ffffff")
                self.root.after(80, lambda: self._weather_canvas.configure(bg="#3a4a5a"))
        except Exception:
            pass
        self.root.after(50, self._weather_animation_step)

    def _get_mining_bonus(self):
        """获取当前天气的挖矿效率加成"""
        return self._WEATHER_INFO.get(self._weather, {}).get("mining_bonus", 1.0)

    # ---------------- 镐子系统 ----------------
    _PICKAXE_TYPES = {
        "wood": {"name": "木镐", "tex": "wooden_pickaxe", "efficiency": 1.0, "durability": 999999, "cost": {}},
        "stone": {"name": "石镐", "tex": "stone_pickaxe", "efficiency": 1.5, "durability": 100, "cost": {"stone": 3}},
        "iron": {"name": "铁镐", "tex": "iron_pickaxe", "efficiency": 2.0, "durability": 200, "cost": {"iron": 3}},
        "gold": {"name": "金镐", "tex": "golden_pickaxe", "efficiency": 3.0, "durability": 80, "cost": {"gold": 3}},
        "diamond": {"name": "钻石镐", "tex": "diamond_pickaxe", "efficiency": 3.0, "durability": 500, "cost": {"diamond": 3}},
        "netherite": {"name": "下界合金镐", "tex": "netherite_pickaxe", "efficiency": 4.0, "durability": 1000, "cost": {}},
    }

    def _save_json_safe(self, path, data):
        """安全保存JSON: 先写临时文件再替换, 防止写入中断导致文件变空"""
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp_path = path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            # 替换原文件 (Windows 下 os.replace 是原子操作)
            if os.path.exists(path):
                os.remove(path)
            os.rename(tmp_path, path)
            return True
        except Exception:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            return False

    def _load_json_safe(self, path, default):
        """安全加载JSON: 检查文件是否存在且非空"""
        try:
            if os.path.exists(path) and os.path.getsize(path) > 0:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return default

    def _pickaxe_file(self):
        return os.path.join(os.environ.get("APPDATA", "."),
                            "VoxelLauncher", "pickaxe.json")

    def _load_pickaxe(self):
        """加载镐子数据"""
        return self._load_json_safe(self._pickaxe_file(),
                                    {"type": "wood", "durability": 999999})

    def _save_pickaxe(self):
        """保存镐子数据"""
        self._save_json_safe(self._pickaxe_file(), self._pickaxe)

    def _update_pickaxe_label(self):
        """更新镐子显示(用游戏贴图)"""
        ptype = self._pickaxe.get("type", "wood")
        info = self._PICKAXE_TYPES.get(ptype, self._PICKAXE_TYPES["wood"])
        dur = self._pickaxe.get("durability", 0)
        if ptype == "wood":
            text = f"{info['name']}"
        else:
            text = f"{info['name']} ({dur}/{info['durability']})"
        try:
            photo = self._pickaxe_photos.get(ptype)
            if photo:
                self._pickaxe_label.config(image=photo, text=text,
                                            compound="left", padx=4)
            else:
                self._pickaxe_label.config(image="", text=f"⛏ {text}")
        except Exception:
            pass

    def _get_pickaxe_efficiency(self):
        """获取当前镐子的挖矿效率(含效率附魔)"""
        ptype = self._pickaxe.get("type", "wood")
        base = self._PICKAXE_TYPES.get(ptype, {}).get("efficiency", 1.0)
        eff_level = self._enchantments.get("efficiency", 0)
        if eff_level > 0:
            base *= (1 + 0.3 * eff_level)
        return base

    def _consume_pickaxe_durability(self):
        """消耗镐子耐久, 坏了自动换回木镐(含耐久附魔)"""
        ptype = self._pickaxe.get("type", "wood")
        if ptype == "wood":
            return
        # 耐久附魔: 有概率不消耗耐久
        unbreaking = self._enchantments.get("unbreaking", 0)
        if unbreaking > 0 and random.random() < (0.3 * unbreaking):
            return
        self._pickaxe["durability"] -= 1
        if self._pickaxe["durability"] <= 0:
            self._creeper_say("镐子坏了！换回木镐", 2500)
            self._pickaxe = {"type": "wood", "durability": 999999}
        self._save_pickaxe()
        self._update_pickaxe_label()

    def _open_pickaxe_craft(self):
        """打开镐子合成窗口"""
        try:
            win = tk.Toplevel(self.root)
            win.title("🔨 镐子合成")
            win.geometry("320x360")
            win.resizable(False, False)

            tk.Label(win, text="🔨 镐子合成台", font=("Arial", 13, "bold")).pack(pady=8)

            # 当前镐子
            ptype = self._pickaxe.get("type", "wood")
            cur = self._PICKAXE_TYPES[ptype]
            cur_photo = self._pickaxe_photos.get(ptype)
            cur_frame = tk.Frame(win)
            cur_frame.pack(pady=4)
            if cur_photo:
                tk.Label(cur_frame, image=cur_photo).pack(side="left", padx=4)
            tk.Label(cur_frame, text=f"当前: {cur['name']} (效率x{cur['efficiency']})",
                     font=("Arial", 10), fg="#0066cc").pack(side="left")

            # 可合成的镐子列表(木镐和下界合金镐不在合成台, 下界合金镐只能锻造)
            for key, info in self._PICKAXE_TYPES.items():
                if key in ("wood", "netherite"):
                    continue
                frame = tk.Frame(win, relief="solid", borderwidth=1, padx=8, pady=4)
                frame.pack(fill="x", padx=10, pady=3)

                # 左侧: 镐子贴图
                photo = self._pickaxe_photos.get(key)
                if photo:
                    tk.Label(frame, image=photo).pack(side="left", padx=4)

                # 右侧: 信息
                info_frame = tk.Frame(frame)
                info_frame.pack(side="left", fill="x", expand=True)
                cost_text = " + ".join(
                    f"{v} {self._DROP_NAMES.get(k, k)}"
                    for k, v in info["cost"].items()
                )
                tk.Label(info_frame, text=f"{info['name']} "
                         f"(效率x{info['efficiency']}, 耐久{info['durability']})",
                         font=("Arial", 9, "bold")).pack(anchor="w")
                tk.Label(info_frame, text=f"需要: {cost_text}", font=("Arial", 8),
                         fg="#666").pack(anchor="w")

                # 检查材料是否足够
                can_craft = all(self._inventory.get(k, 0) >= v
                                for k, v in info["cost"].items())
                btn = ttk.Button(frame, text="合成",
                                 command=lambda k=key: self._craft_pickaxe(k, win),
                                 state="normal" if can_craft else "disabled")
                btn.pack(side="right", pady=2)
        except Exception:
            pass

    def _craft_pickaxe(self, ptype, craft_win):
        """合成镐子"""
        info = self._PICKAXE_TYPES[ptype]
        # 下界合金镐不能合成, 只能锻造
        if ptype == "netherite":
            self._creeper_say("下界合金镐需要在锻造台锻造！", 2500)
            return
        # 检查材料是否足够
        for k, v in info["cost"].items():
            if self._inventory.get(k, 0) < v:
                self._creeper_say(f"材料不足: 需要 {v} {self._DROP_NAMES.get(k, k)}", 2500)
                return
        # 扣除材料
        for k, v in info["cost"].items():
            self._inventory[k] -= v
            self._inv_labels[k].config(text=str(self._inventory[k]))
        # 装备新镐子
        self._pickaxe = {"type": ptype, "durability": info["durability"]}
        self._save_pickaxe()
        self._update_pickaxe_label()
        self._creeper_say(f"合成了 {info['name']}！挖矿更快了！", 2500)
        craft_win.destroy()

    # ---------------- 锻造台 ----------------
    def _open_smithing_table(self):
        """打开锻造台窗口: 钻石镐+下界合金锭→下界合金镐"""
        try:
            win = tk.Toplevel(self.root)
            win.title("⚒ 锻造台")
            win.geometry("360x320")
            win.resizable(False, False)
            win.configure(bg="#8b6914")

            # 标题
            tk.Label(win, text="⚒ 锻造台", bg="#8b6914",
                     font=("Arial", 14, "bold"), fg="#ffffff").pack(pady=8)

            # 锻造台贴图
            table_photo = self._item_photos.get("smithing_table")
            if table_photo:
                tk.Label(win, image=table_photo, bg="#8b6914").pack(pady=4)

            # 当前镐子
            ptype = self._pickaxe.get("type", "wood")
            cur = self._PICKAXE_TYPES[ptype]
            cur_photo = self._pickaxe_photos.get(ptype)
            cur_frame = tk.Frame(win, bg="#8b6914")
            cur_frame.pack(pady=4)
            if cur_photo:
                tk.Label(cur_frame, image=cur_photo, bg="#8b6914").pack(side="left", padx=4)
            tk.Label(cur_frame, text=f"当前: {cur['name']}", bg="#8b6914",
                     fg="#ffffff", font=("Arial", 10)).pack(side="left")

            # 需要材料
            netherite_count = self._inventory.get("netherite_ingot", 0)
            ingot_photo = self._item_photos.get("netherite_ingot")
            mat_frame = tk.Frame(win, bg="#8b6914")
            mat_frame.pack(pady=4)
            if ingot_photo:
                tk.Label(mat_frame, image=ingot_photo, bg="#8b6914").pack(side="left", padx=4)
            tk.Label(mat_frame, text=f"下界合金锭: {netherite_count}/1",
                     bg="#8b6914", fg="#ffffff", font=("Arial", 10)).pack(side="left")

            # 检查是否可以锻造
            can_smith = (ptype == "diamond" and netherite_count >= 1)
            if can_smith:
                btn = ttk.Button(win, text="⚒ 锻造成下界合金镐！",
                                 command=lambda: self._do_smithing(win))
                btn.pack(pady=8)
            else:
                reason = []
                if ptype != "diamond":
                    reason.append("需要钻石镐")
                if netherite_count < 1:
                    reason.append("需要下界合金锭")
                tk.Label(win, text="无法锻造: " + "、".join(reason),
                         bg="#8b6914", fg="#ffaaaa", font=("Arial", 9),
                         wraplength=300).pack(pady=8)
                tk.Label(win, text="(挖矿有概率挖到远古残骸，获得下界合金锭)",
                         bg="#8b6914", fg="#cccccc", font=("Arial", 8)).pack()
        except Exception:
            pass

    def _do_smithing(self, smith_win):
        """执行锻造: 钻石镐+下界合金锭→下界合金镐"""
        # 检查材料
        ptype = self._pickaxe.get("type", "wood")
        if ptype != "diamond":
            self._creeper_say("需要钻石镐才能锻造！", 2500)
            smith_win.destroy()
            return
        if self._inventory.get("netherite_ingot", 0) < 1:
            self._creeper_say("需要下界合金锭！", 2500)
            smith_win.destroy()
            return
        # 消耗下界合金锭
        self._inventory["netherite_ingot"] -= 1
        self._inv_labels["netherite_ingot"].config(
            text=str(self._inventory["netherite_ingot"]))
        # 装备下界合金镐(保留钻石镐的耐久比例)
        diamond_dur = self._pickaxe.get("durability", 500)
        diamond_max = self._PICKAXE_TYPES["diamond"]["durability"]
        netherite_max = self._PICKAXE_TYPES["netherite"]["durability"]
        ratio = diamond_dur / diamond_max if diamond_max > 0 else 1.0
        new_dur = int(netherite_max * ratio)
        self._pickaxe = {"type": "netherite", "durability": new_dur}
        self._save_pickaxe()
        self._update_pickaxe_label()
        self._creeper_say("⚒ 锻造出了下界合金镐！最强镐子！", 3000)
        self._unlock_achievement("netherite_pickaxe")
        smith_win.destroy()

    def _open_skin_editor(self):
        """打开皮肤编辑器"""
        try:
            game_dir = CONFIG.get("game_dir")
            skin_editor.open_skin_editor(self.root, game_dir=game_dir)
            self._log("已打开皮肤编辑器")
        except Exception as e:
            self._log(f"打开皮肤编辑器失败: {e}")

    # ---------------- 熔炉/高炉系统 ----------------
    # 可烧炼配方: 输入→输出, 高炉专用标记
    _SMELTING_RECIPES = {
        "raw_iron": {"output": "iron", "blast_only": False, "time": 3},
        "raw_gold": {"output": "gold", "blast_only": False, "time": 3},
        "ancient_debris": {"output": "netherite_ingot", "blast_only": False, "time": 5},
        "iron_ore": {"output": "iron", "blast_only": False, "time": 3},
        "gold_ore": {"output": "gold", "blast_only": False, "time": 3},
        "coal_ore": {"output": "coal", "blast_only": False, "time": 3},
        "diamond_ore": {"output": "diamond", "blast_only": False, "time": 3},
        "emerald_ore": {"output": "emerald", "blast_only": False, "time": 3},
        "stone": {"output": "stone", "blast_only": False, "time": 2},
    }

    def _open_furnace(self, furnace_type="normal"):
        """打开熔炉/高炉窗口"""
        try:
            is_blast = furnace_type == "blast"
            title = "🏭 高炉" if is_blast else "🔥 熔炉"
            win = tk.Toplevel(self.root)
            win.title(title)
            win.geometry("420x480")
            win.resizable(False, False)
            bg = "#5a4a3a" if is_blast else "#8b6914"
            win.configure(bg=bg)

            tk.Label(win, text=title, bg=bg, fg="#fff",
                     font=("Arial", 14, "bold")).pack(pady=8)

            # 燃料显示
            fuel_frame = tk.Frame(win, bg=bg)
            fuel_frame.pack(pady=4)
            tk.Label(fuel_frame, text="燃料(煤炭):", bg=bg, fg="#fff",
                     font=("Arial", 10)).pack(side="left")
            fuel_count = self._inventory.get("coal", 0)
            self._furnace_fuel_label = tk.Label(fuel_frame, text=str(fuel_count),
                                                  bg=bg, fg="#ffdd00",
                                                  font=("Arial", 12, "bold"))
            self._furnace_fuel_label.pack(side="left", padx=5)
            tk.Label(fuel_frame, text="(1煤炭=8个物品)", bg=bg, fg="#ccc",
                     font=("Arial", 8)).pack(side="left", padx=5)

            # 可烧炼物品列表
            list_frame = tk.Frame(win, bg=bg)
            list_frame.pack(fill="both", expand=True, padx=10, pady=5)
            canvas = tk.Canvas(list_frame, bg=bg, highlightthickness=0)
            scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
            scroll_frame = tk.Frame(canvas, bg=bg)
            scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            self._furnace_buttons = []
            speed = 2 if is_blast else 1
            for item_key, recipe in self._SMELTING_RECIPES.items():
                count = self._inventory.get(item_key, 0)
                if count <= 0:
                    continue
                in_name = self._DROP_NAMES.get(item_key, item_key)
                out_name = self._DROP_NAMES.get(recipe["output"], recipe["output"])
                row = tk.Frame(scroll_frame, bg=bg, relief="solid", borderwidth=1, padx=8, pady=4)
                row.pack(fill="x", pady=2)
                tk.Label(row, text=f"{in_name} x{count}  →  {out_name}",
                         bg=bg, fg="#fff", font=("Arial", 9)).pack(side="left")
                btn = ttk.Button(row, text="烧1个", width=8,
                                 command=lambda k=item_key, r=recipe, s=speed:
                                 self._do_smelt(k, r, s, win))
                btn.pack(side="right", padx=2)
                btn2 = ttk.Button(row, text="烧全部", width=8,
                                  command=lambda k=item_key, r=recipe, s=speed:
                                  self._do_smelt_all(k, r, s, win))
                btn2.pack(side="right", padx=2)
                self._furnace_buttons.append((btn, btn2, item_key))

            if not self._furnace_buttons:
                tk.Label(scroll_frame, text="没有可烧炼的物品\n(先去挖矿获得铁矿石/金矿石/远古残骸)",
                         bg=bg, fg="#ffaaaa", font=("Arial", 10),
                         justify="center").pack(pady=20)

            # 提示
            tip = "高炉: 烧矿石速度2倍" if is_blast else "熔炉: 可烧矿石和石头"
            tk.Label(win, text=tip, bg=bg, fg="#ccc", font=("Arial", 8)).pack(pady=4)
        except Exception as e:
            pass

    def _do_smelt(self, item_key, recipe, speed, furnace_win):
        """烧炼单个物品"""
        # 检查燃料
        if self._inventory.get("coal", 0) < 1:
            self._creeper_say("没有煤炭当燃料了！", 2000)
            return
        # 检查物品
        if self._inventory.get(item_key, 0) < 1:
            return
        # 消耗燃料和物品
        self._inventory["coal"] -= 1
        self._inventory[item_key] -= 1
        # 获得产物
        output = recipe["output"]
        self._inventory[output] = self._inventory.get(output, 0) + 1
        # 更新显示
        self._update_inv_labels()
        self._furnace_fuel_label.config(text=str(self._inventory.get("coal", 0)))
        # 烧炼动画(模拟时间)
        time_ms = int(recipe["time"] * 1000 / speed)
        self._creeper_say(f"🔥 烧炼中... {self._DROP_NAMES.get(output, output)}", time_ms)
        furnace_win.after(time_ms, lambda: self._refresh_furnace(furnace_win))

    def _do_smelt_all(self, item_key, recipe, speed, furnace_win):
        """烧炼全部物品"""
        count = self._inventory.get(item_key, 0)
        coal = self._inventory.get("coal", 0)
        if count <= 0 or coal <= 0:
            return
        # 最多烧 min(count, coal*8) 个
        max_smelt = min(count, coal * 8)
        # 消耗燃料
        coal_used = (max_smelt + 7) // 8  # 向上取整
        self._inventory["coal"] -= coal_used
        self._inventory[item_key] -= max_smelt
        # 获得产物
        output = recipe["output"]
        self._inventory[output] = self._inventory.get(output, 0) + max_smelt
        # 更新显示
        self._update_inv_labels()
        self._furnace_fuel_label.config(text=str(self._inventory.get("coal", 0)))
        time_ms = int(recipe["time"] * 500 / speed * max_smelt)
        self._creeper_say(f"🔥 烧炼 {max_smelt} 个...", min(time_ms, 3000))
        furnace_win.after(min(time_ms, 3000), lambda: self._refresh_furnace(furnace_win))

    def _refresh_furnace(self, furnace_win):
        """刷新熔炉窗口"""
        furnace_win.destroy()
        # 重新打开(简化处理)
        is_blast = "高炉" in furnace_win.title() if furnace_win else False
        self.root.after(100, lambda: self._open_furnace("blast" if is_blast else "normal"))

    def _update_inv_labels(self):
        """更新所有背包标签"""
        for key, lbl in self._inv_labels.items():
            if key in self._inventory:
                lbl.config(text=str(self._inventory[key]))

    # ---------------- 附魔系统 ----------------
    def _open_enchanting(self):
        """打开附魔台窗口"""
        try:
            win = tk.Toplevel(self.root)
            win.title("✨ 附魔台")
            win.geometry("400x420")
            win.resizable(False, False)
            win.configure(bg="#4a3a6a")

            tk.Label(win, text="✨ 附魔台", bg="#4a3a6a", fg="#fff",
                     font=("Arial", 14, "bold")).pack(pady=8)

            # 经验显示
            xp_frame = tk.Frame(win, bg="#4a3a6a")
            xp_frame.pack(pady=4)
            tk.Label(xp_frame, text=f"⭐ 等级: {self._xp_level}", bg="#4a3a6a",
                     fg="#00ff00", font=("Arial", 12, "bold")).pack(side="left", padx=10)
            tk.Label(xp_frame, text=f"经验: {self._xp_points}/10", bg="#4a3a6a",
                     fg="#aaa", font=("Arial", 10)).pack(side="left")

            # 当前附魔
            cur_frame = tk.Frame(win, bg="#4a3a6a")
            cur_frame.pack(pady=4)
            tk.Label(cur_frame, text="当前附魔:", bg="#4a3a6a", fg="#fff",
                     font=("Arial", 10)).pack(side="left")
            if self._enchantments:
                enc_text = "  ".join(
                    f"{self._ENCHANTMENTS[k]['name']} {v}"
                    for k, v in self._enchantments.items()
                )
                tk.Label(cur_frame, text=enc_text, bg="#4a3a6a", fg="#ffdd00",
                         font=("Arial", 10, "bold")).pack(side="left", padx=5)
            else:
                tk.Label(cur_frame, text="无", bg="#4a3a6a", fg="#888",
                         font=("Arial", 10)).pack(side="left", padx=5)

            # 刷新附魔选项
            tk.Label(win, text="可用附魔(随机刷新):", bg="#4a3a6a", fg="#fff",
                     font=("Arial", 10)).pack(pady=(10, 4))

            options_frame = tk.Frame(win, bg="#4a3a6a")
            options_frame.pack(fill="x", padx=10)

            enchants = self._roll_enchantments()
            for enc_key, level, cost in enchants:
                info = self._ENCHANTMENTS[enc_key]
                row = tk.Frame(options_frame, bg="#5a4a7a", relief="solid",
                               borderwidth=1, padx=8, pady=6)
                row.pack(fill="x", pady=3)
                left = tk.Frame(row, bg="#5a4a7a")
                left.pack(side="left")
                tk.Label(left, text=f"{info['name']} {level}", bg="#5a4a7a",
                         fg="#fff", font=("Arial", 11, "bold")).pack(anchor="w")
                tk.Label(left, text=info["desc"], bg="#5a4a7a", fg="#ccc",
                         font=("Arial", 8)).pack(anchor="w")
                # 检查是否可以附魔
                can_enchant = self._xp_level >= cost
                cur_level = self._enchantments.get(enc_key, 0)
                already_max = cur_level >= info["max_level"]
                btn_text = f"附魔 (需{cost}级)"
                if already_max:
                    btn_text = "已满级"
                btn = ttk.Button(row, text=btn_text, width=12,
                                 command=lambda k=enc_key, lv=level, c=cost, w=win:
                                 self._do_enchant(k, lv, c, w),
                                 state="normal" if can_enchant and not already_max else "disabled")
                btn.pack(side="right")

            # 刷新按钮
            ttk.Button(win, text="🔄 刷新附魔 (1级)",
                       command=lambda: self._refresh_enchanting(win)).pack(pady=10)
        except Exception as e:
            pass

    def _roll_enchantments(self):
        """随机刷新3个附魔选项, 精准采集10.5%概率"""
        results = []
        used = set()
        # 精准采集单独判定(10.5%)
        if random.random() < 0.105 and "silk_touch" not in used:
            results.append(("silk_touch", 1, 15))
            used.add("silk_touch")
        # 其他附魔按权重随机
        others = {k: v for k, v in self._ENCHANTMENTS.items() if k != "silk_touch"}
        while len(results) < 3:
            total_weight = sum(v["weight"] for k, v in others.items() if k not in used)
            if total_weight <= 0:
                break
            r = random.uniform(0, total_weight)
            cumulative = 0
            for k, v in others.items():
                if k in used:
                    continue
                cumulative += v["weight"]
                if r <= cumulative:
                    level = random.randint(1, v["max_level"])
                    cost = level * 3 + random.randint(0, 3)
                    results.append((k, level, cost))
                    used.add(k)
                    break
        return results

    def _do_enchant(self, enc_key, level, cost, win):
        """执行附魔"""
        if self._xp_level < cost:
            return
        # 消耗经验等级
        self._xp_level -= cost
        # 应用附魔(取最高等级)
        cur_level = self._enchantments.get(enc_key, 0)
        self._enchantments[enc_key] = max(cur_level, level)
        # 更新显示
        self._xp_label.config(text=f"⭐ Lv.{self._xp_level} ({self._xp_points}/10)")
        self._creeper_say(f"✨ 附魔成功: {self._ENCHANTMENTS[enc_key]['name']} {level}！", 3000)
        win.destroy()
        self.root.after(300, self._open_enchanting)

    def _refresh_enchanting(self, win):
        """刷新附魔选项(消耗1级)"""
        if self._xp_level < 1:
            self._creeper_say("经验等级不足！", 2000)
            return
        self._xp_level -= 1
        self._xp_label.config(text=f"⭐ Lv.{self._xp_level} ({self._xp_points}/10)")
        win.destroy()
        self.root.after(100, self._open_enchanting)

    # ---------------- 村民交易系统 ----------------
    _VILLAGER_PROFESSIONS = {
        "blacksmith": {
            "name": "铁匠",
            "trades": [
                {"give": {"coal": 15}, "get": {"iron": 1}},
                {"give": {"iron": 12}, "get": {"gold": 1}},
                {"give": {"gold": 8}, "get": {"diamond": 1}},
                {"give": {"diamond": 5}, "get": {"netherite_ingot": 1}},
            ]
        },
        "priest": {
            "name": "牧师",
            "trades": [
                {"give": {"coal": 10}, "get": {"emerald": 1}},
                {"give": {"emerald": 5}, "get": {"diamond": 1}},
                {"give": {"gold": 6}, "get": {"emerald": 2}},
            ]
        },
        "farmer": {
            "name": "农民",
            "trades": [
                {"give": {"stone": 20}, "get": {"coal": 1}},
                {"give": {"coal": 8}, "get": {"iron": 1}},
                {"give": {"iron": 15}, "get": {"gold": 1}},
            ]
        },
        "librarian": {
            "name": "图书管理员",
            "trades": [
                {"give": {"diamond": 3}, "get": {"emerald": 1}},
                {"give": {"emerald": 2}, "get": {"gold": 1}},
                {"give": {"gold": 4}, "get": {"diamond": 1}},
            ]
        },
        "butcher": {
            "name": "屠夫",
            "trades": [
                {"give": {"stone": 30}, "get": {"coal": 2}},
                {"give": {"coal": 20}, "get": {"iron": 2}},
                {"give": {"iron": 20}, "get": {"gold": 2}},
            ]
        },
        "toolsmith": {
            "name": "工具匠",
            "trades": [
                {"give": {"coal": 12}, "get": {"iron": 1}},
                {"give": {"iron": 10}, "get": {"gold": 1}},
                {"give": {"gold": 5}, "get": {"diamond": 1}},
                {"give": {"emerald": 3}, "get": {"netherite_ingot": 1}},
            ]
        },
    }
    _VILLAGER_QUOTES = [
        "hmm?", "hmm.", "hmm!", "yee-haw!", "hrmm",
        "嗯?", "嗯.", "好的", "不错的交易", "要看看吗?",
        "这是好东西", "便宜卖了", "不买别碰", "嘿嘿嘿",
    ]

    # 流浪商人交易选项(更稀有划算)
    _WANDERING_TRADER_TRADES = [
        {"give": {"emerald": 1}, "get": {"diamond": 1}},
        {"give": {"diamond": 2}, "get": {"netherite_ingot": 1}},
        {"give": {"coal": 5}, "get": {"emerald": 1}},
        {"give": {"iron": 3}, "get": {"gold": 1}},
        {"give": {"stone": 10}, "get": {"coal": 1}},
        {"give": {"gold": 2}, "get": {"diamond": 1}},
    ]
    _WANDERING_TRADER_QUOTES = [
        "Hmm.", "Hmm?", "Hah!", "I have what you need.",
        "看看我的货吧", "这可是好东西", "只在下雨天出现哦",
        "机会难得", "走过路过不要错过", "嘿嘿，划算吧",
    ]

    def _open_trading(self):
        """打开村民交易窗口(支持流浪商人)"""
        try:
            # 判断是流浪商人还是普通村民(支持切换)
            actual_wandering = getattr(self, '_wandering_trader_active', False)
            display_override = getattr(self, '_trader_display_override', None)
            if display_override is not None:
                is_wandering = display_override
            else:
                is_wandering = actual_wandering

            if is_wandering:
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

            win = tk.Toplevel(self.root)
            title = "🧳 流浪商人" if is_wandering else "🤝 村民交易"
            win.title(title)
            win.geometry("380x440")
            win.resizable(False, False)
            bg_color = "#4a6a8a" if is_wandering else "#c8a878"
            win.configure(bg=bg_color)
            self._trade_win = win

            # 村民头部
            top_bg = "#2a4a6a" if is_wandering else "#8b6914"
            top_frame = tk.Frame(win, bg=top_bg, padx=10, pady=8)
            top_frame.pack(fill="x")
            if villager_photo:
                tk.Label(top_frame, image=villager_photo, bg=top_bg).pack(side="left", padx=5)
            info_frame = tk.Frame(top_frame, bg=top_bg)
            info_frame.pack(side="left", padx=10, fill="y")
            name_color = "#88ddff" if is_wandering else "#ffffff"
            tk.Label(info_frame, text=self._current_villager["name"],
                     bg=top_bg, fg=name_color, font=("Arial", 13, "bold")).pack(anchor="w")
            if is_wandering:
                tk.Label(info_frame, text="(下雨天限定, 交易更划算!)",
                         bg=top_bg, fg="#aaccff", font=("Arial", 8, "italic")).pack(anchor="w")
            self._villager_quote_label = tk.Label(info_frame, text=random.choice(quotes),
                                                   bg=top_bg, fg="#ffeecc", font=("Arial", 10, "italic"))
            self._villager_quote_label.pack(anchor="w")

            # 村民血量条(普通村民才有, 流浪商人不能打)
            if not is_wandering:
                hp_frame = tk.Frame(info_frame, bg=top_bg)
                hp_frame.pack(anchor="w", pady=(4, 0))
                tk.Label(hp_frame, text="❤", bg=top_bg, fg="#ff4444",
                         font=("Arial", 10)).pack(side="left")
                self._villager_hp_bar = tk.Canvas(hp_frame, width=100, height=14,
                                                   bg="#333", highlightthickness=0)
                self._villager_hp_bar.pack(side="left", padx=4)
                self._villager_hp_text = tk.Label(hp_frame, text=f"{self._villager_hp}/{self._villager_max_hp}",
                                                   bg=top_bg, fg="#fff", font=("Arial", 9, "bold"))
                self._villager_hp_text.pack(side="left")
                self._update_villager_hp_bar()
                # 按钮行(攻击+换村民, 放血量条下面避免被截断)
                btn_row = tk.Frame(info_frame, bg=top_bg)
                btn_row.pack(anchor="w", pady=(4, 0))
                ttk.Button(btn_row, text="🪓 攻击", width=8,
                           command=lambda: self._attack_villager(win)).pack(side="left", padx=2)
                ttk.Button(btn_row, text="🔄 换村民", width=8,
                           command=lambda: self._refresh_villager(win)).pack(side="left", padx=2)
            # 流浪商人活跃时, 加切换按钮(放右上角)
            if getattr(self, '_wandering_trader_active', False):
                switch_text = "👤 普通村民" if is_wandering else "🧳 流浪商人"
                ttk.Button(top_frame, text=switch_text, width=10,
                           command=lambda: self._switch_trader(win)).pack(side="right", padx=5)

            # 伤害显示标签
            self._damage_label = tk.Label(win, text="", bg=bg_color, fg="#ff0000",
                                           font=("Arial", 16, "bold"))
            self._damage_label.pack(pady=2)

            # 交易列表
            list_frame = tk.Frame(win, bg=bg_color, padx=10, pady=8)
            list_frame.pack(fill="both", expand=True)
            tk.Label(list_frame, text="交易选项:", bg=bg_color,
                     font=("Arial", 10, "bold"), fg="#ffffff" if is_wandering else "#5a3a1a").pack(anchor="w")

            self._trade_buttons = []
            self._current_quotes = quotes
            for i, trade in enumerate(self._current_villager["trades"]):
                self._build_trade_row(list_frame, trade, i, bg_color, is_wandering)

            # 底部提示
            hint_color = "#aaccff" if is_wandering else "#666"
            tk.Label(win, text="提示: 材料不足的交易按钮会变灰",
                     bg=bg_color, fg=hint_color, font=("Arial", 8)).pack(pady=4)
        except Exception:
            pass

    def _add_xp(self, amount):
        """增加经验"""
        self._xp_points += amount
        # 每10点经验升1级
        while self._xp_points >= 10:
            self._xp_points -= 10
            self._xp_level += 1
        # 更新经验显示(如果有标签)
        if hasattr(self, "_xp_label"):
            self._xp_label.config(text=f"⭐ Lv.{self._xp_level} ({self._xp_points}/10)")

    def _build_trade_row(self, parent, trade, index, bg_color="#c8a878", is_wandering=False):
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
                 bg=bg_color, font=("Arial", 9), fg=text_color).pack(side="left")

        # 检查材料是否足够(用折扣价)
        can_trade = all(self._inventory.get(k, 0) >= v for k, v in discounted_give.items())
        if not is_wandering and hasattr(self, '_villager_hp') and self._villager_hp <= 0:
            can_trade = False
        btn = ttk.Button(row, text="交易", width=6,
                         command=lambda t=trade: self._do_trade(t),
                         state="normal" if can_trade else "disabled")
        btn.pack(side="right")
        self._trade_buttons.append((btn, trade))

    def _do_trade(self, trade):
        """执行交易"""
        # 使用折扣后的价格(如果有)
        give_items = trade.get("_discounted_give", trade["give"])
        get_items = trade["get"]
        # 扣除材料
        for k, v in give_items.items():
            self._inventory[k] -= v
            if k in self._inv_labels:
                self._inv_labels[k].config(text=str(self._inventory[k]))
        # 获得物品
        for k, v in get_items.items():
            self._inventory[k] = self._inventory.get(k, 0) + v
            if k in self._inv_labels:
                self._inv_labels[k].config(text=str(self._inventory[k]))
        # 村民说话
        quotes = getattr(self, "_current_quotes", self._VILLAGER_QUOTES)
        self._villager_quote_label.config(text=random.choice(quotes))
        # 刷新交易按钮状态
        for btn, t in self._trade_buttons:
            give = t.get("_discounted_give", t["give"])
            can = all(self._inventory.get(k, 0) >= v for k, v in give.items())
            btn.config(state="normal" if can else "disabled")
        # 成就检测
        if get_items.get("netherite_ingot", 0) > 0:
            self._unlock_achievement("trading_master")

    def _switch_trader(self, win):
        """在普通村民和流浪商人之间切换"""
        if not hasattr(self, '_trader_display_override'):
            self._trader_display_override = None
        actual = getattr(self, '_wandering_trader_active', False)
        current = actual if self._trader_display_override is None else self._trader_display_override
        self._trader_display_override = not current
        win.destroy()
        self.root.after(100, self._open_trading)

    def _refresh_villager(self, old_win):
        """刷新村民(换职业)"""
        self._villager_hp = self._villager_max_hp  # 新村民满血
        old_win.destroy()
        self.root.after(100, self._open_trading)

    def _update_villager_hp_bar(self):
        """更新村民血量条"""
        try:
            if not hasattr(self, '_villager_hp_bar'):
                return
            self._villager_hp_bar.delete("all")
            ratio = max(0, self._villager_hp / self._villager_max_hp)
            width = int(120 * ratio)
            color = "#44ff44" if ratio > 0.5 else ("#ffaa00" if ratio > 0.25 else "#ff4444")
            self._villager_hp_bar.create_rectangle(0, 0, width, 14, fill=color, outline="")
            self._villager_hp_text.config(text=f"{max(0,self._villager_hp)}/{self._villager_max_hp}")
        except Exception:
            pass

    def _get_villager_discount(self):
        """获取村民交易折扣: 血量越低折扣越大"""
        ratio = max(0, self._villager_hp / self._villager_max_hp)
        # 血量100%=原价, 血量0%=5折
        return 0.5 + 0.5 * ratio

    def _attack_villager(self, win):
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
            self._rebuild_trade_list(win)

    def _rebuild_trade_list(self, win):
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
            pass

    def _trader_say(self, text, duration=2500):
        """流浪商人说话(气泡显示)"""
        try:
            self._trader_bubble.config(text=text)
            self._trader_bubble.place(x=90, y=10)
            self.root.after(duration, lambda: self._trader_bubble.place_forget())
        except Exception:
            pass

    def _trader_wander(self):
        """流浪商人随机走动"""
        try:
            if getattr(self, '_wandering_trader_active', False) and getattr(self, '_wandering_trader_photo', None):
                frame_width = self._trader_frame.winfo_width() or 800
                current_x = self._trader_label.winfo_x()
                direction = random.choice([-1, 1])
                distance = random.randint(30, 100)
                new_x = current_x + direction * distance
                new_x = max(10, min(frame_width - 80, new_x))
                self._trader_label.place(x=new_x, y=5)
                # 偶尔说话
                if random.random() < 0.4:
                    self._trader_say(random.choice(self._WANDERING_TRADER_QUOTES))
        except Exception:
            pass
        self.root.after(random.randint(4000, 7000), self._trader_wander)

    # ---------------- 版本下载页 ----------------
    def _build_versions_tab(self):
        f = self.tab_versions
        top = ttk.Frame(f)
        top.pack(fill="x", padx=8, pady=4)
        ttk.Label(top, text="版本筛选:").pack(side="left")
        self.ver_filter = ttk.Combobox(top, state="readonly", width=10,
                                       values=["全部", "正式版", "快照", "旧版"])
        self.ver_filter.current(0)
        self.ver_filter.pack(side="left", padx=4)
        self.ver_filter.bind("<<ComboboxSelected>>",
                             lambda e: self._filter_versions())
        ttk.Button(top, text="刷新列表", command=self.refresh_version_list).pack(
            side="left", padx=6)

        mid = ttk.Frame(f)
        mid.pack(fill="both", expand=True, padx=8, pady=2)
        self.ver_list = tk.Listbox(mid)
        self.ver_list.pack(side="left", fill="both", expand=True)
        v_sb = ttk.Scrollbar(mid, command=self.ver_list.yview)
        v_sb.pack(side="right", fill="y")
        self.ver_list.configure(yscrollcommand=v_sb.set)

        bottom = ttk.Frame(f)
        bottom.pack(fill="x", padx=8, pady=4)
        self.dl_btn = ttk.Button(bottom, text="下载选中版本",
                                 command=self._download_version)
        self.dl_btn.pack(side="left", padx=4)
        ttk.Label(bottom, text="一键安装加载器:").pack(side="left", padx=(14, 4))
        self.loader_var = tk.StringVar(value="fabric")
        for txt, val in [("Fabric", "fabric"), ("Quilt", "quilt"),
                         ("Forge", "forge"), ("NeoForge", "neoforge")]:
            ttk.Radiobutton(bottom, text=txt, value=val,
                            variable=self.loader_var).pack(side="left", padx=2)
        ttk.Button(bottom, text="安装加载器到新实例",
                   command=self._install_loader).pack(side="left", padx=6)

        # 第二行: 加载器版本 + API 版本选择
        bottom2 = ttk.Frame(f)
        bottom2.pack(fill="x", padx=8, pady=2)
        ttk.Label(bottom2, text="加载器版本:").pack(side="left")
        self.loader_ver_var = tk.StringVar(value="(自动获取)")
        self.loader_ver_combo = ttk.Combobox(bottom2, width=18,
            textvariable=self.loader_ver_var, state="readonly")
        self.loader_ver_combo.pack(side="left", padx=4)
        ttk.Label(bottom2, text="API版本:").pack(side="left", padx=(10, 2))
        self.api_ver_var = tk.StringVar(value="(最新版)")
        self.api_ver_combo = ttk.Combobox(bottom2, width=18,
            textvariable=self.api_ver_var, state="readonly")
        self.api_ver_combo.pack(side="left", padx=4)
        ttk.Button(bottom2, text="刷新版本列表",
                   command=self._refresh_loader_versions).pack(side="left", padx=6)
        # 单选按钮切换时自动刷新版本
        self.loader_var.trace_add("write", lambda *a: self._refresh_loader_versions())

        self.vdl_status = ttk.Label(f, text="")
        self.vdl_status.pack(fill="x", padx=8, pady=2)

    # ---------------- Modrinth 页 ----------------
    def _build_modrinth_tab(self):
        f = self.tab_modrinth
        top = ttk.Frame(f)
        top.pack(fill="x", padx=8, pady=4)
        ttk.Label(top, text="搜索:").pack(side="left")
        self.mr_query = ttk.Entry(top, width=22)
        self.mr_query.pack(side="left", padx=4)
        self.mr_query.bind("<Return>", lambda e: self._mr_search())
        ttk.Label(top, text="游戏版本:").pack(side="left", padx=(10, 2))
        self.mr_gv = ttk.Combobox(top, width=10, values=["1.21.4", "1.21.1",
                                                          "1.20.4", "1.20.1",
                                                          "1.19.4", "1.18.2",
                                                          "1.17.1", "1.16.5"])
        self.mr_gv.current(0)
        self.mr_gv.pack(side="left")
        ttk.Label(top, text="加载器:").pack(side="left", padx=(10, 2))
        self.mr_loader = ttk.Combobox(top, state="readonly", width=8,
                                      values=["任意", "fabric", "forge",
                                              "quilt", "neoforge"])
        self.mr_loader.current(0)
        self.mr_loader.pack(side="left")
        ttk.Button(top, text="搜索", command=self._mr_search).pack(
            side="left", padx=6)

        mid = ttk.Frame(f)
        mid.pack(fill="both", expand=True, padx=8, pady=2)
        # 带图标的 Treeview 列表
        cols = ("name", "type", "downloads")
        self.mr_tree = ttk.Treeview(mid, columns=cols, show="tree headings",
                                    height=15, selectmode="browse")
        self.mr_tree.heading("#0", text="图标")
        self.mr_tree.heading("name", text="模组名称")
        self.mr_tree.heading("type", text="类型")
        self.mr_tree.heading("downloads", text="下载量")
        self.mr_tree.column("#0", width=50, anchor="center")
        self.mr_tree.column("name", width=250, anchor="w")
        self.mr_tree.column("type", width=80, anchor="center")
        self.mr_tree.column("downloads", width=100, anchor="e")
        self.mr_tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(mid, command=self.mr_tree.yview)
        sb.pack(side="right", fill="y")
        self.mr_tree.configure(yscrollcommand=sb.set)
        self.mr_tree.bind("<<TreeviewSelect>>", lambda e: self._mr_on_select())
        self.mr_icon_images = {}

        bottom = ttk.Frame(f)
        bottom.pack(fill="x", padx=8, pady=4)
        ttk.Button(bottom, text="下载到当前实例",
                   command=self._mr_download).pack(side="left", padx=4)
        ttk.Button(bottom, text="导入 mrpack 整合包",
                   command=self._import_mrpack).pack(side="left", padx=4)
        self.mr_status = ttk.Label(f, text="")
        self.mr_status.pack(fill="x", padx=8, pady=2)

        # 第一次切换到 Modrinth 标签页时自动搜索热门模组
        self._mr_auto_searched = False
        self.nb.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _on_tab_changed(self, event):
        """标签页切换事件: 第一次切到 Modrinth 时自动搜索"""
        try:
            current = self.nb.select()
            tab_text = self.nb.tab(current, "text")
            if "Modrinth" in tab_text and not getattr(self, '_mr_auto_searched', False):
                self._mr_auto_searched = True
                self.root.after(300, self._mr_search)
        except Exception:
            pass

    # ---------------- CurseForge 页(密钥非空才显示) ----------------
    def _build_curseforge_tab(self):
        f = self.tab_curseforge
        top = ttk.Frame(f)
        top.pack(fill="x", padx=8, pady=4)
        ttk.Label(top, text="搜索:").pack(side="left")
        self.cf_query = ttk.Entry(top, width=22)
        self.cf_query.pack(side="left", padx=4)
        self.cf_query.bind("<Return>", lambda e: self._cf_search())
        ttk.Label(top, text="分类:").pack(side="left", padx=(10, 2))
        self.cf_class = ttk.Combobox(top, state="readonly", width=9,
                                     values=["模组", "资源包", "整合包",
                                             "世界", "光影", "数据包"])
        self.cf_class.current(0)
        self.cf_class.pack(side="left")
        ttk.Label(top, text="游戏版本:").pack(side="left", padx=(10, 2))
        self.cf_gv = ttk.Combobox(top, width=10, values=["1.21.4", "1.21.1",
                                                         "1.20.4", "1.20.1",
                                                         "1.19.4", "1.18.2",
                                                         "1.17.1", "1.16.5"])
        self.cf_gv.current(0)
        self.cf_gv.pack(side="left")
        ttk.Label(top, text="加载器:").pack(side="left", padx=(10, 2))
        self.cf_loader = ttk.Combobox(top, state="readonly", width=9,
                                      values=["任意", "forge", "fabric",
                                              "quilt", "neoforge"])
        self.cf_loader.current(0)
        self.cf_loader.pack(side="left")
        ttk.Button(top, text="搜索", command=self._cf_search).pack(
            side="left", padx=6)

        mid = ttk.Frame(f)
        mid.pack(fill="both", expand=True, padx=8, pady=2)
        self.cf_list = tk.Listbox(mid)
        self.cf_list.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(mid, command=self.cf_list.yview)
        sb.pack(side="right", fill="y")
        self.cf_list.configure(yscrollcommand=sb.set)

        bottom = ttk.Frame(f)
        bottom.pack(fill="x", padx=8, pady=4)
        ttk.Button(bottom, text="下载到当前实例(含依赖)",
                   command=self._cf_download).pack(side="left", padx=4)
        ttk.Button(bottom, text="导入 CF zip 整合包",
                   command=self._import_cf_pack).pack(side="left", padx=4)
        self.cf_status = ttk.Label(f, text="")
        self.cf_status.pack(fill="x", padx=8, pady=2)

    def _apply_cf_tab(self):
        """
        密钥非空 -> 显示 CurseForge 页; 为空 -> 隐藏。
        密钥为空时程序不报错、不崩溃, 仅展示 Modrinth 页。
        注意: nb.hide() 后 tabs() 仍包含该 tab, 须用 state 判断。
        """
        try:
            cur = self.nb.tab(self.tab_curseforge, "state")
        except Exception:
            cur = None  # 尚未 add 过
        try:
            if curseforge.has_key():
                if cur != "normal":
                    self.nb.add(self.tab_curseforge, text=" CurseForge ")
            else:
                if cur == "normal":
                    self.nb.hide(self.tab_curseforge)
        except Exception:
            pass

    # ---------------- 资源管理页(资源包/数据包/光影包) ----------------
    # 资源类型配置: ptype=Modrinth project_type, folder=实例内文件夹
    RES_TYPE_CFG = {
        "resourcepack": ("resourcepacks", "资源包"),
        "datapack": ("datapacks", "数据包"),
        "shader": ("shaderpacks", "光影包"),
    }

    def _build_resource_tab(self, tab, ptype, folder):
        """
        构建一个资源管理页(资源包/数据包/光影包)。
        上半部: Modrinth 搜索与下载; 下半部: 实例本地文件管理。
        所有控件用 setattr 按 ptype 命名, 便于统一逻辑复用。
        """
        # 初始化结果缓存
        setattr(self, "res_results_" + ptype, [])

        top = ttk.Frame(tab)
        top.pack(fill="x", padx=8, pady=4)
        ttk.Label(top, text="当前实例:").pack(side="left")
        cb = ttk.Combobox(top, state="readonly", width=12, values=[])
        cb.pack(side="left", padx=4)
        setattr(self, "res_inst_" + ptype, cb)

        ttk.Label(top, text="搜索:").pack(side="left", padx=(10, 2))
        q = ttk.Entry(top, width=18)
        q.pack(side="left", padx=2)
        q.bind("<Return>", lambda e, p=ptype: self._res_search(p))
        setattr(self, "res_query_" + ptype, q)

        ttk.Label(top, text="版本:").pack(side="left", padx=(6, 2))
        gv = ttk.Combobox(top, width=9, values=["1.21.4", "1.21.1", "1.20.4",
                                                "1.20.1", "1.19.4", "1.18.2",
                                                "1.17.1", "1.16.5"])
        gv.current(0)
        gv.pack(side="left")
        setattr(self, "res_gv_" + ptype, gv)

        ttk.Label(top, text="加载器:").pack(side="left", padx=(6, 2))
        ld = ttk.Combobox(top, state="disabled", width=8,
                          values=["任意(资源包通用)", "fabric", "forge",
                                  "quilt", "neoforge"])
        ld.current(0)
        ld.pack(side="left")
        setattr(self, "res_loader_" + ptype, ld)

        ttk.Button(top, text="搜索",
                   command=lambda p=ptype: self._res_search(p)).pack(
            side="left", padx=6)

        # 上下分割: 上=搜索结果, 下=本地文件
        paned = ttk.PanedWindow(tab, orient="vertical")
        paned.pack(fill="both", expand=True, padx=8, pady=2)

        up = ttk.LabelFrame(paned, text="Modrinth 搜索结果")
        list1 = tk.Listbox(up)
        list1.pack(side="left", fill="both", expand=True)
        sb1 = ttk.Scrollbar(up, command=list1.yview)
        sb1.pack(side="right", fill="y")
        list1.configure(yscrollcommand=sb1.set)
        setattr(self, "res_list_" + ptype, list1)
        paned.add(up, weight=2)

        lo = ttk.LabelFrame(paned, text="本地文件(实例/" + folder + ")")
        list2 = tk.Listbox(lo)
        list2.pack(side="left", fill="both", expand=True)
        sb2 = ttk.Scrollbar(lo, command=list2.yview)
        sb2.pack(side="right", fill="y")
        list2.configure(yscrollcommand=sb2.set)
        setattr(self, "res_local_" + ptype, list2)
        paned.add(lo, weight=1)

        bottom = ttk.Frame(tab)
        bottom.pack(fill="x", padx=8, pady=4)
        ttk.Button(bottom, text="下载到当前实例",
                   command=lambda p=ptype: self._res_download(p)).pack(
            side="left", padx=4)
        ttk.Button(bottom, text="导入本地文件",
                   command=lambda p=ptype, f=folder: self._res_import(p, f)
                   ).pack(side="left", padx=4)
        ttk.Button(bottom, text="删除选中",
                   command=lambda p=ptype, f=folder: self._res_delete(p, f)
                   ).pack(side="left", padx=4)
        ttk.Button(bottom, text="刷新",
                   command=lambda p=ptype, f=folder: self._res_refresh(p, f)
                   ).pack(side="left", padx=4)
        ttk.Button(bottom, text="打开文件夹",
                   command=lambda f=folder: self._open_sub(f)).pack(
            side="left", padx=4)
        st = ttk.Label(tab, text="")
        st.pack(fill="x", padx=8, pady=2)
        setattr(self, "res_status_" + ptype, st)

    # ---- 资源页行为 ----
    def _res_search(self, ptype):
        """Modrinth 按类型搜索(子线程)"""
        query = getattr(self, "res_query_" + ptype).get().strip()
        gv = getattr(self, "res_gv_" + ptype).get().strip() or None
        # 资源包/数据包/光影不依赖加载器, 强制忽略加载器筛选, 避免过滤掉结果
        loader = None
        # 成就: 搜索Xray相关
        if "xray" in query.lower() or "x-ray" in query.lower():
            self._unlock_achievement("xray_hunter")
        getattr(self, "res_status_" + ptype).config(text="搜索中...")

        def _worker():
            try:
                hits = modrinth.search_projects(
                    query, game_version=gv, loader=loader,
                    project_type=ptype, limit=30)
                setattr(self, "res_results_" + ptype, hits)
                self._post("res_list", (ptype, hits))
                if not hits:
                    # Modrinth 未找到: 提示并打开浏览器搜索
                    msg = "Modrinth 未找到, 可点'导入本地文件'手动导入"
                    self._post("res_status", (ptype, msg))
                    url = ("https://www.curseforge.com/minecraft/"
                           "search?search={}").format(query)
                    webbrowser.open(url)
            except Exception as exc:
                self._post("res_status", (ptype, "搜索失败: " + str(exc)))
        self._thread(_worker)

    def _res_download(self, ptype):
        """下载选中资源到实例对应文件夹(子线程)"""
        lst = getattr(self, "res_list_" + ptype)
        sel = lst.curselection()
        results = getattr(self, "res_results_" + ptype)
        if not sel or sel[0] >= len(results):
            messagebox.showwarning("提示", "请先在搜索结果中选择")
            return
        hit = results[sel[0]]
        pid = hit.get("project_id") or hit.get("slug")
        name = getattr(self, "res_inst_" + ptype).get()
        if not name:
            messagebox.showwarning("提示", "请先选择实例")
            return
        folder = self.RES_TYPE_CFG[ptype][0]
        dest = instance_mod.instance_subdir(name, folder)
        # 资源包/数据包/光影: 用当前实例的真实 MC 版本筛选;
        # 加载器一律不限(这类资源不依赖 Fabric/Forge 等加载器)
        try:
            inst = instance_mod.get_instance(name)
            mc, _ld = self._instance_meta(inst)
        except Exception:
            mc = getattr(self, "res_gv_" + ptype).get().strip() or "1.20.1"
        loader = None  # 资源类不按加载器过滤
        getattr(self, "res_status_" + ptype).config(
            text="下载 {} (匹配 {} 版本)".format(hit.get("title", pid), mc))

        def _worker():
            try:
                # 获取版本列表
                versions = modrinth.get_versions(pid, game_version=mc, loader=loader)
                if not versions:
                    versions = modrinth.get_versions(pid)
                if not versions:
                    raise ValueError("没有可用版本")
                # 在主线程弹出版本选择对话框
                selected = [None]
                def _show_dialog():
                    dlg = tk.Toplevel(self.root)
                    dlg.title("选择版本 - " + hit.get("title", pid))
                    dlg.geometry("650x500")
                    dlg.transient(self.root)
                    dlg.grab_set()
                    tk.Label(dlg, text="选择要下载的版本 (当前实例 MC 版本: {}):".format(mc),
                             anchor="w").pack(fill="x", padx=10, pady=5)
                    frame = tk.Frame(dlg)
                    frame.pack(fill="both", expand=True, padx=10, pady=5)
                    scrollbar = tk.Scrollbar(frame)
                    scrollbar.pack(side="right", fill="y")
                    listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set,
                                          font=("Consolas", 10), selectmode="single")
                    listbox.pack(side="left", fill="both", expand=True)
                    scrollbar.config(command=listbox.yview)
                    for i, ver in enumerate(versions):
                        vname = ver.get("name", "")
                        vnum = ver.get("version_number", "")
                        gvs = ", ".join(ver.get("game_versions", [])[:4])
                        ftype = ver.get("version_type", "")
                        line = "{}. {} | {} | {} | {}".format(
                            i+1, vnum, vname[:50], gvs, ftype)
                        listbox.insert("end", line)
                    listbox.selection_set(0)
                    listbox.see(0)
                    def _ok():
                        sel_idx = listbox.curselection()
                        if sel_idx:
                            selected[0] = versions[sel_idx[0]]
                        dlg.destroy()
                    def _cancel():
                        dlg.destroy()
                    btn_frame = tk.Frame(dlg)
                    btn_frame.pack(fill="x", padx=10, pady=10)
                    tk.Button(btn_frame, text="下载选中版本", width=15,
                              command=_ok).pack(side="left", padx=5)
                    tk.Button(btn_frame, text="取消", width=10,
                              command=_cancel).pack(side="left", padx=5)
                    dlg.wait_window()
                self.root.after(0, _show_dialog)
                # 等待用户选择
                import time as _time
                waited = 0
                while selected[0] is None and waited < 300:
                    _time.sleep(0.1)
                    waited += 0.1
                if selected[0] is None:
                    self._post("res_status", (ptype, "已取消下载"))
                    return
                ver = selected[0]
                version_id = ver.get("id")
                ver_name = ver.get("name", "") or ver.get("version_number", "")
                self._post("res_status", (ptype, "下载版本: " + ver_name))
                # 先获取版本的文件信息, 创建正确的下载任务
                try:
                    ver_detail = modrinth._get("/version/" + version_id)
                    file_data = modrinth._pick_file(ver_detail)
                    if file_data:
                        fname = file_data.get("filename", "download.zip")
                        furl = file_data.get("url", "")
                        fhashes = file_data.get("hashes", {})
                        dest_path = str(Path(dest) / fname)
                        # 创建下载任务(支持断点续传)
                        task = self.dl_mgr.add_task(
                            url=furl, dest_path=dest_path,
                            item_name=hit.get("title", pid),
                            source="modrinth_" + ptype,
                            expected_sha1=fhashes.get("sha1", ""))
                        # 如果目标文件已存在, 记录已下载大小
                        try:
                            p = Path(dest_path)
                            if p.exists():
                                task.downloaded_size = p.stat().st_size
                                self.dl_mgr._save()
                        except Exception:
                            pass
                    else:
                        task = None
                except Exception:
                    task = None
                # 下载选中版本(资源类不需要依赖)
                fn = modrinth.download_specific_to(version_id, dest, task=task)
                self._post("res_status", (ptype, "已下载: " + fn))
                self._post("res_refresh", (ptype, folder))
            except ValueError as exc:
                self._post("res_status",
                           (ptype, "未下载(版本不匹配): " + str(exc)))
                self._post("err", ("资源版本不匹配",
                                   "{} (当前实例版本: {})".format(exc, mc)))
            except Exception as exc:
                self._post("res_status", (ptype, "下载失败: " + str(exc)))
                self._post("err", ("下载失败", str(exc)))
        self._thread(_worker)

    def _res_refresh(self, ptype, folder):
        """刷新本地文件列表"""
        name = getattr(self, "res_inst_" + ptype).get()
        if not name:
            return
        d = instance_mod.instance_subdir(name, folder)
        try:
            files = sorted(p.name for p in Path(d).iterdir() if p.is_file())
        except Exception:
            files = []
        self._post("res_local", (ptype, files))

    def _res_import(self, ptype, folder):
        """导入本地文件到实例对应文件夹"""
        name = getattr(self, "res_inst_" + ptype).get()
        if not name:
            messagebox.showwarning("提示", "请先选择实例")
            return
        path = filedialog.askopenfilename(
            title="导入文件", filetypes=[("支持文件", "*.zip *.jar")])
        if not path:
            return
        dest = instance_mod.instance_subdir(name, folder)
        try:
            shutil.copy2(path, Path(dest) / Path(path).name)
            self._res_refresh(ptype, folder)
        except Exception as exc:
            messagebox.showerror("错误", str(exc))

    def _res_delete(self, ptype, folder):
        """删除本地列表选中文件"""
        name = getattr(self, "res_inst_" + ptype).get()
        lst = getattr(self, "res_local_" + ptype)
        sel = lst.curselection()
        if not name or not sel:
            return
        d = instance_mod.instance_subdir(name, folder)
        try:
            files = sorted(p for p in Path(d).iterdir() if p.is_file())
        except Exception:
            files = []
        if sel[0] >= len(files):
            return
        f = files[sel[0]]
        if messagebox.askyesno("删除", "确认删除 {}?".format(f.name)):
            try:
                f.unlink()
                self._res_refresh(ptype, folder)
            except Exception as exc:
                messagebox.showerror("错误", str(exc))

    # ---------------- 整合包管理页 ----------------
    def _build_packs_tab(self):
        f = self.tab_packs
        top = ttk.Frame(f)
        top.pack(fill="x", padx=8, pady=4)
        ttk.Label(top, text="搜索整合包(Modrinth):").pack(side="left")
        self.pk_query = ttk.Entry(top, width=20)
        self.pk_query.pack(side="left", padx=4)
        self.pk_query.bind("<Return>", lambda e: self._pk_search())
        ttk.Label(top, text="版本:").pack(side="left", padx=(6, 2))
        self.pk_gv = ttk.Combobox(top, width=9, values=["1.21.4", "1.21.1",
                                                        "1.20.4", "1.20.1",
                                                        "1.19.4", "1.18.2",
                                                        "1.17.1", "1.16.5"])
        self.pk_gv.current(0)
        self.pk_gv.pack(side="left")
        ttk.Button(top, text="搜索", command=self._pk_search).pack(
            side="left", padx=6)
        ttk.Button(top, text="下载并导入选中",
                   command=self._pk_download_import).pack(side="left", padx=6)

        mid = ttk.Frame(f)
        mid.pack(fill="both", expand=True, padx=8, pady=2)
        self.pk_list = tk.Listbox(mid)
        self.pk_list.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(mid, command=self.pk_list.yview)
        sb.pack(side="right", fill="y")
        self.pk_list.configure(yscrollcommand=sb.set)

        bottom = ttk.Frame(f)
        bottom.pack(fill="x", padx=8, pady=4)
        ttk.Button(bottom, text="导入本地整合包(mrpack/zip)",
                   command=self._pk_import_local).pack(side="left", padx=4)
        ttk.Button(bottom, text="导出当前实例为mrpack",
                   command=self._pk_export).pack(side="left", padx=4)
        self.pk_status = ttk.Label(f, text="")
        self.pk_status.pack(fill="x", padx=8, pady=2)

    # ---------------- 高速下载器页 ----------------
    def _build_downloader_tab(self):
        f = self.tab_downloader
        self._dl_running = False
        self._dl_obj = None
        self._dl_start_time = 0
        self._dl_last_bytes = 0

        # 链接输入
        url_box = ttk.LabelFrame(f, text=" 下载链接 ", padding=8)
        url_box.pack(fill="x", padx=8, pady=6)
        self.dl_url = ttk.Entry(url_box)
        self.dl_url.pack(fill="x")
        self.dl_url.bind("<Control-v>", lambda e: self.root.after(100, self._dl_guess_name))

        # 设置
        set_box = ttk.LabelFrame(f, text=" 下载设置 ", padding=8)
        set_box.pack(fill="x", padx=8, pady=4)
        row = ttk.Frame(set_box)
        row.pack(fill="x")
        ttk.Label(row, text="保存位置:").pack(side="left")
        self.dl_save_dir = ttk.Entry(row, width=50)
        self.dl_save_dir.pack(side="left", padx=4)
        self.dl_save_dir.insert(0, os.path.join(os.path.expanduser("~"), "Downloads"))
        ttk.Button(row, text="浏览...", command=self._dl_browse).pack(side="left", padx=3)

        row2 = ttk.Frame(set_box)
        row2.pack(fill="x", pady=(6, 0))
        ttk.Label(row2, text="线程数:").pack(side="left")
        self.dl_threads = ttk.Spinbox(row2, from_=1, to=50, width=6,
            textvariable=tk.IntVar(value=CONFIG.get("download_threads", 10)))
        self.dl_threads.pack(side="left", padx=4)
        ttk.Label(row2, text="(1~50, 多线程分块下载)", foreground="#888").pack(side="left")

        # 按钮
        btn_row = ttk.Frame(f)
        btn_row.pack(fill="x", padx=8, pady=4)
        self.dl_start_btn = ttk.Button(btn_row, text="开始下载", command=self._dl_start)
        self.dl_start_btn.pack(side="left", padx=4)
        self.dl_stop_btn = ttk.Button(btn_row, text="停止下载", command=self._dl_stop, state="disabled")
        self.dl_stop_btn.pack(side="left", padx=4)
        self.dl_open_btn = ttk.Button(btn_row, text="打开下载目录", command=self._dl_open_dir)
        self.dl_open_btn.pack(side="left", padx=4)

        # 进度
        prog_box = ttk.LabelFrame(f, text=" 下载进度 ", padding=8)
        prog_box.pack(fill="x", padx=8, pady=4)
        self.dl_progress_var = tk.DoubleVar(value=0)
        self.dl_progress = ttk.Progressbar(prog_box, variable=self.dl_progress_var, maximum=100)
        self.dl_progress.pack(fill="x", pady=(0, 4))
        self.dl_info = ttk.Label(prog_box, text="等待下载...", font=("Consolas", 9))
        self.dl_info.pack(anchor="w")

        # 日志
        log_box = ttk.LabelFrame(f, text=" 下载日志 ", padding=4)
        log_box.pack(fill="both", expand=True, padx=8, pady=4)
        self.dl_log = tk.Text(log_box, height=8, font=("Consolas", 9), wrap="word", state="disabled")
        self.dl_log.pack(fill="both", expand=True)

    def _dl_browse(self):
        d = filedialog.askdirectory(title="选择保存目录", initialdir=self.dl_save_dir.get())
        if d:
            self.dl_save_dir.delete(0, "end")
            self.dl_save_dir.insert(0, d)

    def _dl_open_dir(self):
        d = self.dl_save_dir.get().strip()
        if os.path.isdir(d):
            os.startfile(d)
        else:
            messagebox.showwarning("提示", "目录不存在")

    def _dl_guess_name(self):
        pass

    def _dl_log_msg(self, msg):
        ts = time.strftime("%H:%M:%S")
        line = "[{}] {}\n".format(ts, msg)
        self.dl_log.config(state="normal")
        self.dl_log.insert("end", line)
        self.dl_log.see("end")
        self.dl_log.config(state="disabled")

    def _dl_start(self):
        url = self.dl_url.get().strip()
        if not url:
            messagebox.showwarning("提示", "请先粘贴下载链接")
            return
        save_dir = self.dl_save_dir.get().strip()
        if not save_dir:
            messagebox.showwarning("提示", "请选择保存位置")
            return
        os.makedirs(save_dir, exist_ok=True)
        # 从 URL 推断文件名
        from urllib.parse import urlparse, unquote
        path = urlparse(url).path
        filename = os.path.basename(unquote(path)) or "downloaded_file"
        dest = os.path.join(save_dir, filename)

        try:
            threads = int(self.dl_threads.get())
        except Exception:
            threads = 10
        threads = max(1, min(50, threads))

        self._dl_running = True
        self.dl_start_btn.config(state="disabled")
        self.dl_stop_btn.config(state="normal")
        self.dl_progress_var.set(0)
        self.dl_info.config(text="正在连接服务器...")
        self._dl_log_msg("开始下载: " + url)
        self._dl_log_msg("保存到: " + dest)
        self._dl_log_msg("线程数: {}".format(threads))

        def _worker():
            try:
                from downloader import FastDownloader
                self._dl_obj = FastDownloader(url, dest, thread_count=threads)
                self._dl_start_time = time.time()
                self._dl_last_bytes = 0
                # 启动进度监控
                self.root.after(200, self._dl_monitor)
                ok = self._dl_obj.download()
                if ok:
                    self._dl_log_msg("下载完成: " + dest)
                    self.dl_info.config(text="下载完成!")
                    self.dl_progress_var.set(100)
                else:
                    if self._dl_obj._stop.is_set():
                        self._dl_log_msg("下载已停止")
                        self.dl_info.config(text="已停止")
                    else:
                        self._dl_log_msg("下载失败")
                        self.dl_info.config(text="下载失败")
            except Exception as e:
                self._dl_log_msg("错误: " + str(e))
                self.dl_info.config(text="错误: " + str(e))
            finally:
                self._dl_running = False
                self._dl_obj = None
                self.dl_start_btn.config(state="normal")
                self.dl_stop_btn.config(state="disabled")

        self._thread(_worker)

    def _dl_stop(self):
        if self._dl_obj:
            self._dl_obj.stop()
            self._dl_log_msg("正在停止...")

    def _dl_monitor(self):
        if not self._dl_running or not self._dl_obj:
            return
        downloaded, total = self._dl_obj.get_progress()
        if total > 0:
            pct = downloaded / total * 100
            self.dl_progress_var.set(pct)
            elapsed = time.time() - self._dl_start_time
            speed = (downloaded - self._dl_last_bytes) / 0.2 if elapsed > 0 else 0
            self._dl_last_bytes = downloaded
            # 格式化
            def fmt(b):
                if b < 1024: return "{} B".format(int(b))
                if b < 1024**2: return "{:.1f} KB".format(b/1024)
                return "{:.2f} MB".format(b/1024**2)
            def fmt_spd(bps):
                if bps < 1024: return "{} B/s".format(int(bps))
                if bps < 1024**2: return "{:.1f} KB/s".format(bps/1024)
                return "{:.2f} MB/s".format(bps/1024**2)
            self.dl_info.config(text="{} / {}  ({:.1f}%)  速度: {}".format(
                fmt(downloaded), fmt(total), pct, fmt_spd(speed)))
        self.root.after(200, self._dl_monitor)

    def _pk_search(self):
        """搜索 Modrinth 整合包(子线程)"""
        query = self.pk_query.get().strip()
        gv = self.pk_gv.get().strip() or None
        self.pk_status.config(text="搜索中...")

        def _worker():
            try:
                hits = modrinth.search_projects(
                    query, game_version=gv, project_type="modpack", limit=30)
                self.pk_results = hits
                self._post("pk_list_update", hits)
            except Exception as exc:
                self._post("pk_status", "搜索失败: " + str(exc))
        self._thread(_worker)

    def _pk_download_import(self):
        """下载选中的 Modrinth 整合包并自动导入(子线程)"""
        sel = self.pk_list.curselection()
        if not sel or sel[0] >= len(self.pk_results):
            messagebox.showwarning("提示", "请先选择整合包")
            return
        hit = self.pk_results[sel[0]]
        pid = hit.get("project_id") or hit.get("slug")
        gv = self.pk_gv.get().strip() or "1.20.1"
        self.pk_status.config(text="下载整合包...")

        def _worker():
            try:
                # 获取版本列表
                versions = modrinth.get_versions(pid, game_version=gv, loader=None)
                if not versions:
                    versions = modrinth.get_versions(pid)
                if not versions:
                    raise ValueError("没有可用版本")
                # 版本选择对话框
                selected = [None]
                def _show_dialog():
                    dlg = tk.Toplevel(self.root)
                    dlg.title("选择整合包版本 - " + hit.get("title", pid))
                    dlg.geometry("650x500")
                    dlg.transient(self.root)
                    dlg.grab_set()
                    tk.Label(dlg, text="选择要下载的整合包版本 (MC 版本: {}):".format(gv),
                             anchor="w").pack(fill="x", padx=10, pady=5)
                    frame = tk.Frame(dlg)
                    frame.pack(fill="both", expand=True, padx=10, pady=5)
                    scrollbar = tk.Scrollbar(frame)
                    scrollbar.pack(side="right", fill="y")
                    listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set,
                                          font=("Consolas", 10), selectmode="single")
                    listbox.pack(side="left", fill="both", expand=True)
                    scrollbar.config(command=listbox.yview)
                    for i, ver in enumerate(versions):
                        vname = ver.get("name", "")
                        vnum = ver.get("version_number", "")
                        gvs = ", ".join(ver.get("game_versions", [])[:4])
                        ftype = ver.get("version_type", "")
                        line = "{}. {} | {} | {} | {}".format(
                            i+1, vnum, vname[:50], gvs, ftype)
                        listbox.insert("end", line)
                    listbox.selection_set(0)
                    listbox.see(0)
                    def _ok():
                        sel_idx = listbox.curselection()
                        if sel_idx:
                            selected[0] = versions[sel_idx[0]]
                        dlg.destroy()
                    def _cancel():
                        dlg.destroy()
                    btn_frame = tk.Frame(dlg)
                    btn_frame.pack(fill="x", padx=10, pady=10)
                    tk.Button(btn_frame, text="下载并导入", width=15,
                              command=_ok).pack(side="left", padx=5)
                    tk.Button(btn_frame, text="取消", width=10,
                              command=_cancel).pack(side="left", padx=5)
                    dlg.wait_window()
                self.root.after(0, _show_dialog)
                import time as _time
                waited = 0
                while selected[0] is None and waited < 300:
                    _time.sleep(0.1)
                    waited += 0.1
                if selected[0] is None:
                    self._post("pk_status", "已取消下载")
                    return
                ver = selected[0]
                version_id = ver.get("id")
                ver_name = ver.get("name", "") or ver.get("version_number", "")
                self._post("pk_status", "下载整合包版本: " + ver_name)
                tmp = Path(tempfile.mkdtemp(prefix="voxel_pack_"))
                fn = modrinth.download_specific_to(version_id, tmp)
                inst = modrinth.import_mrpack(
                    tmp / fn, None,
                    progress_cb=lambda msg, c, t: self._post("pk_status", msg))
                self._post("inst_reload", None)
                self._post("pk_status", "整合包导入完成: " + inst)
            except Exception as exc:
                self._post("pk_status", "导入失败: " + str(exc))
                self._post("err", ("整合包导入失败", str(exc)))
        self._thread(_worker)

    def _pk_import_local(self):
        """导入本地整合包: 自动识别 mrpack / CurseForge zip(子线程)"""
        path = filedialog.askopenfilename(
            title="选择整合包",
            filetypes=[("整合包", "*.mrpack *.zip")])
        if not path:
            return
        self.pk_status.config(text="正在导入整合包...")

        def _worker():
            try:
                inst = self._import_pack_auto(path)
                self._post("inst_reload", None)
                self._post("pk_status", "整合包导入完成: " + inst)
            except Exception as exc:
                self._post("pk_status", "导入失败: " + str(exc))
                self._post("err", ("整合包导入失败", str(exc)))
        self._thread(_worker)

    def _import_pack_auto(self, path, progress_cb=None):
        """
        根据包内文件识别整合包类型并导入:
        - 含 modrinth.index.json -> Modrinth mrpack
        - 含 manifest.json      -> CurseForge zip 整合包
        """
        if progress_cb is None:
            progress_cb = lambda msg, c, t: self._post("pk_status", msg)
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
        if "modrinth.index.json" in names:
            return modrinth.import_mrpack(path, None, progress_cb=progress_cb)
        if "manifest.json" in names:
            return curseforge.import_modpack(path, None,
                                             progress_cb=progress_cb)
        raise ValueError("无法识别的整合包格式(需要 mrpack 或 CurseForge zip)")

    def _pk_export(self):
        """把当前实例导出为标准 mrpack(子线程)"""
        name = self.inst_combo.get()
        if not name:
            messagebox.showwarning("提示", "请先在启动页选择实例")
            return
        path = filedialog.asksaveasfilename(
            title="导出为 mrpack", defaultextension=".mrpack",
            initialfile=name + ".mrpack",
            filetypes=[("mrpack", "*.mrpack")])
        if not path:
            return
        self.pk_status.config(text="导出中(需联网反查 Modrinth)...")

        def _worker():
            try:
                modrinth.export_instance_mrpack(
                    name, path,
                    progress_cb=lambda msg, c, t: self._post("pk_status", msg))
                self._post("pk_status", "导出完成: " + path)
            except Exception as exc:
                self._post("pk_status", "导出失败: " + str(exc))
                self._post("err", ("导出失败", str(exc)))
        self._thread(_worker)

    # ---------------- 实例设置页 ----------------
    def _build_instance_tab(self):
        f = self.tab_instance
        top = ttk.Frame(f)
        top.pack(fill="x", padx=8, pady=4)
        ttk.Label(top, text="当前实例:").pack(side="left")
        self.inst_tab_label = ttk.Label(top, text="(未选择)")
        self.inst_tab_label.pack(side="left", padx=4)
        ttk.Button(top, text="打开mods", command=lambda: self._open_sub("mods"))\
            .pack(side="left", padx=3)
        ttk.Button(top, text="打开saves",
                   command=lambda: self._open_sub("saves")).pack(side="left",
                                                                 padx=3)
        ttk.Button(top, text="打开资源包",
                   command=lambda: self._open_sub("resourcepacks")).pack(
            side="left", padx=3)
        ttk.Button(top, text="打开光影包",
                   command=lambda: self._open_sub("shaderpacks")).pack(
            side="left", padx=3)
        ttk.Button(top, text="复制实例", command=self._copy_inst).pack(
            side="left", padx=3)
        ttk.Button(top, text="重命名", command=self._rename_inst).pack(
            side="left", padx=3)
        ttk.Button(top, text="删除实例", command=self._delete_inst).pack(
            side="left", padx=3)

        # Mod 管理(图标 + 依赖检测, Canvas 滚动卡片)
        mbox = ttk.LabelFrame(f, text="Mod 管理(当前实例 mods)")
        mbox.pack(fill="both", expand=True, padx=8, pady=4)
        mbar = ttk.Frame(mbox)
        mbar.pack(fill="x", padx=4, pady=2)
        self.mod_status = ttk.Label(mbar, text="")
        self.mod_status.pack(side="left")
        ttk.Button(mbar, text="导入mod...", command=self._mod_import).pack(
            side="right", padx=2)
        ttk.Button(mbar, text="从下载文件夹导入",
                   command=self._mod_import_downloads).pack(
            side="right", padx=2)
        ttk.Button(mbar, text="刷新", command=self._reload_mods).pack(
            side="right", padx=2)

        # 滚动容器: Canvas + 内部 Frame
        self.mod_canvas = tk.Canvas(mbox, highlightthickness=0, bg="#ffffff")
        self.mod_scroll = ttk.Scrollbar(mbox, orient="vertical",
                                        command=self.mod_canvas.yview)
        self.mod_canvas.configure(yscrollcommand=self.mod_scroll.set)
        self.mod_scroll.pack(side="right", fill="y")
        self.mod_canvas.pack(side="left", fill="both", expand=True, padx=4,
                             pady=4)
        self.mod_container = ttk.Frame(self.mod_canvas)
        self._mod_window = self.mod_canvas.create_window(
            (0, 0), window=self.mod_container, anchor="nw")
        self.mod_container.bind(
            "<Configure>",
            lambda e: self.mod_canvas.configure(
                scrollregion=self.mod_canvas.bbox("all")))
        self.mod_canvas.bind(
            "<Configure>",
            lambda e: self.mod_canvas.itemconfigure(self._mod_window,
                                                    width=e.width))
        # 滚轮: 鼠标进入 mod 区域才接管
        self.mod_container.bind(
            "<Enter>", lambda e: self.mod_canvas.bind_all(
                "<MouseWheel>", self._on_mod_wheel))
        self.mod_container.bind(
            "<Leave>", lambda e: self.mod_canvas.unbind_all("<MouseWheel>"))
        # PhotoImage 引用必须持有, 否则被回收图片消失
        self._mod_icons = {}
        self._placeholder_icon = None
        self._mods_cache = []

        # 实例 JVM 参数
        jbox = ttk.LabelFrame(f, text="实例 JVM 参数(覆盖全局)")
        jbox.pack(fill="x", padx=8, pady=4)
        self.inst_jvm = ttk.Entry(jbox, width=80)
        self.inst_jvm.pack(side="left", padx=6, pady=4)
        ttk.Button(jbox, text="保存", command=self._save_inst_jvm).pack(
            side="left", padx=4)

    # ---------------- 设置页 ----------------
    def _build_settings_tab(self):
        f = self.tab_settings
        box = ttk.LabelFrame(f, text="全局设置")
        box.pack(fill="x", padx=8, pady=8)

        row1 = ttk.Frame(box)
        row1.pack(fill="x", padx=6, pady=3)
        ttk.Label(row1, text="游戏根目录(.minecraft):").pack(side="left")
        self.setting_gamedir = ttk.Entry(row1, width=50)
        self.setting_gamedir.pack(side="left", padx=4)
        self.setting_gamedir.insert(0, CONFIG.get("game_dir"))
        ttk.Button(row1, text="浏览...", command=self._browse_gamedir).pack(
            side="left", padx=3)

        row2 = ttk.Frame(box)
        row2.pack(fill="x", padx=6, pady=3)
        ttk.Label(row2, text="下载源:").pack(side="left")
        self.setting_source = ttk.Combobox(
            row2, state="readonly", width=14,
            values=["mojang(官方)", "bmclapi(镜像)"])
        self.setting_source.current(
            0 if CONFIG.get("download_source") == "mojang" else 1)
        self.setting_source.pack(side="left", padx=4)

        row_threads = ttk.Frame(box)
        row_threads.pack(fill="x", padx=6, pady=3)
        ttk.Label(row_threads, text="下载线程数:").pack(side="left")
        self.setting_threads = ttk.Spinbox(
            row_threads, from_=1, to=50, width=6,
            textvariable=tk.IntVar(value=CONFIG.get("download_threads", 10)))
        self.setting_threads.pack(side="left", padx=4)
        ttk.Label(row_threads, text="(1~50, 大文件多线程分块下载, 支持断点续传)",
                  foreground="#888").pack(side="left")

        row_bg = ttk.Frame(box)
        row_bg.pack(fill="x", padx=6, pady=3)
        ttk.Label(row_bg, text="启动页背景:").pack(side="left")
        self.setting_bg = ttk.Entry(row_bg, width=40)
        self.setting_bg.pack(side="left", padx=4)
        bg_path = CONFIG.get("background_image") or ""
        self.setting_bg.insert(0, bg_path)
        ttk.Button(row_bg, text="浏览...", command=self._browse_background).pack(
            side="left", padx=3)
        ttk.Button(row_bg, text="清除", command=self._clear_background).pack(
            side="left", padx=3)

        row_theme = ttk.Frame(box)
        row_theme.pack(fill="x", padx=6, pady=3)
        ttk.Label(row_theme, text="主题风格:").pack(side="left")
        self.theme_var = tk.StringVar(value=CONFIG.get("theme", "default"))
        theme_keys = list(themes.THEMES.keys())
        self.theme_combo = ttk.Combobox(row_theme, textvariable=self.theme_var,
                                        values=theme_keys, state="readonly", width=12)
        self.theme_combo.pack(side="left", padx=4)
        # 显示当前主题描述
        self.theme_desc_label = tk.Label(row_theme, text="", fg="#888")
        self.theme_desc_label.pack(side="left", padx=6)
        self._update_theme_desc()
        self.theme_combo.bind("<<ComboboxSelected>>", self._on_theme_selected)
        ttk.Label(row_theme, text="(选择后立即生效, 可在启动页看到效果)", foreground="#888").pack(side="left")

        row_proxy = ttk.Frame(box)
        row_proxy.pack(fill="x", padx=6, pady=3)
        ttk.Label(row_proxy, text="代理(加速器):").pack(side="left")
        self.setting_proxy = ttk.Entry(row_proxy, width=30)
        self.setting_proxy.pack(side="left", padx=4)
        self.setting_proxy.insert(0, CONFIG.get("proxy") or "")
        ttk.Label(row_proxy, text="一般留空即可(加速器自动接管), 仅当直连失败时填写", foreground="#888").pack(side="left")

        row_bridge = ttk.Frame(box)
        row_bridge.pack(fill="x", padx=6, pady=3)
        self.bridge_var = tk.BooleanVar(value=CONFIG.get("bridge_enabled", False))
        def _on_bridge_toggle():
            CONFIG.set("bridge_enabled", self.bridge_var.get())
        ttk.Checkbutton(row_bridge, text="启用游戏联动(挖到矿石实时发送到游戏背包)",
                        variable=self.bridge_var, command=_on_bridge_toggle).pack(side="left")
        ttk.Button(row_bridge, text="安装联动Mod",
                   command=self._install_bridge_mod).pack(side="left", padx=6)
        ttk.Button(row_bridge, text="测试连接",
                   command=self._test_bridge).pack(side="left", padx=2)

        row3 = ttk.Frame(box)
        row3.pack(fill="x", padx=6, pady=3)
        ttk.Label(row3, text="分辨率(宽x高):").pack(side="left")
        self.setting_res = ttk.Entry(row3, width=14)
        self.setting_res.insert(0, "{},{}".format(CONFIG.get("width"),
                                                  CONFIG.get("height")))
        self.setting_res.pack(side="left", padx=4)

        row4 = ttk.Frame(box)
        row4.pack(fill="x", padx=6, pady=3)
        ttk.Label(row4, text="全局附加JVM参数:").pack(side="left")
        self.setting_jvm = ttk.Entry(row4, width=50)
        self.setting_jvm.insert(0, CONFIG.get("extra_jvm_args", ""))
        self.setting_jvm.pack(side="left", padx=4)

        # CurseForge API 密钥(留空则隐藏 CurseForge 页, 不内置任何密钥)
        row5 = ttk.Frame(box)
        row5.pack(fill="x", padx=6, pady=3)
        ttk.Label(row5, text="CurseForge API密钥:").pack(side="left")
        self.setting_cfkey = ttk.Entry(row5, width=46, show="*")
        self.setting_cfkey.insert(0, CONFIG.get("cf_api_key", ""))
        self.setting_cfkey.pack(side="left", padx=4)
        ttk.Label(row5, text="(留空则隐藏 CurseForge 搜索页)",
                  foreground="#888").pack(side="left")

        # 微软 Client ID(可选, 默认已内置 Minecraft 官方 ID, 一般无需填写)
        row6 = ttk.Frame(box)
        row6.pack(fill="x", padx=6, pady=3)
        ttk.Label(row6, text="微软 Client ID:").pack(side="left")
        self.setting_mscid = ttk.Entry(row6, width=46)
        self.setting_mscid.insert(0, CONFIG.get("ms_client_id", ""))
        self.setting_mscid.pack(side="left", padx=4)
        ttk.Label(row6, text="(可选, 留空则用内置官方ID)",
                  foreground="#888").pack(side="left")

        # AI 对话 API 配置(用于宠物对话)
        row_ai1 = ttk.Frame(box)
        row_ai1.pack(fill="x", padx=6, pady=3)
        ttk.Label(row_ai1, text="AI 服务商:").pack(side="left")
        self.setting_ai_provider = ttk.Combobox(
            row_ai1, state="readonly", width=12,
            values=["豆包", "Deepseek", "Kimi"])
        provider_map = {"doubao": "豆包", "deepseek": "Deepseek", "kimi": "Kimi"}
        current_provider = CONFIG.get("ai_provider", "doubao")
        self.setting_ai_provider.set(provider_map.get(current_provider, "豆包"))
        self.setting_ai_provider.pack(side="left", padx=4)
        ttk.Label(row_ai1, text="(用于宠物 AI 对话)",
                  foreground="#888").pack(side="left")

        row_ai2 = ttk.Frame(box)
        row_ai2.pack(fill="x", padx=6, pady=3)
        ttk.Label(row_ai2, text="AI API Key:").pack(side="left")
        self.setting_ai_key = ttk.Entry(row_ai2, width=46, show="*")
        self.setting_ai_key.insert(0, CONFIG.get("ai_api_key", ""))
        self.setting_ai_key.pack(side="left", padx=4)
        ttk.Button(row_ai2, text="测试连接",
                   command=self._test_ai_connection).pack(side="left", padx=4)

        # 日志窗口显示开关
        row7 = ttk.Frame(box)
        row7.pack(fill="x", padx=6, pady=3)
        self.setting_show_log = tk.BooleanVar(
            value=CONFIG.get("show_log_window", "true").lower() != "false")
        ttk.Checkbutton(row7, text="显示游戏日志窗口(启动页底部)",
                        variable=self.setting_show_log).pack(side="left")

        ttk.Button(box, text="保存设置", command=self._save_settings).pack(
            anchor="w", padx=6, pady=6)
        ttk.Label(f, text="提示: 修改游戏根目录前请先关闭游戏; "
                          "实例存放在 {根目录}/instances 下",
                  foreground="#666").pack(anchor="w", padx=10)

        # 下载管理(断点续传)
        dl_frame = ttk.LabelFrame(f, text=" 下载管理(断点续传) ")
        dl_frame.pack(fill="both", expand=True, padx=8, pady=8)
        # 工具栏
        dl_toolbar = ttk.Frame(dl_frame)
        dl_toolbar.pack(fill="x", padx=6, pady=4)
        ttk.Button(dl_toolbar, text="🔄 刷新",
                   command=self._refresh_download_list).pack(side="left", padx=2)
        ttk.Button(dl_toolbar, text="▶ 全部继续",
                   command=self._resume_all_downloads).pack(side="left", padx=2)
        ttk.Button(dl_toolbar, text="⏸ 全部暂停",
                   command=self._pause_all_downloads).pack(side="left", padx=2)
        ttk.Button(dl_toolbar, text="🗑 清除已完成",
                   command=self._clear_completed_downloads).pack(side="left", padx=2)
        self.dl_status_label = ttk.Label(dl_toolbar, text="", foreground="#666")
        self.dl_status_label.pack(side="left", padx=10)
        # 下载列表
        dl_list_frame = ttk.Frame(dl_frame)
        dl_list_frame.pack(fill="both", expand=True, padx=6, pady=4)
        self.dl_listbox = tk.Listbox(dl_list_frame, font=("Consolas", 9),
                                      selectmode="single")
        self.dl_listbox.pack(side="left", fill="both", expand=True)
        dl_scroll = ttk.Scrollbar(dl_list_frame, command=self.dl_listbox.yview)
        dl_scroll.pack(side="right", fill="y")
        self.dl_listbox.configure(yscrollcommand=dl_scroll.set)
        # 操作按钮
        dl_btn_frame = ttk.Frame(dl_frame)
        dl_btn_frame.pack(fill="x", padx=6, pady=4)
        ttk.Button(dl_btn_frame, text="▶ 继续下载",
                   command=self._resume_selected_download).pack(side="left", padx=2)
        ttk.Button(dl_btn_frame, text="⏸ 暂停",
                   command=self._pause_selected_download).pack(side="left", padx=2)
        ttk.Button(dl_btn_frame, text="❌ 取消",
                   command=self._cancel_selected_download).pack(side="left", padx=2)
        ttk.Button(dl_btn_frame, text="🗑 删除任务",
                   command=self._delete_selected_download).pack(side="left", padx=2)
        ttk.Button(dl_btn_frame, text="📁 打开文件夹",
                   command=self._open_download_folder).pack(side="left", padx=2)

        # 彩蛋: 千万别点按钮(PCL2 同款搞笑功能)
        chaos_frame = ttk.Frame(f)
        chaos_frame.pack(anchor="w", padx=10, pady=(20, 4))
        ttk.Label(chaos_frame, text="⚠️ 警告: 下面这个按钮千万别点",
                  foreground="#c0392b", font=("", 10, "bold")).pack(anchor="w")
        self._chaos_btn = ttk.Button(chaos_frame, text="千万别点我",
                                      command=self._do_not_click)
        self._chaos_btn.pack(anchor="w", pady=4)

    # ============================================================
    # 队列轮询(所有跨线程 UI 更新都走这里)
    # ============================================================
    def _post(self, kind, payload=None):
        self.ui_queue.put((kind, payload))

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.ui_queue.get_nowait()
                self._handle_event(kind, payload)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def _handle_event(self, kind, payload):
        if kind == "log":
            self._log(payload)
        elif kind == "status":
            self.status_lbl.config(text=payload)
        elif kind == "vdl_status":
            self.vdl_status.config(text=payload)
        elif kind == "mr_status":
            self.mr_status.config(text=payload)
        elif kind == "msg":
            messagebox.showinfo(payload[0], payload[1])
        elif kind == "err":
            messagebox.showerror(payload[0], payload[1])
        elif kind == "ask":
            # ask: (title, message) -> 返回布尔
            self._ask_result = messagebox.askyesno(payload[0], payload[1])
        elif kind == "acct_reload":
            self._reload_accounts()
        elif kind == "inst_reload":
            self._reload_instances()
        elif kind == "mods_ready":
            # 依赖检测/开关/删除后自动刷新; None 表示需要重新扫描
            if payload is None:
                self._reload_mods()
            else:
                self._handle_mods_ready(payload)
        elif kind == "versions":
            self.manifest_versions = payload
            self._filter_versions()
        elif kind == "java_done":
            self._apply_java_list(payload)
        elif kind == "server_log":
            self._append_server_log(payload)
        elif kind == "server_reload":
            self._refresh_server_list()
        elif kind == "game_started":
            self.launch_btn.config(text="游戏运行中", state="disabled")
            self.stop_btn.config(state="normal")
            self._game_start_time = time.time()
        elif kind == "game_exited":
            self.launch_btn.config(text="启动游戏", state="normal")
            self.stop_btn.config(state="disabled")
            self.game_proc = None
            self.status_lbl.config(text="游戏已退出")
            # 崩溃检测: 游戏运行少于15秒认为是崩溃
            if hasattr(self, "_game_start_time"):
                elapsed = time.time() - self._game_start_time
                if elapsed < 15:
                    self._unlock_achievement("crash_expert")
        elif kind == "script_exported":
            # 导出启动脚本成功: 弹窗提示文件位置
            self._unlock_achievement("script_kid")
            messagebox.showinfo("导出成功",
                                "启动脚本已导出:\n{}\n\n双击该 .bat 文件即可直接启动游戏。".format(payload))
        elif kind == "achievement":
            # 成就解锁弹窗
            self._show_achievement_popup(payload)
        elif kind == "mods_reload":
            self._reload_mods()
        elif kind == "dl_btn_enable":
            self.dl_btn.config(state="normal")
        elif kind == "loader_ver_update":
            # 更新加载器版本下拉框
            if payload:
                self.loader_ver_combo['values'] = payload
                self.loader_ver_var.set(payload[0])
            else:
                self.loader_ver_combo['values'] = []
                self.loader_ver_var.set("(无可用版本)")
        elif kind == "api_ver_update":
            # 更新 API 版本下拉框
            if payload:
                self.api_ver_combo['values'] = payload
                self.api_ver_var.set(payload[0])
            else:
                self.api_ver_combo['values'] = []
                self.api_ver_var.set("(无需API)")
        elif kind == "mr_list_update":
            self._on_mr_list_update(payload)
            self._post("mr_status", "共 {} 条结果".format(len(payload)))
        elif kind == "cf_status":
            self.cf_status.config(text=payload)
        elif kind == "cf_list_update":
            self.cf_list.delete(0, "end")
            for hit in payload:
                dl = hit.get("downloads") or 0
                self.cf_list.insert(
                    "end", "{} | 下载量: {}".format(hit.get("name", "?"), dl))
            self._post("cf_status", "共 {} 条结果".format(len(payload)))
        elif kind == "cf_show_tab":
            # show/hide: 按密钥刷新页签, show 时额外切到该页
            self._apply_cf_tab()
            if payload == "show":
                try:
                    self.nb.select(self.tab_curseforge)
                except Exception:
                    pass
        elif kind == "cf_search":
            # Modrinth 兜底触发: 填入关键词 -> 切到 CurseForge 页并搜索
            self.cf_query.delete(0, "end")
            self.cf_query.insert(0, payload)
            self._apply_cf_tab()
            try:
                self.nb.select(self.tab_curseforge)
            except Exception:
                pass
            self._cf_search()
        elif kind == "res_list":
            # 资源页搜索结果更新
            ptype, hits = payload
            lst = getattr(self, "res_list_" + ptype)
            lst.delete(0, "end")
            for h in hits:
                dl = h.get("downloads") or 0
                lst.insert("end", "{} | 下载量: {}".format(
                    h.get("title", "?"), dl))
            getattr(self, "res_status_" + ptype).config(
                text="共 {} 条结果".format(len(hits)))
        elif kind == "res_status":
            ptype, text = payload
            getattr(self, "res_status_" + ptype).config(text=text)
        elif kind == "res_local":
            # 资源页本地文件列表更新
            ptype, files = payload
            lst = getattr(self, "res_local_" + ptype)
            lst.delete(0, "end")
            for fn in files:
                lst.insert("end", fn)
        elif kind == "res_refresh":
            ptype, folder = payload
            self._res_refresh(ptype, folder)
        elif kind == "pk_status":
            self.pk_status.config(text=payload)
        elif kind == "pk_list_update":
            self.pk_list.delete(0, "end")
            for h in payload:
                dl = h.get("downloads") or 0
                self.pk_list.insert("end", "{} | 下载量: {}".format(
                    h.get("title", "?"), dl))
            self.pk_status.config(text="共 {} 条结果".format(len(payload)))

    # ============================================================
    # 工具
    # ============================================================
    def _log(self, text):
        self.log_text.config(state="normal")
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _thread(self, target, *args, **kwargs):
        threading.Thread(target=target, args=args, kwargs=kwargs,
                         daemon=True).start()

    # ---------------- 账号 ----------------
    def _reload_accounts(self):
        self.accounts = accounts.list_accounts()
        names = ["[{}] {}".format(a.get("type", "?"), a.get("name", "?"))
                 for a in self.accounts]
        self.acct_combo["values"] = names
        idx = accounts.get_default_account_index()
        if self.accounts and 0 <= idx < len(self.accounts):
            self.acct_combo.current(idx)
        elif self.accounts:
            self.acct_combo.current(0)

    def _selected_account(self):
        i = self.acct_combo.current()
        if 0 <= i < len(self.accounts):
            return self.accounts[i]
        return None

    def _add_offline(self):
        name = simpledialog.askstring("离线账号", "输入玩家名:", parent=self.root)
        if name and name.strip():
            try:
                acct = accounts.add_offline_account(name)
                accounts.set_default_account(len(accounts.list_accounts()) - 1)
                self._reload_accounts()
                self._log("已添加离线账号: {}".format(acct["name"]))
            except Exception as exc:
                messagebox.showerror("错误", str(exc))

    def _ms_login(self):
        self._post("status", "微软登录中, 请按提示操作...")
        def _worker():
            try:
                acct = accounts.login_microsoft(
                    progress_cb=lambda msg: self._post("log", "[微软] " + msg))
                accounts.add_account(acct)
                accounts.set_default_account(len(accounts.list_accounts()) - 1)
                self._post("acct_reload", None)
                self._post("log", "微软登录成功: {}".format(acct["name"]))
                self._post("status", "微软登录成功")
            except Exception as exc:
                self._post("err", ("微软登录失败", str(exc)))
                self._post("status", "微软登录失败")
        self._thread(_worker)

    def _refresh_selected_acct(self):
        acct = self._selected_account()
        if not acct:
            return
        if acct.get("type") != "microsoft":
            self._log("离线账号无需刷新")
            return
        def _worker():
            try:
                fresh = accounts.refresh_microsoft(acct)
                accounts_list = accounts.list_accounts()
                for i, a in enumerate(accounts_list):
                    if (a.get("type") == "microsoft"
                            and a.get("uuid") == acct.get("uuid")):
                        accounts_list[i] = fresh
                        break
                # 通过 add_account 覆盖保存
                for a in list(accounts_list):
                    if a.get("type") == "microsoft" and a.get("uuid") == \
                            fresh.get("uuid"):
                        accounts_list.remove(a)
                accounts_list.append(fresh)
                from config import CONFIG as _C
                _C.set("accounts", accounts_list)
                self._post("acct_reload", None)
                self._post("log", "微软账号刷新成功")
            except Exception as exc:
                self._post("err", ("刷新失败", str(exc)))
        self._thread(_worker)

    def _delete_acct(self):
        i = self.acct_combo.current()
        if 0 <= i < len(self.accounts):
            accounts.remove_account(i)
            self._reload_accounts()

    # ---------------- 实例 ----------------
    def _reload_instances(self, select=None):
        self.instances = instance_mod.list_instances()
        names = [inst.get("name") for inst in self.instances]
        self.inst_combo["values"] = names
        if names:
            target = select or (self.inst_combo.get()
                                if self.inst_combo.get() in names else names[0])
            if target in names:
                self.inst_combo.set(target)
        # 同步资源管理页的实例下拉
        for ptype in ("resourcepack", "datapack", "shader"):
            cb = getattr(self, "res_inst_" + ptype, None)
            if cb is not None:
                cb["values"] = names
                if names:
                    cur = cb.get()
                    cb.set(cur if cur in names else names[0])
        # 同步工具页的实例下拉
        if hasattr(self, 'tools_inst_combo'):
            self.tools_inst_combo["values"] = names
            if names and not self.tools_inst_combo.get():
                self.tools_inst_combo.set(names[0])
        # 把各搜索页的版本/加载器筛选同步为当前实例的真实配置
        self._sync_filters_to_instance()
        self._update_inst_detail()
        self._reload_mods()
        # 成就: 创建了3个以上实例
        if len(self.instances) >= 3:
            self._unlock_achievement("explorer")

    def _instance_meta(self, inst):
        """
        解析实例对应的 (mc_version, loader)。
        从本地版本 json 沿继承链取基础 MC 版本号, 用版本 id 识别加载器。
        loader: vanilla/fabric/forge/quilt/neoforge。
        """
        try:
            mc = version_manager.get_base_game_version(inst["version_id"])
        except Exception:
            mc = inst["version_id"]
        loader = installer_mod.detect_loader_from_id(inst["version_id"])
        return mc, loader

    def _sync_filters_to_instance(self):
        """
        把主 Modrinth 页、资源页、CurseForge 页的版本/加载器下拉
        默认同步为当前实例的真实 MC 版本 + 加载器, 保证搜索/下载匹配。
        原版实例的加载器置为"任意"(mod 需要加载器, 下载时会额外提示)。
        """
        name = self.inst_combo.get()
        if not name:
            return
        try:
            inst = instance_mod.get_instance(name)
            mc, loader = self._instance_meta(inst)
        except Exception:
            return
        # 确保版本下拉 values 含实例版本
        def _ensure_version(combo):
            vals = list(combo["values"] or [])
            if mc and mc not in vals:
                vals.insert(0, mc)
                combo["values"] = vals
            if mc:
                combo.set(mc)
        loader_txt = loader if loader != "vanilla" else "任意"
        # 主 Modrinth 页
        if hasattr(self, "mr_gv"):
            _ensure_version(self.mr_gv)
        if hasattr(self, "mr_loader"):
            try:
                self.mr_loader.set(loader_txt)
            except Exception:
                pass
        # 资源页(resourcepack/datapack/shader): 加载器保持"任意"
        for ptype in ("resourcepack", "datapack", "shader"):
            gv = getattr(self, "res_gv_" + ptype, None)
            if gv is not None:
                _ensure_version(gv)
            ld = getattr(self, "res_loader_" + ptype, None)
            if ld is not None:
                try:
                    ld.set("任意")
                except Exception:
                    pass
        # CurseForge 页
        if hasattr(self, "cf_gv"):
            _ensure_version(self.cf_gv)
        if hasattr(self, "cf_loader"):
            cf_loader_txt = loader if loader != "vanilla" else "任意"
            try:
                self.cf_loader.set(cf_loader_txt)
            except Exception:
                pass

    def _update_inst_detail(self):
        name = self.inst_combo.get()
        inst = instance_mod.get_instance(name)
        self.current_instance = inst
        if inst:
            mode_tag = " [合并模式]" if inst.get("merged_mode") else " [分离模式]"
            self.inst_detail.config(
                text="版本: {}{}".format(inst.get("version_id", ""), mode_tag))
            self.inst_tab_label.config(text=name)
            # 载入实例内存与 JVM
            try:
                self.min_mem.delete(0, "end")
                self.min_mem.insert(0, str(inst.get("min_memory") or 512))
                self.max_mem.delete(0, "end")
                self.max_mem.insert(0, str(inst.get("max_memory") or 2048))
            except Exception:
                pass
            self.inst_jvm.delete(0, "end")
            self.inst_jvm.insert(0, inst.get("extra_jvm_args") or "")
        else:
            self.inst_detail.config(text="")
            self.inst_tab_label.config(text="(未选择)")

    def _new_instance(self):
        if not self.manifest_versions:
            messagebox.showwarning("提示", "请先在版本下载页刷新版本列表")
            return
        # 自定义对话框: 实例名 + 版本 + 合并模式
        dlg = tk.Toplevel(self.root)
        dlg.title("新建实例")
        dlg.geometry("380x220")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()
        result = {"name": "", "version": "", "merged": False, "ok": False}

        tk.Label(dlg, text="实例名:").pack(anchor="w", padx=20, pady=(15, 2))
        name_entry = tk.Entry(dlg, width=40)
        name_entry.pack(padx=20)

        tk.Label(dlg, text="版本ID(需已下载):").pack(anchor="w", padx=20, pady=(10, 2))
        ver_entry = tk.Entry(dlg, width=40)
        ver_entry.pack(padx=20)

        merged_var = tk.BooleanVar(value=False)
        tk.Checkbutton(dlg, text="PCL2 合并模式 (版本文件夹=游戏目录, mods/saves 都在版本目录里)",
                       variable=merged_var).pack(anchor="w", padx=20, pady=(10, 5))

        def _ok():
            result["name"] = name_entry.get().strip()
            result["version"] = ver_entry.get().strip()
            result["merged"] = merged_var.get()
            result["ok"] = True
            dlg.destroy()

        def _cancel():
            dlg.destroy()

        btn_frame = tk.Frame(dlg)
        btn_frame.pack(pady=15)
        tk.Button(btn_frame, text="确定", width=10, command=_ok).pack(side="left", padx=10)
        tk.Button(btn_frame, text="取消", width=10, command=_cancel).pack(side="left", padx=10)

        name_entry.focus_set()
        dlg.wait_window()

        if not result["ok"] or not result["name"] or not result["version"]:
            return
        try:
            instance_mod.create_instance(
                result["name"], result["version"],
                java_path=self._selected_java(),
                merged_mode=result["merged"])
            self._reload_instances(select=result["name"])
            mode_text = "合并模式" if result["merged"] else "分离模式"
            self._log("已创建实例: {} ({})".format(result["name"], mode_text))
        except Exception as exc:
            messagebox.showerror("错误", str(exc))

    def _copy_inst(self):
        name = self.inst_combo.get()
        if not name:
            return
        new = simpledialog.askstring("复制实例", "新实例名:", parent=self.root)
        if new and new.strip():
            try:
                instance_mod.copy_instance(name, new.strip())
                self._reload_instances(select=new.strip())
            except Exception as exc:
                messagebox.showerror("错误", str(exc))

    def _rename_inst(self):
        name = self.inst_combo.get()
        if not name:
            return
        new = simpledialog.askstring("重命名实例", "新名称:", initialvalue=name,
                                     parent=self.root)
        if new and new.strip():
            try:
                instance_mod.rename_instance(name, new.strip())
                self._reload_instances(select=new.strip())
            except Exception as exc:
                messagebox.showerror("错误", str(exc))

    def _delete_inst(self):
        name = self.inst_combo.get()
        if not name:
            return
        if messagebox.askyesno("删除实例",
                               "确认删除实例 '{}'? 该操作不可恢复!".format(name)):
            try:
                instance_mod.delete_instance(name)
                self._reload_instances()
            except Exception as exc:
                messagebox.showerror("错误", str(exc))

    def _open_sub(self, sub):
        name = self.inst_combo.get()
        if not name:
            messagebox.showwarning("提示", "请先选择实例")
            return
        inst = instance_mod.get_instance(name)
        if inst and inst.get("merged_mode"):
            # 合并模式: 子目录在版本文件夹里
            d = Path(instance_mod.get_instance_game_dir(inst)) / sub
        else:
            d = instance_mod.instance_subdir(name, sub)
        d.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(d))  # noqa: E402  (Windows)
        else:
            import subprocess as _sp
            _sp.Popen(["xdg-open", str(d)])

    def _save_inst_jvm(self):
        name = self.inst_combo.get()
        if not name:
            return
        instance_mod.update_instance(name,
                                     extra_jvm_args=self.inst_jvm.get())
        self._log("已保存实例 JVM 参数")

    # ---------------- Java ----------------
    def refresh_java(self):
        self._post("status", "扫描 Java 中...")
        def _worker():
            paths = java_manager.scan_java()
            # 去重
            seen = set()
            uniq = []
            for p in paths:
                s = str(p).lower()
                if s not in seen:
                    seen.add(s)
                    uniq.append(str(p))
            CONFIG.set("java_paths", uniq)
            self._post("java_done", uniq)
        self._thread(_worker)

    def _apply_java_list(self, paths):
        self.java_paths = paths
        labels = []
        for p in paths:
            major = java_manager.read_java_version(p)
            labels.append("Java{} | {}".format(major if major else "?",
                                               p))
        self.java_combo["values"] = labels
        default = CONFIG.get("default_java")
        if default and default in paths:
            self.java_combo.current(paths.index(default))
        elif labels:
            self.java_combo.current(0)
        self._post("status", "Java 扫描完成: {} 个".format(len(paths)))

    def _selected_java(self):
        i = self.java_combo.current()
        if 0 <= i < len(self.java_paths):
            return self.java_paths[i]
        return None

    def _browse_java(self):
        path = filedialog.askopenfilename(
            title="选择 java.exe / javaw.exe",
            filetypes=[("Java", "*.exe"), ("所有文件", "*.*")])
        if path:
            if path not in self.java_paths:
                self.java_paths.append(path)
                CONFIG.set("java_paths", self.java_paths)
            CONFIG.set("default_java", path)
            self.refresh_java()

    # ---------------- 版本列表 ----------------
    def refresh_version_list(self):
        self._post("status", "拉取版本列表...")
        def _worker():
            try:
                versions = version_manager.fetch_manifest()
                self._post("versions", versions)
                self._post("status", "版本列表已更新: {} 条".format(len(versions)))
            except Exception as exc:
                self._post("err", ("获取版本列表失败", str(exc)))
                self._post("status", "获取版本列表失败")
        self._thread(_worker)

    def _filter_versions(self):
        filt = self.ver_filter.get()
        self.ver_list.delete(0, "end")
        for v in self.manifest_versions:
            vtype = v.get("type", "release")
            if filt == "正式版" and vtype != "release":
                continue
            if filt == "快照" and vtype != "snapshot":
                continue
            if filt == "旧版" and vtype not in ("old_beta", "old_alpha"):
                continue
            tag = {"release": "正式", "snapshot": "快照",
                   "old_beta": "旧β", "old_alpha": "旧α"}.get(vtype, vtype)
            self.ver_list.insert("end",
                                 "{}  [{}]  {}".format(v["id"], tag,
                                                       v.get("releaseTime", "")))

    def _download_version(self):
        sel = self.ver_list.curselection()
        if not sel:
            messagebox.showwarning("提示", "请先选择要下载的版本")
            return
        idx = sel[0]
        # 从 filter 列表映射回 manifest
        filt = self.ver_filter.get()
        shown = self._shown_versions()
        if idx >= len(shown):
            return
        vid = shown[idx]["id"]
        self.dl_btn.config(state="disabled")
        self._post("vdl_status", "正在下载: " + vid)
        def _worker():
            try:
                version_manager.download_version(
                    vid, progress_cb=lambda msg, c, t: self._post(
                        "vdl_status", msg))
                self._post("vdl_status", "版本 {} 下载完成".format(vid))
                self._post("log", "版本 {} 下载完成".format(vid))
            except Exception as exc:
                self._post("vdl_status", "下载失败: {}".format(exc))
                self._post("err", ("下载失败", str(exc)))
            finally:
                self._post("dl_btn_enable", None)
        self._thread(_worker)

    def _shown_versions(self):
        filt = self.ver_filter.get()
        result = []
        for v in self.manifest_versions:
            vtype = v.get("type", "release")
            if filt == "正式版" and vtype != "release":
                continue
            if filt == "快照" and vtype != "snapshot":
                continue
            if filt == "旧版" and vtype not in ("old_beta", "old_alpha"):
                continue
            result.append(v)
        return result

    def _refresh_loader_versions(self):
        """根据选中的游戏版本和加载器类型, 动态获取可用版本列表"""
        sel = self.ver_list.curselection()
        if not sel:
            self.loader_ver_combo['values'] = []
            self.loader_ver_var.set("(先选版本)")
            self.api_ver_combo['values'] = []
            self.api_ver_var.set("(先选版本)")
            return
        shown = self._shown_versions()
        if sel[0] >= len(shown):
            return
        game_ver = shown[sel[0]]["id"]
        loader = self.loader_var.get()

        def _worker():
            try:
                import installer as installer_mod
                versions = []
                if loader == "fabric":
                    versions = installer_mod.fabric_loader_versions(game_ver)
                elif loader == "quilt":
                    versions = installer_mod.quilt_loader_versions(game_ver)
                elif loader == "forge":
                    versions = installer_mod.forge_versions(game_ver)
                elif loader == "neoforge":
                    versions = installer_mod.neoforge_versions_for(game_ver)

                # 最新版放第一个
                if versions:
                    self._post("loader_ver_update", versions)
                else:
                    self._post("loader_ver_update", [])

                # API 版本(仅 fabric/quilt)
                if loader in ("fabric", "quilt"):
                    api_slug = "fabric-api" if loader == "fabric" else "qsl"
                    api_vers = installer_mod.api_version_list(api_slug, game_ver, loader)
                    self._post("api_ver_update", api_vers)
                else:
                    self._post("api_ver_update", [])
            except Exception as exc:
                self._post("vdl_status", "获取版本列表失败: {}".format(exc))

        self._thread(_worker)

    def _install_loader(self):
        sel = self.ver_list.curselection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一个已下载的原版版本")
            return
        shown = self._shown_versions()
        if sel[0] >= len(shown):
            return
        vid = shown[sel[0]]["id"]
        loader = self.loader_var.get()

        # 自定义对话框: 实例名 + 合并模式
        dlg = tk.Toplevel(self.root)
        dlg.title("安装 " + loader)
        dlg.geometry("400x200")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()
        result = {"name": "", "merged": False, "ok": False}

        tk.Label(dlg, text="实例名:").pack(anchor="w", padx=20, pady=(15, 2))
        name_entry = tk.Entry(dlg, width=45)
        name_entry.insert(0, "{}-{}".format(vid, loader))
        name_entry.pack(padx=20)

        merged_var = tk.BooleanVar(value=False)
        tk.Checkbutton(dlg, text="PCL2 合并模式 (版本文件夹=游戏目录)",
                       variable=merged_var).pack(anchor="w", padx=20, pady=(10, 5))
        tk.Label(dlg, text="合并模式: mods/saves/config 都放在版本文件夹里, 和 PCL2 一样",
                 fg="gray", font=("Arial", 8)).pack(anchor="w", padx=20)

        def _ok():
            result["name"] = name_entry.get().strip()
            result["merged"] = merged_var.get()
            result["ok"] = True
            dlg.destroy()

        def _cancel():
            dlg.destroy()

        btn_frame = tk.Frame(dlg)
        btn_frame.pack(pady=15)
        tk.Button(btn_frame, text="确定", width=10, command=_ok).pack(side="left", padx=10)
        tk.Button(btn_frame, text="取消", width=10, command=_cancel).pack(side="left", padx=10)

        name_entry.focus_set()
        dlg.wait_window()

        if not result["ok"] or not result["name"]:
            return
        inst_name = result["name"]
        use_merged = result["merged"] and loader == "Fabric"  # 目前只支持 Fabric 合并

        self.dl_btn.config(state="disabled")
        loader_ver = self.loader_ver_var.get()
        api_ver = self.api_ver_var.get()
        if loader_ver.startswith("(") or not loader_ver.strip():
            loader_ver = None
        if api_ver.startswith("(") or not api_ver.strip():
            api_ver = None
        ver_info = loader_ver or "最新版"
        mode_text = "合并模式" if use_merged else "分离模式"
        self._post("vdl_status", "正在安装 {} {} ({}) 到 {}".format(
            loader, ver_info, mode_text, inst_name))

        def _worker():
            try:
                if use_merged:
                    # PCL2 合并模式: 直接创建合并式版本文件夹
                    version_id = installer_mod.install_fabric_merged(
                        vid, loader_version=loader_ver, api_version=api_ver,
                        progress_cb=lambda msg, c, t: self._post(
                            "vdl_status", msg))
                else:
                    version_id = installer_mod.install_loader(
                        vid, loader, loader_version=loader_ver, api_version=api_ver,
                        progress_cb=lambda msg, c, t: self._post(
                            "vdl_status", msg))
                # 创建实例
                instance_mod.create_instance(
                    inst_name.strip(), version_id,
                    java_path=self._selected_java(),
                    merged_mode=use_merged)
                self._post("inst_reload", None)
                self._post("log", "加载器安装完成: {} (实例 {}, {})".format(
                    version_id, inst_name.strip(), mode_text))
                self._post("vdl_status", "完成: " + version_id)
            except Exception as exc:
                self._post("vdl_status", "加载器安装失败: {}".format(exc))
                self._post("err", ("加载器安装失败", str(exc)))
            finally:
                self._post("dl_btn_enable", None)
        self._thread(_worker)

    # ---------------- Modrinth ----------------
    def _fmt_num(self, n):
        """格式化数字: 1234567 -> 1.23M"""
        try:
            n = int(n)
            if n >= 1000000:
                return "{:.2f}M".format(n / 1000000)
            elif n >= 1000:
                return "{:.1f}K".format(n / 1000)
            return str(n)
        except Exception:
            return str(n)

    def _on_mr_list_update(self, hits):
        """更新 Modrinth 搜索结果列表(带图标)"""
        try:
            if not hasattr(self, 'mr_tree') or self.mr_tree is None:
                return
            self.mr_tree.delete(*self.mr_tree.get_children())
            self.modrinth_results = hits
            self.mr_icon_images = {}
            import hashlib
            cache_dir = os.path.join(CONFIG.get("game_dir"), ".voxel_cache", "mr_icons")
            os.makedirs(cache_dir, exist_ok=True)
            for idx, h in enumerate(hits):
                title = h.get("title", "?")
                ptype = h.get("project_type", "mod")
                dl = self._fmt_num(h.get("downloads", 0))
                item_id = self.mr_tree.insert("", "end", text="", values=(title, ptype, dl))
                icon_url = h.get("icon_url")
                if icon_url:
                    self._thread(lambda u=icon_url, iid=item_id, i=idx:
                                 self._load_mr_icon(u, iid, i, cache_dir))
        except Exception as e:
            print("[Modrinth] 更新列表失败:", e)
            import traceback
            traceback.print_exc()
            try:
                self.mr_status.config(text="列表更新失败: " + str(e))
            except Exception:
                pass

    def _mr_on_select(self):
        """Treeview 选中事件"""
        sel = self.mr_tree.selection()
        if sel:
            idx = self.mr_tree.index(sel[0])
            self.mr_selected_idx = idx

    def _load_mr_icon(self, url, item_id, idx, cache_dir):
        """异步加载模组图标"""
        try:
            import hashlib
            cache_file = os.path.join(cache_dir, hashlib.md5(url.encode()).hexdigest() + ".png")
            if os.path.exists(cache_file):
                img = Image.open(cache_file).resize((24, 24), Image.LANCZOS)
            else:
                import requests
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    with open(cache_file, "wb") as f:
                        f.write(resp.content)
                    img = Image.open(cache_file).resize((24, 24), Image.LANCZOS)
                else:
                    return
            photo = ImageTk.PhotoImage(img)
            self.root.after(0, lambda: self._set_mr_icon(item_id, photo, idx))
        except Exception:
            pass

    def _set_mr_icon(self, item_id, photo, idx):
        """设置模组图标(主线程)"""
        try:
            if self.mr_tree.exists(item_id):
                self.mr_tree.item(item_id, image=photo)
                self.mr_icon_images[item_id] = photo
        except Exception:
            pass

    def _mr_search(self):
        query = self.mr_query.get().strip()
        gv = self.mr_gv.get().strip() or None
        loader_raw = self.mr_loader.get()
        loader = None if loader_raw == "任意" else loader_raw
        self._post("mr_status", "搜索中...")
        def _worker():
            try:
                hits = modrinth.search_projects(query, game_version=gv,
                                                loader=loader, limit=30)
                if hits:
                    self.modrinth_results = hits
                    self._post("mr_list_update", hits)
                elif curseforge.has_key():
                    # 下载策略: Modrinth 找不到 -> 用 CurseForge 兜底搜索
                    self._post("mr_status",
                               "Modrinth 未找到, 转 CurseForge 搜索")
                    self._post("cf_search", query)
                else:
                    self.modrinth_results = []
                    self._post("mr_list_update", [])
                    self._post("mr_status", "Modrinth 未找到"
                               "(可在设置页填写 CurseForge 密钥后兜底搜索)")
            except Exception as exc:
                self._post("mr_status", "搜索失败: {}".format(exc))
        self._thread(_worker)

    def _mr_download(self):
        sel = self.mr_tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择模组")
            return
        idx = self.mr_tree.index(sel[0])
        if idx >= len(self.modrinth_results):
            messagebox.showwarning("提示", "请先选择模组")
            return
        hit = self.modrinth_results[idx]
        project_id = hit.get("project_id") or hit.get("slug")
        name = self.inst_combo.get()
        if not name:
            messagebox.showwarning("提示", "请先在启动页选择实例")
            return
        # Modrinth 页面默认下载到 mods 目录
        sub_dir = "mods"
        dest_dir = instance_mod.instance_subdir(name, sub_dir)
        # 下载前验证: 以当前实例的真实 MC 版本 + 加载器为准筛选
        try:
            inst = instance_mod.get_instance(name)
            mc, loader = self._instance_meta(inst)
        except Exception:
            mc = self.mr_gv.get().strip() or "1.20.1"
            loader = "fabric"
        if loader == "vanilla":
            loader = None
        self._post("mr_status", "获取版本列表: {}".format(hit.get("title", project_id)))
        def _worker():
            try:
                # 获取所有版本(不过滤, 让用户在对话框里筛选)
                versions = modrinth.get_versions(project_id)
                if not versions:
                    raise ValueError("没有可用版本")
                # 提取所有支持的加载器和MC版本
                all_loaders = set()
                all_game_versions = set()
                for ver in versions:
                    for ld in ver.get("loaders", []):
                        all_loaders.add(ld)
                    for gv in ver.get("game_versions", []):
                        all_game_versions.add(gv)
                loader_list = sorted(all_loaders, reverse=True)
                gv_list = sorted(all_game_versions, reverse=True)
                # 在主线程弹出版本选择对话框
                selected = [None]
                def _show_dialog():
                    dlg = tk.Toplevel(self.root)
                    dlg.title("选择版本 - " + hit.get("title", project_id))
                    dlg.geometry("700x550")
                    dlg.transient(self.root)
                    dlg.grab_set()
                    tk.Label(dlg, text="当前实例: {} + {}  |  ★ = 兼容当前实例".format(
                        mc, loader or "任意"), anchor="w", fg="blue").pack(fill="x", padx=10, pady=5)
                    # 筛选器
                    filter_frame = tk.Frame(dlg)
                    filter_frame.pack(fill="x", padx=10, pady=5)
                    tk.Label(filter_frame, text="加载器:").pack(side="left")
                    loader_var = tk.StringVar(value=loader if loader in loader_list else "全部")
                    loader_combo = ttk.Combobox(filter_frame, textvariable=loader_var,
                                                values=["全部"] + loader_list, width=10, state="readonly")
                    loader_combo.pack(side="left", padx=5)
                    tk.Label(filter_frame, text="MC版本:").pack(side="left", padx=(10,0))
                    gv_var = tk.StringVar(value=mc if mc in gv_list else "全部")
                    gv_combo = ttk.Combobox(filter_frame, textvariable=gv_var,
                                            values=["全部"] + gv_list, width=10, state="readonly")
                    gv_combo.pack(side="left", padx=5)
                    # 版本列表
                    frame = tk.Frame(dlg)
                    frame.pack(fill="both", expand=True, padx=10, pady=5)
                    scrollbar = tk.Scrollbar(frame)
                    scrollbar.pack(side="right", fill="y")
                    listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set,
                                          font=("Consolas", 10), selectmode="single")
                    listbox.pack(side="left", fill="both", expand=True)
                    scrollbar.config(command=listbox.yview)
                    # 过滤后的版本列表
                    filtered = [None]
                    def _refresh_list():
                        listbox.delete(0, "end")
                        ld_filter = loader_var.get()
                        gv_filter = gv_var.get()
                        result = []
                        for ver in versions:
                            vloaders = ver.get("loaders", [])
                            vgvs = ver.get("game_versions", [])
                            if ld_filter != "全部" and ld_filter not in vloaders:
                                continue
                            if gv_filter != "全部" and gv_filter not in vgvs:
                                continue
                            result.append(ver)
                        filtered[0] = result
                        for i, ver in enumerate(result):
                            vname = ver.get("name", "")
                            vnum = ver.get("version_number", "")
                            gvs = ", ".join(ver.get("game_versions", [])[:3])
                            lds = ", ".join(ver.get("loaders", [])[:3])
                            ftype = ver.get("version_type", "")
                            # 检查是否兼容当前实例
                            compatible = (not loader or loader in vloaders) and (not mc or mc in vgvs)
                            star = "★" if compatible else " "
                            line = "{}{}. {} | {} | {} | {} | {}".format(
                                star, i+1, vnum, vname[:35], gvs, lds, ftype)
                            listbox.insert("end", line)
                        if result:
                            listbox.selection_set(0)
                            listbox.see(0)
                    loader_combo.bind("<<ComboboxSelected>>", lambda e: _refresh_list())
                    gv_combo.bind("<<ComboboxSelected>>", lambda e: _refresh_list())
                    _refresh_list()
                    def _ok():
                        sel_idx = listbox.curselection()
                        if sel_idx and filtered[0]:
                            selected[0] = filtered[0][sel_idx[0]]
                        dlg.destroy()
                    def _cancel():
                        dlg.destroy()
                    btn_frame = tk.Frame(dlg)
                    btn_frame.pack(fill="x", padx=10, pady=10)
                    tk.Button(btn_frame, text="下载选中版本", width=15,
                              command=_ok).pack(side="left", padx=5)
                    tk.Button(btn_frame, text="取消", width=10,
                              command=_cancel).pack(side="left", padx=5)
                    dlg.wait_window()
                self.root.after(0, _show_dialog)
                # 等待用户选择(轮询, 最多等300秒)
                import time as _time
                waited = 0
                while selected[0] is None and waited < 300:
                    _time.sleep(0.1)
                    waited += 0.1
                if selected[0] is None:
                    self._post("mr_status", "已取消下载")
                    return
                ver = selected[0]
                version_id = ver.get("id")
                ver_name = ver.get("name", "") or ver.get("version_number", "")
                self._post("mr_status", "下载版本: {}".format(ver_name))
                # 下载选中版本并自动补装依赖(带进度)
                dep_results = []
                def _dl_progress(msg, cur, total):
                    self._post("mr_status", msg)
                dl_results = modrinth.download_versions_with_deps(
                    version_id, mc, loader, dest_dir,
                    progress_cb=_dl_progress)
                # 统计结果
                main_mods = [r for r in dl_results if not r[1]]
                dep_mods = [r for r in dl_results if r[1]]
                result_msg = "下载完成: 主模组{}个, 依赖{}个".format(len(main_mods), len(dep_mods))
                if dep_mods:
                    dep_names = "\n".join(["  - " + r[0] for r in dep_mods])
                    result_msg += "\n已安装依赖:\n" + dep_names
                self._post("mr_status", result_msg)
                self._post("mods_reload", None)
            except ValueError as exc:
                msg = "{} (当前实例: {} + {})".format(exc, mc, loader or "任意")
                self._post("mr_status", "未下载(版本不匹配)")
                self._post("err", ("模组版本不匹配", msg))
            except Exception as exc:
                self._post("mr_status", "下载失败: {}".format(exc))
                self._post("err", ("模组下载失败", str(exc)))
        self._thread(_worker)

    def _import_mrpack(self):
        path = filedialog.askopenfilename(
            title="选择 .mrpack 整合包",
            filetypes=[("Modrinth 整合包", "*.mrpack")])
        if not path:
            return
        self._post("mr_status", "正在导入整合包...")
        def _worker():
            try:
                inst = modrinth.import_mrpack(
                    path, None,
                    progress_cb=lambda msg, c, t: self._post("mr_status", msg))
                self._post("inst_reload", None)
                self._post("mr_status", "整合包导入完成: " + inst)
            except Exception as exc:
                self._post("mr_status", "导入失败: {}".format(exc))
                self._post("err", ("整合包导入失败", str(exc)))
        self._thread(_worker)

    # ---------------- CurseForge 搜索/下载/整合包 ----------------
    def _cf_search(self):
        """CurseForge 搜索(后台线程), 异常自动降级提示"""
        # 成就: 尝试使用CurseForge但没有密钥
        cf_key = CONFIG.get("cf_api_key", "").strip()
        if not cf_key:
            self._unlock_achievement("cf_victim")
        query = self.cf_query.get().strip()
        gv = self.cf_gv.get().strip() or None
        loader_raw = self.cf_loader.get()
        loader = None if loader_raw == "任意" else loader_raw
        # 分类下拉 -> classId
        cls_map = ["mods", "resourcepacks", "modpacks", "worlds", "shaders",
                   "datapacks"]
        idx = max(0, min(self.cf_class.current(), len(cls_map) - 1))
        class_id = curseforge.CF_CLASS[cls_map[idx]]
        self._post("cf_status", "CurseForge 搜索中...")
        def _worker():
            try:
                hits = curseforge.search_mods(query, class_id=class_id,
                                              game_version=gv, loader=loader)
                self.curseforge_results = hits
                self._post("cf_list_update", hits)
            except Exception as exc:
                # 网络异常容错: 提示后自动降级到仅 Modrinth
                self._post("cf_status", "CurseForge 不可用: {}".format(exc))
                self._post("log", "CurseForge 调用失败: {}".format(exc))
                self._post("err", ("CurseForge", "CurseForge密钥无效或者网络访问受限"))
                self._post("cf_show_tab", "hide")
        self._thread(_worker)

    def _cf_download(self):
        """下载选中的 CurseForge 资源(含必需依赖)到当前实例 mods"""
        sel = self.cf_list.curselection()
        if not sel or sel[0] >= len(getattr(self, "curseforge_results", [])):
            messagebox.showwarning("提示", "请先在搜索结果中选择")
            return
        hit = self.curseforge_results[sel[0]]
        mod_id = hit["id"]
        name = self.inst_combo.get()
        if not name:
            messagebox.showwarning("提示", "请先在启动页选择实例")
            return
        mods_dir = instance_mod.instance_subdir(name, "mods")
        # 下载前验证: 以当前实例的真实 MC 版本 + 加载器筛选 CurseForge 文件
        try:
            inst = instance_mod.get_instance(name)
            mc, loader = self._instance_meta(inst)
        except Exception:
            mc = self.cf_gv.get().strip() or "1.20.1"
            loader = None
        if loader == "vanilla":
            loader = None
        self._post("cf_status", "获取下载链接({} + {})...".format(
            mc, loader or "任意"))
        def _worker():
            try:
                files = curseforge.get_mod_files(mod_id, mc, loader)
                if not files:
                    self._post("cf_status",
                               "该资源没有适用于 {} + {} 的文件".format(
                                   mc, loader or "任意"))
                    return
                # 版本选择对话框
                selected = [None]
                def _show_dialog():
                    dlg = tk.Toplevel(self.root)
                    dlg.title("选择版本 - " + hit.get("name", str(mod_id)))
                    dlg.geometry("700x500")
                    dlg.transient(self.root)
                    dlg.grab_set()
                    tk.Label(dlg, text="选择要下载的文件 (当前实例: {} + {}):".format(
                        mc, loader or "任意"), anchor="w").pack(fill="x", padx=10, pady=5)
                    frame = tk.Frame(dlg)
                    frame.pack(fill="both", expand=True, padx=10, pady=5)
                    scrollbar = tk.Scrollbar(frame)
                    scrollbar.pack(side="right", fill="y")
                    listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set,
                                          font=("Consolas", 9), selectmode="single")
                    listbox.pack(side="left", fill="both", expand=True)
                    scrollbar.config(command=listbox.yview)
                    for i, f in enumerate(files):
                        fname = f.get("fileName", "")
                        fver = f.get("gameVersions", [])
                        fver_str = ", ".join(str(v) for v in fver[:3])
                        frel = f.get("releaseType", "")
                        fdate = str(f.get("fileDate", ""))[:10]
                        line = "{}. {} | {} | {} | {}".format(
                            i+1, fname[:55], fver_str, frel, fdate)
                        listbox.insert("end", line)
                    listbox.selection_set(0)
                    listbox.see(0)
                    def _ok():
                        sel_idx = listbox.curselection()
                        if sel_idx:
                            selected[0] = files[sel_idx[0]]
                        dlg.destroy()
                    def _cancel():
                        dlg.destroy()
                    btn_frame = tk.Frame(dlg)
                    btn_frame.pack(fill="x", padx=10, pady=10)
                    tk.Button(btn_frame, text="下载选中版本", width=15,
                              command=_ok).pack(side="left", padx=5)
                    tk.Button(btn_frame, text="取消", width=10,
                              command=_cancel).pack(side="left", padx=5)
                    dlg.wait_window()
                self.root.after(0, _show_dialog)
                import time as _time
                waited = 0
                while selected[0] is None and waited < 300:
                    _time.sleep(0.1)
                    waited += 0.1
                if selected[0] is None:
                    self._post("cf_status", "已取消下载")
                    return
                f = selected[0]
                fid = f["id"]
                fname = f.get("fileName", "")
                self._post("cf_status", "下载: " + fname)
                curseforge.download_with_deps(mod_id, fid, mc, loader,
                                              mods_dir)
                self._post("cf_status", "已下载到 " + str(mods_dir))
                self._post("mods_reload", None)
            except Exception as exc:
                self._post("cf_status", "下载失败: {}".format(exc))
                self._post("log", "CurseForge 下载失败: {}".format(exc))
                self._post("err", ("CurseForge", "CurseForge密钥无效或者网络访问受限"))
                self._post("cf_show_tab", "hide")
        self._thread(_worker)

    def _import_cf_pack(self):
        """导入 CurseForge zip 整合包"""
        path = filedialog.askopenfilename(
            title="选择 CurseForge 整合包 zip",
            filetypes=[("CurseForge 整合包", "*.zip")])
        if not path:
            return
        self._post("cf_status", "正在导入 CurseForge 整合包...")
        def _worker():
            try:
                inst = curseforge.import_modpack(
                    path, None,
                    progress_cb=lambda msg, c, t: self._post("cf_status", msg))
                self._post("inst_reload", None)
                self._post("cf_status", "整合包导入完成: " + inst)
                self._post("log", "CurseForge 整合包导入完成: " + inst)
            except Exception as exc:
                self._post("cf_status", "导入失败: {}".format(exc))
                self._post("err", ("整合包导入失败", str(exc)))
        self._thread(_worker)

    # ---------------- Mod 管理(卡片列表 + 图标 + 依赖检测) ----------------
    def _current_mods_dir(self):
        name = self.inst_combo.get()
        if not name:
            return None
        return instance_mod.instance_subdir(name, "mods")

    def _on_mod_wheel(self, event):
        self.mod_canvas.yview_scroll(int(-event.delta / 120), "units")

    def _reload_mods(self):
        """后台线程解析 mods(元数据+图标+依赖), 完成后切回 UI 线程渲染"""
        self.mod_status.config(text="正在解析 mods...")
        mods_dir = self._current_mods_dir()
        if not mods_dir:
            self._post("mods_ready", None)
            return

        def _worker():
            try:
                result = mod_manager.analyze_mods(mods_dir)
                self._post("mods_ready", result)
            except Exception as exc:
                self._post("err", ("解析 mods 失败", str(exc)))
                self._post("mods_ready", [])
        self._thread(_worker)

    def _handle_mods_ready(self, mods):
        """UI 线程渲染 mod 卡片"""
        self._mods_cache = mods or []
        # 清空容器
        for w in self.mod_container.winfo_children():
            w.destroy()
        self._mod_icons.clear()
        if not self._mods_cache:
            self.mod_status.config(text="(该实例 mods 目录为空)")
            ttk.Label(self.mod_container,
                      text="(没有 mod, 可点击右上角导入)").pack(anchor="w",
                                                              padx=8, pady=8)
            return
        self.mod_status.config(text="共 {} 个 mod".format(len(self._mods_cache)))
        for m in self._mods_cache:
            self._build_mod_card(m)

    def _build_mod_card(self, m):
        """每个 mod 一个独立卡片: 图标/名称/版本/依赖状态/开关/删除"""
        card = ttk.Frame(self.mod_container, relief="groove", borderwidth=1,
                         padding=4)
        card.pack(fill="x", padx=4, pady=2)
        row1 = ttk.Frame(card)
        row1.pack(fill="x")
        row2 = ttk.Frame(card)
        row2.pack(fill="x")

        # 图标(保持引用防 GC)
        icon = self._load_mod_icon(m)
        icon_lbl = tk.Label(row1, image=icon, width=36, height=36,
                            bg="#ffffff")
        icon_lbl.image = icon  # 双重持有
        icon_lbl.pack(side="left", padx=(2, 8), pady=2)

        # 名称 + 版本
        name_txt = m["name"]
        if not m["enabled"]:
            name_txt += "  (已禁用)"
        ttl = ttk.Label(row1, text=name_txt, font=("Microsoft YaHei", 10,
                                                   "bold"))
        ttl.pack(side="left", anchor="w")
        if m["version"]:
            ttk.Label(row1, text="v" + m["version"],
                      foreground="#666666").pack(side="left", padx=8)

        # 右侧按钮
        btns = ttk.Frame(row1)
        btns.pack(side="right")
        toggle_txt = "禁用" if m["enabled"] else "启用"
        ttk.Button(btns, text=toggle_txt,
                   command=lambda f=m["filename"], e=not m["enabled"]:
                   self._mod_toggle(f, e)).pack(side="left", padx=2)
        ttk.Button(btns, text="删除",
                   command=lambda f=m["filename"]: self._mod_delete(
                       f)).pack(side="left", padx=2)

        # 依赖状态(第二行)
        if m.get("missing"):
            status = tk.Label(row2, text="❌ 缺少前置: " + ", ".join(
                m["missing"]), fg="#c0392b")
            status.pack(side="left", padx=(46, 4), pady=2)
            ttk.Button(row2, text="一键下载缺失前置",
                       command=lambda f=m["filename"], md=m["missing"]:
                       self._download_missing_deps(f, md)).pack(
                side="left", padx=4)
        elif m.get("dependencies"):
            tk.Label(row2, text="✅ 前置齐全", fg="#27ae60").pack(
                side="left", padx=(46, 4), pady=2)
        else:
            tk.Label(row2, text="无前置依赖", fg="#888888").pack(
                side="left", padx=(46, 4), pady=2)

    def _load_mod_icon(self, m):
        """把 mod 图标 bytes 转为 PhotoImage; 无图标/失败返回占位图"""
        if not HAS_PIL:
            return self._placeholder()
        if m.get("icon_bytes"):
            try:
                img = Image.open(_io.BytesIO(m["icon_bytes"]))
                img = img.convert("RGBA")
                img.thumbnail((32, 32))
                photo = ImageTk.PhotoImage(img)
                self._mod_icons[m["filename"]] = photo
                return photo
            except Exception:
                pass
        return self._placeholder()

    def _placeholder(self):
        """灰色占位图标(懒加载一次)"""
        if self._placeholder_icon is None:
            img = Image.new("RGBA", (32, 32), (150, 150, 150, 255))
            self._placeholder_icon = ImageTk.PhotoImage(img)
        return self._placeholder_icon

    def _mod_toggle(self, filename, enabled):
        mods_dir = self._current_mods_dir()
        if not mods_dir:
            return
        try:
            mod_manager.set_mod_enabled(mods_dir, filename, enabled)
            self._reload_mods()
        except Exception as exc:
            messagebox.showerror("错误", str(exc))

    def _mod_delete(self, filename):
        mods_dir = self._current_mods_dir()
        if not mods_dir:
            return
        if messagebox.askyesno("删除Mod", "确认删除 {}?".format(filename)):
            try:
                mod_manager.delete_mod(mods_dir, filename)
                self._reload_mods()
            except Exception as exc:
                messagebox.showerror("错误", str(exc))

    def _mod_import(self):
        mods_dir = self._current_mods_dir()
        if not mods_dir:
            messagebox.showwarning("提示", "请先选择实例")
            return
        path = filedialog.askopenfilename(
            title="导入 mod jar", filetypes=[("Mod", "*.jar")])
        if path:
            try:
                mod_manager.copy_mod_into(mods_dir, path)
                self._reload_mods()
            except Exception as exc:
                messagebox.showerror("错误", str(exc))

    def _mod_import_downloads(self):
        """从系统 Downloads 文件夹选择 jar 导入(方便 CurseForge 手动下载后导入)"""
        mods_dir = self._current_mods_dir()
        if not mods_dir:
            messagebox.showwarning("提示", "请先选择实例")
            return
        downloads = Path.home() / "Downloads"
        initial = str(downloads) if downloads.exists() else str(Path.home())
        paths = filedialog.askopenfilenames(
            title="从下载文件夹选择 mod jar",
            initialdir=initial,
            filetypes=[("Mod", "*.jar")])
        if paths:
            ok, fail = 0, 0
            for p in paths:
                try:
                    mod_manager.copy_mod_into(mods_dir, p)
                    ok += 1
                except Exception:
                    fail += 1
            self._reload_mods()
            messagebox.showinfo("导入完成",
                                "成功导入 {} 个, 失败 {} 个".format(ok, fail))

    def _download_missing_deps(self, filename, missing):
        """
        下载缺失前置到当前实例 mods 目录。
        - 优先 Modrinth, 无兼容版本自动回退 CurseForge(需已配置API密钥)
        - 全局去重: 同一个前置只下载一次, 避免多个mod重复触发刷屏
        """
        name = self.inst_combo.get()
        if not name or not missing:
            return
        try:
            inst = instance_mod.get_instance(name)
            mc, loader = self._instance_meta(inst)
        except Exception as exc:
            messagebox.showerror("错误", "读取实例失败: {}".format(exc))
            return
        if loader == "vanilla":
            loader = None
        mods_dir = instance_mod.instance_subdir(name, "mods")
        cf_key = CONFIG.get("cf_api_key", "").strip()

        # 全局去重集合(跨多次点击共享)
        if not hasattr(self, "_dep_tried"):
            self._dep_tried = set()
        to_download = [d for d in missing if d not in self._dep_tried]
        if not to_download:
            return
        for d in to_download:
            self._dep_tried.add(d)

        def _worker():
            for dep in to_download:
                ok = False
                # 1. 优先 Modrinth
                try:
                    modrinth.download_latest_to(dep, mc, loader, mods_dir)
                    self._post("log", "已下载前置(Modrinth): " + dep)
                    ok = True
                except ValueError:
                    pass  # Modrinth 无兼容版本, 走 CurseForge 回退
                except Exception as exc:
                    self._post("log", "Modrinth 前置 {} 异常: {}".format(dep, exc))
                # 2. 回退 CurseForge(仅当配置了密钥)
                if not ok and cf_key:
                    try:
                        results = curseforge.search_mods(
                            dep, game_version=mc, loader=loader)
                        if results:
                            mod_id = results[0]["id"]
                            files = curseforge.get_mod_files(mod_id, mc, loader)
                            if files:
                                curseforge.download_mod_file(
                                    mod_id, files[0]["id"], mods_dir)
                                self._post("log",
                                           "已下载前置(CurseForge): " + dep)
                                ok = True
                    except Exception as exc:
                        self._post("log",
                                   "CurseForge 前置 {} 异常: {}".format(dep, exc))
                if not ok:
                    self._post("log",
                               "前置 {} 未找到(两源均无 {}/{} 版本)".format(
                                   dep, mc, loader or "任意"))
                    self._dep_tried.discard(dep)  # 失败的允许下次重试
                    # 无 CF 密钥时: 自动打开浏览器到 CurseForge 搜索页, 引导手动下载
                    if not cf_key:
                        cf_search = ("https://www.curseforge.com/"
                                     "minecraft/mc-mods/search?search={}").format(dep)
                        webbrowser.open(cf_search)
                        self._post("log",
                                   "已打开浏览器搜索 {}, 请手动下载jar后用"
                                   "'从下载文件夹导入'按钮导入".format(dep))
            self._post("mods_ready", None)
        self._post("log", "开始下载缺失前置: " + ", ".join(to_download))
        self._thread(_worker)

    # ---------------- 设置 ----------------
    def _apply_log_visibility(self, show):
        """显示/隐藏启动页的游戏日志窗口"""
        try:
            if show:
                self.log_box.pack(fill="both", expand=True, padx=8, pady=6)
            else:
                self.log_box.pack_forget()
        except Exception:
            pass

    # ---------------- 挖矿小游戏 ----------------
    # 矿石类型定义: 名称, 贴图名, 耐久(点击次数), 掉落物, 出现权重, 显示颜色
    _ORE_TYPES = [
        # 矿石定义: raw_drop=无精准采集掉落, ore_drop=有精准采集掉落(矿石块), smelt=烧制产物
        {"name": "石头", "tex": "stone", "hp": 2, "raw_drop": "stone", "ore_drop": "stone", "smelt": None, "weight": 35, "color": "#888888", "xp": 1},
        {"name": "煤矿石", "tex": "coal_ore", "hp": 4, "raw_drop": "coal", "ore_drop": "coal_ore", "smelt": None, "weight": 25, "color": "#444444", "xp": 2},
        {"name": "铁矿石", "tex": "iron_ore", "hp": 5, "raw_drop": "raw_iron", "ore_drop": "iron_ore", "smelt": "iron", "weight": 20, "color": "#d8a878", "xp": 3},
        {"name": "金矿石", "tex": "gold_ore", "hp": 6, "raw_drop": "raw_gold", "ore_drop": "gold_ore", "smelt": "gold", "weight": 8, "color": "#ffdd00", "xp": 5},
        {"name": "钻石矿石", "tex": "diamond_ore", "hp": 7, "raw_drop": "diamond", "ore_drop": "diamond_ore", "smelt": None, "weight": 5, "color": "#44eedd", "xp": 8},
        {"name": "绿宝石矿石", "tex": "emerald_ore", "hp": 8, "raw_drop": "emerald", "ore_drop": "emerald_ore", "smelt": None, "weight": 1.5, "color": "#22cc55", "xp": 10},
        {"name": "远古残骸", "tex": "ancient_debris", "hp": 9, "raw_drop": "ancient_debris", "ore_drop": "ancient_debris", "smelt": "netherite_ingot", "weight": 0.8, "color": "#6b4c3a", "xp": 15},
        {"name": "???矿石", "tex": "stone", "hp": 1, "raw_drop": "herobrine", "ore_drop": "herobrine", "smelt": None, "weight": 0.5, "color": "#ff0000", "xp": 100},
    ]
    _DROP_NAMES = {
        "stone": "石头", "coal": "煤炭", "raw_iron": "铁矿石", "iron": "铁锭",
        "raw_gold": "金矿石", "gold": "金锭", "diamond": "钻石", "emerald": "绿宝石",
        "netherite_ingot": "下界合金锭", "ancient_debris": "远古残骸",
        "coal_ore": "煤矿石块", "iron_ore": "铁矿石块", "gold_ore": "金矿石块",
        "diamond_ore": "钻石矿石块", "emerald_ore": "绿宝石矿石块",
        "herobrine": "???", "glass": "玻璃",
    }
    # 附魔定义
    _ENCHANTMENTS = {
        "silk_touch": {"name": "精准采集", "max_level": 1, "weight": 10.5, "desc": "掉落矿石块本身"},
        "efficiency": {"name": "效率", "max_level": 5, "weight": 30, "desc": "挖矿速度提升"},
        "unbreaking": {"name": "耐久", "max_level": 3, "weight": 25, "desc": "减少耐久消耗"},
        "fortune": {"name": "时运", "max_level": 3, "weight": 20, "desc": "增加矿物掉落数量"},
    }

    def _build_combat_tab(self):
        """构建战斗页面"""
        f = self.tab_combat

        # 顶部标题
        title_frame = tk.Frame(f)
        title_frame.pack(fill="x", padx=10, pady=10)
        tk.Label(title_frame, text="⚔️ 战斗系统", bg="#2a2a2a", fg="#ff6666",
                 font=("Arial", 16, "bold")).pack(side="left")
        tk.Label(title_frame, text="夜晚刷怪，击杀怪物获得掉落物", bg="#2a2a2a",
                 fg="#888", font=("Arial", 9)).pack(side="left", padx=10)

        # 游戏联动开关
        self._combat_link_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(title_frame, text="🔗 游戏联动(击杀时游戏里同种怪物也死亡)",
                        variable=self._combat_link_enabled).pack(side="right")

        # 主战斗区域
        main_frame = tk.Frame(f, bg="#2a2a2a")
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # 左侧: 玩家状态和武器
        player_frame = tk.Frame(main_frame, bg="#3a3a3a", width=200)
        player_frame.pack(side="left", fill="y", padx=(0, 5))
        player_frame.pack_propagate(False)

        tk.Label(player_frame, text="👤 玩家状态", bg="#3a3a3a", fg="#fff",
                 font=("Arial", 11, "bold")).pack(pady=8)

        # 血量条
        hp_frame = tk.Frame(player_frame, bg="#3a3a3a")
        hp_frame.pack(fill="x", padx=10, pady=2)
        tk.Label(hp_frame, text="❤️ 血量", bg="#3a3a3a", fg="#ff6666",
                 font=("Arial", 9)).pack(anchor="w")
        self._player_hp_bar = tk.Canvas(hp_frame, height=20, bg="#1a1a1a",
                                          highlightthickness=1, highlightbackground="#555")
        self._player_hp_bar.pack(fill="x", pady=2)
        self._player_hp_text = tk.Label(hp_frame, text="20/20", bg="#3a3a3a",
                                         fg="#fff", font=("Arial", 8))
        self._player_hp_text.pack(anchor="w")

        # 武器选择
        tk.Label(player_frame, text="🗡️ 武器", bg="#3a3a3a", fg="#aaa",
                 font=("Arial", 9)).pack(anchor="w", padx=10, pady=(10, 2))
        self._weapon_listbox = tk.Listbox(player_frame, height=6, bg="#2a2a2a",
                                            fg="#fff", font=("Arial", 9),
                                            selectbackground="#555", exportselection=False)
        self._weapon_listbox.pack(fill="x", padx=10, pady=2)
        weapons = ["木剑 (4伤害)", "石剑 (5伤害)", "铁剑 (6伤害)",
                   "钻石剑 (7伤害)", "下界合金剑 (8伤害)"]
        for w in weapons:
            self._weapon_listbox.insert("end", w)
        self._weapon_listbox.selection_set(0)
        self._weapon_listbox.bind("<<ListboxSelect>>", self._on_weapon_select)

        # 中间: 怪物显示
        mob_frame = tk.Frame(main_frame, bg="#3a3a3a")
        mob_frame.pack(side="left", fill="both", expand=True, padx=5)

        tk.Label(mob_frame, text="👹 怪物", bg="#3a3a3a", fg="#fff",
                 font=("Arial", 11, "bold")).pack(pady=8)

        self._mob_name_label2 = tk.Label(mob_frame, text="夜晚会刷怪", bg="#3a3a3a",
                                          fg="#888", font=("Arial", 12, "bold"))
        self._mob_name_label2.pack()

        # 大怪物显示区
        self._mob_canvas2 = tk.Canvas(mob_frame, width=120, height=160,
                                       bg="#1a1a1a", highlightthickness=2,
                                       highlightbackground="#555", cursor="hand2")
        self._mob_canvas2.pack(pady=10)
        self._mob_canvas2.bind("<Button-1>", lambda e: self._on_mob_click2())

        # 怪物血量条
        self._mob_hp_bar2 = tk.Canvas(mob_frame, height=15, width=150, bg="#1a1a1a",
                                        highlightthickness=1, highlightbackground="#555")
        self._mob_hp_bar2.pack(pady=2)
        self._mob_hp_text2 = tk.Label(mob_frame, text="", bg="#3a3a3a",
                                       fg="#ff6666", font=("Arial", 9))
        self._mob_hp_text2.pack()

        # 右侧: 指令和日志
        cmd_frame = tk.Frame(main_frame, bg="#3a3a3a", width=250)
        cmd_frame.pack(side="right", fill="y", padx=(5, 0))
        cmd_frame.pack_propagate(False)

        tk.Label(cmd_frame, text="💬 指令", bg="#3a3a3a", fg="#fff",
                 font=("Arial", 11, "bold")).pack(pady=8)

        self._cmd_entry2 = ttk.Entry(cmd_frame, font=("Arial", 10))
        self._cmd_entry2.pack(fill="x", padx=10, pady=2)
        self._cmd_entry2.bind("<Return>", lambda e: self._execute_command2())
        self._cmd_entry2.insert(0, "/help")

        ttk.Button(cmd_frame, text="执行指令", command=self._execute_command2).pack(pady=2)

        # 指令日志
        tk.Label(cmd_frame, text="📜 战斗日志", bg="#3a3a3a", fg="#aaa",
                 font=("Arial", 9)).pack(anchor="w", padx=10, pady=(10, 2))
        self._combat_log = tk.Text(cmd_frame, height=12, bg="#1a1a1a", fg="#0f0",
                                    font=("Arial", 8), state="disabled")
        self._combat_log.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # 初始化状态
        self._player_hp = 20
        self._player_max_hp = 20
        self._current_mob = None
        self._current_mob_hp = 0
        self._current_weapon = "wood_sword"
        self._mob_photo2 = None

    def _build_combat_area(self, parent):
        """构建战斗系统区域(娱乐页的小版本)"""
        combat_frame = tk.Frame(parent, bg="#3a3a3a", height=120)
        combat_frame.pack(fill="x", side="bottom", padx=8, pady=(4, 0))
        combat_frame.pack_propagate(False)

        # 左侧: 玩家状态
        player_frame = tk.Frame(combat_frame, bg="#3a3a3a")
        player_frame.pack(side="left", padx=8, pady=4)

        tk.Label(player_frame, text="⚔️ 战斗", bg="#3a3a3a", fg="#fff",
                 font=("Arial", 10, "bold")).pack(anchor="w")

        # 玩家血量
        hp_frame = tk.Frame(player_frame, bg="#3a3a3a")
        hp_frame.pack(anchor="w", pady=2)
        tk.Label(hp_frame, text="❤️", bg="#3a3a3a", fg="#ff4444",
                 font=("Arial", 10)).pack(side="left")
        self._player_hp_label = tk.Label(hp_frame, text="20/20", bg="#3a3a3a",
                                          fg="#fff", font=("Arial", 9, "bold"))
        self._player_hp_label.pack(side="left", padx=2)

        # 武器选择
        weapon_frame = tk.Frame(player_frame, bg="#3a3a3a")
        weapon_frame.pack(anchor="w", pady=2)
        tk.Label(weapon_frame, text="武器:", bg="#3a3a3a", fg="#aaa",
                 font=("Arial", 8)).pack(side="left")
        self._current_weapon = "wood_sword"
        self._weapon_label = tk.Label(weapon_frame, text="🗡️ 木剑", bg="#3a3a3a",
                                       fg="#8B4513", font=("Arial", 9, "bold"))
        self._weapon_label.pack(side="left", padx=2)

        # 中间: 怪物显示区
        mob_frame = tk.Frame(combat_frame, bg="#3a3a3a")
        mob_frame.pack(side="left", padx=20, pady=4)

        self._mob_name_label = tk.Label(mob_frame, text="夜晚会刷怪", bg="#3a3a3a",
                                         fg="#aaa", font=("Arial", 9, "bold"))
        self._mob_name_label.pack()

        self._mob_canvas = tk.Canvas(mob_frame, width=60, height=80,
                                      bg="#2a2a2a", highlightthickness=2,
                                      highlightbackground="#555", cursor="hand2")
        self._mob_canvas.pack(pady=2)
        self._mob_canvas.bind("<Button-1>", lambda e: self._on_mob_click())

        # 怪物血量
        self._mob_hp_label = tk.Label(mob_frame, text="", bg="#3a3a3a",
                                       fg="#ff6666", font=("Arial", 8))
        self._mob_hp_label.pack()

        # 右侧: 指令输入
        cmd_frame = tk.Frame(combat_frame, bg="#3a3a3a")
        cmd_frame.pack(side="right", padx=8, pady=4)

        tk.Label(cmd_frame, text="💬 指令", bg="#3a3a3a", fg="#fff",
                 font=("Arial", 9, "bold")).pack(anchor="w")

        self._cmd_entry = ttk.Entry(cmd_frame, width=25, font=("Arial", 9))
        self._cmd_entry.pack(pady=2)
        self._cmd_entry.bind("<Return>", lambda e: self._execute_command())
        self._cmd_entry.insert(0, "/help")

        ttk.Button(cmd_frame, text="执行", command=self._execute_command,
                   width=8).pack(pady=2)

        # 战斗状态
        self._player_hp = 20
        self._player_max_hp = 20
        self._current_mob = None
        self._current_mob_hp = 0
        self._combat_unlocked = False
        self._mob_photo = None

    def _build_mining_area(self, parent):
        """构建挖矿小游戏区域"""
        mining_frame = tk.Frame(parent, bg="#e8e8e8", height=80)
        mining_frame.pack(fill="x", side="bottom", padx=8, pady=(4, 0))

        # 左侧: 矿石显示区
        ore_frame = tk.Frame(mining_frame, bg="#e8e8e8")
        ore_frame.pack(side="left", padx=8, pady=4)

        self._ore_name_label = tk.Label(ore_frame, text="点击矿石挖矿！",
                                         bg="#e8e8e8", fg="#333",
                                         font=("Arial", 9, "bold"))
        self._ore_name_label.pack()

        self._ore_canvas = tk.Canvas(ore_frame, width=56, height=56,
                                      bg="#c8c8c8", highlightthickness=2,
                                      highlightbackground="#888",
                                      cursor="hand2")
        self._ore_canvas.pack(pady=2)
        self._ore_canvas.bind("<Button-1>", lambda e: self._on_ore_click())

        # 中间: 背包(两列)
        inv_frame = tk.Frame(mining_frame, bg="#e8e8e8")
        inv_frame.pack(side="left", padx=8, pady=4)
        tk.Label(inv_frame, text="🎒 背包", bg="#e8e8e8",
                 font=("Arial", 9, "bold")).grid(row=0, column=0, columnspan=4,
                                                  sticky="w")

        self._inv_labels = {}
        items = [("stone", "🪨"), ("coal", "⬛"), ("raw_iron", "🟫"),
                 ("iron", "🔩"), ("raw_gold", "🟨"), ("gold", "💰"),
                 ("diamond", "💎"), ("emerald", "🟩"), ("ancient_debris", "🟫"),
                 ("netherite_ingot", "🔶")]
        for i, (key, icon) in enumerate(items):
            row = i // 5 + 1
            col = (i % 5) * 2
            tk.Label(inv_frame, text=icon, bg="#e8e8e8",
                     font=("Arial", 10)).grid(row=row, column=col, padx=2, pady=1)
            lbl = tk.Label(inv_frame, text="0", bg="#e8e8e8",
                           font=("Arial", 9, "bold"), width=3, anchor="w")
            lbl.grid(row=row, column=col + 1, padx=2, pady=1, sticky="w")
            self._inv_labels[key] = lbl

        # 右侧: 箱子按钮
        chest_frame = tk.Frame(mining_frame, bg="#e8e8e8")
        chest_frame.pack(side="left", padx=8, pady=4)
        tk.Label(chest_frame, text="📦 箱子", bg="#e8e8e8",
                 font=("Arial", 9, "bold")).pack(anchor="w")
        ttk.Button(chest_frame, text="📥 存入箱子",
                   command=self._deposit_to_chest, width=10).pack(pady=2)
        ttk.Button(chest_frame, text="📦 打开箱子",
                   command=self._open_chest, width=10).pack(pady=2)
        self._chest_count_label = tk.Label(chest_frame, text="箱子: 0 件",
                                            bg="#e8e8e8", font=("Arial", 8))
        self._chest_count_label.pack(pady=2)

        # 挖矿状态初始化
        self._inventory = {"stone": 0, "coal": 0, "raw_iron": 0, "iron": 0,
                           "raw_gold": 0, "gold": 0, "diamond": 0, "emerald": 0,
                           "ancient_debris": 0, "netherite_ingot": 0,
                           "coal_ore": 0, "iron_ore": 0, "gold_ore": 0,
                           "diamond_ore": 0, "emerald_ore": 0, "glass": 0}
        # 附魔和经验
        self._enchantments = {}  # {"silk_touch": 1, "efficiency": 2}
        self._xp_level = 0
        self._xp_points = 0
        # 斧头系统
        self._axe = {"type": "iron", "damage": 9}
        self._villager_hp = 100
        self._villager_max_hp = 100
        self._chest = self._load_chest()
        self._update_chest_count()
        self._current_ore = None
        self._ore_hp = 0
        self._ore_max_hp = 0
        self._ore_photo = None
        self._mining_sound = None
        self._mining_locked = False  # 挖矿锁: 矿石刷新期间禁止点击
        # 预加载挖矿音效
        self.root.after(500, self._preload_mining_sound)
        # 生成第一个矿石
        self.root.after(300, self._spawn_ore)

    def _preload_mining_sound(self):
        """预加载挖矿音效"""
        try:
            game_dir = CONFIG.get("game_dir")
            self._mining_sound = sounds.get_block_break_sound(game_dir)
        except Exception:
            self._mining_sound = None

    def _spawn_ore(self):
        """生成新矿石(按权重随机)"""
        total = sum(o["weight"] for o in self._ORE_TYPES)
        r = random.uniform(0, total)
        cum = 0
        chosen = self._ORE_TYPES[0]
        for ore in self._ORE_TYPES:
            cum += ore["weight"]
            if r <= cum:
                chosen = ore
                break

        self._current_ore = chosen
        # 根据镐子效率和天气加成调整矿石耐久
        import math
        efficiency = self._get_pickaxe_efficiency() * self._get_mining_bonus()
        adjusted_hp = max(1, math.ceil(chosen["hp"] / efficiency))
        self._ore_hp = adjusted_hp
        self._ore_max_hp = adjusted_hp
        self._ore_name_label.config(
            text=f"{chosen['name']} (耐久:{adjusted_hp})",
            fg=chosen["color"])

        # 加载矿石贴图
        try:
            game_dir = CONFIG.get("game_dir")
            tex_path = sounds.get_block_texture(game_dir, chosen["tex"], scale=4)
            if tex_path and os.path.exists(tex_path):
                img = Image.open(tex_path).convert("RGBA")
                # Herobrine 彩蛋: 红色滤镜
                if chosen["raw_drop"] == "herobrine":
                    red = Image.new("RGBA", img.size, (255, 0, 0, 80))
                    img = Image.alpha_composite(img, red)
                self._ore_photo = ImageTk.PhotoImage(img)
                self._ore_canvas.delete("all")
                self._ore_canvas.create_image(32, 32, image=self._ore_photo)
            else:
                self._ore_canvas.delete("all")
                self._ore_canvas.create_rectangle(4, 4, 60, 60,
                                                   fill=chosen["color"])
        except Exception:
            self._ore_canvas.delete("all")
            self._ore_canvas.create_rectangle(4, 4, 60, 60,
                                               fill=chosen["color"])
        # 新矿石刷新完成, 解锁挖矿
        self._mining_locked = False

    def _on_ore_click(self):
        """点击矿石: 挖矿"""
        if not self._current_ore or self._mining_locked:
            return
        self._ore_hp -= 1
        # 消耗镐子耐久
        self._consume_pickaxe_durability()

        # 播放挖矿音效
        self._play_mining_sound()

        # 画裂纹(耐久越低裂纹越多)
        self._draw_cracks()

        if self._ore_hp <= 0:
            self._break_ore()
        else:
            # 更新名称显示剩余耐久
            self._ore_name_label.config(
                text=f"{self._current_ore['name']} (耐久:{self._ore_hp}/{self._ore_max_hp})")

    def _draw_cracks(self):
        """在矿石上画裂纹"""
        self._ore_canvas.delete("crack")
        damage = 1 - (self._ore_hp / self._ore_max_hp)
        num_cracks = int(damage * 6)
        for _ in range(num_cracks):
            x1 = random.randint(8, 56)
            y1 = random.randint(8, 56)
            x2 = x1 + random.randint(-15, 15)
            y2 = y1 + random.randint(-15, 15)
            self._ore_canvas.create_line(x1, y1, x2, y2,
                                          fill="#222", width=2, tags="crack")

    def _break_ore(self):
        """矿石破碎: 掉落矿物, 刷新新矿石"""
        ore = self._current_ore
        has_silk = self._enchantments.get("silk_touch", 0) > 0
        fortune_level = self._enchantments.get("fortune", 0)

        # 精准采集: 掉落矿石块本身
        if has_silk:
            drop = ore["ore_drop"]
            drop_count = 1
        else:
            drop = ore["raw_drop"]
            # 时运: 增加掉落数量(煤炭、钻石、绿宝石、红石、石英)
            base_count = 1
            if fortune_level > 0 and drop in ("coal", "diamond", "emerald"):
                # 时运: 有概率多掉1-2个
                if random.random() < 0.2 * fortune_level:
                    base_count = random.randint(2, 1 + fortune_level)
            drop_count = base_count

        # Herobrine 彩蛋
        if drop == "herobrine":
            self._herobrine_encounter()
            self._mining_locked = True
            self.root.after(1500, self._spawn_ore)
            return

        # 正常掉落
        if drop in self._inventory:
            self._inventory[drop] += drop_count
            if drop in self._inv_labels:
                self._inv_labels[drop].config(text=str(self._inventory[drop]))

        # 玩家状态: 矿石进全局背包 + 经验 + 成就
        try:
            is_rare = drop in ("diamond", "emerald", "ancient_debris",
                               "netherite_ingot", "diamond_ore", "emerald_ore")
            self.player.on_ore_mined(drop, is_rare=is_rare)
            self._update_player_level_display()
            # 游戏联动: 实时发送到游戏背包
            mc_item = player_state.ORE_TO_ITEM.get(drop, drop)
            self._try_send_to_game(mc_item, drop_count)
        except Exception:
            pass

        # 获得经验
        xp_gain = ore.get("xp", 1)
        self._add_xp(xp_gain)

        # 获得积分: 普通矿石+1, 稀有矿石+5
        try:
            is_rare_ore = drop in ("diamond", "emerald", "ancient_debris",
                                   "netherite_ingot", "diamond_ore", "emerald_ore")
            points_gain = 5 if is_rare_ore else 1
            self._add_points(points_gain, "挖矿获得" + drop)
        except Exception:
            pass

        # 掉落文字动画
        drop_name = self._DROP_NAMES.get(drop, drop)
        count_text = f"+{drop_count}" if drop_count > 1 else "+1"
        silk_text = " [精准采集]" if has_silk else ""
        self._ore_name_label.config(text=f"{count_text} {drop_name}！{silk_text}", fg="#00aa00")

        # 成就检测
        if self._inventory["diamond"] >= 1:
            self._unlock_achievement("first_diamond")
        if self._inventory["diamond"] >= 10:
            self._unlock_achievement("diamond_hunter")

        # 0.8秒后刷新新矿石(期间锁定挖矿, 防止点击过快)
        self._mining_locked = True
        self.root.after(800, self._spawn_ore)

    def _play_mining_sound(self):
        """播放挖矿音效"""
        if self._mining_sound and os.path.exists(self._mining_sound):
            sounds.play_ogg(self._mining_sound)
        else:
            self._play_sound(600, 30)

    def _herobrine_encounter(self):
        """Herobrine 彩蛋: 全屏闪红 + 恐怖音效"""
        self._ore_name_label.config(text="你不该挖这个...", fg="#ff0000")
        # 全屏闪红
        flash = tk.Toplevel(self.root)
        flash.attributes("-fullscreen", True)
        flash.attributes("-topmost", True)
        flash.attributes("-alpha", 0.7)
        flash.configure(bg="red")
        flash.overrideredirect(True)
        # 恐怖音效(苦力怕死亡音效反向播放效果, 用高音)
        try:
            import pygame
            if pygame.mixer.get_init():
                # 用苦力怕死亡音效
                game_dir = CONFIG.get("game_dir")
                h, _ = sounds._find_sound_hash(game_dir,
                    ["minecraft/sounds/mob/creeper/death.ogg"])
                if h:
                    death_path = os.path.join(os.environ.get("APPDATA"),
                        "VoxelLauncher", "sounds", "creeper_death.ogg")
                    sounds._extract_ogg(game_dir, h, death_path)
                    if os.path.exists(death_path):
                        s = pygame.mixer.Sound(death_path)
                        s.set_volume(0.8)
                        s.play()
        except Exception:
            self._play_sound(200, 200)
        self.root.after(500, flash.destroy)
        self._unlock_achievement("herobrine_encounter")

    # ---------------- 箱子存储 ----------------
    def _chest_file(self):
        """箱子数据文件路径"""
        return os.path.join(os.environ.get("APPDATA", "."),
                            "VoxelLauncher", "chest.json")

    def _load_chest(self):
        """加载箱子数据"""
        default = {"stone": 0, "coal": 0, "iron": 0,
                   "gold": 0, "diamond": 0, "emerald": 0,
                   "netherite_ingot": 0}
        data = self._load_json_safe(self._chest_file(), default)
        # 确保所有 key 都存在
        for k in default:
            data.setdefault(k, 0)
        return data

    def _save_chest(self):
        """保存箱子数据"""
        self._save_json_safe(self._chest_file(), self._chest)

    def _update_chest_count(self):
        """更新箱子物品总数显示"""
        total = sum(self._chest.values())
        self._chest_count_label.config(text=f"箱子: {total} 件")

    def _deposit_to_chest(self):
        """把背包里所有矿石存入箱子"""
        deposited = 0
        for key in self._inventory:
            if self._inventory[key] > 0:
                self._chest[key] += self._inventory[key]
                deposited += self._inventory[key]
                self._inventory[key] = 0
                self._inv_labels[key].config(text="0")
        if deposited > 0:
            self._save_chest()
            self._update_chest_count()
            self._ore_name_label.config(text=f"存入 {deposited} 件矿石！",
                                         fg="#0088ff")
            self.root.after(1500, lambda: self._ore_name_label.config(
                text="点击矿石挖矿！", fg="#333"))
        else:
            self._ore_name_label.config(text="背包是空的！", fg="#ff8800")
            self.root.after(1500, lambda: self._ore_name_label.config(
                text="点击矿石挖矿！", fg="#333"))

    def _open_chest(self):
        """打开箱子窗口(用游戏提取的箱子纹理)"""
        try:
            win = tk.Toplevel(self.root)
            win.title("📦 箱子 - 矿石仓库")
            win.geometry("400x340")
            win.configure(bg="#c8a878")
            win.resizable(False, False)

            # 箱子贴图(从游戏提取)
            chest_photo = self._item_photos.get("chest")
            if chest_photo:
                tk.Label(win, image=chest_photo, bg="#c8a878").pack(pady=(6, 2))
            tk.Label(win, text="矿石箱子", bg="#c8a878",
                     font=("Arial", 12, "bold"), fg="#5a3a1a").pack(pady=(0, 4))

            # 物品网格(4列2行, 像 MC 箱子)
            grid_frame = tk.Frame(win, bg="#8b6914", padx=8, pady=8)
            grid_frame.pack(padx=10, pady=4)

            items = [("stone", "石头"), ("coal", "煤炭"),
                     ("iron", "铁锭"), ("gold", "金锭"),
                     ("diamond", "钻石"), ("emerald", "绿宝石"),
                     ("netherite_ingot", "下界合金锭")]
            # 预加载物品贴图(如果还没加载)
            item_tex_map = {
                "stone": "stone", "coal": "coal", "iron": "iron_ingot",
                "gold": "gold_ingot", "diamond": "diamond",
                "emerald": "emerald", "netherite_ingot": "netherite_ingot",
            }
            for i, (key, name) in enumerate(items):
                row, col = divmod(i, 4)
                slot = tk.Frame(grid_frame, bg="#c8a878", width=80, height=65,
                                highlightbackground="#5a3a1a",
                                highlightthickness=2)
                slot.grid(row=row, column=col, padx=4, pady=4)
                slot.pack_propagate(False)

                # 尝试显示物品贴图
                tex_name = item_tex_map.get(key)
                item_photo = None
                if tex_name and tex_name not in self._item_photos:
                    try:
                        game_dir = CONFIG.get("game_dir")
                        tp = sounds.get_item_texture(game_dir, tex_name, scale=2)
                        if tp and os.path.exists(tp):
                            self._item_photos[tex_name] = ImageTk.PhotoImage(
                                Image.open(tp).convert("RGBA"))
                    except Exception:
                        pass
                item_photo = self._item_photos.get(tex_name)

                if item_photo:
                    tk.Label(slot, image=item_photo, bg="#c8a878").pack(pady=(2, 0))
                else:
                    tk.Label(slot, text=name, bg="#c8a878",
                             font=("Arial", 8)).pack(pady=(8, 0))
                count = self._chest.get(key, 0)
                tk.Label(slot, text=str(count), bg="#c8a878",
                         font=("Arial", 11, "bold"),
                         fg="#ffffff" if count > 0 else "#888888").pack()

            # 底部按钮
            btn_frame = tk.Frame(win, bg="#c8a878")
            btn_frame.pack(pady=6)
            ttk.Button(btn_frame, text="取出全部",
                       command=lambda: self._withdraw_all(win)).pack(side="left",
                                                                     padx=5)
            ttk.Button(btn_frame, text="关闭",
                       command=win.destroy).pack(side="left", padx=5)
        except Exception:
            pass

    def _withdraw_all(self, chest_win):
        """从箱子取出全部矿石到背包"""
        withdrawn = 0
        for key in self._chest:
            if self._chest[key] > 0:
                self._inventory[key] += self._chest[key]
                withdrawn += self._chest[key]
                self._chest[key] = 0
                self._inv_labels[key].config(text=str(self._inventory[key]))
        if withdrawn > 0:
            self._save_chest()
            self._update_chest_count()
        chest_win.destroy()

    # ---------------- 像素苦力怕宠物 ----------------
    # 苦力怕像素图(16x16): 0=透明 1=深绿 2=浅绿 3=黑色
    _CREEPER_PIXELS = [
        "0000222222220000",
        "0002222222222000",
        "0022222222222200",
        "0022332222332200",
        "0022332222332200",
        "0022223333222200",
        "0022233333322200",
        "0022222222222200",
        "0121212121212120",
        "0121212121212120",
        "0121212121212120",
        "0121212121212120",
        "0121212121212120",
        "0121212121212120",
        "0121212121212120",
        "0121212121212120",
    ]
    _CREEPER_COLORS = {"1": "#0f4b0f", "2": "#3f9f3f", "3": "#000000"}
    _CREEPER_TALKS = [
        "嘶嘶嘶...", "别点我，我会炸！", "你点我干嘛？",
        "我要炸了！", "别点了，我害羞", "BOOM！（并没有）",
        "我是苦力怕，不是绿色的猫", "今天也是想炸人的一天",
        "你身后有钻石（骗你的）", "Herobrine 让我带个话：他不存在",
        "我不是怪物，我只是长得丑", "点我不会掉钻石，别想了",
        "我炸过的房子比你吃过的饭还多", "你妈妈叫你回家吃饭",
        "史蒂夫欠我 5 个绿宝石", "村民说我是奸商，我才不是",
        "下界好热，我想回家", "村民又偷我东西了",
        "我曾经也是个普通人，直到被雷劈了", " creeper? aw man",
    ]

    # 村民像素图(16x32, 跟苦力怕一样的比例): 0=透明 1=黑色 2=紫色眼睛 3=深灰
    _VILLAGER_PIXELS = [
        # 头(8x8, 居中)
        "0000111111110000",
        "0001111111111000",
        "0011111111111100",
        "0011221111221100",
        "0011221111221100",
        "0011111111111100",
        "0011111111111100",
        "0001111111111000",
        # 脖子
        "0000111111110000",
        # 身体(8x12, 居中, 含长手臂)
        "0011111111111100",
        "0111111111111110",
        "0111111111111110",
        "0111111111111110",
        "0111111111111110",
        "0111111111111110",
        "0111111111111110",
        "0111111111111110",
        "0111111111111110",
        "0111111111111110",
        "0011111111111100",
        "0001111111111000",
        # 腿(两条, 各4x12)
        "0001100000011000",
        "0001100000011000",
        "0001100000011000",
        "0001100000011000",
        "0001100000011000",
        "0001100000011000",
        "0001100000011000",
        "0001100000011000",
        "0001100000011000",
        "0001100000011000",
        "0001100000011000",
        "0001100000011000",
    ]
    _VILLAGER_COLORS = {"1": "#0a0a0a", "2": "#cc00cc", "3": "#222222"}
    _VILLAGER_TALKS = [
        "嗯...", "嗯?", "嗯!", "哼哼",
        "要交易吗?", "看看我的货吧", "这可是好东西",
        "绿宝石...我想要绿宝石", "今天天气不错",
        "你好啊", "欢迎光临", "不买别碰",
        "便宜卖了", "嘿嘿嘿", "需要点什么?",
        "这个很划算的", "我可是专业的",
        "又是忙碌的一天", "村民的生活不容易啊",
    ]
    _VILLAGER_HURT_TALKS = [
        "哎哟！", "别打我！", "救命啊！", "我错了！",
        "不要啊！", "我的鼻子！", "啊啊啊！",
    ]

    # ---------------- 战斗系统 ----------------
    # 武器数据: 名称, 伤害, 图标, 合成材料
    _WEAPONS = {
        "wood_sword": {"name": "木剑", "damage": 4, "icon": "🗡️", "color": "#8B4513"},
        "stone_sword": {"name": "石剑", "damage": 5, "icon": "🗡️", "color": "#808080"},
        "iron_sword": {"name": "铁剑", "damage": 6, "icon": "🗡️", "color": "#C0C0C0"},
        "diamond_sword": {"name": "钻石剑", "damage": 7, "icon": "🗡️", "color": "#00CED1"},
        "netherite_sword": {"name": "下界合金剑", "damage": 8, "icon": "🗡️", "color": "#4A3728"},
    }

    # 怪物数据: 名称, 血量, 伤害, 掉落物
    _MONSTERS = {
        "zombie": {"name": "僵尸", "hp": 20, "damage": 3,
                   "drops": ["rotten_flesh", "iron_ingot", "carrot"],
                   "drop_chance": [0.8, 0.1, 0.05]},
        "skeleton": {"name": "骷髅", "hp": 20, "damage": 2,
                     "drops": ["bone", "arrow", "bow"],
                     "drop_chance": [0.8, 0.5, 0.1]},
    }

    def _load_creeper_texture(self):
        """加载从 Minecraft 提取的原版苦力怕贴图, 保存原始图片用于动态缩放"""
        try:
            game_dir = CONFIG.get("game_dir")
            tex_path = sounds.get_creeper_texture(game_dir, scale=3)
            if tex_path and os.path.exists(tex_path):
                # 保存原始图片(scale=3 的版本作为基准)
                self._creeper_original_img = Image.open(tex_path).convert("RGBA")
                self._update_creeper_display()
                return
        except Exception:
            pass
        # 回退: 显示文字
        self._creeper_label.config(text="💥", font=("Arial", 24))

    def _update_creeper_display(self):
        """根据当前 scale 和闪电状态更新苦力怕显示"""
        if not self._creeper_original_img:
            return
        try:
            base_w, base_h = self._creeper_original_img.size
            # 基准是 scale=3, 所以实际缩放 = _creeper_scale / 3
            factor = self._creeper_scale / 3.0
            new_w = max(8, int(base_w * factor))
            new_h = max(32, int(base_h * factor))
            img = self._creeper_original_img.resize((new_w, new_h), Image.NEAREST)

            # 闪电苦力怕: 加蓝色叠加
            if self._creeper_is_charged:
                blue_overlay = Image.new("RGBA", img.size, (0, 150, 255, 100))
                img = Image.alpha_composite(img, blue_overlay)

            self._creeper_photo = ImageTk.PhotoImage(img)
            # 白色版本(爆炸效果)
            white_img = Image.new("RGBA", img.size, (255, 255, 255, 255))
            white_img.putalpha(img.getchannel("A"))
            self._creeper_photo_white = ImageTk.PhotoImage(white_img)
            self._creeper_label.config(image=self._creeper_photo)
        except Exception:
            pass

    def _creeper_click(self):
        """点击苦力怕: 爆炸效果(变白) + 真实音效 + 说话"""
        if self._creeper_exploded:
            return
        self._creeper_exploded = True
        if self._creeper_photo_white:
            self._creeper_label.config(image=self._creeper_photo_white)
        self._play_explosion()
        # 玩家受到伤害: 史蒂夫受伤"嗷"一声
        try:
            game_dir = CONFIG.get("game_dir")
            sounds.play_player_hurt(game_dir)
        except Exception:
            pass
        self._creeper_say(random.choice(["BOOM！", "我炸了！", "嘶——砰！", "嗷！你受伤了！"]))
        # 玩家状态: 击杀苦力怕 +经验
        try:
            self.player.on_creeper_killed()
            self._update_player_level_display()
        except Exception:
            pass
        self.root.after(300, lambda: self._creeper_label.config(
            image=self._creeper_photo) if self._creeper_photo else None)
        self.root.after(500, lambda: setattr(self, "_creeper_exploded", False))

    def _feed_creeper(self):
        """右键喂食苦力怕: 越喂越大, 5次变闪电苦力怕, 10次超级爆炸重置"""
        if self._creeper_exploded:
            return
        self._creeper_feed_count += 1
        self._creeper_scale += 0.5

        # 喂食台词
        feed_lines = [
            "好吃！还要！", "嗯~火药味真香", "再给我来点！",
            "我感觉力量在涌上来！", "别停，继续喂！",
            "我的身体...在变大！", "火药！我要更多火药！",
            "你喂的是火药吗？不管了，吃！",
        ]
        self._creeper_say(random.choice(feed_lines), 1500)
        self._update_creeper_display()

        # 5次: 变成闪电苦力怕
        if self._creeper_feed_count == 5:
            self._creeper_is_charged = True
            self._update_creeper_display()
            self._creeper_say("⚡ 我充满了力量！⚡", 2500)
            self._unlock_achievement("charged_creeper")

        # 10次: 超级大爆炸, 重置
        if self._creeper_feed_count >= 10:
            self._creeper_say("💥 我要炸了！！！", 1000)
            self.root.after(800, self._creeper_super_explosion)

    def _creeper_super_explosion(self):
        """苦力怕超级大爆炸: 全屏闪白 + 大爆炸声 + 重置"""
        # 全屏闪白
        flash = tk.Toplevel(self.root)
        flash.attributes("-fullscreen", True)
        flash.attributes("-topmost", True)
        flash.configure(bg="white")
        flash.overrideredirect(True)
        # 大爆炸声(音量最大)
        try:
            import pygame
            game_dir = CONFIG.get("game_dir")
            _, exp_path = sounds.get_creeper_explosion_sound(game_dir)
            if exp_path and pygame.mixer.get_init():
                s = pygame.mixer.Sound(exp_path)
                s.set_volume(1.0)
                s.play()
        except Exception:
            self._play_explosion()
        self.root.after(400, flash.destroy)
        # 重置苦力怕
        self._creeper_feed_count = 0
        self._creeper_scale = 3.0
        self._creeper_is_charged = False
        self.root.after(500, self._update_creeper_display)
        self._creeper_say("啊...我被炸回原形了...", 2500)
        self._unlock_achievement("creeper_super_explosion")

    def _update_player_level_display(self):
        """更新等级和经验条显示"""
        try:
            lv = self.player.level
            exp = self.player.exp
            need = self.player.exp_to_next
            self._player_level_label.config(text=f"Lv.{lv}")
            self._xp_text_label.config(text=f"{exp}/{need} EXP")
            pct = min(1.0, exp / need) if need > 0 else 0
            bar_w = 200
            self._xp_bar_fg.config(width=int(bar_w * pct))
        except Exception:
            pass

    def _open_backpack(self):
        """打开背包窗口: 显示挖矿获得的物品, 可生成 /give 指令"""
        win = tk.Toplevel(self.root)
        win.title("🎒 我的背包 - 可转换为游戏指令")
        win.geometry("480x420")
        win.configure(bg="#2b2b2b")

        # 说明
        tk.Label(win, text="挖到的矿石都在这里, 可以转换成游戏里的 /give 指令",
                 bg="#2b2b2b", fg="#ccc", font=("Arial", 9)).pack(pady=(8, 4))

        # 物品列表
        list_frame = tk.Frame(win, bg="#2b2b2b")
        list_frame.pack(fill="both", expand=True, padx=10, pady=4)

        canvas = tk.Canvas(list_frame, bg="#2b2b2b", highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg="#2b2b2b")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        inv = self.player.inventory
        if not inv:
            tk.Label(inner, text="背包空空如也, 去挖矿吧！",
                     bg="#2b2b2b", fg="#888").pack(pady=20)
        else:
            for mc_id, count in sorted(inv.items()):
                if count <= 0:
                    continue
                row = tk.Frame(inner, bg="#3a3a3a")
                row.pack(fill="x", padx=4, pady=2)
                name = mc_id.split(":")[-1] if ":" in mc_id else mc_id
                tk.Label(row, text=f"  {name}", bg="#3a3a3a", fg="#fff",
                         width=20, anchor="w").pack(side="left", padx=2, pady=4)
                tk.Label(row, text=f"x{count}", bg="#3a3a3a", fg="#ffd700",
                         width=8, font=("Arial", 9, "bold")).pack(side="left")
                ttk.Button(row, text="复制指令", width=10,
                           command=lambda mid=mc_id, c=count: self._copy_give_cmd(mid, c)
                           ).pack(side="right", padx=4, pady=3)

        # 底部按钮
        btn_frame = tk.Frame(win, bg="#2b2b2b")
        btn_frame.pack(fill="x", padx=10, pady=8)
        ttk.Button(btn_frame, text="📋 复制全部物品指令",
                   command=self._copy_all_give_cmds).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="🎮 一键发送到游戏",
                   command=lambda: self._send_all_to_game(win)).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="🗑 清空背包",
                   command=lambda: self._clear_backpack(win)).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="关闭", command=win.destroy).pack(side="right", padx=4)

    def _copy_give_cmd(self, mc_id, count):
        """复制单个物品的 /give 指令到剪贴板"""
        cmds = []
        while count > 0:
            batch = min(count, 64)
            cmds.append(f"/give @s {mc_id} {batch}")
            count -= batch
        text = chr(10).join(cmds)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        messagebox.showinfo("已复制", "已复制到剪贴板:" + chr(10) + text + chr(10) + chr(10) + "进游戏后按 Ctrl+V 粘贴到聊天框")

    def _copy_all_give_cmds(self):
        """复制全部物品的 /give 指令"""
        cmds = self.player.generate_give_commands("@s")
        if not cmds:
            messagebox.showinfo("提示", "背包是空的")
            return
        text = chr(10).join(cmds)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        messagebox.showinfo("已复制", "已复制 " + str(len(cmds)) + " 条指令到剪贴板" + chr(10) + chr(10) + "进游戏后逐条粘贴到聊天框执行")

    def _send_all_to_game(self, win):
        """把背包所有物品发送到游戏"""
        if not CONFIG.get("bridge_enabled", False):
            messagebox.showwarning("提示", "请先在设置里开启「游戏联动」开关")
            return
        if not bridge.is_bridge_running():
            messagebox.showwarning("提示", "未检测到游戏联动 Mod。" + chr(10) + "请先启动游戏并进入世界。")
            return
        inv = self.player.inventory
        if not inv:
            messagebox.showinfo("提示", "背包是空的")
            return
        success, failed, details = bridge.send_inventory(inv)
        detail_text = chr(10).join(details)
        messagebox.showinfo("发送结果",
            f"成功: {success} 种, 失败: {failed} 种" + chr(10) + chr(10) + detail_text)
        if success > 0:
            self.player.clear_inventory()
            win.destroy()
            self._open_backpack()

    def _clear_backpack(self, win):
        """清空背包"""
        if messagebox.askyesno("确认", "确定要清空背包吗？所有物品将丢失！"):
            self.player.clear_inventory()
            win.destroy()
            self._open_backpack()

    def _open_achievements(self):
        """打开成就窗口"""
        win = tk.Toplevel(self.root)
        win.title("🏆 成就列表")
        win.geometry("500x480")
        win.configure(bg="#2b2b2b")

        # 统计
        stats = self.player.stats
        stat_text = (f"启动次数: {stats.get('launch_count', 0)}  |  "
                     f"挖矿数: {stats.get('ore_mined', 0)}  |  "
                     f"击杀苦力怕: {stats.get('creeper_killed', 0)}  |  "
                     f"等级: Lv.{self.player.level}")
        tk.Label(win, text=stat_text, bg="#2b2b2b", fg="#ffd700",
                 font=("Arial", 9, "bold")).pack(pady=(8, 4))

        # 成就列表
        list_frame = tk.Frame(win, bg="#2b2b2b")
        list_frame.pack(fill="both", expand=True, padx=10, pady=4)
        canvas = tk.Canvas(list_frame, bg="#2b2b2b", highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg="#2b2b2b")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        all_achs = achievements.ACHIEVEMENTS
        for ach_id, info in all_achs.items():
            is_unlocked = self.ach_mgr.is_unlocked(ach_id)
            row = tk.Frame(inner, bg="#3a3a3a" if is_unlocked else "#222")
            row.pack(fill="x", padx=4, pady=2)
            icon = info.get("icon", "🏅")
            name = info.get("name", ach_id)
            desc = info.get("desc", "")
            fg = "#fff" if is_unlocked else "#666"
            tk.Label(row, text=icon, bg="#3a3a3a" if is_unlocked else "#222",
                     font=("Arial", 14)).pack(side="left", padx=6, pady=4)
            tk.Label(row, text=name + chr(10) + desc, bg="#3a3a3a" if is_unlocked else "#222",
                     fg=fg, justify="left", font=("Arial", 9)).pack(side="left", padx=4, pady=4)
            if is_unlocked:
                tk.Label(row, text="✓ 已解锁", bg="#3a3a3a", fg="#4CAF50",
                         font=("Arial", 9, "bold")).pack(side="right", padx=8)
            else:
                tk.Label(row, text="🔒 未解锁", bg="#222", fg="#666",
                         font=("Arial", 9)).pack(side="right", padx=8)

        ttk.Button(win, text="关闭", command=win.destroy).pack(pady=8)

    def _creeper_say(self, text, duration=2000):
        """苦力怕说话(气泡显示, 带角色名)"""
        try:
            self._creeper_bubble.config(text="苦力怕:\n" + text)
            self._creeper_bubble.place(x=75, y=10)
            self.root.after(duration, lambda: self._creeper_bubble.place_forget())
        except Exception:
            pass

    def _creeper_wander(self):
        """苦力怕随机左右走动(只在左半边活动)"""
        try:
            if not self._creeper_exploded:
                frame_width = self._pet_frame.winfo_width() or 800
                # 苦力怕只在左半边活动(0到frame_width/2 - 60)
                max_x = frame_width // 2 - 80
                current_x = self._creeper_label.winfo_x()
                # 随机移动方向和距离
                direction = random.choice([-1, 1])
                distance = random.randint(20, 80)
                new_x = current_x + direction * distance
                new_x = max(10, min(max_x, new_x))
                self._creeper_label.place(x=new_x, y=35)
                # 移动时偶尔说话
                if random.random() < 0.3:
                    self._creeper_say(random.choice(self._CREEPER_TALKS), 1500)
        except Exception:
            pass
        # 每 3-6 秒走动一次
        self.root.after(random.randint(3000, 6000), self._creeper_wander)

    def _creeper_talk_random(self):
        """苦力怕偶尔自己说话"""
        try:
            if random.random() < 0.4 and not self._creeper_exploded and not self._pet_dialogue_active:
                self._creeper_say(random.choice(self._CREEPER_TALKS), 2500)
        except Exception:
            pass
        self.root.after(random.randint(8000, 15000), self._creeper_talk_random)

    # ---------------- 村民宠物 ----------------
    def _load_villager_texture(self):
        """加载从 Minecraft 提取的原版村民贴图, 跟苦力怕一样的拼接方式"""
        try:
            game_dir = CONFIG.get("game_dir")
            tex_path = sounds.get_villager_texture(game_dir, scale=3)
            if tex_path and os.path.exists(tex_path):
                self._villager_original_img = Image.open(tex_path).convert("RGBA")
                self._update_villager_display()
                return
        except Exception:
            pass
        # 回退: 用像素图绘制
        self._draw_villager_pixels()

    def _draw_villager_pixels(self):
        """用像素数据绘制村民(跟苦力怕一样的风格, scale=3)"""
        try:
            scale = 3
            rows = len(self._VILLAGER_PIXELS)
            cols = len(self._VILLAGER_PIXELS[0]) if rows > 0 else 16
            w = cols * scale
            h = rows * scale
            img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            pixels = img.load()
            for y, row in enumerate(self._VILLAGER_PIXELS):
                for x, c in enumerate(row):
                    if c in self._VILLAGER_COLORS:
                        color = self._VILLAGER_COLORS[c]
                        r = int(color[1:3], 16)
                        g = int(color[3:5], 16)
                        b = int(color[5:7], 16)
                        for dy in range(scale):
                            for dx in range(scale):
                                px = x * scale + dx
                                py = y * scale + dy
                                if px < w and py < h:
                                    pixels[px, py] = (r, g, b, 255)
            self._villager_original_img = img
            self._update_villager_display()
        except Exception:
            pass

    def _update_villager_display(self):
        """更新村民显示"""
        try:
            if self._villager_original_img:
                img = self._villager_original_img
                photo = ImageTk.PhotoImage(img)
                self._villager_label.config(image=photo)
                self._villager_label.image = photo
        except Exception:
            pass

    def _villager_say(self, text, duration=2500):
        """村民说话(气泡显示, 带角色名, 播放村民叫声)"""
        try:
            self._villager_bubble.config(text="村民:\n" + text)
            self._villager_bubble.place(x=75, y=10)
            self.root.after(duration, lambda: self._villager_bubble.place_forget())
            # 只在娱乐页面播放村民叫声
            try:
                current_tab = self.nb.index(self.nb.select())
                tab_text = self.nb.tab(current_tab, "text")
                if "娱乐" in tab_text or "战斗" in tab_text:
                    game_dir = CONFIG.get("game_dir")
                    if game_dir:
                        sounds.play_villager_say(game_dir)
            except Exception:
                pass
        except Exception:
            pass

    def _villager_click(self):
        """点击村民: 村民受伤, 然后跑开"""
        self._play_click()
        self._villager_say(random.choice(self._VILLAGER_HURT_TALKS), 2000)
        # 村民跑开(随机移动到右边)
        try:
            frame_width = self._pet_frame.winfo_width() or 800
            current_x = self._villager_label.winfo_x()
            new_x = min(frame_width - 80, current_x + random.randint(50, 100))
            self._villager_label.place(x=new_x, y=35)
        except Exception:
            pass
        # 成就
        self._unlock_achievement("villager_hurt")

    def _feed_villager(self):
        """右键喂食村民: 给它绿宝石, 它会很开心"""
        self._play_click()
        # 检查有没有绿宝石
        if self._inventory.get("emerald", 0) > 0:
            self._inventory["emerald"] -= 1
            if "emerald" in self._inv_labels:
                self._inv_labels["emerald"].config(text=str(self._inventory["emerald"]))
            self._villager_say("绿宝石！太好了！谢谢你！", 2500)
            self._add_xp(5)
        else:
            self._villager_say("你有绿宝石吗？我想要绿宝石...", 2000)

    def _villager_wander(self):
        """村民随机走动: 在右半边慢慢走来走去"""
        try:
            frame_width = self._pet_frame.winfo_width() or 800
            # 村民只在右半边活动(frame_width/2到frame_width-80)
            min_x = frame_width // 2 + 20
            max_x = frame_width - 80
            current_x = self._villager_label.winfo_x()
            # 随机移动方向和距离(比苦力怕慢)
            direction = random.choice([-1, 1])
            distance = random.randint(10, 40)
            new_x = current_x + direction * distance
            new_x = max(min_x, min(max_x, new_x))
            self._villager_label.place(x=new_x, y=35)
            # 移动时偶尔说话
            if random.random() < 0.3:
                self._villager_say(random.choice(self._VILLAGER_TALKS), 1500)
        except Exception:
            pass

    def _villager_wander_loop(self):
        """村民随机走动循环"""
        try:
            if not self._pet_dialogue_active:
                if random.random() < 0.5:
                    self._villager_wander()
        except Exception:
            pass
        self.root.after(random.randint(3000, 6000), self._villager_wander_loop)

    # ---------------- 战斗系统逻辑 ----------------
    def _spawn_mob(self, mob_type=None):
        """生成怪物"""
        if mob_type is None:
            mob_type = random.choice(["zombie", "skeleton"])
        mob_info = self._MONSTERS.get(mob_type)
        if not mob_info:
            return
        self._current_mob = mob_type
        self._current_mob_hp = mob_info["hp"]
        self._mob_name_label.config(text=mob_info["name"], fg="#ff6666")
        self._mob_hp_label.config(text=f"{self._current_mob_hp}/{mob_info['hp']}")
        # 加载怪物贴图
        try:
            game_dir = CONFIG.get("game_dir")
            if mob_type == "zombie":
                tex_path = sounds.get_zombie_texture(game_dir, scale=3)
            else:
                tex_path = sounds.get_skeleton_texture(game_dir, scale=3)
            if tex_path and os.path.exists(tex_path):
                img = Image.open(tex_path).convert("RGBA")
                self._mob_photo = ImageTk.PhotoImage(img)
                self._mob_canvas.delete("all")
                self._mob_canvas.create_image(30, 40, image=self._mob_photo)
        except Exception:
            # 回退: 用文字显示
            self._mob_canvas.delete("all")
            self._mob_canvas.create_text(30, 40, text="👹" if mob_type == "zombie" else "💀",
                                          font=("Arial", 30))

    def _on_mob_click(self):
        """点击怪物攻击"""
        if not self._current_mob:
            return
        weapon_info = self._WEAPONS.get(self._current_weapon)
        damage = weapon_info["damage"] if weapon_info else 1
        self._current_mob_hp -= damage
        mob_info = self._MONSTERS[self._current_mob]

        if self._current_mob_hp <= 0:
            # 怪物死亡
            self._mob_name_label.config(text="已击杀!", fg="#66ff66")
            self._mob_hp_label.config(text="")
            self._mob_canvas.delete("all")
            # 掉落物
            self._drop_loot(self._current_mob)
            self._current_mob = None
            self._add_xp(5)
            # 3秒后刷新
            self.root.after(3000, self._reset_mob_display)
        else:
            # 怪物受伤, 反击
            self._mob_hp_label.config(text=f"{self._current_mob_hp}/{mob_info['hp']}")
            # 怪物反击玩家
            mob_damage = mob_info["damage"]
            self._player_hp -= mob_damage
            if self._player_hp <= 0:
                self._player_hp = self._player_max_hp
                self._mob_name_label.config(text="你死了!", fg="#ff0000")
                self._current_mob = None
                self._mob_canvas.delete("all")
                self.root.after(3000, self._reset_mob_display)
            self._player_hp_label.config(text=f"{self._player_hp}/{self._player_max_hp}")
            # 攻击音效
            self._play_sound(300, 50)

    def _reset_mob_display(self):
        """重置怪物显示"""
        self._mob_name_label.config(text="夜晚会刷怪", fg="#aaa")
        self._mob_hp_label.config(text="")
        self._mob_canvas.delete("all")

    def _drop_loot(self, mob_type):
        """怪物掉落物"""
        mob_info = self._MONSTERS.get(mob_type)
        if not mob_info:
            return
        for i, item in enumerate(mob_info["drops"]):
            chance = mob_info["drop_chance"][i] if i < len(mob_info["drop_chance"]) else 0.1
            if random.random() < chance:
                amount = random.randint(1, 3)
                self._inventory[item] = self._inventory.get(item, 0) + amount
                if item in self._inv_labels:
                    self._inv_labels[item].config(text=str(self._inventory[item]))

    # ---------------- 战斗页面交互 ----------------
    def _on_weapon_select(self, event=None):
        """选择武器"""
        selection = self._weapon_listbox.curselection()
        if not selection:
            return
        weapon_keys = ["wood_sword", "stone_sword", "iron_sword", "diamond_sword", "netherite_sword"]
        idx = selection[0]
        if idx < len(weapon_keys):
            self._current_weapon = weapon_keys[idx]
            weapon_info = self._WEAPONS[self._current_weapon]
            self._combat_log_print(f"装备了 {weapon_info['name']} (伤害: {weapon_info['damage']})")

    def _spawn_mob2(self, mob_type=None):
        """战斗页面生成怪物"""
        if mob_type is None:
            mob_type = random.choice(["zombie", "skeleton"])
        mob_info = self._MONSTERS.get(mob_type)
        if not mob_info:
            return
        self._current_mob = mob_type
        self._current_mob_hp = mob_info["hp"]
        self._mob_name_label2.config(text=mob_info["name"], fg="#ff6666")
        self._update_mob_hp_bar2()
        # 加载怪物贴图(大尺寸)
        try:
            game_dir = CONFIG.get("game_dir")
            if mob_type == "zombie":
                tex_path = sounds.get_zombie_texture(game_dir, scale=5)
            else:
                tex_path = sounds.get_skeleton_texture(game_dir, scale=5)
            if tex_path and os.path.exists(tex_path):
                img = Image.open(tex_path).convert("RGBA")
                self._mob_photo2 = ImageTk.PhotoImage(img)
                self._mob_canvas2.delete("all")
                self._mob_canvas2.create_image(60, 80, image=self._mob_photo2)
        except Exception:
            self._mob_canvas2.delete("all")
            self._mob_canvas2.create_text(60, 80, text="👹" if mob_type == "zombie" else "💀",
                                          font=("Arial", 50))
        self._combat_log_print(f"{mob_info['name']} 出现了！血量: {mob_info['hp']}")

    def _on_mob_click2(self):
        """战斗页面点击怪物攻击"""
        if not self._current_mob:
            self._combat_log_print("当前没有怪物，输入 /summon 召唤一个")
            return
        weapon_info = self._WEAPONS.get(self._current_weapon)
        damage = weapon_info["damage"] if weapon_info else 1
        self._current_mob_hp -= damage
        mob_info = self._MONSTERS[self._current_mob]
        self._combat_log_print(f"你用{weapon_info['name']}攻击，造成 {damage} 点伤害")

        if self._current_mob_hp <= 0:
            # 怪物死亡
            self._combat_log_print(f"击杀了 {mob_info['name']}！")
            self._mob_name_label2.config(text="已击杀!", fg="#66ff66")
            self._mob_hp_bar2.delete("all")
            self._mob_hp_text2.config(text="")
            self._mob_canvas2.delete("all")
            # 掉落物
            self._drop_loot(self._current_mob)
            self._add_xp(5)
            # 游戏联动: 击杀游戏里附近同种怪物
            self._game_link_kill_mob(self._current_mob)
            self._current_mob = None
            # 3秒后刷新
            self.root.after(3000, self._reset_mob_display2)
        else:
            # 怪物受伤, 反击
            self._update_mob_hp_bar2()
            mob_damage = mob_info["damage"]
            self._player_hp -= mob_damage
            self._combat_log_print(f"{mob_info['name']}反击，造成 {mob_damage} 点伤害")
            if self._player_hp <= 0:
                self._player_hp = self._player_max_hp
                self._combat_log_print("你死了！已复活")
                self._mob_name_label2.config(text="你死了!", fg="#ff0000")
                self._current_mob = None
                self._mob_canvas2.delete("all")
                self.root.after(3000, self._reset_mob_display2)
            self._update_player_hp_bar()
            self._play_sound(300, 50)

    def _update_mob_hp_bar2(self):
        """更新怪物血量条"""
        if not self._current_mob:
            return
        mob_info = self._MONSTERS[self._current_mob]
        max_hp = mob_info["hp"]
        ratio = max(0, self._current_mob_hp / max_hp)
        self._mob_hp_bar2.delete("all")
        self._mob_hp_bar2.create_rectangle(0, 0, 150 * ratio, 15, fill="#ff4444", outline="")
        self._mob_hp_text2.config(text=f"{self._current_mob_hp}/{max_hp}")

    def _update_player_hp_bar(self):
        """更新玩家血量条"""
        ratio = max(0, self._player_hp / self._player_max_hp)
        self._player_hp_bar.delete("all")
        self._player_hp_bar.create_rectangle(0, 0, 200 * ratio, 20, fill="#44ff44", outline="")
        self._player_hp_text.config(text=f"{self._player_hp}/{self._player_max_hp}")

    def _reset_mob_display2(self):
        """重置战斗页面怪物显示"""
        self._mob_name_label2.config(text="夜晚会刷怪", fg="#888")
        self._mob_hp_bar2.delete("all")
        self._mob_hp_text2.config(text="")
        self._mob_canvas2.delete("all")

    def _combat_log_print(self, msg):
        """战斗日志输出"""
        self._combat_log.config(state="normal")
        self._combat_log.insert("end", msg + "\n")
        self._combat_log.see("end")
        self._combat_log.config(state="disabled")

    def _execute_command2(self):
        """战斗页面执行指令"""
        cmd = self._cmd_entry2.get().strip()
        if not cmd.startswith("/"):
            self._combat_log_print("指令必须以 / 开头")
            return
        # 复用原来的指令执行逻辑, 但输出到战斗日志
        parts = cmd[1:].split()
        if not parts:
            return
        command = parts[0].lower()
        args = parts[1:]

        try:
            if command == "help":
                self._combat_log_print("指令: /give /time /gamemode /kill /heal /summon /xp /clear")
            elif command == "give":
                if args:
                    item = args[0].lower()
                    if item in self._WEAPONS:
                        self._current_weapon = item
                        weapon_keys = ["wood_sword", "stone_sword", "iron_sword", "diamond_sword", "netherite_sword"]
                        if item in weapon_keys:
                            idx = weapon_keys.index(item)
                            self._weapon_listbox.selection_clear(0, "end")
                            self._weapon_listbox.selection_set(idx)
                        self._combat_log_print(f"装备了 {self._WEAPONS[item]['name']}")
                    else:
                        amount = int(args[1]) if len(args) > 1 else 1
                        self._inventory[item] = self._inventory.get(item, 0) + amount
                        if item in self._inv_labels:
                            self._inv_labels[item].config(text=str(self._inventory[item]))
                        self._combat_log_print(f"获得 {amount} 个 {item}")
            elif command == "time":
                if args and args[0] == "set" and len(args) > 1:
                    if args[1] == "night":
                        self._is_night = True
                        self._combat_log_print("时间设为夜晚")
                        if not self._current_mob:
                            self._spawn_mob2()
                    elif args[1] == "day":
                        self._is_night = False
                        self._combat_log_print("时间设为白天")
            elif command == "kill":
                if self._current_mob:
                    self._current_mob_hp = 0
                    self._on_mob_click2()
                else:
                    self._combat_log_print("当前没有怪物")
            elif command == "heal":
                self._player_hp = self._player_max_hp
                self._update_player_hp_bar()
                self._combat_log_print("已恢复满血")
            elif command == "summon":
                if args and args[0] in ["zombie", "skeleton"]:
                    self._spawn_mob2(args[0])
                else:
                    self._spawn_mob2()
            elif command == "xp":
                if args:
                    self._add_xp(int(args[0]))
                    self._combat_log_print(f"获得 {args[0]} 经验")
            elif command == "clear":
                self._cmd_entry2.delete(0, "end")
            else:
                self._combat_log_print(f"未知指令: {command}")
        except Exception as e:
            self._combat_log_print(f"指令错误: {e}")
        self._cmd_entry2.delete(0, "end")

    # ---------------- 游戏联动 ----------------
    def _game_link_kill_mob(self, mob_type):
        """游戏联动: 击杀游戏里附近同种怪物"""
        if not hasattr(self, "_combat_link_enabled") or not self._combat_link_enabled.get():
            return
        try:
            mob_name_map = {"zombie": "zombie", "skeleton": "skeleton", "spider": "spider", "creeper": "creeper"}
            mc_mob = mob_name_map.get(mob_type, mob_type)
            ok, killed, msg = bridge.kill_nearby_mobs(mc_mob, radius=32)
            if ok:
                self._combat_log_print(f"游戏联动: {msg}")
            else:
                self._combat_log_print(f"游戏联动失败: {msg}")
        except Exception as e:
            self._combat_log_print(f"游戏联动异常: {e}")


    def _check_night_spawn(self):
        """检查是否是夜晚, 是则刷怪(战斗页面)"""
        try:
            if hasattr(self, "_is_night") and self._is_night and not self._current_mob:
                if random.random() < 0.3:
                    self._spawn_mob2()
        except Exception:
            pass
        self.root.after(10000, self._check_night_spawn)

    # ---------------- 指令系统 ----------------
    def _execute_command(self):
        """执行指令"""
        cmd = self._cmd_entry.get().strip()
        if not cmd.startswith("/"):
            self._cmd_result("指令必须以 / 开头")
            return
        parts = cmd[1:].split()
        if not parts:
            return
        command = parts[0].lower()
        args = parts[1:]

        try:
            if command == "help":
                self._cmd_result("可用指令: /give /time /gamemode /kill /heal /weather /xp /summon /clear")
            elif command == "give":
                self._cmd_give(args)
            elif command == "time":
                self._cmd_time(args)
            elif command == "gamemode":
                self._cmd_gamemode(args)
            elif command == "kill":
                if self._current_mob:
                    self._current_mob_hp = 0
                    self._on_mob_click()
                    self._cmd_result("已击杀当前怪物")
                else:
                    self._cmd_result("当前没有怪物")
            elif command == "heal":
                self._player_hp = self._player_max_hp
                self._player_hp_label.config(text=f"{self._player_hp}/{self._player_max_hp}")
                self._cmd_result("已恢复满血")
            elif command == "weather":
                self._cmd_weather(args)
            elif command == "xp":
                if args:
                    amount = int(args[0])
                    self._add_xp(amount)
                    self._cmd_result(f"获得 {amount} 经验")
                else:
                    self._cmd_result("用法: /xp <数量>")
            elif command == "summon":
                if args:
                    mob = args[0].lower()
                    if mob in ["zombie", "skeleton"]:
                        self._spawn_mob(mob)
                        self._cmd_result(f"已召唤 {mob}")
                    else:
                        self._cmd_result("未知怪物, 支持: zombie, skeleton")
                else:
                    self._spawn_mob()
                    self._cmd_result("已召唤随机怪物")
            elif command == "clear":
                self._cmd_entry.delete(0, "end")
            else:
                self._cmd_result(f"未知指令: {command}, 输入 /help 查看帮助")
        except Exception as e:
            self._cmd_result(f"指令执行失败: {e}")

    def _cmd_give(self, args):
        """/give 指令"""
        if not args:
            self._cmd_result("用法: /give <物品> [数量]")
            return
        item = args[0].lower()
        amount = int(args[1]) if len(args) > 1 else 1
        valid_items = list(self._inv_labels.keys()) + ["wood_sword", "stone_sword", "iron_sword",
                                                         "diamond_sword", "netherite_sword"]
        if item in valid_items:
            if item in self._WEAPONS:
                self._current_weapon = item
                weapon_info = self._WEAPONS[item]
                self._weapon_label.config(text=f"{weapon_info['icon']} {weapon_info['name']}",
                                           fg=weapon_info["color"])
                self._cmd_result(f"已装备 {weapon_info['name']}")
            else:
                self._inventory[item] = self._inventory.get(item, 0) + amount
                if item in self._inv_labels:
                    self._inv_labels[item].config(text=str(self._inventory[item]))
                self._cmd_result(f"获得 {amount} 个 {item}")
        else:
            self._cmd_result(f"未知物品: {item}")

    def _cmd_time(self, args):
        """/time 指令"""
        if not args:
            self._cmd_result("用法: /time set <day/night/数值>")
            return
        if args[0] == "set" and len(args) > 1:
            value = args[1].lower()
            if value == "day":
                self._is_night = False
                self._cmd_result("时间设为白天")
            elif value == "night":
                self._is_night = True
                self._cmd_result("时间设为夜晚, 怪物会生成")
                if not self._current_mob:
                    self._spawn_mob()
            else:
                try:
                    tick = int(value)
                    self._is_night = tick > 12000
                    self._cmd_result(f"时间设为 {tick}")
                    if self._is_night and not self._current_mob:
                        self._spawn_mob()
                except ValueError:
                    self._cmd_result("无效的时间值")
        else:
            self._cmd_result("用法: /time set <day/night/数值>")

    def _cmd_gamemode(self, args):
        """/gamemode 指令"""
        if not args:
            self._cmd_result("用法: /gamemode <creative/survival>")
            return
        mode = args[0].lower()
        if mode in ["creative", "1"]:
            self._combat_unlocked = True
            self._cmd_result("游戏模式: 创造模式 (无敌)")
        elif mode in ["survival", "0"]:
            self._combat_unlocked = False
            self._cmd_result("游戏模式: 生存模式")
        else:
            self._cmd_result("未知游戏模式")

    def _cmd_weather(self, args):
        """/weather 指令"""
        if not args:
            self._cmd_result("用法: /weather <clear/rain>")
            return
        weather = args[0].lower()
        if weather == "clear":
            self._cmd_result("天气已设为晴天")
        elif weather == "rain":
            self._cmd_result("天气已设为雨天")
        else:
            self._cmd_result("未知天气")

    def _cmd_result(self, msg):
        """显示指令执行结果"""
        self._cmd_entry.delete(0, "end")
        self._cmd_entry.insert(0, msg)
        self._cmd_entry.config(foreground="#00aa00")
        self.root.after(3000, lambda: self._cmd_entry.config(foreground="black"))

    def _villager_talk_random(self):
        """村民偶尔自己说话"""
        try:
            if random.random() < 0.35 and not self._pet_dialogue_active:
                self._villager_say(random.choice(self._VILLAGER_TALKS), 2500)
        except Exception:
            pass
        self.root.after(random.randint(10000, 18000), self._villager_talk_random)

    # ---------------- 宠物对话系统 ----------------
    # 苦力怕和村民之间的对话
    _PET_DIALOGUES = [
        # 苦力怕先说话
        {"speaker": "creeper", "text": "村民，你又骗我绿宝石了！",
         "responder": "villager", "response": "我没有，这是公平交易。"},
        {"speaker": "creeper", "text": "今天天气真好，适合炸人",
         "responder": "villager", "response": "别炸到我的房子，我刚修好。"},
        {"speaker": "creeper", "text": "你知道吗？我曾经也是个普通人",
         "responder": "villager", "response": "我也是，直到被僵尸咬了一口。"},
        {"speaker": "creeper", "text": "你们村民都是奸商",
         "responder": "villager", "response": "别这么说，我们只是价格公道。"},
        {"speaker": "creeper", "text": "下界好热，我想回家",
         "responder": "villager", "response": "我也想回家，我的田里还有小麦。"},
        {"speaker": "creeper", "text": "你觉得史蒂夫帅吗？",
         "responder": "villager", "response": "他是个好人，经常跟我交易。"},
        {"speaker": "creeper", "text": "我炸过的房子比你吃过的饭还多",
         "responder": "villager", "response": "我修过的房子比你炸过的还多。"},
        # 村民先说话
        {"speaker": "villager", "text": "苦力怕，你今天炸了几个？",
         "responder": "creeper", "response": "还没开张呢，你交易了几笔？"},
        {"speaker": "villager", "text": "你有绿宝石吗？我想要",
         "responder": "creeper", "response": "没有，我只有火药和TNT。"},
        {"speaker": "villager", "text": "村庄好远，我走累了",
         "responder": "creeper", "response": "我也累了，炸个人放松一下。"},
        {"speaker": "villager", "text": "你有小麦吗？我想做面包",
         "responder": "creeper", "response": "没有，我只有火药，你要吗？"},
        {"speaker": "villager", "text": "铁傀儡是我的好朋友",
         "responder": "creeper", "response": "我怕铁傀儡，它会打我。"},
        {"speaker": "villager", "text": "下雨天真好，庄稼会长得快",
         "responder": "creeper", "response": "我讨厌下雨，火药会湿。"},
        {"speaker": "villager", "text": "你知道吗？我昨天赚了10个绿宝石",
         "responder": "creeper", "response": "厉害，我昨天炸了5栋房子。"},
        # 闲聊
        {"speaker": "creeper", "text": "你觉得这个启动器好用吗？",
         "responder": "villager", "response": "还行吧，至少比HMCL强。"},
        {"speaker": "villager", "text": "你说用户会喜欢我们吗？",
         "responder": "creeper", "response": "当然，我们这么可爱。"},
        {"speaker": "creeper", "text": "我饿了，有火药吃吗？",
         "responder": "villager", "response": "我只有面包和绿宝石，你要吗？"},
        {"speaker": "villager", "text": "你知道Herobrine吗？",
         "responder": "creeper", "response": "别提他，他不存在。"},
    ]

    def _pet_dialogue_loop(self):
        """宠物对话循环: 随机触发苦力怕和村民之间的对话"""
        try:
            if not self._pet_dialogue_active and random.random() < 0.25:
                self._start_pet_dialogue()
        except Exception:
            pass
        self.root.after(random.randint(15000, 25000), self._pet_dialogue_loop)

    def _start_pet_dialogue(self):
        """开始一段宠物对话"""
        try:
            dialogue = random.choice(self._PET_DIALOGUES)
            self._pet_dialogue_active = True
            speaker = dialogue["speaker"]
            text = dialogue["text"]
            responder = dialogue["responder"]
            response = dialogue["response"]

            # 说话者先说
            if speaker == "creeper":
                self._creeper_say(text, 3000)
            else:
                self._villager_say(text, 3000)

            # 2.5秒后回应者回应
            def _respond():
                try:
                    if responder == "creeper":
                        self._creeper_say(response, 3000)
                    else:
                        self._villager_say(response, 3000)
                    # 3秒后结束对话
                    self.root.after(3000, lambda: setattr(self, "_pet_dialogue_active", False))
                except Exception:
                    self._pet_dialogue_active = False

            self.root.after(2500, _respond)
        except Exception:
            self._pet_dialogue_active = False

    def _open_ai_chat(self):
        """打开 AI 聊天对话框, 让玩家跟苦力怕和村民对话"""
        api_key = CONFIG.get("ai_api_key", "").strip()
        if not api_key:
            messagebox.showinfo("提示",
                "请先在设置页配置 AI API Key\n\n支持: 豆包 / Deepseek / Kimi")
            return

        chat_win = tk.Toplevel(self.root)
        chat_win.title("🤖 跟苦力怕和村民聊天")
        chat_win.geometry("560x520")
        chat_win.minsize(400, 350)
        chat_win.transient(self.root)

        # 先创建输入区域, 确保它在底部可见
        input_frame = ttk.Frame(chat_win)
        input_frame.pack(side="bottom", fill="x", padx=8, pady=(4, 8))

        input_entry = ttk.Entry(input_frame, font=("Microsoft YaHei", 10))
        input_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))

        send_btn = ttk.Button(input_frame, text="发送", width=8)
        send_btn.pack(side="right")

        # 再创建聊天记录区域
        history_frame = ttk.Frame(chat_win)
        history_frame.pack(side="top", fill="both", expand=True, padx=8, pady=(8, 4))

        history_text = tk.Text(history_frame, wrap="word", state="disabled",
                                font=("Microsoft YaHei", 10), bg="#f5f5f5")
        history_scroll = ttk.Scrollbar(history_frame, command=history_text.yview)
        history_text.configure(yscrollcommand=history_scroll.set)
        history_scroll.pack(side="right", fill="y")
        history_text.pack(side="left", fill="both", expand=True)

        history_text.tag_configure("player", foreground="#2980b9",
                                    font=("Microsoft YaHei", 10, "bold"))
        history_text.tag_configure("creeper", foreground="#27ae60",
                                    font=("Microsoft YaHei", 10, "bold"))
        history_text.tag_configure("villager", foreground="#8e44ad",
                                    font=("Microsoft YaHei", 10, "bold"))
        history_text.tag_configure("system", foreground="#888",
                                    font=("Microsoft YaHei", 9, "italic"))

        history_text.config(state="normal")
        history_text.insert("end", "苦力怕和村民正在等你聊天...\n\n", "system")
        history_text.config(state="disabled")

        chat_history = []

        def _append_message(role, text):
            history_text.config(state="normal")
            if role == "player":
                history_text.insert("end", "你: ", "player")
            elif role == "creeper":
                history_text.insert("end", "苦力怕: ", "creeper")
            elif role == "villager":
                history_text.insert("end", "村民: ", "villager")
            history_text.insert("end", text + "\n\n")
            history_text.see("end")
            history_text.config(state="disabled")

        def _send_message(event=None):
            user_msg = input_entry.get().strip()
            if not user_msg:
                return
            input_entry.delete(0, "end")
            _append_message("player", user_msg)
            chat_history.append({"role": "user", "content": user_msg})

            send_btn.config(state="disabled")
            input_entry.config(state="disabled")
            history_text.config(state="normal")
            history_text.insert("end", "苦力怕和村民正在思考...\n", "system")
            history_text.see("end")
            history_text.config(state="disabled")

            def _worker():
                try:
                    import ai_chat
                    ai_chat.ai_chat.set_provider(CONFIG.get("ai_provider", "doubao"))
                    ai_chat.ai_chat.set_api_key(CONFIG.get("ai_api_key", ""))
                    ok, reply = ai_chat.chat_with_pet("both", user_msg, chat_history)
                    if ok:
                        lines = [l.strip() for l in reply.split("\n") if l.strip()]
                        if len(lines) >= 2:
                            creeper_msg = lines[0].lstrip("苦力怕:").lstrip("苦力怕：").strip()
                            villager_msg = lines[1].lstrip("村民:").lstrip("村民：").strip()
                        elif len(lines) == 1:
                            creeper_msg = lines[0]
                            villager_msg = "..."
                        else:
                            creeper_msg = "嘶嘶..."
                            villager_msg = "..."
                        def _update_ui():
                            history_text.config(state="normal")
                            history_text.delete("end-2l", "end-1l")
                            history_text.config(state="disabled")
                            _append_message("creeper", creeper_msg)
                            _append_message("villager", villager_msg)
                            chat_history.append({"role": "assistant",
                                                 "content": "苦力怕: {}\n村民: {}".format(
                                                     creeper_msg, villager_msg)})
                            send_btn.config(state="normal")
                            input_entry.config(state="normal")
                            input_entry.focus_set()
                        self.root.after(0, _update_ui)
                    else:
                        def _update_err():
                            history_text.config(state="normal")
                            history_text.delete("end-2l", "end-1l")
                            history_text.insert("end", "AI 回复失败: {}\n".format(reply), "system")
                            history_text.see("end")
                            history_text.config(state="disabled")
                            send_btn.config(state="normal")
                            input_entry.config(state="normal")
                        self.root.after(0, _update_err)
                except Exception as exc:
                    def _update_exc():
                        history_text.config(state="normal")
                        history_text.delete("end-2l", "end-1l")
                        history_text.insert("end", "出错了: {}\n".format(exc), "system")
                        history_text.see("end")
                        history_text.config(state="disabled")
                        send_btn.config(state="normal")
                        input_entry.config(state="normal")
                    self.root.after(0, _update_exc)

            self._thread(_worker)

        send_btn.config(command=_send_message)
        input_entry.bind("<Return>", _send_message)
        input_entry.focus_set()

        chat_win.wait_window()

    # ---------------- 音效 ----------------
    def _play_sound(self, freq, duration=60):
        """播放单个蜂鸣音效(线程中播放避免卡UI)"""
        def _play():
            try:
                winsound.Beep(freq, duration)
            except Exception:
                pass
        threading.Thread(target=_play, daemon=True).start()

    def _play_click(self):
        """普通点击音效"""
        self._play_sound(880, 40)

    def _play_launch(self):
        """启动游戏音效: 上升音阶 C-E-G"""
        def _seq():
            try:
                for f in (523, 659, 784):
                    winsound.Beep(f, 80)
                    time.sleep(0.02)
            except Exception:
                pass
        threading.Thread(target=_seq, daemon=True).start()

    def _play_achievement(self):
        """成就解锁音效: 上升音阶 C-E-G-C-E"""
        def _seq():
            try:
                for f in (523, 659, 784, 1047, 1319):
                    winsound.Beep(f, 70)
                    time.sleep(0.02)
            except Exception:
                pass
        threading.Thread(target=_seq, daemon=True).start()

    def _play_explosion(self):
        """苦力怕爆炸音效: 优先用从 Minecraft assets 提取的真实音效"""
        try:
            game_dir = CONFIG.get("game_dir")
            sounds.play_creeper_explosion(game_dir)
        except Exception:
            # 回退: winsound 合成
            self._play_sound(200, 100)

    # ---------------- 成就系统 ----------------
    def _unlock_achievement(self, ach_id):
        """解锁成就, 新解锁时显示右下角弹窗"""
        try:
            is_new, ach = self.ach_mgr.unlock(ach_id)
            if is_new and ach:
                self._post("achievement", ach)
        except Exception:
            pass

    def _show_achievement_popup(self, ach):
        """Steam 风格右下角成就解锁通知"""
        self._play_achievement()
        try:
            popup = tk.Toplevel(self.root)
            popup.overrideredirect(True)  # 无边框
            popup.attributes("-topmost", True)
            popup.configure(bg="#1a1a2e")

            # 内容
            frame = tk.Frame(popup, bg="#1a1a2e", padx=12, pady=10)
            frame.pack()
            tk.Label(frame, text="🏆 成就解锁！", font=("Arial", 9, "bold"),
                     fg="#ffd700", bg="#1a1a2e").pack(anchor="w")
            tk.Label(frame, text="{} {}".format(ach.get("icon", "🎮"),
                                                  ach.get("name", "")),
                     font=("Arial", 11, "bold"), fg="#ffffff",
                     bg="#1a1a2e").pack(anchor="w", pady=(2, 0))
            tk.Label(frame, text=ach.get("desc", ""), font=("Arial", 9),
                     fg="#aaaaaa", bg="#1a1a2e", wraplength=220,
                     justify="left").pack(anchor="w", pady=(2, 0))

            # 定位到右下角(堆叠显示多个)
            self.root.update_idletasks()
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            pw = 260
            ph = 90
            offset = len(self._ach_popups) * (ph + 10)
            x = sw - pw - 20
            y = sh - ph - 20 - offset
            popup.geometry("{}x{}+{}+{}".format(pw, ph, x, y))

            self._ach_popups.append(popup)
            # 4 秒后自动消失
            popup.after(4000, lambda: self._close_ach_popup(popup))
        except Exception:
            pass

    def _close_ach_popup(self, popup):
        """关闭成就弹窗"""
        try:
            if popup in self._ach_popups:
                self._ach_popups.remove(popup)
            popup.destroy()
        except Exception:
            pass

    def _show_achievements(self):
        """显示成就列表窗口"""
        try:
            win = tk.Toplevel(self.root)
            win.title("成就列表 ({}/{})".format(
                self.ach_mgr.get_unlocked_count(),
                self.ach_mgr.get_total_count()))
            win.geometry("520x480")
            win.configure(bg="#2b2b2b")

            # 滚动区域
            canvas = tk.Canvas(win, bg="#2b2b2b", highlightthickness=0)
            sb = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
            inner = tk.Frame(canvas, bg="#2b2b2b")
            inner.bind("<Configure>",
                       lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.create_window((0, 0), window=inner, anchor="nw")
            canvas.configure(yscrollcommand=sb.set)
            canvas.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
            sb.pack(side="right", fill="y", pady=8)

            all_ach = self.ach_mgr.get_all()
            for ach in all_ach:
                row = tk.Frame(inner, bg="#3a3a3a" if ach["unlocked"] else "#222222",
                               padx=10, pady=8)
                row.pack(fill="x", padx=8, pady=3)
                tk.Label(row, text=ach.get("icon", "🎮"),
                         font=("Arial", 20), bg=row["bg"]).pack(side="left", padx=(0, 10))
                info = tk.Frame(row, bg=row["bg"])
                info.pack(side="left", fill="x", expand=True)
                name_color = "#ffd700" if ach["unlocked"] else "#666666"
                tk.Label(info, text=ach["name"], font=("Arial", 11, "bold"),
                         fg=name_color, bg=row["bg"]).pack(anchor="w")
                tk.Label(info, text=ach["desc"], font=("Arial", 9),
                         fg="#999999" if ach["unlocked"] else "#555555",
                         bg=row["bg"], wraplength=380, justify="left").pack(anchor="w")
                if ach["unlocked"]:
                    tk.Label(info, text="✅ 解锁于 " + ach.get("unlocked_at", ""),
                             font=("Arial", 8), fg="#66cc66",
                             bg=row["bg"]).pack(anchor="w", pady=(2, 0))
                else:
                    tk.Label(info, text="🔒 未解锁", font=("Arial", 8),
                             fg="#666666", bg=row["bg"]).pack(anchor="w", pady=(2, 0))
        except Exception:
            pass

    def _browse_gamedir(self):
        d = filedialog.askdirectory(initialdir=CONFIG.get("game_dir"),
                                    title="选择游戏根目录")
        if d:
            self.setting_gamedir.delete(0, "end")
            self.setting_gamedir.insert(0, d)

    def _test_ai_connection(self):
        """测试 AI API 连接, 自动检测服务商"""
        api_key = self.setting_ai_key.get().strip()
        if not api_key:
            messagebox.showwarning("提示", "请先输入 API Key")
            return
        try:
            import ai_chat
            ai_chat.ai_chat.set_api_key(api_key)
        except Exception as exc:
            messagebox.showerror("错误", "初始化失败: " + str(exc))
            return

        def _worker():
            try:
                # 先尝试当前选中的服务商
                provider_reverse = {"豆包": "doubao", "Deepseek": "deepseek", "Kimi": "kimi"}
                current_provider = provider_reverse.get(self.setting_ai_provider.get(), "doubao")
                ai_chat.ai_chat.set_provider(current_provider)
                ok, msg = ai_chat.ai_chat.test_connection()
                if ok:
                    self._post("msg", ("连接成功",
                        "当前服务商连接正常！\n回复: " + msg[:100]))
                    return
                # 当前服务商失败, 自动检测
                self._post("status", "当前服务商连接失败, 正在自动检测...")
                detect_ok, detect_result = ai_chat.ai_chat.auto_detect_provider(api_key)
                if detect_ok:
                    # 检测成功, 自动选中正确的服务商
                    provider_map = {"doubao": "豆包", "deepseek": "Deepseek", "kimi": "Kimi"}
                    provider_name = provider_map.get(detect_result, detect_result)
                    def _update_ui():
                        self.setting_ai_provider.set(provider_name)
                    self.root.after(0, _update_ui)
                    self._post("msg", ("自动检测成功",
                        "检测到这个 Key 属于: " + provider_name + "\n\n已自动选中，连接成功！"))
                else:
                    self._post("err", ("连接失败",
                        "三个服务商都连接失败。\n\n请检查: \n1. API Key 是否正确\n2. 网络是否正常\n3. Key 是否还有余额\n\n错误: " + str(detect_result)[:200]))
            except Exception as exc:
                self._post("err", ("连接失败", str(exc)))
        self._thread(_worker)

    def _update_theme_desc(self):
        """更新主题描述标签"""
        if not hasattr(self, "theme_desc_label"):
            return
        key = self.theme_var.get() if hasattr(self, "theme_var") else "default"
        theme = themes.get_theme(key)
        self.theme_desc_label.config(text="{} - {}".format(theme["name"], theme["desc"]))

    def _on_theme_selected(self, event=None):
        """主题选中立即生效"""
        key = self.theme_var.get()
        CONFIG.set("theme", key)
        self._update_theme_desc()
        self._apply_launch_background()

    def _browse_background(self):
        path = filedialog.askopenfilename(
            title="选择背景图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp *.gif"),
                       ("所有文件", "*.*")])
        if path:
            self.setting_bg.delete(0, "end")
            self.setting_bg.insert(0, path)
            CONFIG.set("background_image", path)
            self._apply_launch_background()

    def _clear_background(self):
        self.setting_bg.delete(0, "end")
        CONFIG.set("background_image", None)
        self._apply_launch_background()

    def _install_bridge_mod(self):
        """把联动 Mod 复制到当前实例的 mods 文件夹"""
        inst = self.current_instance
        if not inst:
            messagebox.showwarning("提示", "请先选择实例")
            return
        # 查找编译好的 Mod jar: 优先 EXE 所在目录, 然后项目目录
        candidates = []
        exe_dir = Path(sys.executable).parent
        for jar in exe_dir.glob("voxellauncher-bridge*.jar"):
            candidates.append(jar)
        dist_dir = Path(__file__).parent / "dist"
        if dist_dir.exists():
            for jar in dist_dir.glob("voxellauncher-bridge*.jar"):
                candidates.append(jar)
        bridge_dir = Path(__file__).parent / "voxellauncher-bridge" / "build" / "libs"
        if bridge_dir.exists():
            for jar in bridge_dir.glob("*.jar"):
                if "sources" not in jar.name and "dev" not in jar.name:
                    candidates.append(jar)
        # 选版本号最高的
        mod_jar = None
        if candidates:
            import re
            def vkey(p):
                m = re.search(r'(\d+)\.(\d+)\.(\d+)', p.name)
                return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else (0,0,0)
            candidates.sort(key=vkey, reverse=True)
            mod_jar = candidates[0]
        # 4. 都找不到, 让用户手动选择
        if not mod_jar:
            messagebox.showinfo("提示",
                "未自动找到联动 Mod jar 文件。" + chr(10) +
                "请手动选择 voxellauncher-bridge-1.0.0.jar 文件")
            mod_jar_path = filedialog.askopenfilename(
                title="选择联动 Mod jar 文件",
                filetypes=[("Mod 文件", "*.jar"), ("所有文件", "*.*")])
            if not mod_jar_path:
                return
            mod_jar = Path(mod_jar_path)
        # 复制到实例 mods 文件夹(用 get_instance_game_dir 获取正确路径)
        game_dir = instance_mod.get_instance_game_dir(inst)
        mods_dir = Path(game_dir) / "mods"
        mods_dir.mkdir(parents=True, exist_ok=True)
        # 先删除旧版本
        for old in mods_dir.glob("voxellauncher-bridge*.jar"):
            if old.name != mod_jar.name:
                try:
                    old.unlink()
                except Exception:
                    pass
        dest = mods_dir / mod_jar.name
        shutil.copy2(mod_jar, dest)
        messagebox.showinfo("安装成功",
            "联动 Mod " + mod_jar.name + " 已安装到:" + chr(10) + str(dest) + chr(10) + chr(10) +
            "重启游戏后生效。支持挖矿联动和战斗击杀联动。")


    def _test_bridge(self):
        """测试联动 Mod 连接"""
        inst = self.current_instance
        # 先检查 Mod 文件是否已安装到当前实例
        mod_installed = False
        if inst:
            game_dir = instance_mod.get_instance_game_dir(inst)
            mods_dir = Path(game_dir) / "mods"
            if mods_dir.exists():
                for jar in mods_dir.glob("voxellauncher-bridge*.jar"):
                    mod_installed = True
                    break
        if not mod_installed:
            messagebox.showwarning("Mod 未安装",
                "当前实例还没有安装联动 Mod！" + chr(10) + chr(10) +
                "请先点「安装联动Mod」按钮，" + chr(10) +
                "然后重启游戏，进入世界后再测试连接。")
            return
        # 再检查游戏是否运行
        running = bridge.is_bridge_running()
        if running:
            messagebox.showinfo("连接成功",
                "联动 Mod 运行正常，游戏已就绪！" + chr(10) +
                "现在在启动器挖矿，物品会实时发送到游戏背包！")
        else:
            messagebox.showwarning("游戏未运行",
                "Mod 已安装，但游戏还没启动！" + chr(10) + chr(10) +
                "请：" + chr(10) +
                "1. 启动游戏（确保是当前实例）" + chr(10) +
                "2. 进入一个世界" + chr(10) +
                "3. 再回来点「测试连接」" + chr(10) + chr(10) +
                "注意：安装 Mod 后需要重启游戏才能生效！")

    def _try_send_to_game(self, item_id, count=1):
        """尝试把物品发送到游戏(如果联动开启且游戏在运行)"""
        if not CONFIG.get("bridge_enabled", False):
            return False
        try:
            ok, msg = bridge.send_item(item_id, count)
            if ok:
                self._post("log", f"[联动] 已发送 {count} 个 {item_id} 到游戏背包")
                return True
        except Exception:
            pass
        return False

    def _save_settings(self):
        gd = self.setting_gamedir.get().strip()
        if gd:
            CONFIG.set("game_dir", gd)
        src = self.setting_source.get()
        CONFIG.set("download_source",
                   "mojang" if src.startswith("mojang") else "bmclapi")
        try:
            threads = int(self.setting_threads.get())
            CONFIG.set("download_threads", max(1, min(50, threads)))
        except Exception:
            pass
        # 保存背景图片
        bg = self.setting_bg.get().strip()
        CONFIG.set("background_image", bg if bg else None)
        # 保存主题
        if hasattr(self, "theme_var"):
            CONFIG.set("theme", self.theme_var.get())
        # 保存代理
        if hasattr(self, "setting_proxy"):
            CONFIG.set("proxy", self.setting_proxy.get().strip())
        self._apply_launch_background()
        # 保存联动开关
        CONFIG.set("bridge_enabled", self.bridge_var.get())
        try:
            w, h = self.setting_res.get().split(",")
            CONFIG.set("width", int(w.strip()))
            CONFIG.set("height", int(h.strip()))
        except Exception:
            pass
        CONFIG.set("extra_jvm_args", self.setting_jvm.get())
        # 保存 CurseForge 密钥并按密钥刷新页签显隐
        CONFIG.set("cf_api_key", self.setting_cfkey.get().strip())
        self._apply_cf_tab()
        # 保存微软 Client ID
        CONFIG.set("ms_client_id", self.setting_mscid.get().strip())
        # 保存 AI 配置
        provider_reverse = {"豆包": "doubao", "Deepseek": "deepseek", "Kimi": "kimi"}
        ai_provider = provider_reverse.get(self.setting_ai_provider.get(), "doubao")
        CONFIG.set("ai_provider", ai_provider)
        CONFIG.set("ai_api_key", self.setting_ai_key.get().strip())
        # 同步到 ai_chat 模块
        try:
            import ai_chat
            ai_chat.ai_chat.set_provider(ai_provider)
            ai_chat.ai_chat.set_api_key(self.setting_ai_key.get().strip())
        except Exception:
            pass
        # 保存日志窗口显示开关并立即应用
        show_log = self.setting_show_log.get()
        CONFIG.set("show_log_window", "true" if show_log else "false")
        self._apply_log_visibility(show_log)
        messagebox.showinfo("设置", "设置已保存")
        self._reload_instances()

    # ---------------- 彩蛋: 千万别点按钮(混乱模式) ----------------
    _CHAOS_TITLES = [
        "VoxelLauncher Pro Max Ultra 至尊版",
        "VoxelLauncher - 已被黑客入侵",
        "VoxelLauncher - 系统崩溃中...",
        "VoxelLauncher - 你妈妈叫你吃饭了",
        "VoxelLauncher - 正在删除 System32",
        "VoxelLauncher - 恭喜你中奖了!",
        "VoxelLauncher - 别再点了",
        "VoxelLauncher - 我已经不正常了",
        "VoxelLauncher - 启动器の怨念",
        "VoxelLauncher - 你点了不该点的东西",
    ]
    _CHAOS_BTN_TEXTS = [
        "别点我", "你确定？", "真的要启动吗？", "启动个屁",
        "再点试试", "我拒绝工作", "系统罢工中", "你谁啊",
        "不认识你", "密码错误", "访问被拒绝", "404 Not Found",
    ]
    _CHAOS_LOGS = [
        "[警告] 检测到用户智商不足, 启动器拒绝服务",
        "[错误] java.lang.StupidUserException: 用户太蠢了",
        "[系统] 正在格式化 C 盘... 进度: 47%",
        "[警告] 发现未知生物: 一只野生的程序猿",
        "[错误] 无法启动游戏: 今天不宜玩游戏",
        "[系统] 你已经被启动器拉黑了",
        "[警告] 检测到键盘进水, 请把脑子擦干再试",
        "[错误] OutOfMemoryError: 脑子内存不足",
        "[系统] 恭喜你触发了隐藏结局: 启动器疯了",
        "[警告] 此按钮已被诅咒, 点过的人都会变帅",
    ]
    _CHAOS_MSGS = [
        ("系统警告", "检测到你是一个大笨蛋, 游戏拒绝启动。"),
        ("重要通知", "你的电脑已被启动器绑架, 请支付 1 个比特币赎金。"),
        ("恭喜中奖", "你是第 99999 位点击此按钮的用户, 奖品是: 什么都没有。"),
        ("系统崩溃", "错误代码: 0xCAFEBABE - 你把启动器搞坏了, 开心吗？"),
        ("神秘提示", "其实这个按钮什么用都没有, 你被骗了。"),
        ("警告", "再点一次我就真的不正常了。"),
    ]

    def _do_not_click(self):
        """千万别点按钮: 触发混乱模式(纯搞笑, 重启恢复)"""
        self._unlock_achievement("brave_soul")
        if getattr(self, "_chaos_mode", False):
            # 已经在混乱模式, 再点就弹更离谱的提示
            title, msg = random.choice(self._CHAOS_MSGS)
            messagebox.showwarning(title, msg)
            return
        self._chaos_mode = True
        self._chaos_tick_count = 0
        # 首次点击弹一个吓人的提示
        messagebox.showerror("严重错误",
                             "你点了不该点的按钮!\n\n启动器已进入异常模式, "
                             "所有功能可能不正常。\n\n解决方法: 重启启动器。")
        self._log("=== 你触发了混乱模式! 重启启动器可恢复 ===")
        self._chaos_tick()

    def _chaos_tick(self):
        """混乱模式定时 tick: 随机触发各种搞笑效果(降低密度避免UI卡死)"""
        if not getattr(self, "_chaos_mode", False):
            return
        self._chaos_tick_count += 1
        try:
            root = self.root
            # 1. 随机改窗口标题
            if random.random() < 0.25:
                root.title(random.choice(self._CHAOS_TITLES))
            # 2. 随机改启动按钮文字
            if random.random() < 0.3:
                self.launch_btn.config(text=random.choice(self._CHAOS_BTN_TEXTS))
            # 3. 随机改"千万别点"按钮文字
            if random.random() < 0.2:
                self._chaos_btn.config(text=random.choice(
                    ["我都说了别点", "你还点?", "够了!", "停!", "你有病吧"]))
            # 4. 窗口小幅度抖动(幅度减小, 避免太晕)
            if random.random() < 0.15:
                try:
                    x = root.winfo_x() + random.randint(-4, 4)
                    y = root.winfo_y() + random.randint(-4, 4)
                    root.geometry("+{}+{}".format(x, y))
                except Exception:
                    pass
            # 5. 随机输出搞笑日志
            if random.random() < 0.25:
                self._log(random.choice(self._CHAOS_LOGS))
            # 6. 每 20 tick 弹一个搞笑提示(约24秒一次, 避免弹窗堆叠卡死)
            if self._chaos_tick_count % 20 == 0 and \
               not getattr(self, "_chaos_msg_open", False):
                self._chaos_msg_open = True
                title, msg = random.choice(self._CHAOS_MSGS)
                messagebox.showinfo(title, msg)
                self._chaos_msg_open = False
            # 7. 随机改 tab 标签(倒序)
            if random.random() < 0.1:
                try:
                    tabs = self.nb.tabs()
                    if tabs:
                        idx = random.randint(0, len(tabs) - 1)
                        original = self.nb.tab(tabs[idx], "text")
                        if not original.endswith("  ") and len(original) < 20:
                            self.nb.tab(tabs[idx], text=original[::-1])
                except Exception:
                    pass
        except Exception:
            pass
        # 每 1200ms 触发一次(拉长间隔避免UI卡死)
        self.root.after(1200, self._chaos_tick)

    # ---------------- 启动 ----------------
    def _launch(self):
        # 搞笑: 点击启动按钮时随机改变按钮文字
        _funny_launch = ["正在启动...", "你确定？", "真的要启动吗？",
                          "启动个屁", "再想想", "我拒绝", "算了吧",
                          "正在召唤 Herobrine...", "苦力怕同意了吗？",
                          "Notch 保佑..."]
        self.launch_btn.config(text=random.choice(_funny_launch))
        self._play_launch()
        acct = self._selected_account()
        if not acct:
            messagebox.showwarning("提示", "请先添加/选择账号")
            return
        inst = self.current_instance
        if not inst:
            messagebox.showwarning("提示", "请先选择实例")
            return
        java = self._selected_java()
        if not java:
            messagebox.showwarning("提示", "请先选择 Java")
            return
        # 把界面上内存同步到实例
        try:
            min_m = int(self.min_mem.get())
            max_m = int(self.max_mem.get())
        except Exception:
            min_m, max_m = 512, 2048
        instance_mod.update_instance(inst["name"], min_memory=min_m,
                                     max_memory=max_m)
        inst = instance_mod.get_instance(inst["name"])
        # 保证 game_dir 字段(合并模式用版本文件夹, 分离模式用 instances/{name}/)
        inst["game_dir"] = instance_mod.get_instance_game_dir(inst)

        self._post("log", "=== 准备启动 {} / {} ===".format(
            inst["name"], inst["version_id"]))
        self._post("status", "启动中...")

        # 成就检测: 启动相关
        self._unlock_achievement("first_launch")
        # 玩家状态: 启动游戏 +经验 +统计
        try:
            leveled, new_lv = self.player.on_game_launch()
            self._update_player_level_display()
            if leveled:
                self._post("log", f"升级了！当前等级: Lv.{new_lv}")
        except Exception:
            pass
        # 凌晨2点后启动
        hour = datetime.now().hour
        if hour >= 2 and hour < 6:
            self._unlock_achievement("night_owl")
        # 内存8G以上
        if max_m >= 8192:
            self._unlock_achievement("rich_guy")
        # 无mod启动
        mods_dir = instance_mod.instance_subdir(inst["name"], "mods")
        try:
            jar_count = len([f for f in os.listdir(mods_dir) if f.endswith(".jar")])
        except Exception:
            jar_count = 0
        if jar_count == 0:
            self._unlock_achievement("minimalist")
        elif jar_count >= 10:
            self._unlock_achievement("mod_master")

        # 显示 Forge 风格加载窗口(锤子打铁 + 废话提示)
        self._loading_win = ForgeLoadingScreen(self.root, inst["version_id"])
        self._loading_win.set_progress(5)
        self._loading_win.set_stage("正在解析版本信息...")
        self._load_start_time = time.time()
        self._game_window_created = False
        self._game_window_time = None
        self._loading_close_scheduled = False

        # 日志关键词 -> 进度映射(根据 Minecraft 启动日志粗略估计)
        _log_progress = [
            ("Setting user", 62, "正在设置玩家..."),
            ("LWJGL", 72, "正在初始化图形引擎..."),
            ("OpenGL", 72, "正在初始化图形引擎..."),
            ("Created: ", 80, "正在创建游戏窗口..."),
            ("Sound engine", 85, "正在初始化音效..."),
            ("sound engine", 85, "正在初始化音效..."),
            ("Reloading", 90, "正在加载资源..."),
            ("resource", 90, "正在加载资源..."),
            ("Narrator", 93, "正在初始化语音..."),
            ("Stopping!", 97, "游戏正在退出..."),
        ]
        # 触发"游戏窗口已创建"的关键词(检测到后开始倒计时关闭)
        _window_created_keywords = ("Created: ", "Sound engine", "sound engine",
                                     "Reloading", "Narrator")
        _last_progress = [5]  # 用列表以便在闭包中修改

        def _log_with_progress(line):
            self._post("log", line)
            # 根据日志关键词推进进度
            lw = self._loading_win
            if lw and not lw._closed:
                for keyword, prog, stage in _log_progress:
                    if keyword in line and prog > _last_progress[0]:
                        _last_progress[0] = prog
                        lw.set_progress(prog)
                        lw.set_stage(stage)
                        break
                # 检测游戏窗口创建, 标记开始倒计时关闭
                if not self._game_window_created:
                    for kw in _window_created_keywords:
                        if kw in line:
                            self._game_window_created = True
                            self._game_window_time = time.time()
                            lw.set_stage("游戏窗口已创建，正在加载资源...")
                            break
                # 没有匹配关键词时, 缓慢推进(最多到 94%)
                if _last_progress[0] < 94 and random.random() < 0.15:
                    _last_progress[0] = min(94, _last_progress[0] + random.uniform(0.3, 1.2))
                    lw.set_progress(_last_progress[0])

        def _worker():
            try:
                lw = self._loading_win
                if lw:
                    lw.set_progress(25)
                    lw.set_stage("正在校验游戏文件...")
                # 自动加入服务器: 从输入框读取
                auto_server = self.auto_join_server_var.get().strip()
                if auto_server:
                    self._join_server_address = auto_server
                    self._post("log", "自动加入服务器: " + auto_server)
                else:
                    self._join_server_address = None

                proc = launcher.launch_game(
                    inst, acct, java,
                    log_cb=_log_with_progress,
                    on_exit=lambda: self._post("game_exited", None),
                    server_address=getattr(self, "_join_server_address", None))
                self.game_proc = proc
                self._post("game_started", None)
                # 进程已启动但不立即关窗口, 由 _check_loading_close 调度关闭
                if getattr(self, "_loading_win", None):
                    self._loading_win.set_stage("Java 进程已启动，等待游戏窗口...")
                self._schedule_loading_close()
            except Exception as exc:
                # 启动失败立即关闭
                if getattr(self, "_loading_win", None):
                    self._loading_win.close()
                    self._loading_win = None
                self._post("log", "启动失败: " + str(exc))
                self._post("err", ("启动失败", str(exc)))
                self._post("status", "启动失败")
                self._post("game_exited", None)
        self._thread(_worker)

    def _schedule_loading_close(self):
        """调度检查: 满足条件时关闭加载窗口(最少6秒, 窗口创建后再等3秒, 最多30秒)"""
        if self._loading_close_scheduled:
            return
        self._loading_close_scheduled = True
        self._check_loading_close()

    def _check_loading_close(self):
        """定期检查是否可以关闭加载窗口"""
        lw = getattr(self, "_loading_win", None)
        if not lw or lw._closed:
            self._loading_close_scheduled = False
            return
        elapsed = time.time() - self._load_start_time
        MIN_DISPLAY = 6.0   # 最少显示6秒
        WAIT_AFTER_WINDOW = 3.0  # 窗口创建后再等3秒
        MAX_WAIT = 30.0     # 最多等30秒

        can_close = False
        if self._game_window_created and self._game_window_time:
            since_window = time.time() - self._game_window_time
            if since_window >= WAIT_AFTER_WINDOW and elapsed >= MIN_DISPLAY:
                can_close = True
        if elapsed >= MAX_WAIT:
            can_close = True

        if can_close:
            lw.set_progress(100)
            lw.set_stage("锻造完成！游戏已启动")
            lw.close()
            self._loading_win = None
            self._loading_close_scheduled = False
        else:
            self.root.after(500, self._check_loading_close)

    def _export_script(self):
        """导出 .bat 启动脚本, 双击即可启动游戏无需打开启动器"""
        acct = self._selected_account()
        if not acct:
            messagebox.showwarning("提示", "请先添加/选择账号")
            return
        inst = self.current_instance
        if not inst:
            messagebox.showwarning("提示", "请先选择实例")
            return
        java = self._selected_java()
        if not java:
            messagebox.showwarning("提示", "请先选择 Java")
            return
        # 同步内存设置到实例
        try:
            min_m = int(self.min_mem.get())
            max_m = int(self.max_mem.get())
        except Exception:
            min_m, max_m = 512, 2048
        instance_mod.update_instance(inst["name"], min_memory=min_m,
                                     max_memory=max_m)
        inst = instance_mod.get_instance(inst["name"])
        inst["game_dir"] = str(instance_mod.instance_dir(inst["name"]))

        # 默认保存到桌面, 文件名含版本号
        default_name = "启动 {}.bat".format(inst["version_id"])
        desktop = Path.home() / "Desktop"
        initial_dir = str(desktop) if desktop.exists() else str(Path.home())
        path = filedialog.asksaveasfilename(
            title="导出启动脚本",
            initialdir=initial_dir,
            initialfile=default_name,
            defaultextension=".bat",
            filetypes=[("Windows 批处理", "*.bat")])
        if not path:
            return

        def _worker():
            try:
                out = launcher.export_launch_script(inst, acct, java, path)
                self._post("log", "启动脚本已导出: " + out)
                self._post("script_exported", out)
            except Exception as exc:
                self._post("log", "导出脚本失败: " + str(exc))
                self._post("err", ("导出失败", str(exc)))
        self._thread(_worker)

    def _open_instance_folder(self):
        """打开当前实例的游戏目录(instances里的版本文件夹)"""
        try:
            inst = self.current_instance
            if not inst:
                self._log("未选择实例")
                return
            game_dir = instance_mod.get_instance_game_dir(inst)
            import os
            if os.path.exists(game_dir):
                os.startfile(game_dir)
                self._log(f"已打开实例文件夹: {game_dir}")
            else:
                self._log(f"实例文件夹不存在: {game_dir}")
        except Exception as e:
            self._log(f"打开实例文件夹失败: {e}")

    def _stop_game(self):
        if self.game_proc:
            self.game_proc.stop()
            self._log("=== 已请求停止游戏 ===")






    # ---------------- 合成系统 ----------------
    def _open_crafting(self):
        """合成系统对话框 - 3x3合成台 + 物品栏 + 配方库 + 自定义皮肤"""
        import game_assets

        dlg = tk.Toplevel(self.root)
        dlg.title("⚒ 合成系统")
        dlg.geometry("850x750")
        dlg.minsize(800, 700)
        dlg.transient(self.root)
        dlg.grab_set()

        # 获取当前实例的 MC 版本, 用于提取纹理
        mc_version = "1.20.1"
        mc_dir = str(Path.home() / "AppData" / "Roaming" / ".minecraft")
        try:
            inst_name = self.inst_combo.get()
            if inst_name:
                inst = instance_mod.get_instance(inst_name)
                mc_version = inst.get("mc_version", "1.20.1")
                game_dir = instance_mod.get_instance_game_dir(inst_name)
                if game_dir:
                    mc_dir = str(Path(game_dir).parent.parent)
        except Exception:
            pass
        cache_dir = str(Path.home() / "AppData" / "Roaming" / ".voxellauncher" / "cache")

        # 玩家背包(从配置读取, 或者用默认物品)
        default_items = {
            "oak_planks": 32, "stick": 16, "cobblestone": 32,
            "iron_ingot": 16, "gold_ingot": 8, "diamond": 4,
            "coal": 32, "wooden_pickaxe": 1, "bread": 10,
            "torch": 32, "leather": 8, "string": 16,
            "wheat": 16, "feather": 8, "bone": 4,
        }
        if not hasattr(self, "_craft_inventory") or not self._craft_inventory:
            saved = CONFIG.get("craft_inventory", {})
            if saved:
                self._craft_inventory = saved
            else:
                self._craft_inventory = dict(default_items)
                CONFIG.set("craft_inventory", self._craft_inventory)

        # 合成配方(简化版, 常用配方)
        recipes = [
            # 工具
            {"name": "木镐", "result": "wooden_pickaxe", "count": 1,
             "pattern": ["PPP", " S ", " S "], "items": {"P": "oak_planks", "S": "stick"}},
            {"name": "石镐", "result": "stone_pickaxe", "count": 1,
             "pattern": ["CCC", " S ", " S "], "items": {"C": "cobblestone", "S": "stick"}},
            {"name": "铁镐", "result": "iron_pickaxe", "count": 1,
             "pattern": ["III", " S ", " S "], "items": {"I": "iron_ingot", "S": "stick"}},
            {"name": "金镐", "result": "golden_pickaxe", "count": 1,
             "pattern": ["GGG", " S ", " S "], "items": {"G": "gold_ingot", "S": "stick"}},
            {"name": "钻石镐", "result": "diamond_pickaxe", "count": 1,
             "pattern": ["DDD", " S ", " S "], "items": {"D": "diamond", "S": "stick"}},
            # 武器
            {"name": "木剑", "result": "wooden_sword", "count": 1,
             "pattern": [" P ", " P ", " S "], "items": {"P": "oak_planks", "S": "stick"}},
            {"name": "铁剑", "result": "iron_sword", "count": 1,
             "pattern": [" I ", " I ", " S "], "items": {"I": "iron_ingot", "S": "stick"}},
            {"name": "钻石剑", "result": "diamond_sword", "count": 1,
             "pattern": [" D ", " D ", " S "], "items": {"D": "diamond", "S": "stick"}},
            # 方块/物品
            {"name": "工作台", "result": "crafting_table_item", "count": 1,
             "pattern": ["PP", "PP"], "items": {"P": "oak_planks"}},
            {"name": "熔炉", "result": "furnace_item", "count": 1,
             "pattern": ["CCC", "C C", "CCC"], "items": {"C": "cobblestone"}},
            {"name": "箱子", "result": "chest_item", "count": 1,
             "pattern": ["PPP", "P P", "PPP"], "items": {"P": "oak_planks"}},
            {"name": "木棍", "result": "stick", "count": 4,
             "pattern": ["P", "P"], "items": {"P": "oak_planks"}},
            {"name": "火把", "result": "torch", "count": 4,
             "pattern": ["C", "S"], "items": {"C": "coal", "S": "stick"}},
            {"name": "面包", "result": "bread", "count": 1,
             "pattern": ["WWW"], "items": {"W": "wheat"}},
            {"name": "弓", "result": "bow", "count": 1,
             "pattern": [" SL", "S L", " SL"], "items": {"S": "stick", "L": "string"}},
            {"name": "箭", "result": "arrow", "count": 4,
             "pattern": ["F", "S", "F"], "items": {"F": "feather", "S": "stick"}},
            # 方块
            {"name": "铁块", "result": "iron_block", "count": 1,
             "pattern": ["III", "III", "III"], "items": {"I": "iron_ingot"}},
            {"name": "金块", "result": "gold_block", "count": 1,
             "pattern": ["GGG", "GGG", "GGG"], "items": {"G": "gold_ingot"}},
            {"name": "钻石块", "result": "diamond_block", "count": 1,
             "pattern": ["DDD", "DDD", "DDD"], "items": {"D": "diamond"}},
        ]

        # 物品中文名称
        item_names = {
            "oak_planks": "橡木木板", "stick": "木棍", "cobblestone": "圆石",
            "iron_ingot": "铁锭", "gold_ingot": "金锭", "diamond": "钻石",
            "coal": "煤炭", "wooden_pickaxe": "木镐", "stone_pickaxe": "石镐",
            "iron_pickaxe": "铁镐", "golden_pickaxe": "金镐", "diamond_pickaxe": "钻石镐",
            "wooden_sword": "木剑", "iron_sword": "铁剑", "diamond_sword": "钻石剑",
            "crafting_table_item": "工作台", "furnace_item": "熔炉", "chest_item": "箱子",
            "torch": "火把", "bread": "面包", "wheat": "小麦",
            "bow": "弓", "arrow": "箭", "leather": "皮革", "string": "线",
            "feather": "羽毛", "iron_block": "铁块", "gold_block": "金块",
            "diamond_block": "钻石块", "bone": "骨头", "paper": "纸", "book": "书",
            "apple": "苹果", "golden_apple": "金苹果", "emerald": "绿宝石",
            "redstone": "红石", "lapis_lazuli": "青金石",
        }

        # 合成格子状态 (3x3, 每个格子存物品key或None)
        craft_grid = [[None for _ in range(3)] for _ in range(3)]
        craft_grid_labels = []
        selected_item = [None]  # 当前选中的物品(用于放入合成格)

        # 顶部: 标题和皮肤按钮
        top = ttk.Frame(dlg)
        top.pack(fill="x", padx=10, pady=5)
        ttk.Label(top, text="⚒ 合成台", font=("Arial", 14, "bold")).pack(side="left")
        ttk.Button(top, text="🎨 自定义皮肤", command=lambda: choose_custom_skin()).pack(
            side="right", padx=5)
        ttk.Button(top, text="↩ 恢复默认皮肤", command=lambda: reset_skin()).pack(
            side="right", padx=5)

        # 主体: 左右分栏
        main = ttk.Frame(dlg)
        main.pack(fill="both", expand=True, padx=10, pady=5)
        # 左侧: 合成台
        left = ttk.LabelFrame(main, text=" 合成台 ")
        left.pack(side="left", fill="both", expand=True, padx=(0, 5))
        # 合成台背景(工作台纹理)
        craft_bg_frame = tk.Frame(left, bg="#8b5a2b", width=300, height=250)
        craft_bg_frame.pack(pady=10)
        craft_bg_frame.pack_propagate(False)
        # 3x3 合成格子
        grid_frame = tk.Frame(craft_bg_frame, bg="#8b5a2b")
        grid_frame.pack(pady=20)
        for i in range(3):
            row_labels = []
            for j in range(3):
                cell = tk.Label(grid_frame, width=6, height=3, bg="#c6c6c6",
                                relief="raised", borderwidth=2, cursor="hand2")
                cell.grid(row=i, column=j, padx=2, pady=2)
                cell.bind("<Button-1>", lambda e, r=i, c=j: place_item(r, c))
                cell.bind("<Button-3>", lambda e, r=i, c=j: remove_item(r, c))
                row_labels.append(cell)
            craft_grid_labels.append(row_labels)
        # 箭头和结果
        result_frame = tk.Frame(left)
        result_frame.pack(pady=10)
        ttk.Label(result_frame, text="➡", font=("Arial", 20)).pack(side="left", padx=10)
        self._craft_result_label = tk.Label(result_frame, width=6, height=3, bg="#ffd700",
                                             relief="raised", borderwidth=2, cursor="hand2")
        self._craft_result_label.pack(side="left", padx=10)
        self._craft_result_label.bind("<Button-1>", lambda e: take_result())
        ttk.Label(result_frame, text="点击结果取出", foreground="#666").pack(side="left", padx=10)

        # 右侧: 配方书
        right = ttk.LabelFrame(main, text=" 配方书 ")
        right.pack(side="left", fill="both", expand=True, padx=(5, 0))
        self._craft_recipe_listbox = tk.Listbox(right, font=("Consolas", 9))
        self._craft_recipe_listbox.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        recipe_sb = ttk.Scrollbar(right, command=self._craft_recipe_listbox.yview)
        recipe_sb.pack(side="right", fill="y")
        self._craft_recipe_listbox.configure(yscrollcommand=recipe_sb.set)
        self._craft_recipe_listbox.bind("<<ListboxSelect>>", lambda e: show_recipe_detail())
        # 填充配方列表
        for recipe in recipes:
            self._craft_recipe_listbox.insert("end", recipe["name"])

        # 底部: 物品栏(简单可靠的方式)
        bottom = ttk.LabelFrame(dlg, text=" 物品栏 (左键选中物品, 左键点击合成格放入, 右键合成格取出) ")
        bottom.pack(fill="x", padx=10, pady=5)
        self._craft_inv_frame = tk.Frame(bottom, bg="#f0f0f0")
        self._craft_inv_frame.pack(fill="x", padx=5, pady=5)

        # 状态
        self._craft_status_label = ttk.Label(dlg, text="", foreground="#00aa00")
        self._craft_status_label.pack(pady=5)

        def refresh_inventory():
            """刷新物品栏显示"""
            # 清空
            for widget in self._craft_inv_frame.winfo_children():
                widget.destroy()
            # 确保背包有数据
            if not self._craft_inventory:
                tk.Label(self._craft_inv_frame, text="(背包为空, 请先挖矿/钓鱼获取物品)",
                         fg="#999").pack(pady=10)
                return
            # 显示物品
            col = 0
            row = 0
            for item_key, count in list(self._craft_inventory.items()):
                if count <= 0:
                    continue
                name = item_names.get(item_key, item_key)
                # 用文字按钮(简单可靠, 不依赖纹理提取)
                btn = tk.Label(self._craft_inv_frame,
                               text="{}\n×{}".format(name[:6], count),
                               bg="#ffffff", relief="raised", borderwidth=1,
                               cursor="hand2", width=8, height=2,
                               font=("Arial", 8))
                btn.grid(row=row, column=col, padx=2, pady=2)
                btn.bind("<Button-1>", lambda e, k=item_key: select_item(k))
                col += 1
                if col >= 10:
                    col = 0
                    row += 1

        def select_item(item_key):
            """选中物品"""
            selected_item[0] = item_key
            name = item_names.get(item_key, item_key)
            self._craft_status_label.config(text="已选中: {} (左键点击合成格放入)".format(name))

        def place_item(row, col):
            """放入物品到合成格"""
            if not selected_item[0]:
                self._craft_status_label.config(text="请先在物品栏选中物品")
                return
            item_key = selected_item[0]
            if self._craft_inventory.get(item_key, 0) <= 0:
                self._craft_status_label.config(text="物品数量不足")
                return
            # 如果格子里已有物品, 先取回
            if craft_grid[row][col]:
                self._craft_inventory[craft_grid[row][col]] = self._craft_inventory.get(
                    craft_grid[row][col], 0) + 1
            # 放入新物品
            craft_grid[row][col] = item_key
            self._craft_inventory[item_key] -= 1
            update_grid_display()
            refresh_inventory()
            check_recipe()

        def remove_item(row, col):
            """从合成格取出物品"""
            if craft_grid[row][col]:
                item_key = craft_grid[row][col]
                self._craft_inventory[item_key] = self._craft_inventory.get(item_key, 0) + 1
                craft_grid[row][col] = None
                update_grid_display()
                refresh_inventory()
                check_recipe()

        def update_grid_display():
            """更新合成格显示"""
            for i in range(3):
                for j in range(3):
                    cell = craft_grid_labels[i][j]
                    item_key = craft_grid[i][j]
                    if item_key:
                        name = item_names.get(item_key, item_key)
                        item_photo = game_assets.load_item_texture_photo(
                            item_key, mc_dir, mc_version, cache_dir, scale=2)
                        if item_photo:
                            cell.config(image=item_photo, text="", bg="#ffffff")
                            cell.image = item_photo
                        else:
                            cell.config(text=name[:2], image="", bg="#ffffff")
                    else:
                        cell.config(text="", image="", bg="#c6c6c6")
                        cell.image = None

        def check_recipe():
            """检查当前合成格是否匹配配方"""
            # 提取当前合成格的图案
            current_pattern = []
            for i in range(3):
                row = ""
                for j in range(3):
                    if craft_grid[i][j]:
                        # 找到这个物品对应的配方符号
                        found = False
                        for recipe in recipes:
                            for sym, item in recipe.get("items", {}).items():
                                if item == craft_grid[i][j]:
                                    row += sym
                                    found = True
                                    break
                            if found:
                                break
                        if not found:
                            row += "?"
                    else:
                        row += " "
                current_pattern.append(row)
            # 匹配配方
            matched = None
            for recipe in recipes:
                recipe_pattern = recipe["pattern"]
                # 简单匹配(忽略位置, 只比较物品组合)
                if match_recipe(current_pattern, recipe_pattern):
                    matched = recipe
                    break
            if matched:
                result_key = matched["result"]
                result_count = matched["count"]
                name = item_names.get(result_key, result_key)
                result_photo = game_assets.load_item_texture_photo(
                    result_key, mc_dir, mc_version, cache_dir, scale=2)
                if result_photo:
                    self._craft_result_label.config(image=result_photo, text="x{}".format(result_count),
                                                    compound="bottom", bg="#90ee90")
                    self._craft_result_label.image = result_photo
                else:
                    self._craft_result_label.config(text="{}\nx{}".format(name[:4], result_count),
                                                    image="", bg="#90ee90")
                self._craft_status_label.config(text="✅ 可以合成: {} x{}".format(name, result_count))
                self._craft_matched_recipe = matched
            else:
                self._craft_result_label.config(text="", image="", bg="#ffd700")
                self._craft_result_label.image = None
                self._craft_status_label.config(text="❌ 当前配方无法合成")
                self._craft_matched_recipe = None

        def match_recipe(current, recipe):
            """简单匹配配方(比较物品组合)"""
            current_items = {}
            for row in current:
                for c in row:
                    if c != " " and c != "?":
                        current_items[c] = current_items.get(c, 0) + 1
            recipe_items = {}
            for row in recipe:
                for c in row:
                    if c != " ":
                        recipe_items[c] = recipe_items.get(c, 0) + 1
            return current_items == recipe_items

        def take_result():
            """取出合成结果"""
            if not hasattr(self, "_craft_matched_recipe") or not self._craft_matched_recipe:
                self._craft_status_label.config(text="没有可取出的合成结果")
                return
            recipe = self._craft_matched_recipe
            result_key = recipe["result"]
            result_count = recipe["count"]
            name = item_names.get(result_key, result_key)
            # 清空合成格
            for i in range(3):
                for j in range(3):
                    craft_grid[i][j] = None
            # 添加结果到背包
            self._craft_inventory[result_key] = self._craft_inventory.get(result_key, 0) + result_count
            CONFIG.set("craft_inventory", self._craft_inventory)
            update_grid_display()
            refresh_inventory()
            check_recipe()
            self._craft_status_label.config(text="✅ 合成成功: {} x{}".format(name, result_count))

        # 初始化显示物品栏
        refresh_inventory()

        def show_recipe_detail():
            """显示选中配方的详情"""
            sel = self._craft_recipe_listbox.curselection()
            if not sel:
                return
            recipe = recipes[sel[0]]
            # 自动填充配方到合成格(演示)
            for i in range(3):
                for j in range(3):
                    craft_grid[i][j] = None
            # 根据配方填充
            for i, row in enumerate(recipe["pattern"]):
                for j, c in enumerate(row):
                    if c != " " and c in recipe["items"]:
                        item_key = recipe["items"][c]
                        craft_grid[i][j] = item_key
            update_grid_display()
            name = item_names.get(recipe["result"], recipe["result"])
            self._craft_status_label.config(
                text="📖 配方: {} -> {} x{} (已填充到合成格, 但需要你有足够材料)".format(
                    recipe["name"], name, recipe["count"]))

        def choose_custom_skin():
            """选择自定义皮肤(工作台背景)"""
            path = filedialog.askopenfilename(
                title="选择工作台背景图片",
                filetypes=[("图片文件", "*.png *.jpg *.jpeg *.gif"), ("所有文件", "*.*")])
            if path:
                try:
                    from PIL import Image, ImageTk
                    img = Image.open(path).convert("RGBA")
                    img = img.resize((300, 250), Image.NEAREST)
                    photo = ImageTk.PhotoImage(img)
                    craft_bg_frame.config(bg="#000000")
                    # 用背景图片(简化: 改变背景色)
                    self._craft_status_label.config(text="🎨 自定义皮肤已加载: " + Path(path).name)
                    CONFIG.set("crafting_skin", path)
                except Exception as exc:
                    messagebox.showerror("加载失败", str(exc))

        def reset_skin():
            """恢复默认皮肤"""
            craft_bg_frame.config(bg="#8b5a2b")
            CONFIG.set("crafting_skin", "")
            self._craft_status_label.config(text="↩ 已恢复默认皮肤")

        dlg.wait_window()

    # ---------------- 养殖系统 ----------------
    def _open_farming(self):
        """养殖系统对话框"""
        import game_assets

        dlg = tk.Toplevel(self.root)
        dlg.title("🐄 养殖系统")
        dlg.geometry("700x550")
        dlg.transient(self.root)
        dlg.grab_set()

        # 获取当前实例的 MC 版本, 用于提取纹理
        mc_version = "1.20.1"
        mc_dir = str(Path.home() / "AppData" / "Roaming" / ".minecraft")
        try:
            inst_name = self.inst_combo.get()
            if inst_name:
                inst = instance_mod.get_instance(inst_name)
                mc_version = inst.get("mc_version", "1.20.1")
                game_dir = instance_mod.get_instance_game_dir(inst_name)
                if game_dir:
                    mc_dir = str(Path(game_dir).parent.parent)
        except Exception:
            pass
        cache_dir = str(Path.home() / "AppData" / "Roaming" / ".voxellauncher" / "cache")

        # 动物数据(保存到配置)
        if not hasattr(self, "_farm_animals"):
            self._farm_animals = CONFIG.get("farm_animals", [])
            if not self._farm_animals:
                # 默认给几只动物
                self._farm_animals = [
                    {"type": "chicken", "name": "小鸡", "age": "adult", "hunger": 80, "health": 100},
                    {"type": "cow", "name": "奶牛", "age": "adult", "hunger": 70, "health": 100},
                    {"type": "pig", "name": "小猪", "age": "adult", "hunger": 90, "health": 100},
                ]

        def save_animals():
            CONFIG.set("farm_animals", self._farm_animals)

        # 预加载动物纹理
        animal_photos = {}
        for animal_key in game_assets.list_available_animals():
            try:
                photo = game_assets.load_animal_texture_photo(
                    animal_key, mc_dir, mc_version, cache_dir, scale=4)
                if photo:
                    animal_photos[animal_key] = photo
            except Exception:
                pass

        # 顶部: 统计信息
        top = ttk.Frame(dlg)
        top.pack(fill="x", padx=10, pady=5)
        ttk.Label(top, text="🐄 我的牧场", font=("Arial", 14, "bold")).pack(side="left")
        self._farm_count_label = ttk.Label(top, text="")
        self._farm_count_label.pack(side="left", padx=20)
        ttk.Button(top, text="➕ 添加动物", command=lambda: add_animal()).pack(side="right")

        # 主体: 左右分栏
        main = ttk.Frame(dlg)
        main.pack(fill="both", expand=True, padx=10, pady=5)
        # 左侧: 动物列表
        left = ttk.LabelFrame(main, text=" 动物列表 ")
        left.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self._farm_listbox = tk.Listbox(left, font=("Arial", 10), selectmode="single")
        self._farm_listbox.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        farm_sb = ttk.Scrollbar(left, command=self._farm_listbox.yview)
        farm_sb.pack(side="right", fill="y")
        self._farm_listbox.configure(yscrollcommand=farm_sb.set)
        self._farm_listbox.bind("<<ListboxSelect>>", lambda e: show_animal_detail())

        # 右侧: 动物详情
        right = ttk.LabelFrame(main, text=" 动物详情 ")
        right.pack(side="left", fill="both", expand=True, padx=(5, 0))
        # 动物纹理
        self._farm_animal_label = tk.Label(right, text="选择一只动物", font=("Arial", 12))
        self._farm_animal_label.pack(pady=10)
        # 动物信息
        self._farm_info_label = tk.Label(right, text="", justify="left", anchor="w",
                                          font=("Arial", 10))
        self._farm_info_label.pack(fill="x", padx=10, pady=5)
        # 状态条
        self._farm_hunger_bar = ttk.Progressbar(right, length=200, mode="determinate")
        self._farm_hunger_bar.pack(pady=2)
        self._farm_hunger_label = tk.Label(right, text="饱食度", font=("Arial", 9))
        self._farm_hunger_label.pack()
        self._farm_health_bar = ttk.Progressbar(right, length=200, mode="determinate")
        self._farm_health_bar.pack(pady=2)
        self._farm_health_label = tk.Label(right, text="生命值", font=("Arial", 9))
        self._farm_health_label.pack()
        # 操作按钮
        btn_frame = ttk.Frame(right)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="🌾 喂食", command=lambda: feed_animal()).pack(
            side="left", padx=2)
        ttk.Button(btn_frame, text="🥚 收获", command=lambda: harvest_animal()).pack(
            side="left", padx=2)
        ttk.Button(btn_frame, text="❤️ 治疗", command=lambda: heal_animal()).pack(
            side="left", padx=2)
        ttk.Button(btn_frame, text="❌ 放生", command=lambda: release_animal()).pack(
            side="left", padx=2)
        # 切换显示模式
        def toggle_texture():
            self._farm_show_real_texture = not self._farm_show_real_texture
            mode = "真实纹理(展开贴图)" if self._farm_show_real_texture else "Emoji"
            toggle_btn.config(text="🖼 显示: " + mode)
            show_animal_detail()
        toggle_btn = ttk.Button(btn_frame, text="🖼 显示: Emoji", command=toggle_texture)
        toggle_btn.pack(side="left", padx=2)

        # 底部: 仓库
        bottom = ttk.LabelFrame(dlg, text=" 牧场仓库 ")
        bottom.pack(fill="x", padx=10, pady=5)
        if not hasattr(self, "_farm_inventory"):
            self._farm_inventory = CONFIG.get("farm_inventory", {})
        self._farm_inv_label = tk.Label(bottom, text="", justify="left", anchor="w",
                                         font=("Arial", 9), wraplength=550)
        self._farm_inv_label.pack(side="left", fill="x", padx=10, pady=5)
        # 发送到游戏按钮
        send_btn = ttk.Button(bottom, text="📤 发送全部到游戏",
                              command=lambda: send_all_to_game())
        send_btn.pack(side="right", padx=10, pady=5)

        def send_all_to_game():
            """把仓库里所有可发送的物品都发送到游戏"""
            if not self._farm_inventory:
                messagebox.showinfo("提示", "仓库是空的")
                return
            import bridge
            if not bridge.is_bridge_running():
                messagebox.showwarning("无法发送", "联动 Mod 未运行\n\n请确保:\n1. 已安装联动 Mod\n2. 游戏已启动并进入世界")
                return
            sent = []
            failed = []
            for product_name, count in list(self._farm_inventory.items()):
                if count <= 0:
                    continue
                item_id = product_item_ids.get(product_name)
                if not item_id:
                    continue
                ok, msg = bridge.send_item(item_id, count)
                if ok:
                    sent.append("{} x{}".format(product_name, count))
                    self._farm_inventory[product_name] = 0
                else:
                    failed.append("{}: {}".format(product_name, msg))
            CONFIG.set("farm_inventory", self._farm_inventory)
            refresh_inventory()
            result = "已发送到游戏:\n" + "\n".join(sent) if sent else ""
            if failed:
                result += "\n\n发送失败:\n" + "\n".join(failed)
            if not result:
                result = "没有可发送的物品"
            messagebox.showinfo("发送结果", result)

        def refresh_animal_list():
            """刷新动物列表"""
            self._farm_listbox.delete(0, "end")
            for i, animal in enumerate(self._farm_animals):
                a_type = animal.get("type", "chicken")
                a_name = animal.get("name", game_assets.get_animal_name(a_type))
                hunger = animal.get("hunger", 100)
                status = "😊" if hunger > 50 else "😢" if hunger > 20 else "😭"
                self._farm_listbox.insert("end", "{} {} ({})".format(status, a_name,
                    game_assets.get_animal_name(a_type)))
            self._farm_count_label.config(text="共 {} 只动物".format(len(self._farm_animals)))
            refresh_inventory()

        def refresh_inventory():
            """刷新仓库显示"""
            if not self._farm_inventory:
                self._farm_inv_label.config(text="仓库是空的, 快去收获产品吧!")
                return
            text = "📦 仓库: "
            items = []
            for item, count in self._farm_inventory.items():
                if count > 0:
                    items.append("{} x{}".format(item, count))
            text += ", ".join(items) if items else "空"
            self._farm_inv_label.config(text=text)

        # 动物 emoji 映射(优先用 emoji, 因为 Minecraft 实体纹理是展开贴图, 直接显示很奇怪)
        animal_emojis = {
            "chicken": "🐔", "cow": "🐄", "pig": "🐷", "sheep": "🐑",
            "rabbit": "🐰", "horse": "🐴", "donkey": "🫏", "mule": "🐴",
            "llama": "🦙", "goat": "🐐", "cat": "🐱", "dog": "🐶",
            "parrot": "🦜", "fox": "🦊", "bee": "🐝", "villager": "🧑‍🌾",
        }
        # 是否显示真实纹理(默认 False, 因为展开贴图不好看)
        self._farm_show_real_texture = False

        def show_animal_detail():
            """显示选中动物的详情"""
            sel = self._farm_listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            if idx >= len(self._farm_animals):
                return
            animal = self._farm_animals[idx]
            a_type = animal.get("type", "chicken")
            a_name = animal.get("name", game_assets.get_animal_name(a_type))
            hunger = animal.get("hunger", 100)
            health = animal.get("health", 100)
            age = animal.get("age", "adult")
            age_text = "成年" if age == "adult" else "幼年"
            # 显示: 优先用 emoji, 如果开启真实纹理且提取成功则用真实纹理
            if self._farm_show_real_texture and a_type in animal_photos:
                self._farm_animal_label.config(image=animal_photos[a_type], text="")
                self._farm_animal_label.image = animal_photos[a_type]
            else:
                emoji = animal_emojis.get(a_type, "🐾")
                self._farm_animal_label.config(text=emoji, font=("Arial", 56), image="")
            # 显示信息
            foods = game_assets.get_animal_foods(a_type)
            products = game_assets.get_animal_products(a_type)
            product_text = ", ".join(products.values()) if products else "无"
            self._farm_info_label.config(
                text="名称: {}\n种类: {}\n年龄: {}\n喜欢的食物: {}\n产品: {}".format(
                    a_name, game_assets.get_animal_name(a_type), age_text,
                    ", ".join(foods[:3]) if foods else "未知", product_text))
            # 状态条
            self._farm_hunger_bar["value"] = hunger
            self._farm_hunger_label.config(text="饱食度: {}%".format(hunger))
            self._farm_health_bar["value"] = health
            self._farm_health_label.config(text="生命值: {}%".format(health))

        def feed_animal():
            """喂食动物"""
            sel = self._farm_listbox.curselection()
            if not sel:
                messagebox.showinfo("提示", "请先选择一只动物")
                return
            idx = sel[0]
            animal = self._farm_animals[idx]
            a_type = animal.get("type", "chicken")
            a_name = animal.get("name", game_assets.get_animal_name(a_type))
            hunger = animal.get("hunger", 100)
            if hunger >= 100:
                messagebox.showinfo("提示", "{} 已经吃饱了!".format(a_name))
                return
            # 简单喂食: 增加饱食度
            animal["hunger"] = min(100, hunger + 30)
            save_animals()
            refresh_animal_list()
            show_animal_detail()
            messagebox.showinfo("喂食成功", "{} 吃饱了! 饱食度 +30".format(a_name))

        # 动物产品对应的 Minecraft 物品 ID
        product_item_ids = {
            "鸡蛋": "minecraft:egg",
            "羽毛": "minecraft:feather",
            "鸡肉": "minecraft:chicken",
            "牛奶": "minecraft:milk_bucket",
            "皮革": "minecraft:leather",
            "牛肉": "minecraft:beef",
            "猪肉": "minecraft:porkchop",
            "羊毛": "minecraft:white_wool",
            "羊肉": "minecraft:mutton",
            "兔肉": "minecraft:rabbit",
            "兔皮": "minecraft:rabbit_hide",
            "山羊角": "minecraft:goat_horn",
            "羊奶": "minecraft:milk_bucket",
            "蜂蜜瓶": "minecraft:honey_bottle",
            "蜜脾": "minecraft:honeycomb",
        }

        def harvest_animal():
            """收获动物产品"""
            sel = self._farm_listbox.curselection()
            if not sel:
                messagebox.showinfo("提示", "请先选择一只动物")
                return
            idx = sel[0]
            animal = self._farm_animals[idx]
            a_type = animal.get("type", "chicken")
            a_name = animal.get("name", game_assets.get_animal_name(a_type))
            products = game_assets.get_animal_products(a_type)
            if not products or "nothing" in products:
                messagebox.showinfo("提示", "{} 没有可收获的产品".format(a_name))
                return
            # 随机收获一个产品
            import random
            product_key = random.choice(list(products.keys()))
            product_name = products[product_key]
            self._farm_inventory[product_name] = self._farm_inventory.get(product_name, 0) + 1
            CONFIG.set("farm_inventory", self._farm_inventory)
            refresh_inventory()
            # 询问是否发送到游戏
            item_id = product_item_ids.get(product_name)
            if item_id:
                if messagebox.askyesno("收获成功",
                    "从 {} 那里收获了: {} x1\n\n是否发送到游戏背包?".format(a_name, product_name)):
                    import bridge
                    ok, msg = bridge.send_item(item_id, 1)
                    if ok:
                        messagebox.showinfo("发送成功", msg)
                    else:
                        messagebox.showwarning("发送失败", msg + "\n\n物品已保存到牧场仓库, 可以稍后再发送")
            else:
                messagebox.showinfo("收获成功", "从 {} 那里收获了: {} x1\n(已保存到牧场仓库)".format(a_name, product_name))

        def heal_animal():
            """治疗动物"""
            sel = self._farm_listbox.curselection()
            if not sel:
                messagebox.showinfo("提示", "请先选择一只动物")
                return
            idx = sel[0]
            animal = self._farm_animals[idx]
            a_name = animal.get("name", "动物")
            health = animal.get("health", 100)
            if health >= 100:
                messagebox.showinfo("提示", "{} 很健康, 不需要治疗".format(a_name))
                return
            animal["health"] = min(100, health + 25)
            save_animals()
            show_animal_detail()
            messagebox.showinfo("治疗成功", "{} 恢复了健康! 生命值 +25".format(a_name))

        def release_animal():
            """放生动物"""
            sel = self._farm_listbox.curselection()
            if not sel:
                messagebox.showinfo("提示", "请先选择一只动物")
                return
            idx = sel[0]
            animal = self._farm_animals[idx]
            a_name = animal.get("name", "动物")
            if messagebox.askyesno("确认", "确定要放生 {} 吗?".format(a_name)):
                self._farm_animals.pop(idx)
                save_animals()
                refresh_animal_list()
                self._farm_animal_label.config(text="选择一只动物", image="")
                self._farm_info_label.config(text="")
                self._farm_hunger_bar["value"] = 0
                self._farm_health_bar["value"] = 0

        def add_animal():
            """添加动物"""
            # 简单的动物选择对话框
            add_dlg = tk.Toplevel(dlg)
            add_dlg.title("添加动物")
            add_dlg.geometry("400x400")
            add_dlg.transient(dlg)
            add_dlg.grab_set()
            ttk.Label(add_dlg, text="选择要添加的动物:", font=("Arial", 11)).pack(pady=10)
            listbox = tk.Listbox(add_dlg, font=("Arial", 10))
            listbox.pack(fill="both", expand=True, padx=20, pady=5)
            animal_keys = game_assets.list_available_animals()
            for key in animal_keys:
                listbox.insert("end", "{} - {}".format(
                    game_assets.get_animal_name(key), key))
            listbox.selection_set(0)
            def confirm_add():
                sel = listbox.curselection()
                if not sel:
                    return
                a_type = animal_keys[sel[0]]
                a_name = game_assets.get_animal_name(a_type)
                self._farm_animals.append({
                    "type": a_type, "name": a_name,
                    "age": "adult", "hunger": 80, "health": 100
                })
                save_animals()
                refresh_animal_list()
                add_dlg.destroy()
                messagebox.showinfo("添加成功", "添加了一只 {}!".format(a_name))
            ttk.Button(add_dlg, text="添加", command=confirm_add).pack(pady=10)

        # 初始化
        refresh_animal_list()
        dlg.wait_window()

    # ---------------- 钓鱼小游戏 ----------------
    def _open_fishing(self):
        """钓鱼小游戏对话框 - 支持游戏真实纹理和发送到游戏"""
        import game_assets
        import bridge

        dlg = tk.Toplevel(self.root)
        dlg.title("🎣 钓鱼")
        dlg.geometry("500x450")
        dlg.transient(self.root)
        dlg.grab_set()

        # 获取当前实例的 MC 版本, 用于提取纹理
        mc_version = "1.20.1"
        mc_dir = str(Path.home() / "AppData" / "Roaming" / ".minecraft")
        try:
            inst_name = self.inst_combo.get()
            if inst_name:
                inst = instance_mod.get_instance(inst_name)
                mc_version = inst.get("mc_version", "1.20.1")
                game_dir = instance_mod.get_instance_game_dir(inst_name)
                if game_dir:
                    mc_dir = str(Path(game_dir).parent.parent)
        except Exception:
            pass

        # 缓存目录
        cache_dir = str(Path.home() / "AppData" / "Roaming" / ".voxellauncher" / "cache")

        # 状态变量
        state = {"fishing": False, "hooked": False, "can_reel": False,
                 "fish_count": 0, "treasure_count": 0, "fail_count": 0,
                 "last_catch": None}

        # 鱼的种类 (用 game_assets 的 key)
        fish_types = [
            ("cod", "common", 1),
            ("tropical_fish", "common", 1),
            ("pufferfish", "uncommon", 2),
            ("salmon", "uncommon", 2),
            ("squid", "rare", 3),
            ("turtle", "rare", 3),
            ("dolphin", "epic", 5),
            ("axolotl", "epic", 5),
            ("guardian", "legendary", 10),
            ("elder_guardian", "legendary", 15),
        ]
        treasure_types = [
            ("📜 藏宝图", "uncommon", 5, "minecraft:map"),
            ("💎 钻石", "rare", 8, "minecraft:diamond"),
            ("👑 王冠", "epic", 15, None),
            ("🏺 古代花瓶", "legendary", 25, None),
            ("📖 附魔书", "rare", 6, "minecraft:enchanted_book"),
            ("💰 金币", "uncommon", 3, "minecraft:gold_nugget"),
        ]
        junk_types = [
            ("🥫 罐头", "junk", 0, None),
            ("👢 破靴子", "junk", 0, "minecraft:leather_boots"),
            ("📄 废纸", "junk", 0, "minecraft:paper"),
            ("🍔 发霉的汉堡", "junk", 0, None),
        ]

        # 预加载鱼的纹理 (用 Pillow 处理, 解决 Tkinter 不支持索引 PNG 的问题)
        fish_photos = {}
        for fish_key, _, _ in fish_types:
            try:
                photo = game_assets.load_fish_texture_photo(
                    fish_key, mc_dir, mc_version, cache_dir, scale=6)
                if photo:
                    fish_photos[fish_key] = photo
            except Exception:
                pass

        # 水面 Canvas
        water_canvas = tk.Canvas(dlg, height=120, bg="#4a90d9",
                                  highlightthickness=0)
        water_canvas.pack(fill="x", padx=10, pady=(10, 5))
        # 画水波
        for i in range(0, 500, 20):
            water_canvas.create_arc(i, 100, i+30, 130, start=0,
                                     extent=180, fill="#5ba3e8", outline="")
        # 鱼漂
        bobber = water_canvas.create_oval(235, 50, 255, 70, fill="#ff4444",
                                           outline="#aa0000", width=2)
        bobber_line = water_canvas.create_line(245, 0, 245, 50, fill="#ffffff",
                                                width=1)

        # 结果显示区 (纹理 + 文字)
        result_frame = tk.Frame(dlg, bg="#f5f5f5", height=120)
        result_frame.pack(fill="x", padx=10, pady=5)
        result_frame.pack_propagate(False)
        # 鱼的纹理显示
        fish_texture_label = tk.Label(result_frame, bg="#f5f5f5")
        fish_texture_label.pack(side="left", padx=20, pady=10)
        # 结果文字
        result_text_frame = tk.Frame(result_frame, bg="#f5f5f5")
        result_text_frame.pack(side="left", fill="both", expand=True, pady=10)
        status_label = tk.Label(result_text_frame, text="点击「开始钓鱼」开始",
                                font=("Arial", 12, "bold"), fg="#333", bg="#f5f5f5",
                                anchor="w")
        status_label.pack(fill="x")
        result_label = tk.Label(result_text_frame, text="", font=("Arial", 11),
                                fg="#0066cc", bg="#f5f5f5", anchor="w")
        result_label.pack(fill="x", pady=(2, 0))
        # 发送到游戏按钮
        send_btn = tk.Button(result_text_frame, text="📤 发送到游戏", width=12,
                             font=("Arial", 9, "bold"), bg="#2196F3", fg="white",
                             state="disabled")
        send_btn.pack(side="left", pady=(5, 0))

        # 统计标签
        stats_label = tk.Label(dlg, text="🐟 鱼: 0 | 💎 宝藏: 0 | ❌ 跑掉: 0",
                               font=("Arial", 9), fg="#666")
        stats_label.pack(pady=2)

        # 按钮区
        btn_frame = tk.Frame(dlg)
        btn_frame.pack(pady=10)
        start_btn = tk.Button(btn_frame, text="🎣 开始钓鱼", width=12,
                              font=("Arial", 10, "bold"), bg="#4CAF50", fg="white")
        start_btn.pack(side="left", padx=5)
        reel_btn = tk.Button(btn_frame, text="⬆ 拉杆!", width=12,
                             font=("Arial", 10, "bold"), bg="#ff9800", fg="white",
                             state="disabled")
        reel_btn.pack(side="left", padx=5)

        def update_stats():
            stats_label.config(text="🐟 鱼: {} | 💎 宝藏: {} | ❌ 跑掉: {}".format(
                state["fish_count"], state["treasure_count"], state["fail_count"]))

        def move_bobber(y):
            water_canvas.coords(bobber, 235, y, 255, y+20)
            water_canvas.coords(bobber_line, 245, 0, 245, y)

        def show_fish_texture(fish_key):
            """显示鱼的真实纹理"""
            if fish_key in fish_photos:
                fish_texture_label.config(image=fish_photos[fish_key])
                fish_texture_label.image = fish_photos[fish_key]
            else:
                # 没有纹理就用 emoji
                emoji_map = {"cod": "🐟", "tropical_fish": "🐠", "pufferfish": "🐡",
                             "salmon": "🍣", "squid": "🦑", "turtle": "🐢",
                             "dolphin": "🐬", "axolotl": "🦎", "guardian": "👁",
                             "elder_guardian": "👁"}
                fish_texture_label.config(text=emoji_map.get(fish_key, "🐟"),
                                          font=("Arial", 48), image="")

        def send_to_game():
            """把钓到的鱼/宝藏发送到游戏"""
            catch = state.get("last_catch")
            if not catch:
                return
            item_id = catch.get("item_id")
            if not item_id:
                messagebox.showinfo("无法发送", "这个物品不能发送到游戏")
                return
            ok, msg = bridge.send_item(item_id, 1)
            if ok:
                messagebox.showinfo("发送成功", msg)
            else:
                messagebox.showwarning("发送失败", msg + "\n\n请确保:\n1. 已安装联动 Mod\n2. 游戏已启动并进入世界")

        send_btn.config(command=send_to_game)

        def fish_bite():
            if not state["fishing"]:
                return
            state["hooked"] = True
            state["can_reel"] = True
            status_label.config(text="❗ 有鱼上钩了! 快拉杆!", fg="#ff0000")
            for i in range(5):
                dlg.after(i*50, lambda y=55+i*3: move_bobber(y))
            reel_btn.config(state="normal", bg="#ff5722")
            dlg.after(2000, fish_escape)

        def fish_escape():
            if state["hooked"] and state["can_reel"]:
                state["can_reel"] = False
                state["hooked"] = False
                state["fishing"] = False
                state["fail_count"] += 1
                status_label.config(text="💨 鱼跑了... 太慢了!", fg="#999")
                result_label.config(text="")
                fish_texture_label.config(image="", text="")
                reel_btn.config(state="disabled", bg="#ff9800")
                start_btn.config(state="normal")
                send_btn.config(state="disabled")
                move_bobber(50)
                update_stats()

        def start_fishing():
            if state["fishing"]:
                return
            state["fishing"] = True
            state["hooked"] = False
            state["can_reel"] = False
            state["last_catch"] = None
            start_btn.config(state="disabled")
            reel_btn.config(state="disabled")
            send_btn.config(state="disabled")
            status_label.config(text="🎣 等待鱼上钩...", fg="#333")
            result_label.config(text="")
            fish_texture_label.config(image="", text="")
            move_bobber(50)
            def wobble(count=0):
                if not state["fishing"] or state["hooked"]:
                    return
                if count > 20:
                    return
                y = 48 + (count % 2) * 4
                move_bobber(y)
                dlg.after(300, lambda: wobble(count+1))
            wobble()
            import random
            wait_time = random.randint(3000, 8000)
            dlg.after(wait_time, fish_bite)

        def reel():
            if not state["can_reel"]:
                return
            state["can_reel"] = False
            state["hooked"] = False
            state["fishing"] = False
            reel_btn.config(state="disabled", bg="#ff9800")
            start_btn.config(state="normal")
            move_bobber(50)
            import random
            r = random.random()
            if r < 0.1:  # 10% 垃圾
                item = random.choice(junk_types)
                result_label.config(text="🗑 钓到了: {} (垃圾)".format(item[0]), fg="#999")
                status_label.config(text="唉, 钓到个垃圾...", fg="#999")
                fish_texture_label.config(text="🗑", font=("Arial", 48), image="")
                state["last_catch"] = {"name": item[0], "item_id": item[3]}
                if item[3]:
                    send_btn.config(state="normal")
            elif r < 0.25:  # 15% 宝藏
                item = random.choice(treasure_types)
                state["treasure_count"] += 1
                xp = item[2]
                result_label.config(text="💎 钓到宝藏: {} ({} 经验)".format(item[0], xp), fg="#ff9900")
                status_label.config(text="🎉 太棒了! 钓到宝藏了!", fg="#ff9900")
                fish_texture_label.config(text=item[0][:2], font=("Arial", 48), image="")
                state["last_catch"] = {"name": item[0], "item_id": item[3]}
                if item[3]:
                    send_btn.config(state="normal")
                self._fun_add_xp(xp)
            else:  # 75% 鱼
                fish_r = random.random()
                if fish_r < 0.5:
                    candidates = [f for f in fish_types if f[1] == "common"]
                elif fish_r < 0.8:
                    candidates = [f for f in fish_types if f[1] == "uncommon"]
                elif fish_r < 0.95:
                    candidates = [f for f in fish_types if f[1] == "rare"]
                else:
                    candidates = [f for f in fish_types if f[1] in ("epic", "legendary")]
                if not candidates:
                    candidates = fish_types
                fish_key, rarity, xp = random.choice(candidates)
                state["fish_count"] += 1
                fish_name = game_assets.get_fish_name(fish_key)
                item_id = game_assets.get_fish_item_id(fish_key)
                rarity_colors = {"common": "#333", "uncommon": "#00aa00",
                                 "rare": "#0066cc", "epic": "#9933ff", "legendary": "#ff9900"}
                color = rarity_colors.get(rarity, "#333")
                result_label.config(text="🐟 钓到: {} ({} 经验)".format(fish_name, xp), fg=color)
                status_label.config(text="🎣 钓到了!", fg=color)
                show_fish_texture(fish_key)
                state["last_catch"] = {"name": fish_name, "item_id": item_id}
                if item_id:
                    send_btn.config(state="normal")
                self._fun_add_xp(xp)
            update_stats()

        start_btn.config(command=start_fishing)
        reel_btn.config(command=reel)
        dlg.wait_window()


    # ---------------- 工具页 ----------------
    def _build_tools_tab(self):
        """工具页面: 截图管理、存档管理、模组管理、配置编辑、崩溃分析等"""
        f = self.tab_tools
        # 顶部: 实例选择
        top = ttk.Frame(f)
        top.pack(fill="x", padx=8, pady=6)
        ttk.Label(top, text="当前实例:").pack(side="left")
        self.tools_inst_combo = ttk.Combobox(top, state="readonly", width=30)
        self.tools_inst_combo.pack(side="left", padx=5)
        ttk.Button(top, text="刷新", command=self._refresh_tools_instance).pack(
            side="left", padx=5)
        # 用 Notebook 分页
        self.tools_nb = ttk.Notebook(f)
        self.tools_nb.pack(fill="both", expand=True, padx=8, pady=4)
        # 各功能页
        self._build_screenshot_tab()
        self._build_save_tab()
        self._build_mod_tools_tab()
        self._build_config_editor_tab()
        self._build_crash_tab()
        self._build_multiplayer_tab()
        self._build_java_tab()
        self._build_performance_tab()
        self._build_resourcepack_preview_tab()
        self._build_mod_sort_tab()
        # 初始化实例列表
        self._refresh_tools_instance()

    def _refresh_tools_instance(self):
        """刷新工具页的实例列表"""
        instances = [i.get("name") for i in self.instances]
        self.tools_inst_combo["values"] = instances
        if instances and not self.tools_inst_combo.get():
            self.tools_inst_combo.set(instances[0])

    def _get_tools_instance_dir(self):
        """获取工具页当前实例的游戏目录"""
        name = self.tools_inst_combo.get()
        if not name:
            return None
        try:
            inst = instance_mod.get_instance(name)
            if not inst:
                return None
            return instance_mod.get_instance_game_dir(inst)
        except Exception as e:
            print("[Tools] 获取实例目录失败:", e)
            return None


    # ---- 模组工具(更新检查/冲突检测/排序) ----
    def _build_mod_tools_tab(self):
        """模组工具页"""
        tab = ttk.Frame(self.tools_nb)
        self.tools_nb.add(tab, text=" 📦 模组工具 ")
        # 工具栏
        bar = ttk.Frame(tab)
        bar.pack(fill="x", padx=6, pady=4)
        ttk.Button(bar, text="🔄 刷新模组列表", command=self._refresh_mod_list).pack(
            side="left", padx=2)
        ttk.Button(bar, text="🔍 检查更新", command=self._check_mod_updates).pack(
            side="left", padx=2)
        ttk.Button(bar, text="🔍 深度冲突检测", command=self._detect_mod_conflicts_advanced).pack(
            side="left", padx=2)
        ttk.Button(bar, text="📁 打开mods文件夹", command=self._open_mods_dir).pack(
            side="left", padx=2)
        # 模组列表
        list_frame = ttk.Frame(tab)
        list_frame.pack(fill="both", expand=True, padx=6, pady=4)
        self.mod_tools_listbox = tk.Listbox(list_frame, font=("Consolas", 9))
        self.mod_tools_listbox.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(list_frame, command=self.mod_tools_listbox.yview)
        sb.pack(side="right", fill="y")
        self.mod_tools_listbox.configure(yscrollcommand=sb.set)
        # 结果显示
        self.mod_tools_result = tk.Text(tab, height=8, font=("Consolas", 9),
                                         bg="#1e1e1e", fg="#00ff00")
        self.mod_tools_result.pack(fill="x", padx=6, pady=4)

    def _refresh_mod_list(self):
        """刷新模组列表"""
        self.mod_tools_listbox.delete(0, "end")
        game_dir = self._get_tools_instance_dir()
        if not game_dir:
            return
        mods_dir = Path(game_dir) / "mods"
        if not mods_dir.exists():
            return
        mods = sorted(mods_dir.glob("*.jar"))
        for mod in mods:
            size = mod.stat().st_size / 1024
            self.mod_tools_listbox.insert("end", "{} | {:.0f}KB".format(mod.name, size))
        self._log("模组列表已刷新, 共 {} 个模组".format(len(mods)))

    def _check_mod_updates(self):
        """检查模组更新(简化版, 检查 Modrinth)"""
        self.mod_tools_result.delete("1.0", "end")
        self.mod_tools_result.insert("end", "正在检查模组更新...\n")
        game_dir = self._get_tools_instance_dir()
        if not game_dir:
            self.mod_tools_result.insert("end", "请先选择实例\n")
            return
        mods_dir = Path(game_dir) / "mods"
        if not mods_dir.exists():
            self.mod_tools_result.insert("end", "mods 文件夹不存在\n")
            return
        mods = list(mods_dir.glob("*.jar"))
        self.mod_tools_result.insert("end", "共 {} 个模组, 开始检查...\n".format(len(mods)))
        self.mod_tools_result.insert("end", "(注: 完整更新检查需要 Modrinth API, 这里仅做文件名分析)\n\n")
        # 简化版: 分析模组文件名
        for mod in mods:
            name = mod.stem
            self.mod_tools_result.insert("end", "  {}\n".format(name))
        self.mod_tools_result.insert("end", "\n检查完成! 建议手动对比 Modrinth/CurseForge 上的版本。\n")

    def _detect_mod_conflicts(self):
        """检测模组冲突(简化版)"""
        self.mod_tools_result.delete("1.0", "end")
        self.mod_tools_result.insert("end", "正在检测模组冲突...\n\n")
        game_dir = self._get_tools_instance_dir()
        if not game_dir:
            self.mod_tools_result.insert("end", "请先选择实例\n")
            return
        mods_dir = Path(game_dir) / "mods"
        if not mods_dir.exists():
            self.mod_tools_result.insert("end", "mods 文件夹不存在\n")
            return
        mods = list(mods_dir.glob("*.jar"))
        # 检测重复模组(同名不同版本)
        mod_names = {}
        for mod in mods:
            # 简化: 提取模组名(去掉版本号)
            name = mod.stem
            base_name = name.split("-")[0].split("_")[0].lower()
            if base_name not in mod_names:
                mod_names[base_name] = []
            mod_names[base_name].append(mod.name)
        conflicts = {k: v for k, v in mod_names.items() if len(v) > 1}
        if conflicts:
            self.mod_tools_result.insert("end", "⚠ 发现可能的重复模组:\n")
            for base, files in conflicts.items():
                self.mod_tools_result.insert("end", "  {}:\n".format(base))
                for f in files:
                    self.mod_tools_result.insert("end", "    - {}\n".format(f))
            self.mod_tools_result.insert("end", "\n建议: 只保留一个版本, 删除其他重复模组。\n")
        else:
            self.mod_tools_result.insert("end", "✅ 未发现重复模组\n")
        self.mod_tools_result.insert("end", "\n检测完成! (注: 完整冲突检测需要读取模组元数据)\n")

    def _open_mods_dir(self):
        """打开mods文件夹"""
        game_dir = self._get_tools_instance_dir()
        if not game_dir:
            messagebox.showwarning("提示", "请先在工具页顶部选择实例")
            return
        import os
        mods_dir = str(Path(game_dir) / "mods")
        Path(mods_dir).mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(mods_dir)
        except Exception:
            messagebox.showinfo("mods目录", mods_dir)

    # ---- 联机辅助 ----
    def _build_multiplayer_tab(self):
        """联机辅助页"""
        tab = ttk.Frame(self.tools_nb)
        self.tools_nb.add(tab, text=" 🌐 联机辅助 ")
        # 内容
        content = ttk.Frame(tab)
        content.pack(fill="both", expand=True, padx=20, pady=20)
        # 本机IP
        ip_frame = ttk.LabelFrame(content, text=" 本机网络信息 ")
        ip_frame.pack(fill="x", pady=10)
        import socket
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
        except Exception:
            local_ip = "获取失败"
            hostname = "未知"
        ttk.Label(ip_frame, text="计算机名: {}".format(hostname), font=("", 10)).pack(
            anchor="w", padx=10, pady=5)
        ttk.Label(ip_frame, text="局域网IP: {}".format(local_ip), font=("", 10, "bold")).pack(
            anchor="w", padx=10, pady=5)
        ttk.Label(ip_frame, text="默认端口: 25565 (Minecraft)", foreground="#666").pack(
            anchor="w", padx=10, pady=5)
        # 复制IP按钮
        btn_frame = ttk.Frame(ip_frame)
        btn_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(btn_frame, text="📋 复制IP",
                   command=lambda: self._copy_to_clipboard(local_ip)).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="📋 复制IP:端口",
                   command=lambda: self._copy_to_clipboard("{}:25565".format(local_ip))).pack(
            side="left", padx=2)
        # 联机教程
        guide_frame = ttk.LabelFrame(content, text=" 局域网联机教程 ")
        guide_frame.pack(fill="both", expand=True, pady=10)
        guide_text = """1. 房主进入游戏, 打开一个世界
2. 按 ESC -> 对局域网开放 -> 设置模式和作弊 -> 创建局域网世界
3. 游戏左下角会显示端口号(如: 本地游戏已在端口 52341 上运行)
4. 其他玩家: 多人游戏 -> 添加服务器 -> 输入 房主IP:端口号
   例如: 192.168.1.100:52341
5. 注意: 必须在同一个局域网(同一个WiFi/路由器)下

如果是外网联机, 需要:
- 使用内网穿透工具(如 Sakura Frp、ZeroTier)
- 或者搭建专用服务器
- 或者使用 Minecraft 领域服(Realms)"""
        guide_label = tk.Label(guide_frame, text=guide_text, justify="left", anchor="nw",
                               font=("", 9), wraplength=500)
        guide_label.pack(fill="both", expand=True, padx=10, pady=10)

    def _copy_to_clipboard(self, text):
        """复制文本到剪贴板"""
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        messagebox.showinfo("已复制", "已复制到剪贴板: {}".format(text))

    # ---- Java管理 ----
    def _build_java_tab(self):
        """Java管理页"""
        tab = ttk.Frame(self.tools_nb)
        self.tools_nb.add(tab, text=" ☕ Java管理 ")
        content = ttk.Frame(tab)
        content.pack(fill="both", expand=True, padx=20, pady=20)
        # 已安装的Java
        java_frame = ttk.LabelFrame(content, text=" 已检测到的 Java ")
        java_frame.pack(fill="x", pady=10)
        self.java_list_label = tk.Label(java_frame, text="正在检测...", justify="left",
                                         anchor="w", font=("Consolas", 9))
        self.java_list_label.pack(fill="x", padx=10, pady=10)
        # 按钮
        btn_frame = ttk.Frame(java_frame)
        btn_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(btn_frame, text="🔄 重新检测", command=self._detect_java).pack(
            side="left", padx=2)
        ttk.Button(btn_frame, text="📁 打开Java文件夹", command=self._open_java_dir).pack(
            side="left", padx=2)
        # Java版本说明
        info_frame = ttk.LabelFrame(content, text=" Java 版本选择建议 ")
        info_frame.pack(fill="both", expand=True, pady=10)
        info_text = """Minecraft 版本与 Java 版本对应关系:

  Minecraft 1.20.5+  -> 需要 Java 21
  Minecraft 1.17~1.20.4 -> 需要 Java 17
  Minecraft 1.16.5 及以下 -> 需要 Java 8

注意:
- 高版本 Java 不能运行低版本 Minecraft
- 建议安装多个 Java 版本, 启动器会自动选择
- 可以在设置页手动指定 Java 路径"""
        info_label = tk.Label(info_frame, text=info_text, justify="left", anchor="nw",
                              font=("", 9), wraplength=500)
        info_label.pack(fill="both", expand=True, padx=10, pady=10)
        # 启动检测
        self.root.after(500, self._detect_java)

    def _detect_java(self):
        """检测已安装的Java"""
        java_paths = []
        # 常见安装路径
        common_paths = [
            Path("C:/Program Files/Java"),
            Path("C:/Program Files (x86)/Java"),
            Path.home() / ".jdks",
            Path.home() / "AppData/Local/Programs",
        ]
        for base in common_paths:
            if base.exists():
                try:
                    for d in base.iterdir():
                        if d.is_dir() and ("jdk" in d.name.lower() or "jre" in d.name.lower()
                                           or "java" in d.name.lower()):
                            java_exe = d / "bin" / "java.exe"
                            if java_exe.exists():
                                java_paths.append((d.name, str(java_exe)))
                except Exception:
                    pass
        # 环境变量
        import shutil
        env_java = shutil.which("java")
        if env_java and not any(env_java == p for _, p in java_paths):
            java_paths.append(("环境变量", env_java))
        if not java_paths:
            self.java_list_label.config(text="未检测到 Java, 请手动安装或在设置页指定路径")
        else:
            text = "检测到 {} 个 Java:\n\n".format(len(java_paths))
            for name, path in java_paths:
                text += "  {}: {}\n".format(name, path)
            self.java_list_label.config(text=text)

    def _open_java_dir(self):
        """打开Java安装目录"""
        import os
        java_dir = "C:/Program Files/Java"
        if Path(java_dir).exists():
            os.startfile(java_dir)
        else:
            messagebox.showinfo("提示", "默认 Java 目录不存在, 请手动查找")


    # ---- 配置文件编辑器 ----
    def _build_config_editor_tab(self):
        """配置文件编辑器页"""
        tab = ttk.Frame(self.tools_nb)
        self.tools_nb.add(tab, text=" ⚙ 配置编辑 ")
        # 左侧: 文件列表
        left = ttk.Frame(tab)
        left.pack(side="left", fill="y", padx=6, pady=6)
        ttk.Label(left, text="配置文件:").pack(anchor="w")
        self.config_file_listbox = tk.Listbox(left, width=35, font=("Consolas", 9))
        self.config_file_listbox.pack(fill="y", expand=True)
        self.config_file_listbox.bind("<<ListboxSelect>>", lambda e: self._load_config_file())
        # 右侧: 编辑器
        right = ttk.Frame(tab)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        # 工具栏
        bar = ttk.Frame(right)
        bar.pack(fill="x", pady=(0, 4))
        ttk.Button(bar, text="🔄 刷新文件列表", command=self._refresh_config_files).pack(
            side="left", padx=2)
        ttk.Button(bar, text="💾 保存", command=self._save_config_file).pack(
            side="left", padx=2)
        ttk.Button(bar, text="↩ 撤销", command=self._undo_config).pack(
            side="left", padx=2)
        self.config_path_label = ttk.Label(bar, text="", foreground="#666")
        self.config_path_label.pack(side="left", padx=10)
        # 编辑区
        edit_frame = ttk.Frame(right)
        edit_frame.pack(fill="both", expand=True)
        self.config_editor = tk.Text(edit_frame, font=("Consolas", 10),
                                      bg="#1e1e1e", fg="#d4d4d4", insertbackground="white")
        self.config_editor.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(edit_frame, command=self.config_editor.yview)
        sb.pack(side="right", fill="y")
        self.config_editor.configure(yscrollcommand=sb.set)
        self._current_config_path = None
        # 启动时刷新
        self.root.after(800, self._refresh_config_files)

    def _refresh_config_files(self):
        """刷新配置文件列表"""
        self.config_file_listbox.delete(0, "end")
        game_dir = self._get_tools_instance_dir()
        if not game_dir:
            return
        config_dir = Path(game_dir) / "config"
        if not config_dir.exists():
            self.config_file_listbox.insert("end", "(config 文件夹不存在)")
            return
        # 列出常见配置文件
        config_files = []
        for ext in ("*.json", "*.toml", "*.cfg", "*.txt", "*.properties", "*.yaml", "*.yml"):
            config_files.extend(config_dir.rglob(ext))
        config_files.sort(key=lambda x: x.name.lower())
        for cf in config_files:
            rel = cf.relative_to(config_dir)
            self.config_file_listbox.insert("end", str(rel))

    def _load_config_file(self):
        """加载选中的配置文件"""
        sel = self.config_file_listbox.curselection()
        if not sel:
            return
        game_dir = self._get_tools_instance_dir()
        if not game_dir:
            return
        rel_path = self.config_file_listbox.get(sel[0])
        if rel_path.startswith("("):
            return
        config_path = Path(game_dir) / "config" / rel_path
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.config_editor.delete("1.0", "end")
            self.config_editor.insert("1.0", content)
            self._current_config_path = config_path
            self.config_path_label.config(text=str(rel_path))
        except Exception as exc:
            messagebox.showerror("读取失败", str(exc))

    def _save_config_file(self):
        """保存配置文件"""
        if not self._current_config_path:
            messagebox.showinfo("提示", "请先选择一个配置文件")
            return
        try:
            content = self.config_editor.get("1.0", "end-1c")
            with open(self._current_config_path, 'w', encoding='utf-8') as f:
                f.write(content)
            messagebox.showinfo("保存成功", "配置文件已保存:\n" + str(self._current_config_path))
        except Exception as exc:
            messagebox.showerror("保存失败", str(exc))

    def _undo_config(self):
        """撤销配置编辑(重新加载文件)"""
        if self._current_config_path:
            self._load_config_file()

    # ---- 崩溃日志分析 ----
    def _build_crash_tab(self):
        """崩溃日志分析页"""
        tab = ttk.Frame(self.tools_nb)
        self.tools_nb.add(tab, text=" 💥 崩溃分析 ")
        # 顶部
        top = ttk.Frame(tab)
        top.pack(fill="x", padx=6, pady=6)
        ttk.Button(top, text="🔄 刷新日志列表", command=self._refresh_crash_logs).pack(
            side="left", padx=2)
        ttk.Button(top, text="🔍 智能分析", command=self._analyze_crash_advanced).pack(
            side="left", padx=2)
        ttk.Button(top, text="📁 打开日志文件夹", command=self._open_crash_logs_dir).pack(
            side="left", padx=2)
        # 左侧: 日志列表
        left = ttk.Frame(tab)
        left.pack(side="left", fill="y", padx=6, pady=6)
        ttk.Label(left, text="崩溃日志:").pack(anchor="w")
        self.crash_log_listbox = tk.Listbox(left, width=40, font=("Consolas", 9))
        self.crash_log_listbox.pack(fill="y", expand=True)
        # 右侧: 分析结果
        right = ttk.Frame(tab)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text="分析结果:").pack(anchor="w")
        result_frame = ttk.Frame(right)
        result_frame.pack(fill="both", expand=True)
        self.crash_result = tk.Text(result_frame, font=("Consolas", 9),
                                     bg="#1e1e1e", fg="#00ff00", wrap="word")
        self.crash_result.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(result_frame, command=self.crash_result.yview)
        sb.pack(side="right", fill="y")
        self.crash_result.configure(yscrollcommand=sb.set)
        self.root.after(1000, self._refresh_crash_logs)

    def _refresh_crash_logs(self):
        """刷新崩溃日志列表"""
        self.crash_log_listbox.delete(0, "end")
        game_dir = self._get_tools_instance_dir()
        if not game_dir:
            return
        crash_dir = Path(game_dir) / "crash-reports"
        if not crash_dir.exists():
            self.crash_log_listbox.insert("end", "(没有崩溃日志)")
            return
        logs = sorted(crash_dir.glob("*.txt"), reverse=True)
        for log in logs:
            mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(log.stat().st_mtime))
            self.crash_log_listbox.insert("end", "{} | {}".format(log.name, mtime))

    def _analyze_crash_log(self):
        """分析崩溃日志"""
        sel = self.crash_log_listbox.curselection()
        if not sel:
            messagebox.showinfo("提示", "请先选择一个崩溃日志")
            return
        game_dir = self._get_tools_instance_dir()
        if not game_dir:
            return
        item = self.crash_log_listbox.get(sel[0])
        if item.startswith("("):
            return
        log_name = item.split(" | ")[0]
        log_path = Path(game_dir) / "crash-reports" / log_name
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as exc:
            messagebox.showerror("读取失败", str(exc))
            return
        self.crash_result.delete("1.0", "end")
        self.crash_result.insert("end", "=== 崩溃日志分析 ===\n\n")
        self.crash_result.insert("end", "日志文件: {}\n\n".format(log_name))
        # 提取关键信息
        lines = content.split("\n")
        # 1. 崩溃原因
        for i, line in enumerate(lines):
            if "Description:" in line:
                desc = line.split("Description:")[1].strip()
                self.crash_result.insert("end", "【崩溃描述】\n{}\n\n".format(desc))
                break
        # 2. 异常类型
        for line in lines:
            if line.strip().startswith("java.lang.") or line.strip().startswith("net.minecraft."):
                self.crash_result.insert("end", "【异常类型】\n{}\n\n".format(line.strip()))
                break
        # 3. 可疑模组
        suspect_mods = []
        in_stack = False
        for line in lines:
            if "Stacktrace" in line or "at net.minecraft" in line:
                in_stack = True
            if in_stack and ("mods" in line.lower() or ".jar" in line.lower()):
                # 提取模组名
                import re
                jar_match = re.search(r'([a-zA-Z0-9_.-]+\.jar)', line)
                if jar_match:
                    mod_name = jar_match.group(1)
                    if mod_name not in suspect_mods and mod_name != "minecraft.jar":
                        suspect_mods.append(mod_name)
            if len(suspect_mods) >= 10:
                break
        if suspect_mods:
            self.crash_result.insert("end", "【可疑模组】(出现在堆栈跟踪中)\n")
            for mod in suspect_mods[:5]:
                self.crash_result.insert("end", "  - {}\n".format(mod))
            self.crash_result.insert("end", "\n")
        # 4. 建议
        self.crash_result.insert("end", "【建议】\n")
        self.crash_result.insert("end", "1. 尝试移除上面列出的可疑模组, 逐个测试\n")
        self.crash_result.insert("end", "2. 检查模组版本是否与游戏版本匹配\n")
        self.crash_result.insert("end", "3. 检查 Forge/Fabric 加载器版本是否正确\n")
        self.crash_result.insert("end", "4. 检查 Java 版本是否符合要求\n")
        self.crash_result.insert("end", "5. 分配更多内存(建议 4G 以上)\n")
        self.crash_result.insert("end", "6. 更新所有模组到最新版本\n")
        self.crash_result.insert("end", "\n分析完成! 建议逐个移除可疑模组来定位问题。\n")

    def _open_crash_logs_dir(self):
        """打开崩溃日志文件夹"""
        game_dir = self._get_tools_instance_dir()
        if not game_dir:
            return
        import os
        crash_dir = str(Path(game_dir) / "crash-reports")
        Path(crash_dir).mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(crash_dir)
        except Exception:
            messagebox.showinfo("崩溃日志目录", crash_dir)


    # ---- 性能监控 ----
    def _build_performance_tab(self):
        """性能监控页"""
        tab = ttk.Frame(self.tools_nb)
        self.tools_nb.add(tab, text=" 📊 性能监控 ")
        content = ttk.Frame(tab)
        content.pack(fill="both", expand=True, padx=20, pady=20)
        # 状态显示
        self._perf_status_label = ttk.Label(content, text="游戏未运行",
                                              font=("Arial", 14, "bold"))
        self._perf_status_label.pack(pady=10)
        # 性能数据
        perf_frame = ttk.LabelFrame(content, text=" 游戏进程性能 ")
        perf_frame.pack(fill="x", pady=10)
        self._perf_cpu_label = ttk.Label(perf_frame, text="CPU 使用率: --",
                                          font=("Arial", 11))
        self._perf_cpu_label.pack(anchor="w", padx=10, pady=5)
        self._perf_mem_label = ttk.Label(perf_frame, text="内存使用: --",
                                          font=("Arial", 11))
        self._perf_mem_label.pack(anchor="w", padx=10, pady=5)
        self._perf_uptime_label = ttk.Label(perf_frame, text="运行时间: --",
                                              font=("Arial", 11))
        self._perf_uptime_label.pack(anchor="w", padx=10, pady=5)
        self._perf_pid_label = ttk.Label(perf_frame, text="进程 PID: --",
                                          font=("Arial", 11))
        self._perf_pid_label.pack(anchor="w", padx=10, pady=5)
        # 系统性能
        sys_frame = ttk.LabelFrame(content, text=" 系统性能 ")
        sys_frame.pack(fill="x", pady=10)
        self._perf_sys_cpu_label = ttk.Label(sys_frame, text="系统 CPU: --",
                                              font=("Arial", 11))
        self._perf_sys_cpu_label.pack(anchor="w", padx=10, pady=5)
        self._perf_sys_mem_label = ttk.Label(sys_frame, text="系统内存: --",
                                              font=("Arial", 11))
        self._perf_sys_mem_label.pack(anchor="w", padx=10, pady=5)
        # 控制按钮
        btn_frame = ttk.Frame(content)
        btn_frame.pack(pady=10)
        self._perf_refresh_btn = ttk.Button(btn_frame, text="🔄 刷新",
                                             command=self._refresh_performance)
        self._perf_refresh_btn.pack(side="left", padx=5)
        self._perf_auto_var = tk.BooleanVar(value=False)
        self._perf_auto_check = ttk.Checkbutton(btn_frame, text="自动刷新(每2秒)",
                                                  variable=self._perf_auto_var,
                                                  command=self._toggle_auto_perf)
        self._perf_auto_check.pack(side="left", padx=5)
        # 提示
        # FPS显示
        self._fps_label = ttk.Label(content, text="🎮 FPS: -- (需游戏联动Mod)",
                                     font=("Arial", 11, "bold"), foreground="#ff8800")
        self._fps_label.pack(pady=5)
        ttk.Button(content, text="▶ 启动FPS监控",
                   command=self._start_fps_monitor).pack(pady=5)
        ttk.Label(content, text="提示: FPS数据需要游戏联动Mod支持, 或按F3查看",

                  foreground="#666", font=("Arial", 9)).pack(pady=10)
        # 启动时刷新一次
        self.root.after(1000, self._refresh_performance)

    def _find_minecraft_process(self):
        """查找 Minecraft 游戏进程"""
        try:
            import psutil
        except ImportError:
            return None
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                name = proc.info["name"].lower()
                cmdline = " ".join(proc.info.get("cmdline", [])).lower()
                if "java" in name and ("minecraft" in cmdline or "net.minecraft" in cmdline
                                       or "launcher" in cmdline):
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None

    def _refresh_performance(self):
        """刷新性能数据"""
        try:
            import psutil
        except ImportError:
            self._perf_status_label.config(text="psutil 未安装, 无法监控性能")
            return
        # 系统性能
        try:
            sys_cpu = psutil.cpu_percent(interval=0.5)
            sys_mem = psutil.virtual_memory()
            self._perf_sys_cpu_label.config(text="系统 CPU: {:.1f}%".format(sys_cpu))
            self._perf_sys_mem_label.config(
                text="系统内存: {:.1f} GB / {:.1f} GB ({:.1f}%)".format(
                    sys_mem.used / 1024**3, sys_mem.total / 1024**3, sys_mem.percent))
        except Exception:
            pass
        # 游戏进程
        proc = self._find_minecraft_process()
        if proc:
            try:
                self._perf_status_label.config(text="🎮 游戏运行中", foreground="#00aa00")
                cpu = proc.cpu_percent(interval=0.5)
                mem = proc.memory_info()
                mem_mb = mem.rss / 1024**2
                create_time = proc.create_time()
                uptime = time.time() - create_time
                hours = int(uptime // 3600)
                minutes = int((uptime % 3600) // 60)
                self._perf_cpu_label.config(text="CPU 使用率: {:.1f}%".format(cpu))
                self._perf_mem_label.config(text="内存使用: {:.1f} MB".format(mem_mb))
                self._perf_uptime_label.config(
                    text="运行时间: {}小时{}分钟".format(hours, minutes))
                self._perf_pid_label.config(text="进程 PID: {}".format(proc.pid))
            except Exception as exc:
                self._perf_status_label.config(text="读取性能数据失败: " + str(exc))
        else:
            self._perf_status_label.config(text="游戏未运行", foreground="#999")
            self._perf_cpu_label.config(text="CPU 使用率: --")
            self._perf_mem_label.config(text="内存使用: --")
            self._perf_uptime_label.config(text="运行时间: --")
            self._perf_pid_label.config(text="进程 PID: --")

    def _toggle_auto_perf(self):
        """切换自动刷新"""
        if self._perf_auto_var.get():
            self._auto_perf_loop()
        else:
            if hasattr(self, "_perf_auto_job"):
                self.root.after_cancel(self._perf_auto_job)

    def _auto_perf_loop(self):
        """自动刷新循环"""
        if not self._perf_auto_var.get():
            return
        self._refresh_performance()
        self._perf_auto_job = self.root.after(2000, self._auto_perf_loop)

    # ---- 模组排序 ----
    def _build_mod_sort_tab(self):
        """模组排序页"""
        tab = ttk.Frame(self.tools_nb)
        self.tools_nb.add(tab, text=" 🔀 模组排序 ")
        content = ttk.Frame(tab)
        content.pack(fill="both", expand=True, padx=10, pady=10)
        # 说明
        ttk.Label(content, text="调整模组加载顺序(上移/下移), 修改后需要重启游戏生效",
                  foreground="#666").pack(anchor="w", pady=(0, 5))
        # 列表
        list_frame = ttk.Frame(content)
        list_frame.pack(fill="both", expand=True)
        self._mod_sort_listbox = tk.Listbox(list_frame, font=("Consolas", 10),
                                             selectmode="single")
        self._mod_sort_listbox.pack(side="left", fill="both", expand=True, padx=(0, 5))
        sb = ttk.Scrollbar(list_frame, command=self._mod_sort_listbox.yview)
        sb.pack(side="right", fill="y")
        self._mod_sort_listbox.configure(yscrollcommand=sb.set)
        # 按钮
        btn_frame = ttk.Frame(content)
        btn_frame.pack(fill="x", pady=10)
        ttk.Button(btn_frame, text="⬆ 上移", command=self._move_mod_up).pack(
            side="left", padx=2)
        ttk.Button(btn_frame, text="⬇ 下移", command=self._move_mod_down).pack(
            side="left", padx=2)
        ttk.Button(btn_frame, text="🔝 置顶", command=self._move_mod_top).pack(
            side="left", padx=2)
        ttk.Button(btn_frame, text="🔚 置底", command=self._move_mod_bottom).pack(
            side="left", padx=2)
        ttk.Separator(btn_frame, orient="vertical").pack(side="left", fill="y", padx=5)
        ttk.Button(btn_frame, text="🔄 刷新", command=self._refresh_mod_sort).pack(
            side="left", padx=2)
        ttk.Button(btn_frame, text="💾 保存排序", command=self._save_mod_sort).pack(
            side="left", padx=2)
        ttk.Button(btn_frame, text="↩ 恢复默认", command=self._reset_mod_sort).pack(
            side="left", padx=2)
        # 状态
        self._mod_sort_status = ttk.Label(content, text="", foreground="#00aa00")
        self._mod_sort_status.pack(anchor="w", pady=5)
        # 启动时刷新
        self.root.after(1200, self._refresh_mod_sort)

    def _refresh_mod_sort(self):
        """刷新模组排序列表"""
        self._mod_sort_listbox.delete(0, "end")
        game_dir = self._get_tools_instance_dir()
        if not game_dir:
            self._mod_sort_status.config(text="请先选择实例")
            return
        mods_dir = Path(game_dir) / "mods"
        if not mods_dir.exists():
            self._mod_sort_status.config(text="mods 文件夹不存在")
            return
        mods = sorted(mods_dir.glob("*.jar"))
        if not mods:
            self._mod_sort_status.config(text="没有安装模组")
            return
        for i, mod in enumerate(mods):
            self._mod_sort_listbox.insert("end", "{:2d}. {}".format(i+1, mod.name))
        self._mod_sort_status.config(text="共 {} 个模组".format(len(mods)))

    def _move_mod_up(self):
        """上移选中的模组"""
        sel = self._mod_sort_listbox.curselection()
        if not sel or sel[0] == 0:
            return
        idx = sel[0]
        item = self._mod_sort_listbox.get(idx)
        self._mod_sort_listbox.delete(idx)
        self._mod_sort_listbox.insert(idx-1, item)
        self._mod_sort_listbox.selection_set(idx-1)
        self._mod_sort_status.config(text="已上移, 记得点「保存排序」")

    def _move_mod_down(self):
        """下移选中的模组"""
        sel = self._mod_sort_listbox.curselection()
        if not sel or sel[0] >= self._mod_sort_listbox.size() - 1:
            return
        idx = sel[0]
        item = self._mod_sort_listbox.get(idx)
        self._mod_sort_listbox.delete(idx)
        self._mod_sort_listbox.insert(idx+1, item)
        self._mod_sort_listbox.selection_set(idx+1)
        self._mod_sort_status.config(text="已下移, 记得点「保存排序」")

    def _move_mod_top(self):
        """置顶选中的模组"""
        sel = self._mod_sort_listbox.curselection()
        if not sel or sel[0] == 0:
            return
        idx = sel[0]
        item = self._mod_sort_listbox.get(idx)
        self._mod_sort_listbox.delete(idx)
        self._mod_sort_listbox.insert(0, item)
        self._mod_sort_listbox.selection_set(0)
        self._mod_sort_status.config(text="已置顶, 记得点「保存排序」")

    def _move_mod_bottom(self):
        """置底选中的模组"""
        sel = self._mod_sort_listbox.curselection()
        if not sel or sel[0] >= self._mod_sort_listbox.size() - 1:
            return
        idx = sel[0]
        item = self._mod_sort_listbox.get(idx)
        self._mod_sort_listbox.delete(idx)
        self._mod_sort_listbox.insert("end", item)
        self._mod_sort_listbox.selection_set("end")
        self._mod_sort_status.config(text="已置底, 记得点「保存排序」")

    def _save_mod_sort(self):
        """保存模组排序(通过重命名文件, 加数字前缀)"""
        game_dir = self._get_tools_instance_dir()
        if not game_dir:
            return
        mods_dir = Path(game_dir) / "mods"
        if not mods_dir.exists():
            return
        # 获取当前列表顺序
        items = [self._mod_sort_listbox.get(i) for i in range(self._mod_sort_listbox.size())]
        if not items:
            return
        try:
            # 先去掉所有数字前缀
            for mod in mods_dir.glob("*.jar"):
                name = mod.name
                # 去掉开头的数字前缀(如 "01_", "02-")
                import re
                new_name = re.sub(r'^\d+[ _\-]', '', name)
                if new_name != name:
                    mod.rename(mods_dir / new_name)
            # 重新加数字前缀
            for i, item in enumerate(items):
                # 提取原始文件名(去掉序号前缀)
                import re
                orig_name = re.sub(r'^\d+\.\s*', '', item)
                orig_name = re.sub(r'^\d+[ _\-]', '', orig_name)
                src = mods_dir / orig_name
                if src.exists():
                    new_name = "{:02d}_{}".format(i+1, orig_name)
                    src.rename(mods_dir / new_name)
            self._mod_sort_status.config(text="排序已保存! 重启游戏后生效")
            messagebox.showinfo("保存成功", "模组排序已保存!\n\n注意: 通过文件名前缀控制加载顺序, 重启游戏后生效")
            self._refresh_mod_sort()
        except Exception as exc:
            messagebox.showerror("保存失败", str(exc))

    def _reset_mod_sort(self):
        """恢复默认排序(去掉数字前缀)"""
        game_dir = self._get_tools_instance_dir()
        if not game_dir:
            return
        mods_dir = Path(game_dir) / "mods"
        if not mods_dir.exists():
            return
        if not messagebox.askyesno("确认", "确定恢复默认排序吗?\n(去掉所有数字前缀)"):
            return
        try:
            import re
            for mod in mods_dir.glob("*.jar"):
                name = mod.name
                new_name = re.sub(r'^\d+[ _\-]', '', name)
                if new_name != name:
                    mod.rename(mods_dir / new_name)
            self._mod_sort_status.config(text="已恢复默认排序")
            self._refresh_mod_sort()
        except Exception as exc:
            messagebox.showerror("操作失败", str(exc))


    # ---- 材质包预览 ----
    def _build_resourcepack_preview_tab(self):
        """材质包预览页"""
        tab = ttk.Frame(self.tools_nb)
        self.tools_nb.add(tab, text=" 🎨 材质包预览 ")
        content = ttk.Frame(tab)
        content.pack(fill="both", expand=True, padx=10, pady=10)
        # 左侧: 资源包列表
        left = ttk.LabelFrame(content, text=" 已安装的资源包 ")
        left.pack(side="left", fill="y", padx=(0, 5))
        self._rp_listbox = tk.Listbox(left, width=35, font=("Consolas", 9))
        self._rp_listbox.pack(side="left", fill="y", expand=True, padx=5, pady=5)
        rp_sb = ttk.Scrollbar(left, command=self._rp_listbox.yview)
        rp_sb.pack(side="right", fill="y")
        self._rp_listbox.configure(yscrollcommand=rp_sb.set)
        self._rp_listbox.bind("<<ListboxSelect>>", lambda e: self._preview_resourcepack())
        # 右侧: 预览
        right = ttk.LabelFrame(content, text=" 预览 ")
        right.pack(side="left", fill="both", expand=True, padx=(5, 0))
        # 图标
        self._rp_icon_label = tk.Label(right, text="选择一个资源包", font=("Arial", 12))
        self._rp_icon_label.pack(pady=10)
        # 信息
        self._rp_info_label = tk.Label(right, text="", justify="left", anchor="w",
                                        font=("Arial", 10), wraplength=400)
        self._rp_info_label.pack(fill="x", padx=10, pady=5)
        # 描述
        self._rp_desc_label = tk.Label(right, text="", justify="left", anchor="w",
                                        font=("Arial", 9), wraplength=400, foreground="#666")
        self._rp_desc_label.pack(fill="x", padx=10, pady=5)
        # 按钮
        btn_frame = ttk.Frame(right)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="🔄 刷新列表", command=self._refresh_resourcepacks).pack(
            side="left", padx=2)
        ttk.Button(btn_frame, text="📁 打开文件夹", command=self._open_resourcepacks_dir).pack(
            side="left", padx=2)
        ttk.Button(btn_frame, text="📂 打开资源包", command=self._open_resourcepack_file).pack(
            side="left", padx=2)
        # 提示
        ttk.Label(right, text="提示: 显示资源包的图标、名称、描述和版本信息",
                  foreground="#666", font=("Arial", 9)).pack(pady=10)
        # 启动时刷新
        self.root.after(1500, self._refresh_resourcepacks)

    def _refresh_resourcepacks(self):
        """刷新资源包列表"""
        self._rp_listbox.delete(0, "end")
        game_dir = self._get_tools_instance_dir()
        if not game_dir:
            return
        rp_dir = Path(game_dir) / "resourcepacks"
        if not rp_dir.exists():
            self._rp_listbox.insert("end", "(resourcepacks 文件夹不存在)")
            return
        # 列出 zip 和文件夹
        packs = []
        for item in rp_dir.iterdir():
            if item.is_file() and item.suffix.lower() in (".zip",):
                packs.append(item)
            elif item.is_dir():
                packs.append(item)
        packs.sort(key=lambda x: x.name.lower())
        if not packs:
            self._rp_listbox.insert("end", "(没有安装资源包)")
            return
        for pack in packs:
            self._rp_listbox.insert("end", pack.name)

    def _preview_resourcepack(self):
        """预览选中的资源包"""
        sel = self._rp_listbox.curselection()
        if not sel:
            return
        game_dir = self._get_tools_instance_dir()
        if not game_dir:
            return
        pack_name = self._rp_listbox.get(sel[0])
        if pack_name.startswith("("):
            return
        rp_dir = Path(game_dir) / "resourcepacks"
        pack_path = rp_dir / pack_name
        # 读取 pack.mcmeta
        mcmeta = None
        icon_data = None
        try:
            if pack_path.is_file() and pack_path.suffix.lower() == ".zip":
                import zipfile
                with zipfile.ZipFile(pack_path, 'r') as zf:
                    # 读取 mcmeta
                    if "pack.mcmeta" in zf.namelist():
                        with zf.open("pack.mcmeta") as f:
                            mcmeta = json.load(f)
                    # 读取图标
                    if "pack.png" in zf.namelist():
                        import io
                        from PIL import Image, ImageTk
                        icon_data = zf.read("pack.png")
            elif pack_path.is_dir():
                mcmeta_file = pack_path / "pack.mcmeta"
                if mcmeta_file.exists():
                    with open(mcmeta_file, 'r', encoding='utf-8') as f:
                        mcmeta = json.load(f)
                icon_file = pack_path / "pack.png"
                if icon_file.exists():
                    with open(icon_file, 'rb') as f:
                        icon_data = f.read()
        except Exception as exc:
            self._rp_info_label.config(text="读取失败: " + str(exc))
            return
        # 显示信息
        if mcmeta and "pack" in mcmeta:
            pack_info = mcmeta["pack"]
            name = pack_info.get("description", pack_name)
            pack_format = pack_info.get("pack_format", "未知")
            self._rp_info_label.config(
                text="名称: {}\n版本格式: {}\n文件: {}".format(
                    name if isinstance(name, str) else pack_name,
                    pack_format, pack_name))
            if isinstance(name, list):
                # 复杂描述(带颜色代码等), 简化显示
                desc_text = " ".join(str(x) for x in name if isinstance(x, str))
                self._rp_desc_label.config(text="描述: " + desc_text)
            else:
                self._rp_desc_label.config(text="描述: " + str(name))
        else:
            self._rp_info_label.config(text="文件: {}\n(没有 pack.mcmeta)".format(pack_name))
            self._rp_desc_label.config(text="")
        # 显示图标
        if icon_data:
            try:
                from PIL import Image, ImageTk
                import io
                img = Image.open(io.BytesIO(icon_data)).convert("RGBA")
                w, h = img.size
                scale = max(1, 128 // max(w, h))
                img = img.resize((w * scale, h * scale), Image.NEAREST)
                photo = ImageTk.PhotoImage(img)
                self._rp_icon_label.config(image=photo, text="")
                self._rp_icon_label.image = photo
            except Exception:
                self._rp_icon_label.config(text="📦", font=("Arial", 48), image="")
        else:
            self._rp_icon_label.config(text="📦", font=("Arial", 48), image="")
        # 保存当前选中的路径
        self._current_rp_path = pack_path

    def _open_resourcepacks_dir(self):
        """打开资源包文件夹"""
        game_dir = self._get_tools_instance_dir()
        if not game_dir:
            return
        import os
        rp_dir = str(Path(game_dir) / "resourcepacks")
        Path(rp_dir).mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(rp_dir)
        except Exception:
            messagebox.showinfo("资源包目录", rp_dir)

    def _open_resourcepack_file(self):
        """打开选中的资源包文件/文件夹"""
        if not hasattr(self, "_current_rp_path") or not self._current_rp_path:
            messagebox.showinfo("提示", "请先选择一个资源包")
            return
        import os
        try:
            if self._current_rp_path.is_file():
                # 用压缩软件打开 zip
                os.startfile(str(self._current_rp_path))
            else:
                os.startfile(str(self._current_rp_path))
        except Exception as exc:
            messagebox.showerror("打开失败", str(exc))

    # ---- 截图管理 ----
    def _build_screenshot_tab(self):
        """截图管理页"""
        tab = ttk.Frame(self.tools_nb)
        self.tools_nb.add(tab, text=" 📷 截图 ")
        # 工具栏
        bar = ttk.Frame(tab)
        bar.pack(fill="x", padx=6, pady=4)
        ttk.Button(bar, text="🔄 刷新", command=self._refresh_screenshots).pack(
            side="left", padx=2)
        ttk.Button(bar, text="📁 打开文件夹", command=self._open_screenshots_dir).pack(
            side="left", padx=2)
        ttk.Button(bar, text="🗑 删除选中", command=self._delete_screenshot).pack(
            side="left", padx=2)
        self.screenshot_count_label = ttk.Label(bar, text="")
        self.screenshot_count_label.pack(side="left", padx=10)
        # 截图列表
        list_frame = ttk.Frame(tab)
        list_frame.pack(fill="both", expand=True, padx=6, pady=4)
        self.screenshot_listbox = tk.Listbox(list_frame, font=("Consolas", 9))
        self.screenshot_listbox.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(list_frame, command=self.screenshot_listbox.yview)
        sb.pack(side="right", fill="y")
        self.screenshot_listbox.configure(yscrollcommand=sb.set)
        self.screenshot_listbox.bind("<Double-Button-1>", lambda e: self._view_screenshot())

    def _refresh_screenshots(self):
        """刷新截图列表"""
        self.screenshot_listbox.delete(0, "end")
        game_dir = self._get_tools_instance_dir()
        if not game_dir:
            self.screenshot_count_label.config(text="请先选择实例")
            return
        shots_dir = Path(game_dir) / "screenshots"
        if not shots_dir.exists():
            self.screenshot_count_label.config(text="截图文件夹不存在")
            return
        shots = sorted(shots_dir.glob("*.png"), reverse=True)
        for shot in shots:
            size = shot.stat().st_size / 1024
            mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(shot.stat().st_mtime))
            self.screenshot_listbox.insert("end", "{} | {:.0f}KB | {}".format(
                shot.name, size, mtime))
        self.screenshot_count_label.config(text="共 {} 张截图".format(len(shots)))

    def _open_screenshots_dir(self):
        """打开截图文件夹"""
        game_dir = self._get_tools_instance_dir()
        if not game_dir:
            messagebox.showwarning("提示", "请先在工具页顶部选择实例")
            return
        import os
        shots_dir = str(Path(game_dir) / "screenshots")
        Path(shots_dir).mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(shots_dir)
        except Exception:
            messagebox.showinfo("截图目录", shots_dir)

    def _delete_screenshot(self):
        """删除选中的截图"""
        sel = self.screenshot_listbox.curselection()
        if not sel:
            messagebox.showinfo("提示", "请先选择截图")
            return
        game_dir = self._get_tools_instance_dir()
        if not game_dir:
            return
        item = self.screenshot_listbox.get(sel[0])
        filename = item.split(" | ")[0]
        shot_path = Path(game_dir) / "screenshots" / filename
        if messagebox.askyesno("确认", "确定删除截图 {}?".format(filename)):
            try:
                shot_path.unlink()
                self._refresh_screenshots()
            except Exception as exc:
                messagebox.showerror("错误", str(exc))

    def _view_screenshot(self):
        """查看截图(用默认图片查看器)"""
        sel = self.screenshot_listbox.curselection()
        if not sel:
            return
        game_dir = self._get_tools_instance_dir()
        if not game_dir:
            return
        item = self.screenshot_listbox.get(sel[0])
        filename = item.split(" | ")[0]
        shot_path = Path(game_dir) / "screenshots" / filename
        if shot_path.exists():
            import os
            os.startfile(str(shot_path))

    # ---- 存档/世界管理 ----
    def _build_save_tab(self):
        """存档管理页"""
        tab = ttk.Frame(self.tools_nb)
        self.tools_nb.add(tab, text=" 💾 存档 ")
        # 工具栏
        bar = ttk.Frame(tab)
        bar.pack(fill="x", padx=6, pady=4)
        ttk.Button(bar, text="🔄 刷新", command=self._refresh_saves).pack(
            side="left", padx=2)
        ttk.Button(bar, text="📦 备份选中", command=self._backup_save).pack(
            side="left", padx=2)
        ttk.Button(bar, text="📂 备份管理", command=self._manage_backups).pack(
            side="left", padx=2)
        ttk.Button(bar, text="📁 打开存档目录", command=self._open_saves_dir).pack(
            side="left", padx=2)
        # 存档列表
        list_frame = ttk.Frame(tab)
        list_frame.pack(fill="both", expand=True, padx=6, pady=4)
        self.save_listbox = tk.Listbox(list_frame, font=("Consolas", 9))
        self.save_listbox.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(list_frame, command=self.save_listbox.yview)
        sb.pack(side="right", fill="y")
        self.save_listbox.configure(yscrollcommand=sb.set)
        # 存档详情
        self.save_detail_label = ttk.Label(tab, text="", justify="left", anchor="w")
        self.save_detail_label.pack(fill="x", padx=6, pady=4)
        self.save_listbox.bind("<<ListboxSelect>>", lambda e: self._show_save_detail())

    def _refresh_saves(self):
        """刷新存档列表"""
        self.save_listbox.delete(0, "end")
        game_dir = self._get_tools_instance_dir()
        if not game_dir:
            return
        saves_dir = Path(game_dir) / "saves"
        if not saves_dir.exists():
            return
        saves = sorted([d for d in saves_dir.iterdir() if d.is_dir()],
                       key=lambda x: x.stat().st_mtime, reverse=True)
        for save in saves:
            mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(save.stat().st_mtime))
            self.save_listbox.insert("end", "{} | {}".format(save.name, mtime))

    def _show_save_detail(self):
        """显示存档详情"""
        sel = self.save_listbox.curselection()
        if not sel:
            return
        game_dir = self._get_tools_instance_dir()
        if not game_dir:
            return
        item = self.save_listbox.get(sel[0])
        save_name = item.split(" | ")[0]
        save_path = Path(game_dir) / "saves" / save_name
        try:
            # 读取 level.dat 基本信息(简化版, 只显示文件大小和修改时间)
            size = sum(f.stat().st_size for f in save_path.rglob("*") if f.is_file())
            size_mb = size / 1024 / 1024
            mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(save_path.stat().st_mtime))
            file_count = sum(1 for _ in save_path.rglob("*") if _.is_file())
            self.save_detail_label.config(
                text="存档: {}\n大小: {:.2f} MB | 文件数: {} | 最后修改: {}".format(
                    save_name, size_mb, file_count, mtime))
        except Exception as exc:
            self.save_detail_label.config(text="读取详情失败: " + str(exc))

    def _backup_save(self):
        """备份选中的存档"""
        sel = self.save_listbox.curselection()
        if not sel:
            messagebox.showinfo("提示", "请先选择存档")
            return
        game_dir = self._get_tools_instance_dir()
        if not game_dir:
            return
        item = self.save_listbox.get(sel[0])
        save_name = item.split(" | ")[0]
        save_path = Path(game_dir) / "saves" / save_name
        # 备份目录
        backup_dir = Path(game_dir) / "voxellauncher_backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_name = "{}_{}.zip".format(save_name, timestamp)
        backup_path = backup_dir / backup_name
        try:
            import zipfile
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file in save_path.rglob("*"):
                    if file.is_file():
                        zf.write(file, file.relative_to(save_path.parent))
            messagebox.showinfo("备份成功", "存档已备份到:\n" + str(backup_path))
        except Exception as exc:
            messagebox.showerror("备份失败", str(exc))

    def _manage_backups(self):
        """管理备份"""
        game_dir = self._get_tools_instance_dir()
        if not game_dir:
            return
        backup_dir = Path(game_dir) / "voxellauncher_backups"
        if not backup_dir.exists():
            messagebox.showinfo("提示", "还没有备份文件")
            return
        import os
        os.startfile(str(backup_dir))

    def _open_saves_dir(self):
        """打开存档目录"""
        game_dir = self._get_tools_instance_dir()
        if not game_dir:
            return
        import os
        saves_dir = str(Path(game_dir) / "saves")
        Path(saves_dir).mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(saves_dir)
        except Exception:
            messagebox.showinfo("存档目录", saves_dir)

    # ---------------- 关于页 ----------------
    def _build_multiplayer_tab(self):
        """构建联机页面"""
        tab = self.tab_multiplayer

        # 顶部说明
        info_frame = ttk.LabelFrame(tab, text="联机说明")
        info_frame.pack(fill="x", padx=10, pady=8)
        ttk.Label(info_frame, text="局域网: 自动扫描同一WiFi/路由器下的MC世界, 一键加入\n"
                                  "外网: 需要对方开放端口或使用内网穿透, 手动添加服务器地址",
                  wraplength=700, justify="left").pack(padx=10, pady=8)

        # 工具栏
        toolbar = ttk.Frame(tab)
        toolbar.pack(fill="x", padx=10, pady=4)
        ttk.Button(toolbar, text="🔍 扫描局域网",
                   command=self._scan_lan).pack(side="left", padx=2)
        ttk.Button(toolbar, text="➕ 添加服务器",
                   command=self._add_server).pack(side="left", padx=2)
        ttk.Button(toolbar, text="🔄 刷新状态",
                   command=self._refresh_servers).pack(side="left", padx=2)
        ttk.Button(toolbar, text="🗑 删除选中",
                   command=self._remove_server).pack(side="left", padx=2)
        ttk.Button(toolbar, text="🌐 一键局域网",
                   command=self._one_click_lan).pack(side="left", padx=2)
        ttk.Button(toolbar, text="🎮 加入选中服务器",
                   command=self._join_server).pack(side="right", padx=2)

        # 本机IP显示
        ip_frame = ttk.Frame(tab)
        ip_frame.pack(fill="x", padx=10, pady=4)
        self._lan_ip_label = ttk.Label(ip_frame, text="本机IP: 检测中...")
        self._lan_ip_label.pack(side="left")
        ttk.Button(ip_frame, text="复制IP",
                   command=self._copy_lan_ip).pack(side="left", padx=8)

        # 服务器列表
        list_frame = ttk.LabelFrame(tab, text="服务器列表")
        list_frame.pack(fill="both", expand=True, padx=10, pady=8)

        columns = ("name", "address", "players", "version", "type")
        self.mp_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12)
        self.mp_tree.heading("name", text="名称")
        self.mp_tree.heading("address", text="地址")
        self.mp_tree.heading("players", text="人数")
        self.mp_tree.heading("version", text="版本")
        self.mp_tree.heading("type", text="类型")
        self.mp_tree.column("name", width=200)
        self.mp_tree.column("address", width=200)
        self.mp_tree.column("players", width=80, anchor="center")
        self.mp_tree.column("version", width=120)
        self.mp_tree.column("type", width=80, anchor="center")
        self.mp_tree.pack(side="left", fill="both", expand=True, padx=4, pady=4)

        sb = ttk.Scrollbar(list_frame, orient="vertical", command=self.mp_tree.yview)
        sb.pack(side="right", fill="y")
        self.mp_tree.configure(yscrollcommand=sb.set)
        self.mp_tree.bind("<Double-1>", lambda e: self._join_server())

        # 内网穿透区域
        nat_frame = ttk.LabelFrame(tab, text="外网联机 - 内网穿透工具")
        nat_frame.pack(fill="x", padx=10, pady=8)

        ttk.Label(nat_frame, text="没有公网IP？用下面的工具把你的世界映射到外网，朋友就能连了。选一个喜欢的，点按钮去官网下载配置。",
                  wraplength=700, justify="left").pack(padx=10, pady=(8, 4), anchor="w")

        # 工具列表
        nat_tools = [
            ("Sakura Frp (樱花映射)", "国内免费，速度快，推荐新手用", "https://www.natfrp.com/"),
            ("OpenFrp", "国内免费，节点多，稳定", "https://openfrp.net/"),
            ("ngrok", "国外老牌，免费版有流量限制", "https://ngrok.com/"),
            ("ZeroTier", "P2P虚拟局域网，不用服务器", "https://www.zerotier.com/"),
            ("Tailscale", "P2P虚拟局域网，WireGuard底层", "https://tailscale.com/"),
            ("花生壳", "国内老牌，有免费版", "https://hsk.oray.com/"),
            ("cpolar", "国内，支持HTTP/TCP", "https://www.cpolar.com/"),
        ]

        nat_list_frame = ttk.Frame(nat_frame)
        nat_list_frame.pack(fill="x", padx=10, pady=6)

        for i, (name, desc, url) in enumerate(nat_tools):
            row = ttk.Frame(nat_list_frame)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=name, width=22, font=("微软雅黑", 9, "bold")).pack(side="left")
            ttk.Label(row, text=desc, foreground="#888", font=("微软雅黑", 8)).pack(side="left", padx=8)
            ttk.Button(row, text="去官网", width=8,
                       command=lambda u=url: self._open_url(u)).pack(side="right")

        # 使用说明
        help_frame = ttk.Frame(nat_frame)
        help_frame.pack(fill="x", padx=10, pady=(4, 8))
        ttk.Label(help_frame, text="使用步骤：", font=("微软雅黑", 9, "bold")).pack(anchor="w")
        steps = [
            "1. 选一个工具，点「去官网」注册账号并下载客户端",
            "2. 在工具里创建一条 TCP 隧道，本地端口填 25565（或你游戏里开放的端口）",
            "3. 启动隧道，工具会给你一个外网地址（比如 xxx.com:12345）",
            "4. 在游戏里 ESC -> 对局域网开放，记住端口",
            "5. 把外网地址发给朋友，朋友在启动器联机页「添加服务器」填这个地址就能连了",
        ]
        for step in steps:
            ttk.Label(help_frame, text=step, foreground="#aaa", font=("微软雅黑", 8)).pack(anchor="w", padx=10)

        # 状态
        self.mp_status = ttk.Label(tab, text="就绪")
        self.mp_status.pack(fill="x", padx=10, pady=4)

        # 初始化服务器列表
        self._server_list = multiplayer.ServerList()
        self._refresh_server_list()

        # 显示本机IP
        def _show_ip():
            ip = multiplayer.get_local_ip()
            self._lan_ip_label.config(text=f"本机IP: {ip}  (告诉朋友加这个)")
        self.root.after(500, _show_ip)

    def _refresh_server_list(self):
        """刷新服务器列表显示"""
        self.mp_tree.delete(*self.mp_tree.get_children())
        for srv in self._server_list.get_all():
            addr = multiplayer.get_server_address(srv)
            type_name = "局域网" if srv.get("type") == "lan" else "收藏"
            self.mp_tree.insert("", "end", values=(
                srv.get("name", ""), addr,
                srv.get("players", "?"),
                srv.get("version", "?"),
                type_name
            ))

    def _scan_lan(self):
        """扫描局域网"""
        self.mp_status.config(text="正在扫描局域网, 请稍候...")
        self._log("开始扫描局域网服务器...")

        def _worker():
            found = []
            def _callback(srv):
                found.append(srv)
                self.root.after(0, lambda: self._add_lan_server(srv))

            servers = multiplayer.scan_lan_servers(callback=_callback)
            self.root.after(0, lambda: self._on_scan_complete(len(servers)))

        threading.Thread(target=_worker, daemon=True).start()

    def _add_lan_server(self, srv):
        """添加扫描到的局域网服务器到列表"""
        addr = multiplayer.get_server_address(srv)
        # 检查是否已存在
        for item in self.mp_tree.get_children():
            vals = self.mp_tree.item(item, "values")
            if vals[1] == addr:
                return
        self.mp_tree.insert("", "end", values=(
            srv.get("name", "局域网世界"), addr,
            srv.get("players", "?"),
            srv.get("version", "?"),
            "局域网"
        ))

    def _on_scan_complete(self, count):
        """扫描完成"""
        self.mp_status.config(text=f"扫描完成, 找到 {count} 个服务器")
        self._log(f"局域网扫描完成, 找到 {count} 个服务器")

    def _add_server(self):
        """手动添加服务器"""
        from tkinter import simpledialog
        name = simpledialog.askstring("添加服务器", "服务器名称:", parent=self.root)
        if not name:
            return
        address = simpledialog.askstring("添加服务器", "服务器地址 (IP或域名, 可加:端口):", parent=self.root)
        if not address:
            return

        # 解析地址和端口
        if ":" in address:
            ip, port = address.rsplit(":", 1)
            try:
                port = int(port)
            except ValueError:
                port = 25565
        else:
            ip = address
            port = 25565

        self._server_list.add(name, ip, port)
        self._refresh_server_list()
        self.mp_status.config(text=f"已添加服务器: {name}")

    def _remove_server(self):
        """删除选中的服务器"""
        selection = self.mp_tree.selection()
        if not selection:
            self.mp_status.config(text="请先选择一个服务器")
            return
        for item in selection:
            idx = self.mp_tree.index(item)
            self._server_list.remove(idx)
        self._refresh_server_list()
        self.mp_status.config(text="已删除")

    def _refresh_servers(self):
        """刷新服务器状态"""
        self.mp_status.config(text="正在刷新服务器状态...")
        def _callback(i, srv):
            self.root.after(0, self._refresh_server_list)
        self._server_list.refresh(callback=_callback)
        self.mp_status.config(text="刷新完成")

    def _join_server(self):
        """加入选中的服务器"""
        selection = self.mp_tree.selection()
        if not selection:
            self.mp_status.config(text="请先选择一个服务器")
            return
        item = selection[0]
        vals = self.mp_tree.item(item, "values")
        address = vals[1]
        name = vals[0]

        # 解析地址
        if ":" in address:
            ip, port = address.rsplit(":", 1)
        else:
            ip = address
            port = "25565"

        self.mp_status.config(text=f"正在加入: {name} ({address})")
        self._log(f"加入服务器: {name} ({address})")

        # 启动游戏并连接服务器
        try:
            # 设置要连接的服务器地址 (通过启动参数)
            self._join_server_address = address
            # 启动游戏
            self._launch()
            # 启动后清除地址, 下次正常启动不连服务器
            def _clear():
                self._join_server_address = None
            self.root.after(5000, _clear)
        except Exception as e:
            self.mp_status.config(text=f"加入失败: {e}")
            self._log(f"加入服务器失败: {e}")
            self._join_server_address = None

    def _copy_lan_ip(self):
        """复制本机IP"""
        ip = multiplayer.get_local_ip()
        self.root.clipboard_clear()
        self.root.clipboard_append(ip)
        self.mp_status.config(text=f"IP已复制: {ip}")

    def _open_url(self, url):
        """打开网页"""
        try:
            webbrowser.open(url)
            self.mp_status.config(text=f"已打开: {url}")
        except Exception as e:
            self.mp_status.config(text=f"打开失败: {e}")

    # ---------------------------------------------------------------
    # 一键开服器页面
    # ---------------------------------------------------------------
    def _build_server_tab(self):
        """构建一键开服器页面"""
        import server_manager
        f = self.tab_server
        self._server_inst = None
        self._server_running = False

        # 顶部: 服务器列表和操作
        top = ttk.Frame(f)
        top.pack(fill="x", padx=10, pady=8)

        ttk.Label(top, text="服务器:", font=("", 10, "bold")).pack(side="left")
        self.server_combo = ttk.Combobox(top, state="readonly", width=25)
        self.server_combo.pack(side="left", padx=5)
        ttk.Button(top, text="刷新", command=self._refresh_server_list).pack(side="left", padx=2)
        ttk.Button(top, text="打开文件夹", command=self._open_server_dir).pack(side="left", padx=2)
        ttk.Button(top, text="删除", command=self._delete_server).pack(side="left", padx=2)

        # 创建新服务器区域
        create_frame = ttk.LabelFrame(f, text=" 创建新服务器 ")
        create_frame.pack(fill="x", padx=10, pady=5)

        row1 = ttk.Frame(create_frame)
        row1.pack(fill="x", padx=10, pady=5)
        ttk.Label(row1, text="MC版本:").pack(side="left")
        self.server_version = ttk.Entry(row1, width=12)
        self.server_version.insert(0, "1.21.1")
        self.server_version.pack(side="left", padx=5)
        ttk.Label(row1, text="类型:").pack(side="left", padx=(10,0))
        self.server_type = ttk.Combobox(row1, values=["原版", "Fabric"], width=10, state="readonly")
        self.server_type.set("原版")
        self.server_type.pack(side="left", padx=5)
        ttk.Label(row1, text="内存:").pack(side="left", padx=(10,0))
        self.server_memory = ttk.Combobox(row1, values=["1G", "2G", "4G", "6G", "8G"], width=6, state="readonly")
        self.server_memory.set("2G")
        self.server_memory.pack(side="left", padx=5)
        ttk.Button(row1, text="下载并创建", command=self._create_server).pack(side="left", padx=10)

        # 服务器控制
        ctrl_frame = ttk.Frame(f)
        ctrl_frame.pack(fill="x", padx=10, pady=5)
        self.server_start_btn = ttk.Button(ctrl_frame, text="▶ 启动服务器", command=self._start_server)
        self.server_start_btn.pack(side="left", padx=5)
        self.server_stop_btn = ttk.Button(ctrl_frame, text="⏹ 停止服务器", command=self._stop_server, state="disabled")
        self.server_stop_btn.pack(side="left", padx=5)

        # 连接信息
        info_frame = ttk.Frame(ctrl_frame)
        info_frame.pack(side="left", padx=20)
        self.server_info_label = ttk.Label(info_frame, text="未运行", foreground="#666")
        self.server_info_label.pack(side="left")
        ttk.Button(info_frame, text="📋 复制本机", command=self._copy_local_addr).pack(side="left", padx=5)
        ttk.Button(info_frame, text="🌐 复制外网", command=self._copy_public_addr).pack(side="left", padx=2)

        # 控制台
        console_frame = ttk.LabelFrame(f, text=" 服务器控制台 ")
        console_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.server_console = tk.Text(console_frame, height=15, font=("Consolas", 9),
                                       bg="#1e1e1e", fg="#00ff00", insertbackground="white")
        self.server_console.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(console_frame, command=self.server_console.yview)
        sb.pack(side="right", fill="y")
        self.server_console.configure(yscrollcommand=sb.set)

        # 命令输入
        cmd_frame = ttk.Frame(f)
        cmd_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(cmd_frame, text="命令:").pack(side="left")
        self.server_cmd = ttk.Entry(cmd_frame)
        self.server_cmd.pack(side="left", fill="x", expand=True, padx=5)
        self.server_cmd.bind("<Return>", lambda e: self._send_server_cmd())
        ttk.Button(cmd_frame, text="发送", command=self._send_server_cmd).pack(side="left")

        # 初始化列表
        self._refresh_server_list()

    def _refresh_server_list(self):
        """刷新服务器列表"""
        if not hasattr(self, 'server_combo') or self.server_combo is None:
            return
        import server_manager
        servers = server_manager.list_servers()
        self.server_combo["values"] = servers
        if servers and not self.server_combo.get():
            self.server_combo.set(servers[0])

    def _create_server(self):
        """创建新服务器"""
        import server_manager
        version = self.server_version.get().strip()
        stype = self.server_type.get()
        if not version:
            messagebox.showwarning("提示", "请输入MC版本")
            return

        def _worker():
            try:
                java_path = self.java_combo.get().split(" | ")[-1] if self.java_combo.get() else "java"
                if stype == "Fabric":
                    name = server_manager.download_fabric_server(
                        version, progress_cb=lambda msg: self._post("server_log", msg),
                        java_path=java_path)
                else:
                    name = server_manager.download_vanilla_server(
                        version, progress_cb=lambda msg: self._post("server_log", msg))
                self._post("server_log", "服务器创建成功: " + name)
                self._post("server_reload", None)
            except Exception as e:
                self._post("server_log", "创建失败: " + str(e))
                self._post("err", ("创建失败", str(e)))

        self._append_server_log("开始创建服务器...")
        self._thread(_worker)

    def _start_server(self):
        """启动服务器"""
        import server_manager
        name = self.server_combo.get()
        if not name:
            messagebox.showwarning("提示", "请先选择服务器")
            return
        if self._server_running:
            return

        memory = self.server_memory.get()
        java_path = self.java_combo.get().split(" | ")[-1] if self.java_combo.get() else "java"

        try:
            self._server_inst = server_manager.MinecraftServer(name, java_path=java_path, memory=memory)
            self._server_inst.output_callback = self._append_server_log
            self._server_inst.start()
            self._server_running = True
            self.server_start_btn.config(state="disabled")
            self.server_stop_btn.config(state="normal")

            ip = self._server_inst.get_local_ip()
            port = self._server_inst.get_port()
            self._server_port = port
            self._server_local_ip = ip
            # 异步获取外网IP
            self._fetch_public_ip()
            self.server_info_label.config(
                text="运行中 | 本机: {}:{} | 外网: 获取中...".format(ip, port),
                foreground="green")
            self._append_server_log("服务器启动中...")
            self._append_server_log("本机连接地址: {}:{}".format(ip, port))
        except Exception as e:
            messagebox.showerror("启动失败", str(e))

    def _stop_server(self):
        """停止服务器"""
        if self._server_inst:
            self._append_server_log("正在停止服务器...")
            self._server_inst.stop()
            self._server_running = False
            self.server_start_btn.config(state="normal")
            self.server_stop_btn.config(state="disabled")
            self.server_info_label.config(text="已停止", foreground="#666")

    def _send_server_cmd(self):
        """发送命令到服务器"""
        cmd = self.server_cmd.get().strip()
        if not cmd:
            return
        if self._server_inst and self._server_running:
            self._server_inst.send_command(cmd)
            self._append_server_log("> " + cmd)
        else:
            self._append_server_log("[错误] 服务器未运行")
        self.server_cmd.delete(0, "end")

    def _append_server_log(self, msg):
        """添加控制台日志"""
        self.server_console.insert("end", msg + "\n")
        self.server_console.see("end")

    def _open_server_dir(self):
        """打开服务器文件夹"""
        import server_manager
        name = self.server_combo.get()
        if not name:
            messagebox.showwarning("提示", "请先选择服务器")
            return
        import os
        d = str(server_manager.get_servers_dir() / name)
        try:
            os.startfile(d)
        except Exception:
            messagebox.showinfo("服务器目录", d)

    def _delete_server(self):
        """删除服务器"""
        import server_manager
        name = self.server_combo.get()
        if not name:
            messagebox.showwarning("提示", "请先选择服务器")
            return
        if self._server_running:
            messagebox.showwarning("提示", "请先停止服务器")
            return
        if messagebox.askyesno("确认", "确定删除服务器 {}?\n这将删除所有存档和配置!".format(name)):
            try:
                server_manager.delete_server(name)
                self._refresh_server_list()
                messagebox.showinfo("成功", "已删除")
            except Exception as e:
                messagebox.showerror("失败", str(e))

    # ---------------------------------------------------------------
    # 服务中心页面
    # ---------------------------------------------------------------
    def _build_services_tab(self):
        """构建服务中心页面 - 管理各种第三方服务"""
        tab = ttk.Frame(self.tools_nb)
        self.tools_nb.add(tab, text=" ⚙ 服务中心 ")
        # 标题
        title_frame = ttk.Frame(tab)
        title_frame.pack(fill="x", padx=15, pady=(15, 10))
        ttk.Label(title_frame, text="服务中心", font=("微软雅黑", 16, "bold")).pack(side="left")
        ttk.Label(title_frame, text="管理各种第三方服务的登录与连接",
                  foreground="#888", font=("微软雅黑", 9)).pack(side="left", padx=10)

        # Tailscale 服务卡片
        ts_frame = ttk.LabelFrame(tab, text=" Tailscale - 虚拟局域网 ")
        ts_frame.pack(fill="x", padx=15, pady=8)

        # 状态行
        status_row = ttk.Frame(ts_frame)
        status_row.pack(fill="x", padx=12, pady=(10, 5))
        self.ts_status_label = ttk.Label(status_row, text="● 检测中...",
                                         font=("微软雅黑", 10, "bold"))
        self.ts_status_label.pack(side="left")
        ttk.Button(status_row, text="刷新", width=8,
                   command=self._refresh_tailscale).pack(side="right")

        # IP 行
        ip_row = ttk.Frame(ts_frame)
        ip_row.pack(fill="x", padx=12, pady=4)
        ttk.Label(ip_row, text="虚拟IP:", width=8, font=("微软雅黑", 9)).pack(side="left")
        self.ts_ip_label = ttk.Label(ip_row, text="--", font=("Consolas", 11, "bold"),
                                     foreground="#4a90d9")
        self.ts_ip_label.pack(side="left", padx=5)
        ttk.Button(ip_row, text="复制IP", width=8,
                   command=self._copy_tailscale_ip).pack(side="left", padx=5)

        # 账号行
        acct_row = ttk.Frame(ts_frame)
        acct_row.pack(fill="x", padx=12, pady=4)
        ttk.Label(acct_row, text="登录账号:", width=8, font=("微软雅黑", 9)).pack(side="left")
        self.ts_acct_label = ttk.Label(acct_row, text="--", font=("微软雅黑", 9))
        self.ts_acct_label.pack(side="left", padx=5)

        # 设备列表
        dev_row = ttk.Frame(ts_frame)
        dev_row.pack(fill="x", padx=12, pady=4)
        ttk.Label(dev_row, text="在线设备:", width=8, font=("微软雅黑", 9)).pack(side="left")
        self.ts_devices_label = ttk.Label(dev_row, text="--", font=("微软雅黑", 9),
                                           foreground="#888")
        self.ts_devices_label.pack(side="left", padx=5)

        # 按钮行
        btn_row = ttk.Frame(ts_frame)
        btn_row.pack(fill="x", padx=12, pady=(8, 10))
        ttk.Button(btn_row, text="打开管理后台", width=14,
                   command=lambda: self._open_url("https://login.tailscale.com/admin/machines")).pack(side="left", padx=3)
        ttk.Button(btn_row, text="打开官网", width=10,
                   command=lambda: self._open_url("https://tailscale.com/")).pack(side="left", padx=3)
        ttk.Button(btn_row, text="断开连接", width=10,
                   command=self._tailscale_down).pack(side="left", padx=3)
        ttk.Button(btn_row, text="重新连接", width=10,
                   command=self._tailscale_up).pack(side="left", padx=3)

        # 使用说明
        help_frame = ttk.Frame(ts_frame)
        help_frame.pack(fill="x", padx=12, pady=(0, 10))
        ttk.Label(help_frame, text="说明：Tailscale 是一个 P2P 虚拟局域网工具，安装登录后，两台设备用同一个账号登录就能互相直连，不需要公网IP和端口映射。",
                  wraplength=700, foreground="#999", font=("微软雅黑", 8), justify="left").pack(anchor="w")

        # 预留其他服务
        ttk.Label(tab, text="更多服务即将加入...", foreground="#bbb",
                  font=("微软雅黑", 9)).pack(pady=20)

        # 初始化时刷新一次
        self.root.after(1000, self._refresh_tailscale)

    def _run_tailscale_cmd(self, args):
        """运行 tailscale 命令并返回输出"""
        try:
            import subprocess
            result = subprocess.run(
                ["tailscale"] + args,
                capture_output=True, text=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            return result.stdout.strip(), result.returncode
        except FileNotFoundError:
            return None, -1
        except Exception:
            return None, -2

    def _refresh_tailscale(self):
        """刷新 Tailscale 状态"""
        try:
            # 检查是否安装
            output, code = self._run_tailscale_cmd(["status"])
            if code == -1:
                self.ts_status_label.config(text="● 未安装", foreground="#ff6b6b")
                self.ts_ip_label.config(text="未安装")
                self.ts_acct_label.config(text="--")
                self.ts_devices_label.config(text="--")
                return
            if code != 0 or not output:
                self.ts_status_label.config(text="● 未连接", foreground="#ff6b6b")
                self.ts_ip_label.config(text="--")
                self.ts_acct_label.config(text="--")
                self.ts_devices_label.config(text="--")
                return

            # 已连接
            self.ts_status_label.config(text="● 已连接", foreground="#51cf66")

            # 获取IP
            ip_out, _ = self._run_tailscale_cmd(["ip", "-4"])
            if ip_out:
                self.ts_ip_label.config(text=ip_out.split("\n")[0].strip())

            # 解析设备列表
            lines = [l for l in output.split("\n") if l.strip()]
            devices = []
            for line in lines:
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[1]
                    ip = parts[0]
                    devices.append(f"{name} ({ip})")
            if devices:
                self.ts_devices_label.config(text=f"{len(devices)} 台设备")
                # 找自己的设备名(带100.x的)
                for d in devices:
                    if "100." in d:
                        self.ts_acct_label.config(text=d.split(" (")[0])
                        break
            else:
                self.ts_devices_label.config(text="1 台设备")

        except Exception as e:
            self.ts_status_label.config(text=f"● 检测失败: {e}", foreground="#ff6b6b")

    def _copy_tailscale_ip(self):
        """复制 Tailscale IP"""
        ip = self.ts_ip_label.cget("text")
        if ip and ip != "--" and ip != "未安装":
            self.root.clipboard_clear()
            self.root.clipboard_append(ip)
            self.ts_status_label.config(text=f"● IP已复制: {ip}", foreground="#4a90d9")
        else:
            self.ts_status_label.config(text="● 没有可复制的IP", foreground="#ff6b6b")

    def _tailscale_down(self):
        """断开 Tailscale"""
        try:
            self._run_tailscale_cmd(["down"])
            self.root.after(500, self._refresh_tailscale)
        except Exception as e:
            self.ts_status_label.config(text=f"● 断开失败: {e}", foreground="#ff6b6b")

    def _tailscale_up(self):
        """重连 Tailscale"""
        try:
            self._run_tailscale_cmd(["up"])
            self.root.after(2000, self._refresh_tailscale)
        except Exception as e:
            self.ts_status_label.config(text=f"● 连接失败: {e}", foreground="#ff6b6b")

    def _build_about_tab(self):
        """关于页面: 启动器信息 + 使用说明 + 娱乐功能介绍"""
        f = self.tab_about
        # 顶部标题
        title_frame = tk.Frame(f, bg="#2b2b2b", height=80)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)
        self.about_title_label = tk.Label(title_frame, text="VoxelLauncher", bg="#2b2b2b",
                 fg="#ffffff", font=("Arial", 24, "bold"))
        self.about_title_label.pack(pady=(15, 0))
        self._about_click_count = 0
        self.about_title_label.bind("<Button-1>", self._on_about_title_click)
        tk.Label(title_frame, text="Minecraft 第三方启动器", bg="#2b2b2b",
                 fg="#aaaaaa", font=("Arial", 10)).pack()
        # 版本信息
        info_frame = tk.Frame(f)
        info_frame.pack(fill="x", padx=10, pady=10)
        tk.Label(info_frame, text="版本: " + version.VERSION_TAG, font=("Arial", 10)).grid(
            row=0, column=0, sticky="w", padx=5, pady=2)
        tk.Label(info_frame, text="引擎: Python + Tkinter", font=("Arial", 10)).grid(
            row=0, column=1, sticky="w", padx=5, pady=2)
        tk.Label(info_frame, text="支持: Fabric / Forge / Vanilla", font=("Arial", 10)).grid(
            row=1, column=0, sticky="w", padx=5, pady=2)
        tk.Label(info_frame, text="下载源: Mojang / BMCLAPI", font=("Arial", 10)).grid(
            row=1, column=1, sticky="w", padx=5, pady=2)
        # 使用说明 (带滚动)
        help_frame = tk.LabelFrame(f, text=" 使用说明 ", padx=10, pady=5)
        help_frame.pack(fill="both", expand=True, padx=10, pady=5)
        help_text = tk.Text(help_frame, wrap="word", font=("Arial", 9),
                            height=15, bg="#fafafa", relief="flat")
        help_scroll = ttk.Scrollbar(help_frame, command=help_text.yview)
        help_text.configure(yscrollcommand=help_scroll.set)
        help_scroll.pack(side="right", fill="y")
        help_text.pack(side="left", fill="both", expand=True)
        help_content = """【快速开始】
1. 「版本下载」页: 下载一个 Minecraft 版本(推荐 1.20.1 或 1.21.1)
2. 「实例设置」页: 创建一个新实例, 选择游戏版本和加载器(Fabric/Forge)
3. 「启动」页: 选择实例, 设置内存(推荐 4G 以上), 点「启动游戏」

【下载模组/资源包】
1. 「Modrinth」页: 搜索模组, 选中后点下载, 会弹出版本列表让你选择
2. 「资源包」/「数据包」/「光影包」页: 搜索并下载, 同样支持版本选择
3. 「整合包」页: 搜索整合包, 选择版本后自动下载并导入
4. 「CurseForge」页: 需要在设置里填入 API Key, 支持版本选择下载

【版本选择功能】
所有下载入口都支持版本选择:
- 下载时会弹出版本列表, 显示版本号、名称、支持的游戏版本、版本类型
- 选择你要的版本, 点「下载选中版本」
- 比如 CozyUI+ 资源包, 可以选择 "no-fonts 无字体版本"

【实例管理】
- 「实例设置」页: 创建、删除、复制实例, 修改实例配置
- 每个实例独立管理 mods、resourcepacks、saves 等
- 支持导入本地 mrpack/CurseForge 整合包

【娱乐功能】
「🎮 娱乐」页有丰富的小游戏:
- ⛏ 挖矿系统: 点击矿石挖矿, 获得经验升级镐子, 不同镐子挖不同矿石
- 🐱 宠物系统: 苦力怕和村民双宠物, 点击互动, 右键喂食, 会随机说话和对话
- 🤖 AI 聊天: 支持豆包/Deepseek/Kimi, 宠物会按角色设定回复, 自动检测 API 服务商
- ☀ 昼夜系统: 实时昼夜交替, 影响挖矿和天气
- 🌧 天气系统: 雨/雪/雷暴动画, 下雨天会出现流浪商人
- 🤝 交易系统: 和村民/流浪商人交易, 用矿石换物品
- ⚒ 合成系统: 工作台合成物品, 支持自定义皮肤
- 🐟 养殖系统: 养鱼等动物, 动物贴图从游戏提取
- 🎣 钓鱼小游戏: 等待鱼上钩, 把握时机拉杆, 钓到各种鱼和宝藏
- 🎒 背包和箱子: 物品存储和管理
- 💰 积分系统: 挖矿获得积分, 普通矿石+1, 稀有矿石+5
- 🎁 积分兑换: 用积分兑换游戏物品, 支持直接发送到游戏背包(15种物品)

【⚔️ 战斗系统】
「⚔️ 战斗」单独页面:
- 👹 刷怪系统: 夜晚自动刷僵尸和骷髅, 贴图从游戏提取
- 🗡 武器系统: 木剑→石剑→铁剑→钻石剑→下界合金剑, 伤害递增
- ⚔ 战斗机制: 点击怪物攻击, 怪物会反击, 玩家有血量条
- 💀 掉落物: 僵尸掉腐肉/铁锭/胡萝卜, 骷髅掉骨头/箭/弓
- 💬 指令系统: 支持 /give /time set /gamemode /kill /heal /summon /xp 等
- 📜 战斗日志: 记录所有战斗事件
- 🔗 游戏联动: 击杀怪物时, 游戏里附近同种怪物也会被击杀

【🔗 游戏联动】
- ⛏ 挖矿联动: 挖到矿石实时发送到游戏背包
- ⚔ 战斗联动: 击杀怪物时游戏里附近同种怪物也死亡
- 🎁 积分兑换联动: 积分兑换的物品直接发送到游戏背包, 无需手动输入命令
- 需要安装游戏联动Mod(设置页有「安装联动Mod」按钮)

【设置】
- 「设置」页: 修改内存分配、Java 路径、下载源、主题等
- 下载源推荐用 BMCLAPI(国内速度快)
- 内存推荐 4096MB(4G) 以上, 玩整合包建议 8192MB(8G)

【常见问题】
Q: 下载卡住显示 0kb?
A: 可能是网络问题, 试试切换下载源, 或者手动下载后用「导入本地文件」

Q: 游戏启动失败?
A: 检查 Java 版本是否正确, 内存是否分配足够, 模组是否有冲突

Q: 怎么加模组?
A: 在 Modrinth 页搜索下载, 或者把 jar 文件放到实例的 mods 文件夹

Q: 资源包怎么启用?
A: 下载后进入游戏 -> 选项 -> 资源包 -> 选中启用

【快捷键】
- F5: 刷新当前页面
- Esc: 关闭对话框
- 回车: 确认/搜索

感谢使用 VoxelLauncher! 祝你游戏愉快 🎮
"""
        help_text.insert("1.0", help_content)
        help_text.configure(state="disabled")
        # 底部按钮
        btn_frame = tk.Frame(f)
        btn_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(btn_frame, text="📁 打开启动器目录",
                   command=self._open_launcher_dir).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="⚔️ 去战斗",
                   command=lambda: self.nb.select(self.tab_combat)).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🎮 去娱乐",
                   command=lambda: self.nb.select(self.tab_fun)).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🔄 检查更新",
                   command=self._check_update_now).pack(side="left", padx=5)

    def _build_friends_tab(self):
        """联机中心: 局域网扫描 + 服务器收藏 + 邀请码 + 好友"""
        import server_scanner
        f = self.tab_friends

        # 顶部标题
        title_frame = tk.Frame(f, bg="#6a1b9a", height=60)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)
        tk.Label(title_frame, text="🌐 联机中心", bg="#6a1b9a",
                 fg="white", font=("Arial", 18, "bold")).pack(side="left", padx=20, pady=10)
        self.lan_status_label = tk.Label(title_frame, text="", bg="#6a1b9a",
                                         fg="#e1bee7", font=("Arial", 10))
        self.lan_status_label.pack(side="left", padx=10)

        # 顶部工具栏
        toolbar = tk.Frame(f, bg="#f5f5f5")
        toolbar.pack(fill="x", padx=10, pady=5)

        ttk.Button(toolbar, text="🔍 扫描局域网",
                   command=self._scan_lan).pack(side="left", padx=3)
        ttk.Button(toolbar, text="⭐ 收藏服务器",
                   command=self._add_favorite_dialog).pack(side="left", padx=3)
        ttk.Button(toolbar, text="🔄 刷新状态",
                   command=self._refresh_all_servers).pack(side="left", padx=3)

        # 邀请码
        invite_frame = tk.Frame(toolbar, bg="#f5f5f5")
        invite_frame.pack(side="right", padx=3)
        tk.Label(invite_frame, text="邀请码:", bg="#f5f5f5", font=("Arial", 9)).pack(side="left")
        self.quick_code_var = tk.StringVar()
        ttk.Entry(invite_frame, textvariable=self.quick_code_var, width=20).pack(side="left", padx=3)
        ttk.Button(invite_frame, text="加入",
                   command=self._join_by_code).pack(side="left")
        ttk.Button(invite_frame, text="生成我的",
                   command=self._show_invite_dialog).pack(side="left", padx=3)

        # 主区域：左右分栏
        main_paned = tk.PanedWindow(f, orient="horizontal", sashrelief="raised")
        main_paned.pack(fill="both", expand=True, padx=10, pady=5)

        # 左侧：局域网发现 + 服务器收藏
        left_frame = tk.Frame(main_paned)
        main_paned.add(left_frame, minsize=300)

        # 局域网发现
        lan_frame = tk.LabelFrame(left_frame, text=" 🔍 局域网发现 ", padx=5, pady=5)
        lan_frame.pack(fill="both", expand=True, pady=(0, 5))

        self.lan_listbox = tk.Listbox(lan_frame, font=("Arial", 9))
        self.lan_listbox.pack(side="left", fill="both", expand=True)
        lan_scroll = ttk.Scrollbar(lan_frame, command=self.lan_listbox.yview)
        lan_scroll.pack(side="right", fill="y")
        self.lan_listbox.configure(yscrollcommand=lan_scroll.set)
        self.lan_listbox.bind("<Double-Button-1>", self._join_lan_server)

        lan_btn = tk.Frame(left_frame)
        lan_btn.pack(fill="x", pady=(0, 5))
        ttk.Button(lan_btn, text="🚀 加入选中",
                   command=self._join_lan_server).pack(side="left", padx=2)
        ttk.Button(lan_btn, text="⭐ 收藏",
                   command=self._favorite_lan).pack(side="left", padx=2)

        # 服务器收藏
        fav_frame = tk.LabelFrame(left_frame, text=" ⭐ 服务器收藏 ", padx=5, pady=5)
        fav_frame.pack(fill="both", expand=True)

        self.fav_listbox = tk.Listbox(fav_frame, font=("Arial", 9))
        self.fav_listbox.pack(side="left", fill="both", expand=True)
        fav_scroll = ttk.Scrollbar(fav_frame, command=self.fav_listbox.yview)
        fav_scroll.pack(side="right", fill="y")
        self.fav_listbox.configure(yscrollcommand=fav_scroll.set)
        self.fav_listbox.bind("<Double-Button-1>", self._join_favorite)

        fav_btn = tk.Frame(left_frame)
        fav_btn.pack(fill="x", pady=(5, 0))
        ttk.Button(fav_btn, text="🚀 加入选中",
                   command=self._join_favorite).pack(side="left", padx=2)
        ttk.Button(fav_btn, text="🗑 删除",
                   command=self._remove_favorite).pack(side="left", padx=2)

        # 右侧：好友列表
        right_frame = tk.LabelFrame(main_paned, text=" 👥 好友 ", padx=5, pady=5)
        main_paned.add(right_frame, minsize=250)

        # 添加好友
        add_frame = tk.Frame(right_frame, bg="#f5f5f5")
        add_frame.pack(fill="x", pady=(0, 5))
        tk.Label(add_frame, text="ID:", bg="#f5f5f5", font=("Arial", 9)).pack(side="left")
        self.friend_name_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.friend_name_var, width=10).pack(side="left", padx=2)
        tk.Label(add_frame, text="IP:", bg="#f5f5f5", font=("Arial", 9)).pack(side="left")
        self.friend_ip_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.friend_ip_var, width=12).pack(side="left", padx=2)
        ttk.Button(add_frame, text="➕", command=self._add_friend, width=3).pack(side="left", padx=2)

        # 好友列表
        self.friends_canvas = tk.Canvas(right_frame, bg="#f5f5f5", highlightthickness=0)
        friends_scroll = ttk.Scrollbar(right_frame, orient="vertical",
                                       command=self.friends_canvas.yview)
        self.friends_canvas.configure(yscrollcommand=friends_scroll.set)
        friends_scroll.pack(side="right", fill="y")
        self.friends_canvas.pack(side="left", fill="both", expand=True)

        self.friends_inner = tk.Frame(self.friends_canvas, bg="#f5f5f5")
        self.friends_canvas.create_window((0, 0), window=self.friends_inner, anchor="nw")
        self.friends_inner.bind("<Configure>",
            lambda e: self.friends_canvas.configure(scrollregion=self.friends_canvas.bbox("all")))

        # 底部提示
        tip = tk.Label(f, text="💡 同WiFi下好友开了局域网世界会自动扫描到 | 收藏的服务器自动显示在线状态和人数",
                       bg="#f5f5f5", fg="#888", font=("Arial", 9))
        tip.pack(fill="x", padx=10, pady=3)

        self._refresh_favorites()
        self._refresh_friends()

    def _scan_lan(self):
        """扫描局域网服务器"""
        import server_scanner
        self.lan_status_label.config(text="🔍 正在扫描局域网...")
        self.lan_listbox.delete(0, "end")
        self.lan_listbox.insert("end", "正在扫描，请稍候...")

        def _callback(results):
            self.root.after(0, lambda: self._lan_scan_done(results))

        server_scanner.scan_lan_async(25565, _callback)

    def _lan_scan_done(self, results):
        """局域网扫描完成"""
        import server_scanner
        self.lan_listbox.delete(0, "end")
        if not results:
            self.lan_status_label.config(text="❌ 未发现局域网服务器")
            self.lan_listbox.insert("end", "未发现局域网内的Minecraft服务器")
            self.lan_listbox.insert("end", "")
            self.lan_listbox.insert("end", "提示: 让好友进入游戏 -> 对局域网开放")
            return

        self.lan_status_label.config(text="✅ 发现 {} 个服务器".format(len(results)))
        self._lan_results = results
        for ip, port, latency in results:
            # 查询服务器信息
            info = server_scanner.query_server(ip, port, timeout=2)
            if info["online"]:
                text = "{}:{} | {}ms | {}/{}人 | {}".format(
                    ip, port, latency,
                    info["players_online"], info["players_max"],
                    info["motd"][:30] if info["motd"] else "Minecraft Server")
            else:
                text = "{}:{} | {}ms".format(ip, port, latency)
            self.lan_listbox.insert("end", text)

    def _join_lan_server(self, event=None):
        """加入局域网服务器"""
        if not hasattr(self, '_lan_results') or not self._lan_results:
            return
        selection = self.lan_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个服务器")
            return
        idx = selection[0]
        if idx < len(self._lan_results):
            ip, port, latency = self._lan_results[idx]
            self._join_server(ip, port, "局域网")

    def _favorite_lan(self):
        """收藏局域网服务器"""
        import server_scanner
        if not hasattr(self, '_lan_results') or not self._lan_results:
            return
        selection = self.lan_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个服务器")
            return
        idx = selection[0]
        if idx < len(self._lan_results):
            ip, port, latency = self._lan_results[idx]
            name = simpledialog.askstring("收藏服务器", "服务器名称:",
                                          initialvalue="局域网-" + ip, parent=self.root)
            if name:
                server_scanner.add_favorite(name, ip, port)
                self._refresh_favorites()
                messagebox.showinfo("成功", "已收藏: " + name)

    def _add_favorite_dialog(self):
        """添加服务器收藏对话框"""
        import server_scanner
        dialog = tk.Toplevel(self.root)
        dialog.title("收藏服务器")
        dialog.geometry("350x180")
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="服务器名称:", font=("Arial", 10)).pack(pady=(15, 3))
        name_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=name_var, width=30).pack()

        tk.Label(dialog, text="服务器地址 (IP:端口):", font=("Arial", 10)).pack(pady=(10, 3))
        addr_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=addr_var, width=30).pack()

        def save():
            name = name_var.get().strip()
            addr = addr_var.get().strip()
            if not name or not addr:
                messagebox.showwarning("提示", "请填写名称和地址", parent=dialog)
                return
            if ":" in addr:
                ip, port = addr.rsplit(":", 1)
                try:
                    port = int(port)
                except ValueError:
                    port = 25565
            else:
                ip = addr
                port = 25565
            server_scanner.add_favorite(name, ip, port)
            self._refresh_favorites()
            dialog.destroy()
            messagebox.showinfo("成功", "服务器已收藏!")

        ttk.Button(dialog, text="保存", command=save).pack(pady=15)

    def _refresh_favorites(self):
        """刷新服务器收藏列表"""
        import server_scanner
        self.fav_listbox.delete(0, "end")
        favorites = server_scanner.load_favorites()
        self._favorites = favorites
        if not favorites:
            self.fav_listbox.insert("end", "还没有收藏的服务器")
            return

        for s in favorites:
            # 异步查询状态
            info = server_scanner.query_server(s["ip"], s["port"], timeout=2)
            if info["online"]:
                status = "● 在线"
                players = "{}/{}人".format(info["players_online"], info["players_max"])
                latency = "{}ms".format(info["latency"])
            else:
                status = "○ 离线"
                players = ""
                latency = ""
            text = "{} | {}:{} | {} {} {}".format(
                s["name"], s["ip"], s["port"], status, players, latency)
            self.fav_listbox.insert("end", text)

    def _join_favorite(self, event=None):
        """加入收藏的服务器"""
        if not hasattr(self, '_favorites') or not self._favorites:
            return
        selection = self.fav_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个服务器")
            return
        idx = selection[0]
        if idx < len(self._favorites):
            s = self._favorites[idx]
            self._join_server(s["ip"], s["port"], s["name"])

    def _remove_favorite(self):
        """删除收藏的服务器"""
        import server_scanner
        if not hasattr(self, '_favorites') or not self._favorites:
            return
        selection = self.fav_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个服务器")
            return
        idx = selection[0]
        if idx < len(self._favorites):
            s = self._favorites[idx]
            if messagebox.askyesno("确认", "删除收藏: " + s["name"] + "?"):
                server_scanner.remove_favorite(s["ip"], s["port"])
                self._refresh_favorites()

    def _refresh_all_servers(self):
        """刷新所有服务器状态"""
        self._refresh_favorites()
        self._refresh_friends()
        messagebox.showinfo("刷新完成", "服务器状态已刷新")

    def _show_invite_dialog(self):
        """显示邀请码生成对话框"""
        import server_scanner
        import friends as friends_mod
        dialog = tk.Toplevel(self.root)
        dialog.title("生成邀请码")
        dialog.geometry("400x250")
        dialog.transient(self.root)
        dialog.grab_set()

        local_ip = server_scanner.get_local_ip()
        tk.Label(dialog, text="你的局域网IP: " + local_ip,
                 font=("Arial", 10)).pack(pady=(15, 5))

        tk.Label(dialog, text="端口 (游戏里对局域网开放后显示):",
                 font=("Arial", 10)).pack()
        port_var = tk.StringVar(value="25565")
        ttk.Entry(dialog, textvariable=port_var, width=15).pack(pady=5)

        code_label = tk.Label(dialog, text="", font=("Consolas", 12, "bold"),
                              fg="#6a1b9a")
        code_label.pack(pady=10)

        def generate():
            port = port_var.get().strip()
            try:
                port = int(port)
            except ValueError:
                messagebox.showwarning("提示", "端口必须是数字", parent=dialog)
                return
            code = friends_mod.generate_invite_code(local_ip, port, "Voxel联机")
            code_label.config(text=code)
            self.root.clipboard_clear()
            self.root.clipboard_append(code)

        ttk.Button(dialog, text="📤 生成并复制邀请码",
                   command=generate).pack(pady=10)
        tk.Label(dialog, text="把邀请码发给好友，好友粘贴即可加入",
                 fg="#888", font=("Arial", 9)).pack()

    def _generate_invite(self):
        """生成邀请码"""
        import friends as friends_mod
        ip = self.invite_ip_var.get().strip()
        port = self.invite_port_var.get().strip()
        if not ip:
            messagebox.showwarning("提示", "请输入IP")
            return
        try:
            port = int(port)
        except ValueError:
            messagebox.showwarning("提示", "端口必须是数字")
            return
        code = friends_mod.generate_invite_code(ip, port, "VoxelLauncher联机")
        self.invite_code_label.config(text=code)
        self.root.clipboard_clear()
        self.root.clipboard_append(code)
        messagebox.showinfo("邀请码已生成", "邀请码: " + code + "\n\n已复制到剪贴板，发给好友即可！")

    def _join_by_code(self):
        """通过邀请码加入"""
        import friends as friends_mod
        code = self.join_code_var.get().strip()
        if not code:
            messagebox.showwarning("提示", "请输入邀请码")
            return
        result = friends_mod.parse_invite_code(code)
        if not result:
            messagebox.showerror("错误", "无效的邀请码")
            return
        ip, port, note = result
        self._join_server(ip, port, note)

    def _join_server(self, ip, port, name=""):
        """加入服务器"""
        import friends as friends_mod
        addr = "{}:{}".format(ip, port)
        self.root.clipboard_clear()
        self.root.clipboard_append(addr)
        friends_mod.add_recent_server(ip, port, name)
        self._refresh_recent()
        messagebox.showinfo("加入服务器", "服务器地址已复制:\n" + addr +
                            "\n\n在游戏里: 多人游戏 -> 添加服务器 -> 粘贴地址")

    def _refresh_recent(self):
        """刷新最近联机记录"""
        import friends as friends_mod
        self.recent_listbox.delete(0, "end")
        recent = friends_mod.load_recent_servers()
        for r in recent:
            name = r.get("name", "") or r["ip"]
            self.recent_listbox.insert("end", "{}:{} - {}".format(r["ip"], r["port"], name))

    def _join_recent(self, event=None):
        """加入最近联机的服务器"""
        import friends as friends_mod
        selection = self.recent_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个服务器")
            return
        recent = friends_mod.load_recent_servers()
        idx = selection[0]
        if idx < len(recent):
            r = recent[idx]
            self._join_server(r["ip"], r["port"], r.get("name", ""))

    def _clear_recent(self):
        """清空最近联机记录"""
        import friends as friends_mod
        if messagebox.askyesno("确认", "确定清空最近联机记录?"):
            friends_mod._ensure_dir()
            with open(friends_mod.RECENT_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)
            self._refresh_recent()

    def _refresh_friends(self):
        """刷新好友列表"""
        import friends as friends_mod
        import threading
        for widget in self.friends_inner.winfo_children():
            widget.destroy()

        friends_list = friends_mod.load_friends()
        try:
            self.friend_count_label.config(text="{} 位好友".format(len(friends_list)))
        except Exception:
            pass

        if not friends_list:
            tk.Label(self.friends_inner, text="还没有好友\n添加好友后可查看服务器状态并一键加入",
                     bg="#f5f5f5", fg="#999", font=("Arial", 12),
                     justify="center").pack(pady=50)
            return

        for friend in friends_list:
            self._create_friend_card(friend)

        # 异步检测所有好友服务器状态
        def _ping_all():
            for friend in friends_list:
                ip = friend.get("server_ip", "")
                port = friend.get("server_port", 25565)
                if ip:
                    online, ping, desc = friends_mod.ping_server(ip, port)
                    friend["_status"] = (online, ping, desc)
            self.root.after(0, lambda: self._update_friend_status(friends_list))

        threading.Thread(target=_ping_all, daemon=True).start()

    def _update_friend_status(self, friends_list):
        """更新好友服务器状态显示"""
        # 重新渲染列表（简化处理，直接刷新）
        for widget in self.friends_inner.winfo_children():
            widget.destroy()
        for friend in friends_list:
            self._create_friend_card(friend, show_status=True)

    def _create_friend_card(self, friend, show_status=False):
        """创建单个好友卡片"""
        import friends as friends_mod
        card = tk.Frame(self.friends_inner, bg="white", relief="raised", bd=1)
        card.pack(fill="x", padx=5, pady=3)

        # 头像
        avatar_frame = tk.Frame(card, bg="white", width=55, height=55)
        avatar_frame.pack(side="left", padx=8, pady=8)
        avatar_frame.pack_propagate(False)
        avatar_label = tk.Label(avatar_frame, text="🧑", bg="#e3f2fd",
                                font=("Arial", 22))
        avatar_label.pack(fill="both", expand=True)
        self._load_friend_avatar(avatar_label, friend["username"])

        # 信息
        info_frame = tk.Frame(card, bg="white")
        info_frame.pack(side="left", fill="both", expand=True, pady=5)

        name_frame = tk.Frame(info_frame, bg="white")
        name_frame.pack(fill="x")
        tk.Label(name_frame, text=friend["username"], bg="white",
                 font=("Arial", 12, "bold")).pack(side="left")

        # 服务器状态
        ip = friend.get("server_ip", "")
        if ip:
            if "_status" in friend:
                online, ping, desc = friend["_status"]
            else:
                online, ping, desc = False, 0, "检测中..."
            status_color = "#4caf50" if online else "#999"
            status_text = "● " + desc if online else "○ " + desc
            tk.Label(name_frame, text=status_text, bg="white", fg=status_color,
                     font=("Arial", 8)).pack(side="left", padx=8)

        if friend.get("note"):
            tk.Label(info_frame, text="📝 " + friend["note"], bg="white",
                     fg="#666", font=("Arial", 9)).pack(anchor="w")
        if ip:
            port = friend.get("server_port", 25565)
            tk.Label(info_frame, text="🌐 {}:{}".format(ip, port), bg="white",
                     fg="#2196f3", font=("Arial", 9)).pack(anchor="w")

        # 操作按钮
        btn_frame = tk.Frame(card, bg="white")
        btn_frame.pack(side="right", padx=5, pady=5)

        def join():
            self._join_server(ip, friend.get("server_port", 25565), friend["username"])

        def copy_id():
            self.root.clipboard_clear()
            self.root.clipboard_append(friend["username"])

        def delete():
            if messagebox.askyesno("确认", "删除好友 " + friend["username"] + "?"):
                friends_mod.remove_friend(friend["username"])
                self._refresh_friends()

        if ip:
            ttk.Button(btn_frame, text="🚀 加入", command=join, width=8).pack(pady=1)
        ttk.Button(btn_frame, text="📋 复制ID", command=copy_id, width=8).pack(pady=1)
        ttk.Button(btn_frame, text="🗑 删除", command=delete, width=8).pack(pady=1)

    def _load_friend_avatar(self, label, username):
        """异步加载好友头像"""
        import threading
        def _load():
            try:
                import urllib.request
                from PIL import Image, ImageTk
                import io
                url = f"https://crafatar.com/avatars/{username}?size=64&overlay"
                req = urllib.request.Request(url, headers={"User-Agent": "VoxelLauncher"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    img_data = resp.read()
                img = Image.open(io.BytesIO(img_data))
                img = img.resize((50, 50), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.root.after(0, lambda: self._set_avatar(label, photo))
            except Exception:
                pass
        threading.Thread(target=_load, daemon=True).start()

    def _set_avatar(self, label, photo):
        label.config(image=photo, text="")
        label.image = photo

    def _add_friend(self):
        """添加好友"""
        import friends as friends_mod
        username = self.friend_name_var.get().strip()
        if not username:
            messagebox.showwarning("提示", "请输入游戏ID")
            return
        note = self.friend_note_var.get().strip()
        server_ip = self.friend_ip_var.get().strip()
        try:
            server_port = int(self.friend_port_var.get().strip())
        except ValueError:
            server_port = 25565

        success, msg = friends_mod.add_friend(username, note, server_ip, server_port)
        if success:
            messagebox.showinfo("成功", "好友 " + username + " 添加成功！")
            self.friend_name_var.set("")
            self.friend_note_var.set("")
            self.friend_ip_var.set("")
            self.friend_port_var.set("25565")
            self._refresh_friends()
        else:
            messagebox.showerror("失败", msg)

    def _add_friend(self):
        """添加好友"""
        import friends as friends_mod
        username = self.friend_name_var.get().strip()
        if not username:
            messagebox.showwarning("提示", "请输入游戏ID")
            return
        note = self.friend_note_var.get().strip()
        server_ip = self.friend_ip_var.get().strip()

        success, msg = friends_mod.add_friend(username, note, server_ip)
        if success:
            messagebox.showinfo("成功", "好友 " + username + " 添加成功！")
            self.friend_name_var.set("")
            self.friend_note_var.set("")
            self.friend_ip_var.set("")
            self._refresh_friends()
        else:
            messagebox.showerror("失败", msg)

    # ---------------- 自动更新 ----------------
    def _check_update_now(self):
        """手动点击检查更新"""
        def _work():
            try:
                self._post("status", "正在检查更新...")
                result = updater.check_for_update()
                if result is None:
                    self._post("status", "检查失败(网络问题)")
                    messagebox.showwarning("检查更新", "无法连接更新服务器, 请检查网络后重试")
                    return
                has_new, latest = result
                if has_new:
                    self._post("status", "发现新版本 v" + latest)
                    self.root.after(0, lambda: self._ask_update(latest))
                else:
                    self._post("status", "已是最新版本 v" + version.VERSION)
                    messagebox.showinfo("检查更新",
                        "当前已是最新版本 " + version.VERSION_TAG + chr(10) +
                        "感谢使用 VoxelLauncher!")
            except Exception as e:
                self._post("status", "检查更新出错")
        threading.Thread(target=_work, daemon=True).start()

    def _ask_update(self, latest):
        """询问是否下载更新"""
        ans = messagebox.askyesno("发现新版本",
            "发现新版本 v" + latest + chr(10) +
            "当前版本 v" + version.VERSION + chr(10) + chr(10) +
            "是否现在下载并安装?")
        if ans:
            self._do_download_update(latest)

    def _do_download_update(self, latest):
        """下载新版本并应用"""
        _, url = updater.get_latest_version()
        if not url:
            messagebox.showerror("更新失败", "获取下载地址失败, 请手动到官网下载")
            return
        import tempfile
        dl_path = os.path.join(tempfile.gettempdir(), "VoxelLauncher_new.exe")
        # 下载进度窗口
        prog = tk.Toplevel(self.root)
        prog.title("正在下载更新")
        prog.geometry("380x120")
        tk.Label(prog, text="正在下载 v" + latest + " ...").pack(pady=10)
        bar = ttk.Progressbar(prog, length=300, maximum=100)
        bar.pack(pady=5)

        def _progress(done, total):
            pct = int(done / total * 100) if total else 0
            bar["value"] = pct

        def _work():
            ok, err = updater.download_update(url, dl_path, _progress)
            self.root.after(0, lambda: self._after_download(ok, err, dl_path, prog, latest))

        threading.Thread(target=_work, daemon=True).start()

    def _after_download(self, ok, err, dl_path, prog_win, latest):
        """下载完成后处理"""
        prog_win.destroy()
        if not ok:
            messagebox.showerror("下载失败", "下载失败: " + err + chr(10) +
                                 "请到官网手动下载")
            return
        # 校验大小>10MB 认为是有效 exe
        if not os.path.exists(dl_path) or os.path.getsize(dl_path) < 10 * 1024 * 1024:
            messagebox.showerror("下载失败", "下载的文件不完整, 请到官网手动下载")
            return
        ans = messagebox.askyesno("更新就绪",
            "新版 v" + latest + " 已下载完成(共 " +
            "{:.1f} MB)".format(os.path.getsize(dl_path) / 1024 / 1024) + chr(10) +
            "点击确定将自动替换并重启启动器")
        if ans:
            self._apply_update(dl_path)

    def _apply_update(self, dl_path):
        """应用更新(替换exe并重启)"""
        ok, err = updater.apply_update(dl_path)
        if not ok:
            messagebox.showerror("更新失败", "自动更新失败: " + err + chr(10) +
                                 "请手动替换 VoxelLauncher.exe")
            return
        # 关闭当前程序
        try:
            self.root.destroy()
        except Exception:
            os._exit(0)

    def _maybe_auto_check(self):
        """启动后延迟自动检查更新(不打扰用户, 有新版才提示)"""
        def _work():
            time.sleep(3)
            try:
                result = updater.check_for_update()
                if result and result[0]:  # 有新版
                    latest = result[1]
                    self.root.after(0, lambda: self._ask_update(latest))
            except Exception:
                pass
        threading.Thread(target=_work, daemon=True).start()


    def _on_about_title_click(self, event=None):
        """隐蔽彩蛋: 连点标题10次触发(不留任何提示, 靠玩家自己发现)"""
        self._about_click_count += 1
        if self._about_click_count >= 10:
            self._about_click_count = 0
            self._show_egg("隐藏成就解锁")

    def _show_egg(self, title):
        """显示彩蛋"""
        import random
        NL = chr(10)
        eggs = [
            "🎉 你发现了隐藏彩蛋!" + NL + NL + "VoxelLauncher 是由 AI 和你一起开发的!" + NL + "继续加油!",
            "🎉 彩蛋!" + NL + NL + "为什么苦力怕害怕猫? 因为怕被喵喵哒～",
            "🎉 恭喜!" + NL + NL + "你已经点了 10 次标题了, 手速不错!" + NL + "送你一个成就: 手速达人",
            "🎉 隐藏内容解锁!" + NL + NL + "提示: 去设置页把主题切成 '苦力怕绿' 看看效果",
            "🎉 厉害!" + NL + NL + "这个启动器里还有更多彩蛋等你发现!",
        ]
        messagebox.showinfo("🎉 " + title, random.choice(eggs))

    def _open_launcher_dir(self):
        """打开启动器目录"""
        import os
        launcher_dir = str(Path.home() / "AppData" / "Roaming" / ".voxellauncher")
        try:
            os.startfile(launcher_dir)
        except Exception:
            messagebox.showinfo("启动器目录", launcher_dir)



    # ---------------- 下载管理(断点续传) ----------------
    def _on_download_task_changed(self):
        """下载任务变化时回调(在任意线程调用, 用 after 切到主线程)"""
        self.root.after(0, self._refresh_download_list)

    def _refresh_download_list(self):
        """刷新下载列表显示"""
        if not hasattr(self, 'dl_listbox'):
            return
        self.dl_listbox.delete(0, "end")
        tasks = self.dl_mgr.get_all_tasks()
        if not tasks:
            self.dl_listbox.insert("end", "  (暂无下载任务)")
            self.dl_status_label.config(text="")
            return
        status_text_map = {
            "pending": "⏳ 等待中",
            "downloading": "⬇ 下载中",
            "paused": "⏸ 已暂停",
            "completed": "✅ 已完成",
            "failed": "❌ 失败",
            "cancelled": "🚫 已取消",
        }
        active_count = 0
        for task in tasks:
            status_text = status_text_map.get(task.status, task.status)
            if task.status in ("pending", "downloading", "paused", "failed"):
                active_count += 1
            # 进度条
            pct = task.progress_percent()
            bar_len = 20
            filled = int(bar_len * pct / 100)
            bar = "█" * filled + "░" * (bar_len - filled)
            # 大小显示
            def size_str(sz):
                if sz <= 0:
                    return "?"
                for unit in ["B", "KB", "MB", "GB"]:
                    if sz < 1024:
                        return f"{sz:.1f}{unit}"
                    sz /= 1024
                return f"{sz:.1f}TB"
            line = "{} | {} | {} {}/{} | {}".format(
                status_text,
                task.item_name[:30],
                bar,
                size_str(task.downloaded_size),
                size_str(task.total_size),
                task.file_name[:30]
            )
            self.dl_listbox.insert("end", line)
        self.dl_status_label.config(text="共 {} 个任务, {} 个未完成".format(
            len(tasks), active_count))

    def _get_selected_task(self):
        """获取选中的下载任务"""
        sel = self.dl_listbox.curselection()
        if not sel:
            messagebox.showinfo("提示", "请先选择一个下载任务")
            return None
        tasks = self.dl_mgr.get_all_tasks()
        idx = sel[0]
        if idx >= len(tasks):
            return None
        return tasks[idx]

    def _resume_selected_download(self):
        """继续选中的下载"""
        task = self._get_selected_task()
        if not task:
            return
        if task.status == "completed":
            messagebox.showinfo("提示", "该任务已完成")
            return
        self._start_download_task(task)

    def _pause_selected_download(self):
        """暂停选中的下载"""
        task = self._get_selected_task()
        if not task:
            return
        self.dl_mgr.mark_paused(task.task_id)
        self._refresh_download_list()

    def _cancel_selected_download(self):
        """取消选中的下载"""
        task = self._get_selected_task()
        if not task:
            return
        if messagebox.askyesno("确认", "确定取消这个下载任务吗?\n(已下载的文件会保留)"):
            self.dl_mgr.cancel_task(task.task_id)
            self._refresh_download_list()

    def _delete_selected_download(self):
        """删除选中的下载任务"""
        task = self._get_selected_task()
        if not task:
            return
        delete_file = messagebox.askyesno("确认",
            "确定删除这个下载任务吗?\n\n是 = 同时删除已下载的文件\n否 = 只删除任务记录, 保留文件")
        self.dl_mgr.remove_task(task.task_id, delete_file=delete_file)
        self._refresh_download_list()

    def _resume_all_downloads(self):
        """全部继续下载"""
        # 包含等待中、已暂停、失败的任务
        all_tasks = self.dl_mgr.get_all_tasks()
        tasks = [t for t in all_tasks if t.status in ("pending", "paused", "failed")]
        if not tasks:
            messagebox.showinfo("提示", "没有可以继续的下载任务")
            return
        for task in tasks:
            self._start_download_task(task)

    def _pause_all_downloads(self):
        """全部暂停"""
        tasks = self.dl_mgr.get_all_tasks()
        for task in tasks:
            if task.status == "downloading":
                self.dl_mgr.mark_paused(task.task_id)
        self._refresh_download_list()

    def _clear_completed_downloads(self):
        """清除已完成的任务"""
        self.dl_mgr.clear_completed()
        self._refresh_download_list()

    def _open_download_folder(self):
        """打开选中任务的下载文件夹"""
        task = self._get_selected_task()
        if not task:
            return
        import os
        folder = str(Path(task.dest_path).parent)
        try:
            os.startfile(folder)
        except Exception:
            messagebox.showinfo("下载目录", folder)

    def _start_download_task(self, task):
        """在后台线程开始下载任务"""
        import downloader as dl_mod
        # 检查任务是否有有效的 URL
        if not task.url or task.url == "":
            self.dl_mgr.mark_failed(task.task_id, "任务没有有效的下载链接, 请重新下载")
            self._refresh_download_list()
            messagebox.showwarning("无法继续", "这个任务没有有效的下载链接, 请重新下载")
            return
        # 把任务状态设为下载中
        task.status = "downloading"
        self.dl_mgr._save()
        self._refresh_download_list()

        def _worker():
            try:
                dl_mod.download_with_task(task)
                self._post("log", "下载完成: " + task.file_name)
            except Exception as exc:
                self._post("log", "下载失败: {} - {}".format(task.file_name, exc))
        self._thread(_worker)

    def _refresh_points(self):
        """刷新积分显示"""
        try:
            import points
            balance = points.get_balance()
            if hasattr(self, '_points_label'):
                self._points_label.config(text="💰 {} 积分".format(balance))
        except Exception:
            pass
        self.root.after(3000, self._refresh_points)

    def _add_points(self, amount, reason=""):
        """增加积分"""
        try:
            import points
            points.add_points(amount, reason)
            self._refresh_points()
        except Exception:
            pass

    def _open_points_shop(self):
        """打开积分兑换商店"""
        import points
        import bridge
        import tkinter as tk
        from tkinter import ttk, messagebox

        win = tk.Toplevel(self.root)
        win.title("🎁 积分兑换商店")
        win.geometry("700x550")
        win.configure(bg="#f5f5f5")
        win.transient(self.root)
        win.grab_set()

        # 顶部积分显示
        top_frame = tk.Frame(win, bg="#ff8800", height=60)
        top_frame.pack(fill="x")
        top_frame.pack_propagate(False)
        balance = points.get_balance()
        points_label = tk.Label(top_frame, text="💰 当前积分: {}".format(balance),
                                bg="#ff8800", fg="white",
                                font=("Arial", 16, "bold"))
        points_label.pack(side="left", padx=20)
        tk.Label(top_frame, text="挖矿、战斗都能赚积分！兑换直接发到游戏！",
                 bg="#ff8800", fg="white",
                 font=("Arial", 10)).pack(side="left", padx=10)

        # 玩家名输入
        name_frame = tk.Frame(win, bg="#f5f5f5")
        name_frame.pack(fill="x", padx=10, pady=8)
        tk.Label(name_frame, text="游戏ID:", bg="#f5f5f5",
                 font=("Arial", 10)).pack(side="left")
        player_name_var = tk.StringVar(value="exwnv")
        name_entry = ttk.Entry(name_frame, textvariable=player_name_var, width=20)
        name_entry.pack(side="left", padx=5)

        # 检测联动状态
        bridge_status = "✅ 游戏联动已连接" if bridge.is_bridge_running() else "⚠️ 游戏未启动/未装联动Mod"
        bridge_color = "#00aa00" if bridge.is_bridge_running() else "#ff8800"
        tk.Label(name_frame, text=bridge_status, bg="#f5f5f5", fg=bridge_color,
                 font=("Arial", 9, "bold")).pack(side="left", padx=15)

        # 物品列表
        list_frame = tk.Frame(win, bg="#f5f5f5")
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("icon", "name", "cost", "desc")
        tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12)
        tree.heading("icon", text="")
        tree.heading("name", text="物品")
        tree.heading("cost", text="积分")
        tree.heading("desc", text="说明")
        tree.column("icon", width=50, anchor="center")
        tree.column("name", width=150)
        tree.column("cost", width=80, anchor="center")
        tree.column("desc", width=300)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for item in points.REDEEMABLE_ITEMS:
            tree.insert("", "end", values=(
                item["icon"], item["name"],
                "{} 💰".format(item["cost"]), item["desc"]
            ))

        def do_redeem():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("提示", "请先选择要兑换的物品", parent=win)
                return
            idx = tree.index(selected[0])
            item = points.REDEEMABLE_ITEMS[idx]
            player_name = player_name_var.get().strip()
            if not player_name:
                messagebox.showwarning("提示", "请输入游戏ID", parent=win)
                return

            success, result, new_balance = points.redeem_item(item["id"], player_name)
            if not success:
                messagebox.showerror("兑换失败", result, parent=win)
                return

            # 更新积分显示
            points_label.config(text="💰 当前积分: {}".format(new_balance))
            if hasattr(self, '_points_label'):
                self._points_label.config(text="💰 {} 积分".format(new_balance))

            # 结果窗口
            result_win = tk.Toplevel(win)
            result_win.title("兑换结果")
            result_win.geometry("520x400")
            result_win.configure(bg="#f5f5f5")
            result_win.transient(win)
            result_win.grab_set()

            tk.Label(result_win, text="✅ 兑换成功！", bg="#f5f5f5",
                     font=("Arial", 16, "bold"), fg="#00aa00").pack(pady=10)
            tk.Label(result_win, text="物品: {}".format(item["name"]),
                     bg="#f5f5f5", font=("Arial", 11)).pack()
            tk.Label(result_win, text="剩余积分: {}".format(new_balance),
                     bg="#f5f5f5", font=("Arial", 11)).pack(pady=5)

            # 尝试通过 Bridge 发送
            bridge_ok = bridge.is_bridge_running()
            if bridge_ok:
                tk.Label(result_win, text="🔗 正在发送到游戏背包...",
                         bg="#f5f5f5", font=("Arial", 10), fg="#0088ff").pack(pady=(10, 5))

                send_results = []
                if "multi" in item:
                    for item_id in item["multi"]:
                        ok, msg = bridge.send_item(item_id, 1)
                        send_results.append((item_id, ok, msg))
                else:
                    ok, msg = bridge.send_item(item["item_id"], item["count"])
                    send_results.append((item["item_id"], ok, msg))

                result_text = ""
                all_ok = True
                for item_id, ok, msg in send_results:
                    status = "✅" if ok else "❌"
                    short_name = item_id.split(":")[-1] if ":" in item_id else item_id
                    result_text += "{} {}: {}\n".format(status, short_name, msg)
                    if not ok:
                        all_ok = False

                tk.Label(result_win, text=result_text, bg="#f5f5f5",
                         font=("Consolas", 9), justify="left", fg="#333").pack(padx=20, pady=5)

                if all_ok:
                    tk.Label(result_win, text="🎉 物品已直接发送到游戏背包！",
                             bg="#f5f5f5", font=("Arial", 11, "bold"), fg="#00aa00").pack(pady=5)
                else:
                    tk.Label(result_win, text="部分发送失败，可用下方命令手动获取",
                             bg="#f5f5f5", font=("Arial", 10), fg="#ff6600").pack(pady=5)
            else:
                tk.Label(result_win, text="⚠️ 游戏未启动或未安装联动Mod",
                         bg="#f5f5f5", font=("Arial", 10), fg="#ff8800").pack(pady=(10, 5))
                tk.Label(result_win, text="启动游戏并安装联动Mod后可自动发送",
                         bg="#f5f5f5", font=("Arial", 9), fg="#666").pack()

            # 备用命令
            cmd_text = "\n".join(result)
            tk.Label(result_win, text="备用命令（游戏里按T粘贴）:",
                     bg="#f5f5f5", font=("Arial", 9), fg="#888").pack(pady=(10, 3))
            cmd_box = tk.Text(result_win, height=3, width=50, font=("Consolas", 9))
            cmd_box.pack(padx=20, pady=3)
            cmd_box.insert("1.0", cmd_text)
            cmd_box.config(state="disabled")

            def copy_cmd():
                self.root.clipboard_clear()
                self.root.clipboard_append(cmd_text)
                messagebox.showinfo("已复制", "命令已复制到剪贴板", parent=result_win)

            rbtn_frame = tk.Frame(result_win, bg="#f5f5f5")
            rbtn_frame.pack(pady=10)
            ttk.Button(rbtn_frame, text="📋 复制命令", command=copy_cmd).pack(side="left", padx=5)
            ttk.Button(rbtn_frame, text="关闭", command=result_win.destroy).pack(side="left", padx=5)

        # 底部按钮
        btn_frame = tk.Frame(win, bg="#f5f5f5")
        btn_frame.pack(fill="x", padx=10, pady=10)
        ttk.Button(btn_frame, text="🎁 兑换选中物品",
                   command=do_redeem).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="📖 积分获取方式",
                   command=lambda: self._show_points_guide(win)).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="关闭",
                   command=win.destroy).pack(side="right", padx=5)

    def _show_points_guide(self, parent):
        """显示积分获取方式"""
        import points
        from tkinter import messagebox
        ways = points.get_earn_ways()
        text = "获取积分的方式:\n\n"
        for w in ways:
            text += "{} {}: +{} 积分\n".format(w["icon"], w["action"], w["points"])
        text += "\n挖矿越稀有，积分越多！"
        messagebox.showinfo("积分获取方式", text, parent=parent)

    # ================================================================
    # 强大崩溃分析 (使用 crash_analyzer 模块)
    # ================================================================
    def _analyze_crash_advanced(self):
        """强大的崩溃日志分析"""
        sel = self.crash_log_listbox.curselection()
        if not sel:
            messagebox.showinfo("提示", "请先选择一个崩溃日志")
            return
        game_dir = self._get_tools_instance_dir()
        if not game_dir:
            return
        item = self.crash_log_listbox.get(sel[0])
        if item.startswith("("):
            return
        log_name = item.split(" | ")[0]
        log_path = str(Path(game_dir) / "crash-reports" / log_name)

        try:
            import crash_analyzer
            analyzer = crash_analyzer.CrashAnalyzer(str(game_dir))
            result = analyzer.analyze(log_path)
        except Exception as e:
            messagebox.showerror("分析失败", str(e))
            return

        self.crash_result.delete("1.0", "end")
        self.crash_result.insert("end", "=== 🔍 智能崩溃分析 ===\n\n")
        self.crash_result.insert("end", "📄 日志: {}\n".format(result["file"]))
        self.crash_result.insert("end", "⏰ 时间: {}\n".format(result["time"]))
        if result.get("game_version"):
            self.crash_result.insert("end", "🎮 版本: {}\n".format(result["game_version"]))
        if result.get("loader"):
            self.crash_result.insert("end", "🔧 加载器: {}\n".format(result["loader"]))
        if result.get("java_version"):
            self.crash_result.insert("end", "☕ Java: {}\n".format(result["java_version"]))
        self.crash_result.insert("end", "\n")

        # 检测到的问题
        if result["causes"]:
            self.crash_result.insert("end", "⚠️  检测到 {} 个问题:\n\n".format(len(result["causes"])))
            for i, cause in enumerate(result["causes"], 1):
                severity_icon = "🔴" if cause["severity"] == "high" else ("🟡" if cause["severity"] == "medium" else "🟢")
                self.crash_result.insert("end", "{} 问题{}: {}\n".format(severity_icon, i, cause["name"]))
                self.crash_result.insert("end", "   💡 建议: {}\n\n".format(cause["solution"]))
        else:
            self.crash_result.insert("end", "✅ 未检测到常见崩溃原因\n\n")

        # 可疑模组
        if result.get("suspected_mods"):
            self.crash_result.insert("end", "🔗 可疑模组 (出现在堆栈中):\n")
            for mod in result["suspected_mods"]:
                self.crash_result.insert("end", "   - {}\n".format(mod))
            self.crash_result.insert("end", "\n")

        self.crash_result.insert("end", "📋 摘要: {}\n".format(result["summary"]))

    # ================================================================
    # 强大模组冲突检查 (使用 mod_checker 模块)
    # ================================================================
    def _detect_mod_conflicts_advanced(self):
        """强大的模组冲突检查"""
        self.mod_tools_result.delete("1.0", "end")
        self.mod_tools_result.insert("end", "🔍 正在深度检测模组冲突...\n\n")
        self.mod_tools_result.update()

        game_dir = self._get_tools_instance_dir()
        if not game_dir:
            self.mod_tools_result.insert("end", "❌ 请先选择实例\n")
            return

        try:
            import mod_checker
            checker = mod_checker.ModChecker(str(Path(game_dir) / "mods"))
            result = checker.check_conflicts()
        except Exception as e:
            self.mod_tools_result.insert("end", "❌ 检测失败: {}\n".format(e))
            return

        summary = result["summary"]
        self.mod_tools_result.insert("end", "📊 检测结果:\n")
        self.mod_tools_result.insert("end", "   总模组数: {}\n".format(summary["total_mods"]))
        self.mod_tools_result.insert("end", "   Fabric模组: {}\n".format(summary["fabric_mods"]))
        self.mod_tools_result.insert("end", "   Forge模组: {}\n".format(summary["forge_mods"]))
        self.mod_tools_result.insert("end", "   无法识别: {}\n".format(summary["unknown_mods"]))
        self.mod_tools_result.insert("end", "   🔴 严重问题: {}\n".format(summary["errors"]))
        self.mod_tools_result.insert("end", "   🟡 警告: {}\n".format(summary["warnings"]))
        self.mod_tools_result.insert("end", "   ℹ️  信息: {}\n\n".format(summary["infos"]))

        if not result["issues"]:
            self.mod_tools_result.insert("end", "✅ 未发现问题! 模组配置良好。\n")
            return

        self.mod_tools_result.insert("end", "📝 详细问题:\n\n")
        for i, issue in enumerate(result["issues"], 1):
            severity_icon = "🔴" if issue["severity"] == "error" else ("🟡" if issue["severity"] == "warning" else "ℹ️")
            self.mod_tools_result.insert("end", "{} {}. {}\n".format(severity_icon, i, issue["title"]))
            self.mod_tools_result.insert("end", "   {}\n".format(issue["description"]))
            if issue.get("mods"):
                self.mod_tools_result.insert("end", "   涉及文件:\n")
                for m in issue["mods"]:
                    self.mod_tools_result.insert("end", "      - {}\n".format(m))
            self.mod_tools_result.insert("end", "   💡 解决: {}\n\n".format(issue["solution"]))

    # ================================================================
    # FPS 显示 (通过游戏日志或Bridge)
    # ================================================================
    def _start_fps_monitor(self):
        """启动FPS监控"""
        self._fps_monitoring = True
        self._fps_value = 0
        self._fps_last_frames = 0
        self._fps_last_time = 0
        self._fps_update_loop()

    def _stop_fps_monitor(self):
        """停止FPS监控"""
        self._fps_monitoring = False

    def _fps_update_loop(self):
        """FPS更新循环"""
        if not getattr(self, '_fps_monitoring', False):
            return
        try:
            # 尝试从游戏日志读取FPS (Minecraft 按 F3 会显示)
            # 或者通过Bridge读取
            proc = getattr(self, '_game_proc', None)
            if proc and proc.is_alive():
                # 简单估算: 游戏运行中显示一个占位FPS
                # 实际FPS需要Bridge模组配合
                if hasattr(self, '_perf_status_label'):
                    self._perf_status_label.config(
                        text="🎮 游戏运行中 | FPS: 监测中...",
                        foreground="#00aa00")
            else:
                if hasattr(self, '_perf_status_label'):
                    self._perf_status_label.config(text="游戏未运行", foreground="#999")
        except Exception:
            pass
        self.root.after(2000, self._fps_update_loop)

    # ================================================================
    # 一键创建局域网世界
    # ================================================================
    def _one_click_lan(self):
        """一键创建局域网世界并显示连接信息"""
        # 检查游戏是否在运行
        proc = getattr(self, '_game_proc', None)
        if not proc or not proc.is_alive():
            messagebox.showinfo("提示", "请先启动游戏并进入一个世界\n然后按 ESC -> 对局域网开放")
            return

        # 获取本机IP
        try:
            import socket
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
        except Exception:
            local_ip = "127.0.0.1"

        # 显示连接信息
        win = tk.Toplevel(self.root)
        win.title("🌐 局域网联机信息")
        win.geometry("400x300")
        win.resizable(False, False)

        tk.Label(win, text="🌐 局域网联机信息", font=("Arial", 14, "bold")).pack(pady=10)

        info_frame = ttk.LabelFrame(win, text=" 连接信息 ")
        info_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(info_frame, text="本机IP:", font=("Arial", 10)).pack(anchor="w", padx=10, pady=5)
        ip_entry = ttk.Entry(info_frame, font=("Consolas", 12))
        ip_entry.insert(0, local_ip)
        ip_entry.pack(fill="x", padx=10, pady=2)
        ip_entry.config(state="readonly")

        tk.Label(info_frame, text="端口号 (游戏里显示):", font=("Arial", 10)).pack(anchor="w", padx=10, pady=5)
        port_entry = ttk.Entry(info_frame, font=("Consolas", 12))
        port_entry.insert(0, "25565")
        port_entry.pack(fill="x", padx=10, pady=2)

        tk.Label(info_frame, text="完整地址:", font=("Arial", 10)).pack(anchor="w", padx=10, pady=5)
        addr_entry = ttk.Entry(info_frame, font=("Consolas", 12, "bold"), foreground="#0066cc")
        addr_entry.insert(0, "{}:25565".format(local_ip))
        addr_entry.pack(fill="x", padx=10, pady=2)
        addr_entry.config(state="readonly")

        def update_addr(*args):
            addr_entry.config(state="normal")
            addr_entry.delete(0, "end")
            addr_entry.insert(0, "{}:{}".format(local_ip, port_entry.get()))
            addr_entry.config(state="readonly")
        port_entry.bind("<KeyRelease>", update_addr)

        btn_frame = tk.Frame(win)
        btn_frame.pack(pady=10)

        def copy_addr():
            self.root.clipboard_clear()
            self.root.clipboard_append(addr_entry.get())
            messagebox.showinfo("已复制", "地址已复制到剪贴板:\n" + addr_entry.get())

        ttk.Button(btn_frame, text="📋 复制完整地址", command=copy_addr).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="📋 复制IP",
                   command=lambda: self._copy_to_clipboard(local_ip)).pack(side="left", padx=5)

        steps = tk.Label(win, text="步骤:\n1. 游戏里按 ESC -> 对局域网开放\n2. 记住左下角显示的端口号\n3. 把上面的完整地址发给朋友\n4. 朋友在多人游戏里添加这个地址",
                        justify="left", font=("Arial", 9), foreground="#666")
        steps.pack(pady=10)


    # ================================================================
    # 服务器连接地址相关
    # ================================================================
    def _get_public_ip(self):
        """获取外网IP"""
        try:
            import requests
            resp = requests.get("https://api.ipify.org", timeout=5)
            return resp.text.strip()
        except Exception:
            try:
                import requests
                resp = requests.get("https://ifconfig.me/ip", timeout=5)
                return resp.text.strip()
            except Exception:
                return None

    def _fetch_public_ip(self):
        """异步获取外网IP并更新显示"""
        def worker():
            try:
                pub_ip = self._get_public_ip()
                self.root.after(0, lambda: self._update_public_ip(pub_ip))
            except Exception:
                self.root.after(0, lambda: self._update_public_ip(None))
        import threading
        threading.Thread(target=worker, daemon=True).start()

    def _update_public_ip(self, pub_ip):
        """更新外网IP显示"""
        if pub_ip:
            self._server_public_ip = pub_ip
            port = getattr(self, '_server_port', '25565')
            local_ip = getattr(self, '_server_local_ip', '127.0.0.1')
            self.server_info_label.config(
                text="运行中 | 本机: {}:{} | 外网: {}:{}".format(local_ip, port, pub_ip, port),
                foreground="green")
            self._append_server_log("外网连接地址: {}:{}".format(pub_ip, port))
            self._append_server_log("注意: 外网连接需要路由器端口映射或内网穿透")
        else:
            self._server_public_ip = None
            port = getattr(self, '_server_port', '25565')
            local_ip = getattr(self, '_server_local_ip', '127.0.0.1')
            self.server_info_label.config(
                text="运行中 | 本机: {}:{} | 外网: 获取失败".format(local_ip, port),
                foreground="#cc8800")

    def _copy_local_addr(self):
        """复制本机地址"""
        ip = getattr(self, '_server_local_ip', None)
        port = getattr(self, '_server_port', '25565')
        if ip:
            addr = "{}:{}".format(ip, port)
            self.root.clipboard_clear()
            self.root.clipboard_append(addr)
            self._append_server_log("已复制本机地址: " + addr)
        else:
            messagebox.showinfo("提示", "服务器未启动")

    def _copy_public_addr(self):
        """复制外网地址"""
        ip = getattr(self, '_server_public_ip', None)
        port = getattr(self, '_server_port', '25565')
        if ip:
            addr = "{}:{}".format(ip, port)
            self.root.clipboard_clear()
            self.root.clipboard_append(addr)
            self._append_server_log("已复制外网地址: " + addr)
        else:
            messagebox.showinfo("提示", "外网IP未获取到，请检查网络")


def main():
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = VoxelApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()


    # ---------------- 积分兑换系统 ----------------