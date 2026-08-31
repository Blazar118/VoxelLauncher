# -*- coding: utf-8 -*-
"""
Minecraft 皮肤编辑器
支持 64x64 格式皮肤(1.8+), 可绘制各个身体部位, 保存为PNG并应用到游戏
"""
import tkinter as tk
from tkinter import ttk, colorchooser, messagebox, filedialog
from PIL import Image, ImageDraw, ImageTk
import os
import json
import shutil


# Minecraft 皮肤各部位在 64x64 贴图上的位置 (x, y, w, h)
# 格式: (u, v, width, height)
SKIN_PARTS = {
    # 头部
    "head_front": (8, 8, 8, 8),
    "head_back": (24, 8, 8, 8),
    "head_left": (16, 8, 8, 8),
    "head_right": (0, 8, 8, 8),
    "head_top": (8, 0, 8, 8),
    "head_bottom": (16, 0, 8, 8),
    # 头部外层(帽子)
    "hat_front": (40, 8, 8, 8),
    "hat_back": (56, 8, 8, 8),
    "hat_left": (48, 8, 8, 8),
    "hat_right": (32, 8, 8, 8),
    "hat_top": (40, 0, 8, 8),
    "hat_bottom": (48, 0, 8, 8),
    # 身体
    "body_front": (20, 20, 8, 12),
    "body_back": (32, 20, 8, 12),
    "body_left": (28, 20, 4, 12),
    "body_right": (16, 20, 4, 12),
    "body_top": (20, 16, 8, 4),
    "body_bottom": (28, 16, 8, 4),
    # 左臂
    "arm_left_front": (44, 20, 4, 12),
    "arm_left_back": (52, 20, 4, 12),
    "arm_left_left": (48, 20, 4, 12),
    "arm_left_right": (40, 20, 4, 12),
    "arm_left_top": (44, 16, 4, 4),
    "arm_left_bottom": (48, 16, 4, 4),
    # 右臂
    "arm_right_front": (36, 52, 4, 12),
    "arm_right_back": (44, 52, 4, 12),
    "arm_right_left": (40, 52, 4, 12),
    "arm_right_right": (32, 52, 4, 12),
    "arm_right_top": (36, 48, 4, 4),
    "arm_right_bottom": (40, 48, 4, 4),
    # 左腿
    "leg_left_front": (4, 20, 4, 12),
    "leg_left_back": (12, 20, 4, 12),
    "leg_left_left": (8, 20, 4, 12),
    "leg_left_right": (0, 20, 4, 12),
    "leg_left_top": (4, 16, 4, 4),
    "leg_left_bottom": (8, 16, 4, 4),
    # 右腿
    "leg_right_front": (20, 52, 4, 12),
    "leg_right_back": (28, 52, 4, 12),
    "leg_right_left": (24, 52, 4, 12),
    "leg_right_right": (16, 52, 4, 12),
    "leg_right_top": (20, 48, 4, 4),
    "leg_right_bottom": (24, 48, 4, 4),
    # 身体外层(夹克)
    "jacket_front": (20, 36, 8, 12),
    "jacket_back": (32, 36, 8, 12),
    "jacket_left": (28, 36, 4, 12),
    "jacket_right": (16, 36, 4, 12),
    "jacket_top": (20, 32, 8, 4),
    "jacket_bottom": (28, 32, 8, 4),
    # 左臂外层
    "arm_left_overlay_front": (44, 36, 4, 12),
    "arm_left_overlay_back": (52, 36, 4, 12),
    "arm_left_overlay_left": (48, 36, 4, 12),
    "arm_left_overlay_right": (40, 36, 4, 12),
    "arm_left_overlay_top": (44, 32, 4, 4),
    "arm_left_overlay_bottom": (48, 32, 4, 4),
    # 右臂外层
    "arm_right_overlay_front": (52, 52, 4, 12),
    "arm_right_overlay_back": (60, 52, 4, 12),
    "arm_right_overlay_left": (56, 52, 4, 12),
    "arm_right_overlay_right": (48, 52, 4, 12),
    "arm_right_overlay_top": (52, 48, 4, 4),
    "arm_right_overlay_bottom": (56, 48, 4, 4),
    # 左腿外层
    "leg_left_overlay_front": (4, 36, 4, 12),
    "leg_left_overlay_back": (12, 36, 4, 12),
    "leg_left_overlay_left": (8, 36, 4, 12),
    "leg_left_overlay_right": (0, 36, 4, 12),
    "leg_left_overlay_top": (4, 32, 4, 4),
    "leg_left_overlay_bottom": (8, 32, 4, 4),
    # 右腿外层
    "leg_right_overlay_front": (20, 68, 4, 12),
    "leg_right_overlay_back": (28, 68, 4, 12),
    "leg_right_overlay_left": (24, 68, 4, 12),
    "leg_right_overlay_right": (16, 68, 4, 12),
    "leg_right_overlay_top": (20, 64, 4, 4),
    "leg_right_overlay_bottom": (24, 64, 4, 4),
}

# 部位中文名
PART_NAMES = {
    "head_front": "头-正面", "head_back": "头-背面",
    "head_left": "头-左面", "head_right": "头-右面",
    "head_top": "头-顶面", "head_bottom": "头-底面",
    "hat_front": "帽子-正面", "hat_back": "帽子-背面",
    "hat_left": "帽子-左面", "hat_right": "帽子-右面",
    "hat_top": "帽子-顶面", "hat_bottom": "帽子-底面",
    "body_front": "身体-正面", "body_back": "身体-背面",
    "body_left": "身体-左面", "body_right": "身体-右面",
    "body_top": "身体-顶面", "body_bottom": "身体-底面",
    "arm_left_front": "左臂-正面", "arm_left_back": "左臂-背面",
    "arm_right_front": "右臂-正面", "arm_right_back": "右臂-背面",
    "leg_left_front": "左腿-正面", "leg_left_back": "左腿-背面",
    "leg_right_front": "右腿-正面", "leg_right_back": "右腿-背面",
}


class SkinEditor:
    """Minecraft 皮肤编辑器"""

    # 预设颜色
    PRESET_COLORS = [
        "#000000", "#333333", "#666666", "#999999", "#cccccc", "#ffffff",
        "#ff0000", "#ff6600", "#ffcc00", "#ffff00", "#99ff00", "#00ff00",
        "#00ff99", "#00ffff", "#0099ff", "#0000ff", "#6600ff", "#cc00ff",
        "#ff00cc", "#ff0066", "#8b4513", "#a0522d", "#cd853f", "#deb887",
        "#f5deb3", "#ffe4c4", "#ffdab9", "#ffc0cb", "#ffb6c1", "#ff69b4",
        "#4a3728", "#3d2817", "#2d1810", "#1a0f08", "#c0c0c0", "#808080",
    ]

    def __init__(self, parent, game_dir=None, on_save=None):
        self.parent = parent
        self.game_dir = game_dir
        self.on_save = on_save
        self.pixel_size = 12  # 每个像素显示大小
        self.current_color = "#000000"
        self.current_tool = "brush"  # brush, eraser, picker, fill
        self.skin_image = None
        self.zoom = 8
        self.history = []
        self.history_index = -1

        self.win = tk.Toplevel(parent)
        self.win.title("皮肤编辑器 - Minecraft Skin Editor")
        self.win.geometry("1100x750")
        self.win.minsize(900, 600)
        self.win.configure(bg="#2b2b2b")

        self._build_ui()
        self._new_skin()

    def _build_ui(self):
        """构建界面"""
        # 顶部工具栏
        toolbar = tk.Frame(self.win, bg="#3c3f41", height=50)
        toolbar.pack(fill="x", side="top")
        toolbar.pack_propagate(False)

        # 工具按钮
        tools = [
            ("画笔", "brush", "✏️"),
            ("橡皮擦", "eraser", "🧹"),
            ("取色器", "picker", "💧"),
            ("填充", "fill", "🪣"),
        ]
        self.tool_buttons = {}
        for name, tool, icon in tools:
            btn = tk.Button(toolbar, text=f"{icon} {name}",
                            command=lambda t=tool: self._set_tool(t),
                            bg="#5c5f61", fg="white", relief="flat",
                            padx=10, pady=5, font=("微软雅黑", 9))
            btn.pack(side="left", padx=4, pady=8)
            self.tool_buttons[tool] = btn
        self._update_tool_buttons()

        tk.Label(toolbar, text="|", bg="#3c3f41", fg="#666").pack(side="left", padx=5)

        # 撤销/重做
        tk.Button(toolbar, text="↩ 撤销", command=self._undo,
                  bg="#5c5f61", fg="white", relief="flat",
                  padx=8, pady=5, font=("微软雅黑", 9)).pack(side="left", padx=2)
        tk.Button(toolbar, text="↪ 重做", command=self._redo,
                  bg="#5c5f61", fg="white", relief="flat",
                  padx=8, pady=5, font=("微软雅黑", 9)).pack(side="left", padx=2)

        tk.Label(toolbar, text="|", bg="#3c3f41", fg="#666").pack(side="left", padx=5)

        # 文件操作
        tk.Button(toolbar, text="📂 打开皮肤", command=self._open_skin,
                  bg="#4a90d9", fg="white", relief="flat",
                  padx=8, pady=5, font=("微软雅黑", 9)).pack(side="left", padx=2)
        tk.Button(toolbar, text="💾 保存", command=self._save_skin,
                  bg="#4caf50", fg="white", relief="flat",
                  padx=8, pady=5, font=("微软雅黑", 9)).pack(side="left", padx=2)
        tk.Button(toolbar, text="🎮 应用到游戏", command=self._apply_to_game,
                  bg="#ff9800", fg="white", relief="flat",
                  padx=8, pady=5, font=("微软雅黑", 9)).pack(side="left", padx=2)
        tk.Button(toolbar, text="🆕 新建", command=self._new_skin,
                  bg="#5c5f61", fg="white", relief="flat",
                  padx=8, pady=5, font=("微软雅黑", 9)).pack(side="left", padx=2)

        # 主区域: 左边调色板, 中间画布, 右边部位选择+预览
        main = tk.Frame(self.win, bg="#2b2b2b")
        main.pack(fill="both", expand=True)

        # 左边: 调色板
        left_panel = tk.Frame(main, bg="#3c3f41", width=200)
        left_panel.pack(side="left", fill="y")
        left_panel.pack_propagate(False)

        tk.Label(left_panel, text="调色板", bg="#3c3f41", fg="#ddd",
                 font=("微软雅黑", 11, "bold")).pack(pady=10)

        # 当前颜色
        color_frame = tk.Frame(left_panel, bg="#3c3f41")
        color_frame.pack(pady=5)
        self.color_preview = tk.Label(color_frame, text="    ", bg=self.current_color,
                                      width=6, height=2, relief="sunken", borderwidth=2)
        self.color_preview.pack(side="left", padx=5)
        tk.Button(color_frame, text="自定义", command=self._pick_color,
                  bg="#5c5f61", fg="white", relief="flat",
                  font=("微软雅黑", 9)).pack(side="left")

        # 预设颜色网格
        palette_frame = tk.Frame(left_panel, bg="#3c3f41")
        palette_frame.pack(pady=10, padx=10)
        for i, color in enumerate(self.PRESET_COLORS):
            row, col = divmod(i, 6)
            btn = tk.Button(palette_frame, bg=color, width=2, height=1,
                            relief="flat", borderwidth=1,
                            command=lambda c=color: self._set_color(c))
            btn.grid(row=row, column=col, padx=1, pady=1)

        # 笔刷大小
        tk.Label(left_panel, text="笔刷大小", bg="#3c3f41", fg="#ddd",
                 font=("微软雅黑", 9)).pack(pady=(15, 2))
        self.brush_size = tk.IntVar(value=1)
        size_frame = tk.Frame(left_panel, bg="#3c3f41")
        size_frame.pack()
        for size in [1, 2, 3]:
            tk.Radiobutton(size_frame, text=str(size), variable=self.brush_size,
                           value=size, bg="#3c3f41", fg="#ddd",
                           selectcolor="#5c5f61", activebackground="#3c3f41",
                           font=("微软雅黑", 9)).pack(side="left", padx=5)

        # 中间: 画布区域
        center_panel = tk.Frame(main, bg="#2b2b2b")
        center_panel.pack(side="left", fill="both", expand=True)

        # 画布标题
        canvas_title = tk.Frame(center_panel, bg="#2b2b2b")
        canvas_title.pack(fill="x", padx=10, pady=5)
        tk.Label(canvas_title, text="皮肤展开图 (64x64)", bg="#2b2b2b", fg="#ddd",
                 font=("微软雅黑", 10, "bold")).pack(side="left")
        tk.Label(canvas_title, text="左键绘制 | 右键取色 | 滚轮缩放",
                 bg="#2b2b2b", fg="#888", font=("微软雅黑", 8)).pack(side="right")

        # 滚动画布
        canvas_container = tk.Frame(center_panel, bg="#1e1e1e")
        canvas_container.pack(fill="both", expand=True, padx=10, pady=5)

        self.canvas = tk.Canvas(canvas_container, bg="#1e1e1e",
                                highlightthickness=0)
        h_scroll = tk.Scrollbar(canvas_container, orient="horizontal",
                                command=self.canvas.xview)
        v_scroll = tk.Scrollbar(canvas_container, orient="vertical",
                                command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=h_scroll.set,
                              yscrollcommand=v_scroll.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        canvas_container.grid_rowconfigure(0, weight=1)
        canvas_container.grid_columnconfigure(0, weight=1)

        self.canvas.bind("<Button-1>", self._on_left_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<Button-3>", self._on_right_click)
        self.canvas.bind("<MouseWheel>", self._on_zoom)

        # 右边: 部位选择 + 3D预览
        right_panel = tk.Frame(main, bg="#3c3f41", width=220)
        right_panel.pack(side="right", fill="y")
        right_panel.pack_propagate(False)

        tk.Label(right_panel, text="部位选择", bg="#3c3f41", fg="#ddd",
                 font=("微软雅黑", 11, "bold")).pack(pady=10)

        # 部位列表
        list_frame = tk.Frame(right_panel, bg="#3c3f41")
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.part_listbox = tk.Listbox(list_frame, bg="#2b2b2b", fg="#ddd",
                                       selectbackground="#4a90d9",
                                       font=("微软雅黑", 9), relief="flat")
        self.part_listbox.pack(side="left", fill="both", expand=True)
        part_scroll = tk.Scrollbar(list_frame, command=self.part_listbox.yview)
        part_scroll.pack(side="right", fill="y")
        self.part_listbox.configure(yscrollcommand=part_scroll.set)

        for key, name in PART_NAMES.items():
            self.part_listbox.insert("end", name)
        self.part_listbox.bind("<<ListboxSelect>>", self._on_part_select)

        # 预览
        tk.Label(right_panel, text="正面预览", bg="#3c3f41", fg="#ddd",
                 font=("微软雅黑", 10, "bold")).pack(pady=(10, 5))
        self.preview_canvas = tk.Canvas(right_panel, width=160, height=240,
                                        bg="#1e1e1e", highlightthickness=0)
        self.preview_canvas.pack(pady=5)

        # 状态栏
        self.status_bar = tk.Label(self.win, text="就绪", bg="#3c3f41", fg="#aaa",
                                   anchor="w", padx=10, font=("微软雅黑", 8))
        self.status_bar.pack(fill="x", side="bottom")

    def _new_skin(self):
        """新建一个空白皮肤(透明背景)"""
        self.skin_image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        # 默认填充皮肤底色
        draw = ImageDraw.Draw(self.skin_image)
        skin_color = (139, 90, 43, 255)  # 默认肤色
        for part in ["head_front", "body_front", "arm_left_front", "arm_right_front",
                     "leg_left_front", "leg_right_front", "head_back", "body_back"]:
            x, y, w, h = SKIN_PARTS[part]
            draw.rectangle([x, y, x + w, y + h], fill=skin_color)
        self._push_history()
        self._redraw()
        self._set_status("新建皮肤完成")

    def _open_skin(self):
        """打开现有皮肤文件"""
        path = filedialog.askopenfilename(
            title="选择皮肤文件",
            filetypes=[("PNG图片", "*.png"), ("所有文件", "*.*")]
        )
        if not path:
            return
        try:
            img = Image.open(path).convert("RGBA")
            if img.size != (64, 64):
                if img.size == (64, 32):
                    # 旧版皮肤, 转换为64x64
                    new_img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
                    new_img.paste(img, (0, 0))
                    img = new_img
                else:
                    messagebox.showwarning("警告", f"皮肤尺寸应为64x64, 当前为{img.size}")
                    return
            self.skin_image = img
            self._push_history()
            self._redraw()
            self._set_status(f"已打开: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("错误", f"打开失败: {e}")

    def _save_skin(self):
        """保存皮肤为PNG"""
        path = filedialog.asksaveasfilename(
            title="保存皮肤",
            defaultextension=".png",
            filetypes=[("PNG图片", "*.png")],
            initialfile="my_skin.png"
        )
        if not path:
            return
        try:
            self.skin_image.save(path, "PNG")
            self._set_status(f"已保存: {path}")
            if self.on_save:
                self.on_save(path)
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {e}")

    def _apply_to_game(self):
        """应用皮肤到游戏"""
        if not self.game_dir:
            messagebox.showwarning("提示", "未设置游戏目录")
            return
        try:
            # 保存到临时位置
            temp_path = os.path.join(os.environ.get("APPDATA", "."),
                                     "VoxelLauncher", "custom_skin.png")
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            self.skin_image.save(temp_path, "PNG")

            # 尝试复制到游戏的皮肤位置
            # Minecraft 离线模式的皮肤在 assets 里, 这里保存到启动器配置
            config_path = os.path.join(os.environ.get("APPDATA", "."),
                                       "VoxelLauncher", "skin_config.json")
            config = {}
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            config["custom_skin"] = temp_path
            config["skin_enabled"] = True
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            self._set_status(f"皮肤已保存, 启动游戏时会自动应用")
            messagebox.showinfo("成功", "皮肤已保存!\n下次启动游戏时会自动应用此皮肤。")
        except Exception as e:
            messagebox.showerror("错误", f"应用失败: {e}")

    def _set_tool(self, tool):
        self.current_tool = tool
        self._update_tool_buttons()
        self._set_status(f"当前工具: {tool}")

    def _update_tool_buttons(self):
        for tool, btn in self.tool_buttons.items():
            if tool == self.current_tool:
                btn.config(bg="#4a90d9", relief="sunken")
            else:
                btn.config(bg="#5c5f61", relief="flat")

    def _set_color(self, color):
        self.current_color = color
        self.color_preview.config(bg=color)
        if self.current_tool == "eraser":
            self.current_tool = "brush"
            self._update_tool_buttons()

    def _pick_color(self):
        color = colorchooser.askcolor(color=self.current_color, title="选择颜色")[1]
        if color:
            self._set_color(color)

    def _on_left_click(self, event):
        self._paint(event)

    def _on_drag(self, event):
        self._paint(event)

    def _on_right_click(self, event):
        """右键取色"""
        x, y = self._canvas_to_skin(event.x, event.y)
        if 0 <= x < 64 and 0 <= y < 64:
            pixel = self.skin_image.getpixel((x, y))
            if pixel[3] > 0:
                color = "#{:02x}{:02x}{:02x}".format(pixel[0], pixel[1], pixel[2])
                self._set_color(color)
                self._set_status(f"取色: {color}")

    def _on_zoom(self, event):
        """滚轮缩放"""
        if event.delta > 0:
            self.zoom = min(self.zoom + 1, 20)
        else:
            self.zoom = max(self.zoom - 1, 2)
        self._redraw()

    def _paint(self, event):
        """在画布上绘制"""
        x, y = self._canvas_to_skin(event.x, event.y)
        if not (0 <= x < 64 and 0 <= y < 64):
            return

        size = self.brush_size.get()
        draw = ImageDraw.Draw(self.skin_image)

        if self.current_tool == "brush":
            color = self._hex_to_rgba(self.current_color)
            for dx in range(size):
                for dy in range(size):
                    px, py = x + dx, y + dy
                    if 0 <= px < 64 and 0 <= py < 64:
                        draw.point((px, py), fill=color)
        elif self.current_tool == "eraser":
            for dx in range(size):
                for dy in range(size):
                    px, py = x + dx, y + dy
                    if 0 <= px < 64 and 0 <= py < 64:
                        draw.point((px, py), fill=(0, 0, 0, 0))
        elif self.current_tool == "picker":
            pixel = self.skin_image.getpixel((x, y))
            if pixel[3] > 0:
                color = "#{:02x}{:02x}{:02x}".format(pixel[0], pixel[1], pixel[2])
                self._set_color(color)
                self.current_tool = "brush"
                self._update_tool_buttons()
        elif self.current_tool == "fill":
            self._flood_fill(x, y)

        self._redraw()

    def _flood_fill(self, x, y):
        """填充工具"""
        target_color = self.skin_image.getpixel((x, y))
        if self.current_tool == "fill":
            fill_color = self._hex_to_rgba(self.current_color)
        else:
            fill_color = (0, 0, 0, 0)

        if target_color == fill_color:
            return

        pixels = self.skin_image.load()
        stack = [(x, y)]
        visited = set()

        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in visited:
                continue
            if not (0 <= cx < 64 and 0 <= cy < 64):
                continue
            if pixels[cx, cy] != target_color:
                continue
            visited.add((cx, cy))
            pixels[cx, cy] = fill_color
            stack.extend([(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)])

    def _canvas_to_skin(self, canvas_x, canvas_y):
        """画布坐标转换为皮肤坐标"""
        x = int(canvas_x / self.zoom)
        y = int(canvas_y / self.zoom)
        return x, y

    def _redraw(self):
        """重绘画布"""
        self.canvas.delete("all")
        if not self.skin_image:
            return

        # 放大显示
        zoomed = self.skin_image.resize((64 * self.zoom, 64 * self.zoom), Image.NEAREST)
        self._canvas_image = ImageTk.PhotoImage(zoomed)
        self.canvas.create_image(0, 0, anchor="nw", image=self._canvas_image)
        self.canvas.configure(scrollregion=(0, 0, 64 * self.zoom, 64 * self.zoom))

        # 画网格线
        for i in range(65):
            x = i * self.zoom
            self.canvas.create_line(x, 0, x, 64 * self.zoom,
                                    fill="#333", width=1)
            self.canvas.create_line(0, x, 64 * self.zoom, x,
                                    fill="#333", width=1)

        # 高亮选中的部位
        selection = self.part_listbox.curselection()
        if selection:
            idx = selection[0]
            part_key = list(PART_NAMES.keys())[idx]
            if part_key in SKIN_PARTS:
                u, v, w, h = SKIN_PARTS[part_key]
                x1 = u * self.zoom
                y1 = v * self.zoom
                x2 = (u + w) * self.zoom
                y2 = (v + h) * self.zoom
                self.canvas.create_rectangle(x1, y1, x2, y2,
                                             outline="#ff6600", width=3)

        self._update_preview()

    def _update_preview(self):
        """更新正面预览"""
        self.preview_canvas.delete("all")
        if not self.skin_image:
            return

        # 简单的正面预览: 头+身体+手臂+腿
        scale = 4
        parts = [
            ("head_front", 64, 10, 8, 8),
            ("body_front", 64, 42, 8, 12),
            ("arm_right_front", 32, 42, 4, 12),
            ("arm_left_front", 96, 42, 4, 12),
            ("leg_right_front", 48, 90, 4, 12),
            ("leg_left_front", 80, 90, 4, 12),
        ]

        for part_key, px, py, pw, ph in parts:
            if part_key not in SKIN_PARTS:
                continue
            u, v, w, h = SKIN_PARTS[part_key]
            region = self.skin_image.crop((u, v, u + w, v + h))
            scaled = region.resize((pw * scale, ph * scale), Image.NEAREST)
            self._preview_img = ImageTk.PhotoImage(scaled)
            self.preview_canvas.create_image(px, py, anchor="nw", image=self._preview_img)

    def _on_part_select(self, event):
        self._redraw()

    def _push_history(self):
        """保存历史记录"""
        if self.skin_image:
            self.history = self.history[:self.history_index + 1]
            self.history.append(self.skin_image.copy())
            self.history_index = len(self.history) - 1
            if len(self.history) > 50:
                self.history.pop(0)
                self.history_index -= 1

    def _undo(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.skin_image = self.history[self.history_index].copy()
            self._redraw()
            self._set_status("撤销")

    def _redo(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.skin_image = self.history[self.history_index].copy()
            self._redraw()
            self._set_status("重做")

    @staticmethod
    def _hex_to_rgba(hex_color):
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4)) + (255,)

    def _set_status(self, text):
        self.status_bar.config(text=text)


def open_skin_editor(parent, game_dir=None, on_save=None):
    """打开皮肤编辑器"""
    return SkinEditor(parent, game_dir, on_save)
