# -*- coding: utf-8 -*-
filepath = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\ui_main.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 确保 modrinth_results 初始化 (在 __init__ 里找个位置加)
old_init = '''        self._reload_accounts()
        self._reload_instances()
        self.refresh_java()'''

new_init = '''        self.modrinth_results = []
        self.mr_selected_idx = -1
        self._reload_accounts()
        self._reload_instances()
        self.refresh_java()'''

if old_init in content:
    content = content.replace(old_init, new_init, 1)
    print("初始化变量添加成功")
else:
    print("未找到初始化位置")

# 2. 把自动搜索延迟从 800ms 改成 1500ms
old_auto = '''        # 打开页面自动搜索热门模组(空查询返回热门)
        self.root.after(800, self._mr_search)'''

new_auto = '''        # 打开页面自动搜索热门模组(空查询返回热门)
        self.root.after(1500, self._mr_search)'''

if old_auto in content:
    content = content.replace(old_auto, new_auto, 1)
    print("自动搜索延迟调整成功")
else:
    print("未找到自动搜索位置")

# 3. 给 _on_mr_list_update 添加 try-except
old_method = '''    def _on_mr_list_update(self, hits):
        """更新 Modrinth 搜索结果列表(带图标)"""
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
                             self._load_mr_icon(u, iid, i, cache_dir))'''

new_method = '''    def _on_mr_list_update(self, hits):
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
            traceback.print_exc()'''

if old_method in content:
    content = content.replace(old_method, new_method, 1)
    print("列表方法错误处理添加成功")
else:
    print("未找到列表方法")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

import ast
ast.parse(content)
print("语法OK")
