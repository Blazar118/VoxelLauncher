# -*- coding: utf-8 -*-
"""将图标 PNG 转为多尺寸 .ico 文件"""
from PIL import Image
import os

src = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\icon_design\icon_orig1_block_launch.png'
out = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\app.ico'

img = Image.open(src)
print('原始尺寸:', img.size, img.mode)
# 转 RGBA（处理透明）
img = img.convert('RGBA')

# 生成多尺寸 ico (Ico 最多支持 256)
sizes = [256, 128, 64, 48, 32, 16]
img.save(out, format='ICO', sizes=[(s, s) for s in sizes])
print('已生成:', out, os.path.getsize(out), 'bytes')

# 同时输出一张 256 的高清 PNG 供官网用
png_out = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\icon_design\app_icon_256.png'
img.resize((256, 256), Image.LANCZOS).save(png_out, format='PNG')
print('已生成 256px PNG:', png_out)

# 验证 ico 可读
from PIL import IcoImagePlugin
ico = Image.open(out)
print('ICO 格式验证:', ico.format, '尺寸列表:', ico.info.get('sizes'))
