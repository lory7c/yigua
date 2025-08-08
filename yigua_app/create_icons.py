#!/usr/bin/env python3
"""
创建临时的Android应用图标
"""
import os
from PIL import Image, ImageDraw, ImageFont

# 创建一个简单的易卦图标
def create_icon(size):
    # 创建一个新图像，使用渐变背景
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 绘制背景（紫色渐变）
    for i in range(size):
        color = int(100 + (155 * i / size))
        draw.rectangle([0, i, size, i+1], fill=(color, 50, 200, 255))
    
    # 绘制圆形背景
    margin = size // 8
    draw.ellipse([margin, margin, size-margin, size-margin], 
                 fill=(255, 255, 255, 240))
    
    # 绘制易字
    text = "易"
    # 计算文字大小
    text_size = size // 2
    try:
        # 尝试使用系统字体
        font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", text_size)
    except:
        # 使用默认字体
        font = ImageFont.load_default()
    
    # 获取文字边界框
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # 计算文字位置（居中）
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - size // 10
    
    # 绘制文字
    draw.text((x, y), text, fill=(100, 50, 200), font=font)
    
    return img

# 图标尺寸配置
icon_sizes = {
    'mipmap-mdpi': 48,
    'mipmap-hdpi': 72,
    'mipmap-xhdpi': 96,
    'mipmap-xxhdpi': 144,
    'mipmap-xxxhdpi': 192,
}

# 创建图标
base_path = 'android/app/src/main/res'
for folder, size in icon_sizes.items():
    # 创建目录
    dir_path = os.path.join(base_path, folder)
    os.makedirs(dir_path, exist_ok=True)
    
    # 创建并保存图标
    icon = create_icon(size)
    icon_path = os.path.join(dir_path, 'ic_launcher.png')
    icon.save(icon_path, 'PNG')
    print(f"Created {icon_path} ({size}x{size})")

print("✅ All icons created successfully!")