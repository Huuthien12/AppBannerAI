import streamlit as st
import pandas as pd
import os
import random
import re
import io
import zipfile
import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter, ImageEnhance
from datetime import datetime
import unicodedata
import hashlib
import tempfile
import shutil
from typing import Optional, Dict, List, Tuple
import google.generativeai as genai
import math

# --- PAGE CONFIG ---
st.set_page_config(page_title="Riviu TikTok AI Pro", layout="wide", page_icon="🎬")

# --- KHỞI TẠO SESSION STATE ---
if 'zip_data' not in st.session_state:
    st.session_state.zip_data = None
if 'excel_data' not in st.session_state:
    st.session_state.excel_data = None
if 'caption_df' not in st.session_state:
    st.session_state.caption_df = None
if 'partner_logs' not in st.session_state:
    st.session_state.partner_logs = {}

# --- CẤU HÌNH ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = tempfile.mkdtemp(prefix="riviu_")
LOGO_PATH = os.path.join(BASE_DIR, "logo_riviu.png")
HARD_HASHTAGS = "#riviudalat #dalat #dalatreview"

# Danh sách font ưu tiên có hỗ trợ tiếng Việt
FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "C:/Windows/Fonts/Arial.ttf",
    "C:/Windows/Fonts/Times.ttf",
    "C:/Windows/Fonts/Calibri.ttf",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "arial.ttf", "Arial.ttf", "DejaVuSans.ttf"
]

FONT_DOWNLOAD_URL = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSans/NotoSans-Regular.ttf"

# --- ĐỊNH NGHĨA LAYOUT VÀ HÌNH DẠNG NỀN ---
TEXT_POSITIONS = [
    "bottom-left",      # Góc dưới trái
    "bottom-right",     # Góc dưới phải  
    "top-center",       # Trên cùng giữa
    "center",           # Chính giữa
    "top-left",         # Góc trên trái
    "bottom-center"     # Dưới cùng giữa
]

BACKGROUND_SHAPES = [
    "rounded-rectangle",    # Hình chữ nhật bo góc
    "ellipse",              # Hình elip
    "banner-ribbon",        # Dải băng
    "highlight-stroke",     # Viền nổi bật
    "tag-label",            # Nhãn tag
    "paper-note",           # Giấy note
    "wooden-sign",          # Bảng gỗ
    "organic-blob",         # Hình blob tự nhiên
    "diagonal-banner",      # Banner chéo
    "glass-morphism"        # Kính mờ
]

# Màu sắc cho các theme (cập nhật để dễ nhìn hơn)
COLOR_THEMES = [
    {"name": "Đỏ Đen", "primary": "#FF1A1A", "secondary": "#FFFFFF", "bg": (0, 0, 0, 180), "text_light": True},
    {"name": "Vàng Trắng", "primary": "#FFD700", "secondary": "#000000", "bg": (255, 255, 255, 200), "text_light": False},
    {"name": "Xanh lá Đen", "primary": "#4CAF50", "secondary": "#FFFFFF", "bg": (0, 0, 0, 160), "text_light": True},
    {"name": "Xanh dương Đen", "primary": "#2196F3", "secondary": "#FFFFFF", "bg": (0, 0, 0, 170), "text_light": True},
    {"name": "Tím Đen", "primary": "#9C27B0", "secondary": "#FFFFFF", "bg": (0, 0, 0, 180), "text_light": True},
    {"name": "Cam Trắng", "primary": "#FF9800", "secondary": "#000000", "bg": (255, 255, 255, 190), "text_light": False},
    {"name": "Hồng Pastel", "primary": "#E91E63", "secondary": "#FFFFFF", "bg": (255, 235, 238, 200), "text_light": False},
    {"name": "Xanh Mint", "primary": "#009688", "secondary": "#FFFFFF", "bg": (0, 0, 0, 170), "text_light": True},
]

# --- HÀM TIỆN ÍCH ---
def normalize_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize('NFKC', text).strip().lower()
    text = re.sub(r'[^\w\s]', '', text)
    return re.sub(r'\s+', ' ', text).strip()

def download_fallback_font():
    font_path = os.path.join(TEMP_DIR, "NotoSans-Regular.ttf")
    if not os.path.exists(font_path):
        try:
            response = requests.get(FONT_DOWNLOAD_URL, timeout=30)
            if response.status_code == 200:
                with open(font_path, 'wb') as f:
                    f.write(response.content)
                return font_path
        except:
            pass
    return font_path if os.path.exists(font_path) else None

def get_random_font_path(seed: int = None) -> str:
    if seed is not None:
        random.seed(seed)
    valid_fonts = [p for p in FONT_PATHS if os.path.exists(p)]
    if not valid_fonts:
        fallback = download_fallback_font()
        if fallback:
            valid_fonts = [fallback]
    if not valid_fonts:
        font_dirs = ["/usr/share/fonts", "C:/Windows/Fonts", "/System/Library/Fonts"]
        for d in font_dirs:
            if os.path.exists(d):
                for root, _, files in os.walk(d):
                    for f in files:
                        if f.lower().endswith(('.ttf', '.otf')):
                            return os.path.join(root, f)
        return None
    return random.choice(valid_fonts)

def load_font(size: int, font_path: str = None) -> ImageFont.FreeTypeFont:
    if font_path and os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, size)
        except:
            pass
    for path in FONT_PATHS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except:
                continue
    fallback = download_fallback_font()
    if fallback:
        try:
            return ImageFont.truetype(fallback, size)
        except:
            pass
    return ImageFont.load_default()

def draw_location_pin(draw, x, y, size=69, color_theme=None):
    red_color = "#FF1A1A"
    stick_color = "#0B0A0A"
    x_offset = int(size * 0.65)
    y_offset = int(size * 0.74)
    new_x = x + x_offset
    new_y = y + y_offset
    stick_height = int(size * 0.7)
    stick_w = max(3, int(size * 0.13))
    circle_r = int(size * 0.35)
    circle_center = (int(new_x + size / 2), int(new_y - stick_height))
    stick_start = (int(new_x + size / 2), int(new_y + size / 2))
    stick_end = (circle_center[0], circle_center[1] - circle_r - int(size * 0.22))
    draw.line([stick_start, stick_end], fill=stick_color, width=stick_w)
    draw.ellipse([
        circle_center[0] - circle_r, circle_center[1] - circle_r,
        circle_center[0] + circle_r, circle_center[1] + circle_r
    ], fill=red_color)
    highlight_r = int(circle_r * 0.4)
    highlight_color = "#FF6666" if color_theme and color_theme["text_light"] else "#FF9999"
    draw.ellipse([
        circle_center[0] - highlight_r, circle_center[1] - highlight_r,
        circle_center[0], circle_center[1]
    ], fill=highlight_color)

def draw_background_shape(draw, bbox, shape_type, color_theme):
    """Vẽ hình dạng nền cho text"""
    x1, y1, x2, y2 = bbox
    padding = 20
    
    if shape_type == "rounded-rectangle":
        draw.rounded_rectangle([x1-padding, y1-padding, x2+padding, y2+padding], 
                              radius=15, fill=color_theme["bg"])
    elif shape_type == "ellipse":
        draw.ellipse([x1-padding, y1-padding, x2+padding, y2+padding], 
                    fill=color_theme["bg"])
    elif shape_type == "banner-ribbon":
        # Vẽ ribbon với đuôi nhọn
        points = [
            (x1-padding-30, y1-padding),  # Điểm nhọn trái
            (x1-padding, y1-padding),
            (x2+padding, y1-padding),
            (x2+padding+30, (y1+y2)/2),    # Điểm nhọn phải
            (x2+padding, y2+padding),
            (x1-padding, y2+padding)
        ]
        draw.polygon(points, fill=color_theme["bg"])
    elif shape_type == "highlight-stroke":
        # Viền đậm với màu primary
        draw.rectangle([x1-padding, y1-padding, x2+padding, y2+padding], 
                      outline=color_theme["primary"], width=4)
    elif shape_type == "tag-label":
        # Hình tag với lỗ tròn
        draw.rounded_rectangle([x1-padding, y1-padding, x2+padding, y2+padding], 
                              radius=10, fill=color_theme["bg"])
        circle_x = x1 - padding + 15
        circle_y = (y1 + y2) // 2
        draw.ellipse([circle_x-8, circle_y-8, circle_x+8, circle_y+8], 
                    fill=color_theme["secondary"])
    elif shape_type == "paper-note":
        # Giấy note với ghim
        draw.rectangle([x1-padding, y1-padding, x2+padding, y2+padding], 
                      fill=color_theme["bg"])
        # Vẽ ghim
        pin_x = (x1 + x2) // 2
        pin_y = y1 - padding + 5
        draw.ellipse([pin_x-10, pin_y-10, pin_x+10, pin_y+10], 
                    fill=color_theme["primary"])
    elif shape_type == "wooden-sign":
        # Bảng gỗ với dây treo
        draw.rectangle([x1-padding, y1-padding, x2+padding, y2+padding], 
                      fill=(139, 69, 19, 200))
        # Vẽ dây
        rope_y = y1 - padding - 10
        draw.arc([x1-padding, rope_y, x1+padding, rope_y+20], 0, 180, 
                fill=(101, 67, 33), width=3)
    elif shape_type == "organic-blob":
        # Hình blob tự nhiên (đơn giản hóa)
        points = []
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        radius_x = (x2 - x1) // 2 + padding
        radius_y = (y2 - y1) // 2 + padding
        for angle in range(0, 360, 30):
            rad = math.radians(angle)
            r_var = 1 + 0.1 * math.sin(3 * rad)
            x = center_x + radius_x * r_var * math.cos(rad)
            y = center_y + radius_y * r_var * math.sin(rad)
            points.append((x, y))
        draw.polygon(points, fill=color_theme["bg"])
    elif shape_type == "diagonal-banner":
        # Banner chéo
        width = x2 - x1 + 2*padding
        height = y2 - y1 + 2*padding
        draw.polygon([
            (x1-padding, y1-padding),
            (x1-padding+width*0.85, y1-padding),
            (x2+padding, y2+padding),
            (x1-padding+width*0.15, y2+padding)
        ], fill=color_theme["bg"])
    elif shape_type == "glass-morphism":
        # Hiệu ứng kính mờ
        overlay = Image.new('RGBA', (x2-x1+2*padding, y2-y1+2*padding), 
                           color_theme["bg"])
        overlay = overlay.filter(ImageFilter.GaussianBlur(radius=5))
        # Vẽ viền trắng mờ
        draw.rounded_rectangle([x1-padding, y1-padding, x2+padding, y2+padding],
                              radius=15, outline=(255,255,255,100), width=2)

def add_text_with_layout(image_pil, ten, gio, dc, target_size, layout_config, color_theme, font_path=None, font_scale=1.0):
    """
    Thêm text vào ảnh với layout, hình dạng nền và COLOR THEME được chỉ định
    """
    try:
        img = ImageOps.fit(image_pil.convert("RGB"), target_size, centering=(0.5, 0.5))
        
        # Tạo overlay cho background shape nếu cần
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Convert to RGBA for compositing
        img = img.convert("RGBA")
        draw = ImageDraw.Draw(img)
        
        width, height = img.size
        scale_factor = (target_size[0] / 900.0) * font_scale
        
        # Font sizes
        font_size_ten = max(35, int(60 * scale_factor))
        font_size_info = max(22, int(28 * scale_factor))
        
        font_ten = load_font(font_size_ten, font_path)
        font_info = load_font(font_size_info, font_path)
        
        position = layout_config.get("position", "bottom-left")
        shape = layout_config.get("shape", "rounded-rectangle")
        
        # Tính toán vị trí text
        margin = int(40 * scale_factor / font_scale)
        
        # Đo kích thước text
        ten_bbox = draw.textbbox((0, 0), ten.upper(), font=font_ten)
        info_bbox = draw.textbbox((0, 0), f"Giờ mở cửa: {gio}", font=font_info)
        dc_bbox = draw.textbbox((0, 0), dc, font=font_info)
        
        ten_width = ten_bbox[2] - ten_bbox[0]
        ten_height = ten_bbox[3] - ten_bbox[1]
        info_height = info_bbox[3] - info_bbox[1]
        dc_height = dc_bbox[3] - dc_bbox[1]
        
        total_height = ten_height + info_height + dc_height + 20
        max_width = max(ten_width, info_bbox[2] - info_bbox[0] + 100, 
                       dc_bbox[2] - dc_bbox[0] + 100)  # +100 cho icon pin
        
        # Xác định vị trí theo layout
        if position == "bottom-left":
            x = margin
            y = height - total_height - margin * 2
        elif position == "bottom-right":
            x = width - max_width - margin
            y = height - total_height - margin * 2
        elif position == "top-center":
            x = (width - max_width) // 2
            y = margin * 2
        elif position == "center":
            x = (width - max_width) // 2
            y = (height - total_height) // 2
        elif position == "top-left":
            x = margin
            y = margin * 2
        elif position == "bottom-center":
            x = (width - max_width) // 2
            y = height - total_height - margin * 2
        else:  # bottom-left default
            x = margin
            y = height - total_height - margin * 2
        
        # Vẽ background shape trên overlay
        text_bbox = [x, y, x + max_width, y + total_height]
        draw_background_shape(overlay_draw, text_bbox, shape, color_theme)
        
        # Composite overlay lên ảnh
        img = Image.alpha_composite(img, overlay)
        draw = ImageDraw.Draw(img)
        
        # Xác định màu text dựa trên theme
        text_color = "#FFFFFF" if color_theme["text_light"] else "#000000"
        primary_color = color_theme["primary"]
        secondary_text_color = "#E0E0E0" if color_theme["text_light"] else "#333333"
        
        # Vẽ text
        current_y = y + 10
        
        # Tên quán
        if position in ["top-center", "center", "bottom-center"]:
            text_x = x + (max_width - ten_width) // 2
        else:
            text_x = x + 10
            
        draw.text((text_x, current_y), ten.upper(), 
                 fill=primary_color if shape == "highlight-stroke" else text_color, 
                 font=font_ten)
        current_y += ten_height + 10
        
        # Giờ mở cửa
        draw.text((text_x, current_y), f"Giờ mở cửa: {gio}", 
                 fill="#FFD700" if color_theme["text_light"] else "#FF8C00", 
                 font=font_info)
        current_y += info_height + 5
        
        # Địa chỉ với icon pin
        pin_size = int(25 * scale_factor / font_scale)
        draw_location_pin(draw, text_x - 5, current_y - 5, size=pin_size, color_theme=color_theme)
        draw.text((text_x + pin_size + 10, current_y), dc, 
                 fill=secondary_text_color, font=font_info)
        
        # Logo
        if os.path.exists(LOGO_PATH):
            try:
                logo = Image.open(LOGO_PATH).convert("RGBA")
                desired_width = int(110 * target_size[0] / 900.0)
                w_percent = desired_width / float(logo.width)
                h_size = int(float(logo.height) * w_percent)
                logo = logo.resize((desired_width, h_size), Image.Resampling.LANCZOS)
                margin_logo = int(30 * target_size[0] / 900.0)
                img.paste(logo, (width - logo.width - margin_logo, margin_logo), logo)
            except Exception:
                pass
        
        return img.convert("RGB")
        
    except Exception as e:
        img = ImageOps.fit(image_pil.convert("RGB"), target_size, centering=(0.5, 0.5))
        draw = ImageDraw.Draw(img)
        draw.text((50, 50), f"Lỗi: {str(e)[:100]}", fill="red")
        return img

def create_cover_image(background_img, quan_list, descriptions, target_size, color_theme, font_path=None):
    """Tạo ảnh bìa cover với background là ảnh random và overlay text"""
    try:
        # Fit ảnh background
        img = ImageOps.fit(background_img.convert("RGB"), target_size, centering=(0.5, 0.5))
        img = img.convert("RGBA")
        
        # Tạo overlay tối NHẸ HƠN để vẫn thấy background
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 140))
        img = Image.alpha_composite(img, overlay)
        
        # Tạo layer mới để vẽ text và shape
        text_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_layer)
        
        # Font sizes - TĂNG MẠNH CHO COVER
        font_title = load_font(int(target_size[0] * 0.08), font_path)  # Tăng từ 0.08 -> 0.12
        font_subtitle = load_font(int(target_size[0] * 0.05), font_path)  # Tăng từ 0.045 -> 0.06
        font_body = load_font(int(target_size[0] * 0.045), font_path)  # Tăng từ 0.035 -> 0.045
        font_small = load_font(int(target_size[0] * 0.032), font_path)  # Tăng từ 0.025 -> 0.032
        
        # Màu sắc từ theme
        primary_color = color_theme["primary"]
        text_color = "#FFFFFF" if color_theme["text_light"] else "#000000"
        secondary_color = "#FFD700" if color_theme["text_light"] else "#FF8C00"
        
        # Tiêu đề chính
        title_text = "KHÁM PHÁ ĐÀ LẠT"
        subtitle_text = f"Bộ sưu tập {len(quan_list)} địa điểm tuyệt vời"
        
        # Vẽ tiêu đề với background
        title_bbox = draw.textbbox((0, 0), title_text, font=font_title)
        title_width = title_bbox[2] - title_bbox[0]
        title_height = title_bbox[3] - title_bbox[1]
        title_x = (target_size[0] - title_width) // 2
        title_y = target_size[1] // 6  # Đưa lên cao hơn một chút
        
        # Background cho title - to hơn
        padding = 50
        draw.rounded_rectangle(
            [title_x - padding, title_y - padding, 
             title_x + title_width + padding, title_y + title_height + padding],
            radius=30,
            fill=(0, 0, 0, 230)
        )
        
        # Thêm outline cho title
        for offset_x, offset_y in [(-3,-3), (-3,3), (3,-3), (3,3)]:
            draw.text((title_x + offset_x, title_y + offset_y), title_text, 
                     fill=(0, 0, 0), font=font_title)
        draw.text((title_x, title_y), title_text, fill=primary_color, font=font_title)
        
        # Subtitle - TĂNG KHOẢNG CÁCH
        subtitle_bbox = draw.textbbox((0, 0), subtitle_text, font=font_subtitle)
        subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
        subtitle_x = (target_size[0] - subtitle_width) // 2
        subtitle_y = title_y + title_height + 70  # Tăng khoảng cách từ 50 -> 80
        
        draw.text((subtitle_x, subtitle_y), subtitle_text, 
                 fill=text_color, font=font_subtitle)
        
        # Danh sách quán - TĂNG KHOẢNG CÁCH GIỮA CÁC ITEM
        y_start = target_size[1] // 3  # Điều chỉnh vị trí bắt đầu
        max_items = min(5, len(quan_list))
        
        for i in range(max_items):
            y_offset = y_start + i * 150  # Tăng spacing từ 120 -> 150
            
            # Vẽ background cho mỗi item - TO HƠN
            item_width = int(target_size[0] * 0.8)  # Rộng hơn từ 0.75 -> 0.8
            item_height = 80  # Cao hơn từ 100 -> 120
            item_x = int(target_size[0] * 0.1)  # Căn giữa hơn
            item_y = y_offset - 10
            
            draw.rounded_rectangle(
                [item_x, item_y, item_x + item_width, item_y + item_height],
                radius=25,
                fill=(0, 0, 0, 200)
            )
            
            # Số thứ tự với màu primary - TO HƠN
            number_x = int(target_size[0] * 0.14)
            number_y = y_offset + 40
            draw.ellipse([number_x-35, number_y-35, number_x+35, number_y+35], 
                        fill=primary_color)
            draw.text((number_x-15, number_y-22), str(i+1), 
                     fill="#FFFFFF" if color_theme["text_light"] else "#000000", 
                     font=font_subtitle)
            
            # Tên quán - TĂNG KHOẢNG CÁCH VỚI SỐ
            text_x = number_x + 70
            text_y = y_offset + 15
            
            # Tính toán chiều cao text để căn chỉnh
            ten_bbox = draw.textbbox((0, 0), quan_list[i], font=font_body)
            ten_height = ten_bbox[3] - ten_bbox[1]
            
            draw.text((text_x, text_y), quan_list[i], fill=text_color, font=font_body)
            
            # Mô tả - TĂNG KHOẢNG CÁCH VỚI TÊN
            if i < len(descriptions) and descriptions[i]:
                desc_text = descriptions[i][:80] + "..." if len(descriptions[i]) > 80 else descriptions[i]
                desc_y = text_y + ten_height + 15  # Tăng khoảng cách
                draw.text((text_x, desc_y), desc_text, 
                         fill=secondary_color, font=font_small)
        
        # Footer - TĂNG KHOẢNG CÁCH
        footer_text = "Riviu AI • Khám phá Đà Lạt cùng chúng tôi"
        footer_bbox = draw.textbbox((0, 0), footer_text, font=font_body)
        footer_width = footer_bbox[2] - footer_bbox[0]
        footer_x = (target_size[0] - footer_width) // 2
        footer_y = target_size[1] - 180  # Đưa lên cao hơn để không bị che
        
        # Footer background
        draw.rounded_rectangle(
            [footer_x - 30, footer_y - 15, footer_x + footer_width + 30, footer_y + footer_bbox[3] + 15],
            radius=20,
            fill=(0, 0, 0, 220)
        )
        draw.text((footer_x, footer_y), footer_text, fill=primary_color, font=font_body)
        
        # COMPOSITE TEXT LAYER LÊN ẢNH GỐC
        img = Image.alpha_composite(img, text_layer)
        img = img.convert("RGB")
        
        # Logo - kích thước 110px
        if os.path.exists(LOGO_PATH):
            try:
                logo = Image.open(LOGO_PATH).convert("RGBA")
                desired_width = 110
                w_percent = desired_width / float(logo.width)
                h_size = int(float(logo.height) * w_percent)
                logo = logo.resize((desired_width, h_size), Image.Resampling.LANCZOS)
                
                logo_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
                logo_layer.paste(logo, (target_size[0] - logo.width - 40, 40), logo)
                img = img.convert("RGBA")
                img = Image.alpha_composite(img, logo_layer)
                img = img.convert("RGB")
            except:
                pass
        
        return img
        
    except Exception as e:
        print(f"Lỗi tạo cover: {e}")
        img = Image.new('RGB', target_size, color=(20, 20, 30))
        draw = ImageDraw.Draw(img)
        draw.text((target_size[0]//2, target_size[1]//2), f"COVER - {len(quan_list)} quán", 
                 fill="white", font=load_font(50, font_path))
        return img

def add_text_with_layout(image_pil, ten, gio, dc, target_size, layout_config, color_theme, font_path=None, font_scale=1.0):
    """
    Thêm text vào ảnh với layout, hình dạng nền và COLOR THEME được chỉ định
    Text to và rõ hơn, không bị dính
    """
    try:
        img = ImageOps.fit(image_pil.convert("RGB"), target_size, centering=(0.5, 0.5))
        
        # Tạo overlay cho background shape nếu cần
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Convert to RGBA for compositing
        img = img.convert("RGBA")
        draw = ImageDraw.Draw(img)
        
        width, height = img.size
        scale_factor = (target_size[0] / 900.0) * font_scale
        
        # Font sizes - GIỮ KÍCH THƯỚC TO
        font_size_ten = max(45, int(75 * scale_factor))
        font_size_info = max(28, int(36 * scale_factor))
        
        font_ten = load_font(font_size_ten, font_path)
        font_info = load_font(font_size_info, font_path)
        
        position = layout_config.get("position", "bottom-left")
        shape = layout_config.get("shape", "rounded-rectangle")
        
        # Tính toán vị trí text
        margin = int(50 * scale_factor / font_scale)
        
        # Đo kích thước text
        ten_bbox = draw.textbbox((0, 0), ten.upper(), font=font_ten)
        info_bbox = draw.textbbox((0, 0), f"Giờ mở cửa: {gio}", font=font_info)
        dc_bbox = draw.textbbox((0, 0), dc, font=font_info)
        
        ten_width = ten_bbox[2] - ten_bbox[0]
        ten_height = ten_bbox[3] - ten_bbox[1]
        info_height = info_bbox[3] - info_bbox[1]
        dc_height = dc_bbox[3] - dc_bbox[1]
        
        # TĂNG KHOẢNG CÁCH GIỮA CÁC DÒNG
        line_spacing = 25  # Khoảng cách cố định giữa các dòng
        total_height = ten_height + info_height + dc_height + line_spacing * 3
        
        max_width = max(ten_width, info_bbox[2] - info_bbox[0] + 120, 
                       dc_bbox[2] - dc_bbox[0] + 120)
        
        # Xác định vị trí theo layout
        if position == "bottom-left":
            x = margin
            y = height - total_height - margin * 2
        elif position == "bottom-right":
            x = width - max_width - margin
            y = height - total_height - margin * 2
        elif position == "top-center":
            x = (width - max_width) // 2
            y = margin * 2
        elif position == "center":
            x = (width - max_width) // 2
            y = (height - total_height) // 2
        elif position == "top-left":
            x = margin
            y = margin * 2
        elif position == "bottom-center":
            x = (width - max_width) // 2
            y = height - total_height - margin * 2
        else:
            x = margin
            y = height - total_height - margin * 2
        
        # Vẽ background shape trên overlay
        text_bbox = [x, y, x + max_width, y + total_height]
        draw_background_shape(overlay_draw, text_bbox, shape, color_theme)
        
        # Composite overlay lên ảnh
        img = Image.alpha_composite(img, overlay)
        draw = ImageDraw.Draw(img)
        
        # Xác định màu text dựa trên theme
        text_color = "#FFFFFF" if color_theme["text_light"] else "#000000"
        primary_color = color_theme["primary"]
        secondary_text_color = "#E0E0E0" if color_theme["text_light"] else "#333333"
        
        # Vẽ text với khoảng cách rõ ràng
        current_y = y + line_spacing
        
        # Tên quán
        if position in ["top-center", "center", "bottom-center"]:
            text_x = x + (max_width - ten_width) // 2
        else:
            text_x = x + 20
        
        # Vẽ text với hiệu ứng đậm hơn
        if shape == "highlight-stroke":
            draw.text((text_x, current_y), ten.upper(), fill=primary_color, font=font_ten)
        else:
            # Thêm outline nhẹ cho text
            outline_color = (0, 0, 0) if color_theme["text_light"] else (255, 255, 255)
            for offset_x, offset_y in [(-2,-2), (-2,2), (2,-2), (2,2)]:
                draw.text((text_x + offset_x, current_y + offset_y), ten.upper(), 
                         fill=outline_color, font=font_ten)
            draw.text((text_x, current_y), ten.upper(), fill=text_color, font=font_ten)
        
        # Tăng current_y với khoảng cách lớn
        current_y += ten_height + line_spacing
        
        # Giờ mở cửa
        hour_color = "#FFD700" if color_theme["text_light"] else "#FF8C00"
        draw.text((text_x, current_y), f"Giờ mở cửa: {gio}", fill=hour_color, font=font_info)
        current_y += info_height + line_spacing
        
        # Địa chỉ với icon pin
        pin_size = int(30 * scale_factor / font_scale)
        draw_location_pin(draw, text_x - 5, current_y - 5, size=pin_size, color_theme=None)
        draw.text((text_x + pin_size + 15, current_y), dc, fill=secondary_text_color, font=font_info)
        
        # Logo - kích thước cố định 110px
        if os.path.exists(LOGO_PATH):
            try:
                logo = Image.open(LOGO_PATH).convert("RGBA")
                desired_width = 110
                w_percent = desired_width / float(logo.width)
                h_size = int(float(logo.height) * w_percent)
                logo = logo.resize((desired_width, h_size), Image.Resampling.LANCZOS)
                margin_logo = int(30 * target_size[0] / 900.0)
                
                logo_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
                logo_layer.paste(logo, (width - logo.width - margin_logo, margin_logo), logo)
                img = Image.alpha_composite(img, logo_layer)
            except Exception:
                pass
        
        return img.convert("RGB")
        
    except Exception as e:
        img = ImageOps.fit(image_pil.convert("RGB"), target_size, centering=(0.5, 0.5))
        draw = ImageDraw.Draw(img)
        draw.text((50, 50), f"Lỗi: {str(e)[:100]}", fill="red")
        return img

# --- GOOGLE DRIVE (giữ nguyên) ---
def extract_folder_id(url: str) -> Optional[str]:
    patterns = [r'/folders/([a-zA-Z0-9_-]+)', r'id=([a-zA-Z0-9_-]+)']
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None

def list_files_in_drive_folder(folder_id: str, api_key: str) -> List[Dict]:
    url = "https://www.googleapis.com/drive/v3/files"
    params = {
        "q": f"'{folder_id}' in parents and trashed = false",
        "key": api_key,
        "fields": "files(id, name, mimeType)",
        "pageSize": 1000
    }
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json().get('files', [])
    except Exception as e:
        st.error(f"Lỗi Google Drive API: {e}")
        return []

def download_drive_file(file_id: str, save_path: str) -> bool:
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    try:
        r = requests.get(url, stream=True, timeout=30)
        if r.status_code == 200:
            with open(save_path, 'wb') as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            return True
    except:
        pass
    return False

# --- EXCEL (giữ nguyên) ---
def read_excel_with_sheets(uploaded_file) -> Dict[str, pd.DataFrame]:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
        return {'Sheet1': df}
    else:
        xl = pd.ExcelFile(uploaded_file)
        return {sheet: pd.read_excel(xl, sheet_name=sheet) for sheet in xl.sheet_names}

def find_required_columns(df: pd.DataFrame) -> Tuple[str, str, str, str, str, str]:
    cols = {normalize_text(c): c for c in df.columns}
    ten = cols.get('ten_quan', cols.get('ten quan', None))
    dia = cols.get('dia_chi', cols.get('dia chi', None))
    gio = cols.get('gio_mo_cua', cols.get('thoi gian mo cua', None))
    doi = cols.get('doi_tac', cols.get('doi tac', None))
    mon = cols.get('mon_an_noi_bat', cols.get('mon an noi bat', cols.get('dac_san', cols.get('dac san', None))))
    style = cols.get('phong_cach', cols.get('phong cach', cols.get('style', None)))
    return ten, dia, gio, doi, mon, style

# --- ẢNH TỪ ZIP (KHÔNG GIẢI NÉN RA Ổ ĐĨA) ---
def extract_images_from_zip(zip_bytes: bytes) -> Dict[str, List[Tuple[str, bytes]]]:
    """
    Trả về dict: key = tên thư mục (chuẩn hóa), value = danh sách các tuple (filename, data_bytes)
    """
    image_dict = {}
    all_images = []  # Lưu tất cả ảnh để chọn random cho cover
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            parts = info.filename.split('/')
            if len(parts) < 2:
                continue
            folder_name = normalize_text(parts[0])
            if not folder_name:
                continue
            ext = os.path.splitext(info.filename)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png']:
                continue
            with zf.open(info) as f:
                img_bytes = f.read()
            if folder_name not in image_dict:
                image_dict[folder_name] = []
            image_dict[folder_name].append((info.filename, img_bytes))
            all_images.append(img_bytes)  # Thêm vào danh sách tổng
    return image_dict, all_images

def process_drive_folder(folder_url: str, drive_api_key: str) -> Tuple[Dict[str, List[str]], List[str]]:
    folder_id = extract_folder_id(folder_url)
    if not folder_id:
        st.error("Không trích xuất được ID folder.")
        return {}, []
    files = list_files_in_drive_folder(folder_id, drive_api_key)
    image_dict = {}
    all_images = []
    prog = st.progress(0, "Đang tải ảnh từ Drive...")
    total = len(files)
    for i, f in enumerate(files):
        if f['mimeType'].startswith('image/'):
            base = os.path.splitext(f['name'])[0]
            name_parts = re.split(r'[\d_\-\s]+', base)
            quán_name = normalize_text(name_parts[0]) if name_parts else "unknown"
            tmp_path = os.path.join(TEMP_DIR, f"{quán_name}_{i}.jpg")
            if download_drive_file(f['id'], tmp_path):
                image_dict.setdefault(quán_name, []).append(tmp_path)
                all_images.append(tmp_path)
        prog.progress((i+1)/total)
    prog.empty()
    return image_dict, all_images

# --- THUẬT TOÁN ƯU TIÊN ĐỐI TÁC ---
def priority_shuffle(quan_list: List[str], partner_dict: Dict[str, bool], num_slots: int, allow_repeat: bool = False) -> List[str]:
    partners = [q for q in quan_list if partner_dict.get(normalize_text(q), False)]
    normals = [q for q in quan_list if not partner_dict.get(normalize_text(q), False)]
    random.shuffle(partners)
    random.shuffle(normals)
    selected = partners + normals
    if allow_repeat and len(selected) < num_slots:
        while len(selected) < num_slots:
            selected += selected[:num_slots - len(selected)]
    return selected[:num_slots]

# --- AI CAPTION & DESCRIPTION ---
def generate_short_description(ten_quan: str, mon_an: str, phong_cach: str, api_key: str, provider: str = 'gemini') -> str:
    """Sinh mô tả ngắn 6-8 từ cho quán"""
    if not api_key:
        return f"{ten_quan} - Điểm đến tuyệt vời tại Đà Lạt"
    
    prompt = f"""
    Viết một câu mô tả NGẮN GỌN (tối đa 8 từ) về quán "{ten_quan}" tại Đà Lạt.
    Món nổi bật: {mon_an if mon_an and pd.notna(mon_an) else 'cafe, đồ uống'}
    Phong cách: {phong_cach if phong_cach and pd.notna(phong_cach) else 'đẹp, sang trọng'}
    
    Yêu cầu:
    - Chỉ trả về 1 câu duy nhất, không quá 8 từ
    - Có thể kèm emoji
    - Không xuống dòng
    - Ví dụ: "Cafe view đồi thông lãng mạn ☕️🌲"
    """
    
    if provider == 'gemini':
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            text = response.text.strip()
            # Giới hạn độ dài
            words = text.split()
            if len(words) > 8:
                text = ' '.join(words[:8])
            return text
        except:
            return f"{ten_quan} - Không gian tuyệt vời tại Đà Lạt ✨"
    else:
        try:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.9,
                "max_tokens": 30
            }
            resp = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                text = resp.json()['choices'][0]['message']['content'].strip()
                words = text.split()
                if len(words) > 8:
                    text = ' '.join(words[:8])
                return text
        except:
            pass
        return f"{ten_quan} - Không gian tuyệt vời tại Đà Lạt ✨"

def generate_tiktok_caption(names: List[str], descriptions: List[str], api_key: str, provider: str = 'gemini') -> str:
    names_str = ", ".join(names)
    desc_str = " ".join(descriptions[:3]) if descriptions else ""
    hashtags = f"{HARD_HASHTAGS} #cafedalat #checkindalat"
    
    prompt = f"""
    Viết caption TikTok cho bài đăng về các quán: {names_str}.
    Đặc điểm nổi bật: {desc_str}
    
    YÊU CẦU:
    - TIÊU ĐỀ VIẾT HOA, không quá 90 ký tự, có từ "Đà Lạt".
    - Nội dung tối đa 300 ký tự, nhồi từ khóa: Đà Lạt, cafe Đà Lạt, review Đà Lạt, quán cafe đẹp Đà Lạt.
    - Kết thúc bằng hashtag {hashtags}.
    Trả về đúng 3 phần: tiêu đề, nội dung, hashtag.
    """
    
    if provider == 'gemini':
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            text = response.text.strip()
            if HARD_HASHTAGS not in text:
                text += "\n" + hashtags
            return text
        except:
            return f"TOP QUÁN CAFE ĐÀ LẠT ĐẸP QUÊN LỐI VỀ\nKhám phá ngay những quán cafe Đà Lạt siêu xinh. Review chi tiết từ A-Z.\n{hashtags}"
    else:
        try:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.9
            }
            resp = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                text = resp.json()['choices'][0]['message']['content'].strip()
                if HARD_HASHTAGS not in text:
                    text += "\n" + hashtags
                return text
        except:
            pass
        return f"TOP QUÁN CAFE ĐÀ LẠT ĐẸP QUÊN LỐI VỀ\nKhám phá ngay những quán cafe Đà Lạt siêu xinh.\n{hashtags}"

def generate_facebook_caption(names: List[str], descriptions: List[str], api_key: str, provider: str = 'gemini') -> str:
    names_str = ", ".join(names)
    desc_str = " ".join(descriptions) if descriptions else ""
    
    prompt = f"""
    Viết caption Facebook dài, có cảm xúc cho bài review các quán: {names_str}.
    Đặc điểm: {desc_str}
    Mô tả không gian, đồ uống, kể chuyện lôi cuốn. Kết thúc bằng lời mời gọi tương tác.
    """
    
    if provider == 'gemini':
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            return response.text.strip()
        except:
            return f"Đà Lạt luôn biết cách vỗ về tâm hồn. Ghé {names_str} để cảm nhận không khí se lạnh và ly cafe thơm nồng. Bạn đã đến những quán này chưa? Để lại bình luận nhé! ☕️🍃"
    else:
        try:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.9
            }
            resp = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                return resp.json()['choices'][0]['message']['content'].strip()
        except:
            pass
        return f"Đà Lạt luôn biết cách vỗ về tâm hồn. Ghé {names_str} để cảm nhận không khí se lạnh và ly cafe thơm nồng. Bạn đã đến những quán này chưa? Để lại bình luận nhé! ☕️🍃"

# ============================================================
# GIAO DIỆN CHÍNH
# ============================================================
st.title("🎬 Riviu AI Content Generator Pro")
st.caption("Tạo ảnh banner & caption tự động – Layout đa dạng, màu sắc đồng bộ")

with st.sidebar:
    st.header("🔑 Cấu hình API")
    gemini_key = st.text_input("Gemini API Key", type="password", help="Dùng để sinh caption AI và mô tả ảnh")
    deepseek_key = st.text_input("DeepSeek API Key (dự phòng)", type="password")
    drive_api_key = st.text_input("Google Drive API Key", type="password", help="Cần nếu dùng link Drive Folder")
    ai_enabled = bool(gemini_key or deepseek_key)
    if not ai_enabled:
        st.warning("⚠️ Chưa có API key AI, sẽ không tạo caption và mô tả.")
    
    st.markdown("---")
    st.markdown("### 🎨 Cấu hình Layout & Màu sắc")
    layout_mode = st.selectbox(
        "Chế độ layout",
        ["Random mỗi bộ (đồng bộ màu)", "Random mỗi ảnh (màu khác nhau)", "Cố định cho tất cả"]
    )
    
    if layout_mode == "Cố định cho tất cả":
        fixed_position = st.selectbox("Vị trí text", TEXT_POSITIONS)
        fixed_shape = st.selectbox("Hình dạng nền", BACKGROUND_SHAPES)
        fixed_theme = st.selectbox("Theme màu", [t["name"] for t in COLOR_THEMES])
    
    st.markdown("---")
    st.markdown("### ℹ️ Hướng dẫn")
    st.markdown("""
    1. **Upload Excel** có sheet chứa cột: `Ten_quan`, `Dia_chi`, `Gio_mo_cua`, `Doi_tac`, `Mon_an_noi_bat`, `Phong_cach`
    2. **Chọn sheet**.
    3. **Nguồn ảnh**: Upload ZIP hoặc Drive link
    4. **Cấu hình số bộ** → Xuất nội dung.
    5. **Layout**: 
       - Random mỗi bộ: Cùng 1 layout & màu cho cả bộ
       - Random mỗi ảnh: Mỗi ảnh layout & màu khác nhau
    """)

# --- BLOCK 1: DỮ LIỆU EXCEL ---
st.markdown("### 📊 1. Dữ liệu Excel")
excel_file = st.file_uploader("Upload file Excel/CSV", type=['xlsx', 'csv'], key="excel")
selected_sheet = None
df = None
ten_col = dia_col = gio_col = doi_col = mon_col = style_col = None

if excel_file:
    sheets = read_excel_with_sheets(excel_file)
    sheet_names = list(sheets.keys())
    default_idx = sheet_names.index('Quan_an') if 'Quan_an' in sheet_names else 0
    selected_sheet = st.selectbox("Chọn sheet chứa dữ liệu quán:", sheet_names, index=default_idx)
    df = sheets[selected_sheet].copy()
    st.success(f"✅ Đã đọc sheet `{selected_sheet}` ({len(df)} dòng)")

    ten_col, dia_col, gio_col, doi_col, mon_col, style_col = find_required_columns(df)
    if not all([ten_col, dia_col, gio_col]):
        st.error("❌ Thiếu cột bắt buộc (Ten_quan, Dia_chi, Gio_mo_cua).")
        st.stop()
    
    # Hiển thị preview
    preview_cols = [ten_col, dia_col, gio_col]
    if doi_col:
        preview_cols.append(doi_col)
    if mon_col:
        preview_cols.append(mon_col)
    if style_col:
        preview_cols.append(style_col)
    
    st.dataframe(df[preview_cols].head())
    
    if not mon_col:
        st.info("💡 Tip: Thêm cột 'Mon_an_noi_bat' và 'Phong_cach' để AI tạo mô tả hay hơn!")

# --- BLOCK 2: NGUỒN ẢNH ---
st.markdown("### 🖼️ 2. Nguồn ảnh (ZIP hoặc Drive Folder)")
src_option = st.radio("Chọn cách cung cấp ảnh:", ["Upload file ZIP", "Link Google Drive Folder"], horizontal=True)
image_dict = {}
all_images_list = []
if src_option == "Upload file ZIP":
    zip_file = st.file_uploader("Upload file ZIP chứa ảnh theo thư mục", type=['zip'])
    if zip_file:
        with st.spinner("Đang đọc chỉ mục ảnh từ ZIP..."):
            image_dict, all_images_list = extract_images_from_zip(zip_file.read())
        st.success(f"✅ Đã tìm thấy ảnh cho {len(image_dict)} thư mục, tổng {len(all_images_list)} ảnh")
else:
    drive_link = st.text_input("Link Google Drive Folder (public)", placeholder="https://drive.google.com/drive/folders/...")
    if drive_link and st.button("📥 Tải ảnh từ Drive"):
        if not drive_api_key:
            st.error("❌ Cần nhập Google Drive API Key ở sidebar.")
        else:
            with st.spinner("Đang tải danh sách ảnh từ Drive..."):
                image_dict, all_images_list = process_drive_folder(drive_link, drive_api_key)
            st.success(f"✅ Đã tải ảnh cho {len(image_dict)} quán, tổng {len(all_images_list)} ảnh")

# --- BLOCK 3: CẤU HÌNH & RENDER ---
st.markdown("### ⚙️ 3. Cấu hình & Render")
col1, col2, col3, col4 = st.columns([1,1,1,1])
num_sets = col1.number_input("Số bộ ảnh", min_value=1, value=1)
imgs_per_set = col2.number_input("Số ảnh mỗi bộ", min_value=1, value=20)
quality = col3.selectbox("Chất lượng", ["Cao (2700x3540)", "Siêu cao (3600x4720)"])
font_scale = col4.slider("🔤 Tỉ lệ cỡ chữ", min_value=0.2, max_value=2.0, value=1.0, step=0.1,
                         help="Mặc định 1.0 là kích thước vừa phải. Kéo lên để chữ to hơn.")
allow_repeat = st.checkbox("🔄 Cho phép lặp quán nếu không đủ ảnh", value=False,
                           help="Nếu số quán có ảnh ít hơn số ảnh yêu cầu, sẽ chọn lặp lại.")

if st.button("🚀 XUẤT NỘI DUNG HÀNG LOẠT", type="primary", use_container_width=True):
    if df is None:
        st.error("Vui lòng upload file Excel.")
        st.stop()
    if not image_dict or not all_images_list:
        st.error("Chưa có ảnh. Vui lòng cung cấp ZIP hoặc Drive link.")
        st.stop()

    # Chuẩn bị dữ liệu
    ten_list = df[ten_col].astype(str).tolist()
    dia_map = dict(zip(df[ten_col].astype(str), df[dia_col].astype(str)))
    gio_map = dict(zip(df[ten_col].astype(str), df[gio_col].astype(str)))
    
    # Map cho món ăn và phong cách
    mon_map = {}
    style_map = {}
    if mon_col:
        mon_map = dict(zip(df[ten_col].astype(str), df[mon_col].astype(str)))
    if style_col:
        style_map = dict(zip(df[ten_col].astype(str), df[style_col].astype(str)))
    
    partner_dict = {}
    if doi_col:
        for _, row in df.iterrows():
            name = str(row[ten_col])
            partner_dict[normalize_text(name)] = str(row[doi_col]).strip().lower() == 'x'

    available_quans = [q for q in ten_list if normalize_text(q) in image_dict]
    if not available_quans:
        st.error("❌ Không có quán nào có ảnh tương ứng. Kiểm tra tên thư mục/tên file.")
        st.stop()

    st.info(f"📸 Có {len(available_quans)} quán có ảnh trong tổng số {len(ten_list)} quán trong Excel.")

    if len(available_quans) < imgs_per_set and not allow_repeat:
        st.warning(f"⚠️ Chỉ có {len(available_quans)} quán có ảnh, nhưng bạn yêu cầu {imgs_per_set} ảnh/bộ. "
                   f"Hãy tích chọn 'Cho phép lặp quán' hoặc bổ sung thêm ảnh.")

    target_size = (2700, 3540) if "Cao" in quality else (3600, 4720)
    jpeg_quality = 95 if "Cao" in quality else 90

    # Xác định provider cho AI
    ai_provider = 'gemini' if gemini_key else 'deepseek'
    ai_key = gemini_key or deepseek_key

    # Tạo ZIP
    zip_buffer = io.BytesIO()
    all_captions = []
    partner_logs = {}

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        prog = st.progress(0, "Đang tạo ảnh...")
        
        for set_idx in range(int(num_sets)):
            # Chọn layout và màu sắc cho bộ này
            if layout_mode == "Cố định cho tất cả":
                theme_idx = [i for i, t in enumerate(COLOR_THEMES) if t["name"] == fixed_theme][0]
                set_color_theme = COLOR_THEMES[theme_idx]
                set_layout = {
                    "position": fixed_position,
                    "shape": fixed_shape
                }
                use_consistent_color = True
            elif layout_mode == "Random mỗi bộ (đồng bộ màu)":
                set_color_theme = random.choice(COLOR_THEMES)
                set_layout = {
                    "position": random.choice(TEXT_POSITIONS),
                    "shape": random.choice(BACKGROUND_SHAPES)
                }
                use_consistent_color = True
            else:  # Random mỗi ảnh
                set_layout = None
                set_color_theme = None
                use_consistent_color = False
            
            selected = priority_shuffle(available_quans, partner_dict, int(imgs_per_set), allow_repeat)
            set_partners = [q for q in selected if partner_dict.get(normalize_text(q), False)]
            partner_logs[f"Bộ {set_idx+1}"] = set_partners

            font_path = get_random_font_path(seed=set_idx)
            set_quans = []
            set_descriptions = []

            # Tạo mô tả ngắn cho từng quán bằng AI
            for ten in selected:
                if ai_enabled:
                    mon = mon_map.get(ten, "") if mon_map else ""
                    style = style_map.get(ten, "") if style_map else ""
                    desc = generate_short_description(ten, mon, style, ai_key, ai_provider)
                else:
                    desc = f"{ten} - Điểm đến tuyệt vời tại Đà Lạt ✨"
                set_descriptions.append(desc)

            # === TẠO ẢNH BÌA COVER ===
            # Random chọn 1 ảnh từ tất cả các ảnh làm background
            if all_images_list:
                if src_option == "Upload file ZIP":
                    # Chọn random ảnh bytes
                    random_img_bytes = random.choice(all_images_list)
                    cover_bg = Image.open(io.BytesIO(random_img_bytes))
                else:
                    # Chọn random file path
                    random_img_path = random.choice(all_images_list)
                    cover_bg = Image.open(random_img_path)
                
                # Sử dụng màu theme của bộ (nếu có) hoặc random
                cover_color_theme = set_color_theme if use_consistent_color else random.choice(COLOR_THEMES)
                
                cover_img = create_cover_image(cover_bg, selected, set_descriptions, target_size, 
                                              cover_color_theme, font_path)
                cover_buf = io.BytesIO()
                cover_img.save(cover_buf, format='JPEG', quality=jpeg_quality)
                zf.writestr(f"Bo_{set_idx+1}/00_COVER.jpg", cover_buf.getvalue())

            # Tạo ảnh cho từng quán
            layout_info_list = []
            for idx, ten in enumerate(selected):
                key = normalize_text(ten)
                if key not in image_dict or not image_dict[key]:
                    continue

                # Lấy ảnh ngẫu nhiên từ thư mục
                img_item = random.choice(image_dict[key])
                gio = gio_map.get(ten, "7:00 - 22:00")
                dc = dia_map.get(ten, "Đà Lạt")

                # Chọn layout và màu cho ảnh này
                if layout_mode == "Random mỗi ảnh (màu khác nhau)":
                    img_layout = {
                        "position": random.choice(TEXT_POSITIONS),
                        "shape": random.choice(BACKGROUND_SHAPES)
                    }
                    img_color_theme = random.choice(COLOR_THEMES)
                else:
                    img_layout = set_layout
                    img_color_theme = set_color_theme
                
                if idx == 0:  # Lưu layout của ảnh đầu tiên để hiển thị
                    layout_info_list.append(f"{img_layout['position']} - {img_layout['shape']} - {img_color_theme['name']}")

                try:
                    if src_option == "Upload file ZIP":
                        img_bytes = img_item[1]
                        img = Image.open(io.BytesIO(img_bytes))
                    else:
                        img = Image.open(img_item)

                    banner = add_text_with_layout(img, ten, gio, dc, target_size,
                                                 img_layout, img_color_theme,
                                                 font_path=font_path, 
                                                 font_scale=font_scale)
                except Exception as e:
                    st.warning(f"⚠️ Lỗi ảnh {ten}: {e}")
                    continue

                buf = io.BytesIO()
                banner.save(buf, format='JPEG', quality=jpeg_quality)
                safe_name = re.sub(r'[<>:"/\\|?*]', '_', ten)
                zf.writestr(f"Bo_{set_idx+1}/{idx+1:02d}_{safe_name}.jpg", buf.getvalue())
                set_quans.append(ten)

            # Sinh caption nếu có API key
            if ai_enabled and set_quans:
                tt_cap = generate_tiktok_caption(set_quans, set_descriptions, ai_key, ai_provider)
                fb_cap = generate_facebook_caption(set_quans, set_descriptions, ai_key, ai_provider)
                all_captions.append({
                    "Bộ": f"Bộ {set_idx+1}",
                    "Quán": ", ".join(set_quans),
                    "Đối tác": ", ".join(set_partners) if set_partners else "Không",
                    "Layout & Màu": layout_info_list[0] if layout_info_list else "N/A",
                    "TikTok": tt_cap,
                    "Facebook": fb_cap
                })
            else:
                all_captions.append({
                    "Bộ": f"Bộ {set_idx+1}",
                    "Quán": ", ".join(set_quans),
                    "Đối tác": ", ".join(set_partners) if set_partners else "Không",
                    "Layout & Màu": layout_info_list[0] if layout_info_list else "N/A",
                    "TikTok": "(Chưa có API key)",
                    "Facebook": "(Chưa có API key)"
                })

            prog.progress((set_idx+1)/num_sets)
        prog.empty()

    st.session_state.zip_data = zip_buffer.getvalue()
    st.session_state.caption_df = pd.DataFrame(all_captions)
    st.session_state.partner_logs = partner_logs

    excel_buf = io.BytesIO()
    st.session_state.caption_df.to_excel(excel_buf, index=False)
    st.session_state.excel_data = excel_buf.getvalue()

    st.success(f"🎉 Hoàn tất {num_sets} bộ, mỗi bộ {imgs_per_set} ảnh + 1 ảnh bìa!")
    st.balloons()
    st.rerun()

# --- HIỂN THỊ KẾT QUẢ ---
if st.session_state.caption_df is not None and not st.session_state.caption_df.empty:
    st.markdown("---")
    st.markdown("### 📋 Kết quả đã tạo")
    tab1, tab2, tab3 = st.tabs(["📝 Captions", "🤝 Danh sách đối tác", "🎨 Layouts & Màu sắc"])

    with tab1:
        for _, row in st.session_state.caption_df.iterrows():
            with st.expander(f"🔥 {row['Bộ']} - {len(row['Quán'].split(','))} quán"):
                st.markdown(f"**📍 Quán:** {row['Quán']}")
                if row['Đối tác'] != "Không":
                    st.markdown(f"**🤝 Đối tác:** {row['Đối tác']}")
                st.markdown(f"**🎨 {row.get('Layout & Màu', 'N/A')}**")
                col_tt, col_fb = st.columns(2)
                with col_tt:
                    st.markdown("**🎵 TikTok Caption:**")
                    st.code(row['TikTok'], language="text")
                with col_fb:
                    st.markdown("**📘 Facebook Caption:**")
                    st.write(row['Facebook'])

    with tab2:
        if st.session_state.partner_logs:
            all_partners = set()
            for set_name, partners in st.session_state.partner_logs.items():
                if partners:
                    st.markdown(f"**{set_name}:** {', '.join(partners)}")
                    all_partners.update(partners)
                else:
                    st.markdown(f"**{set_name}:** *(Không có đối tác)*")
            st.markdown("---")
            st.markdown(f"### 🏆 Tổng đối tác xuất hiện: {len(all_partners)}")
            for p in sorted(all_partners):
                st.markdown(f"- {p}")
    
    with tab3:
        st.markdown("### 🎨 Thống kê Layout & Màu sắc đã sử dụng")
        if 'Layout & Màu' in st.session_state.caption_df.columns:
            layout_counts = st.session_state.caption_df['Layout & Màu'].value_counts()
            for layout, count in layout_counts.items():
                st.markdown(f"- **{layout}**: {count} bộ")

    st.markdown("### 📦 Tải xuống")
    col_dl1, col_dl2, col_dl3 = st.columns(3)
    with col_dl1:
        st.download_button(
            label="📥 Tải Ảnh Banners (Zip)",
            data=st.session_state.zip_data,
            file_name=f"riviu_banners_{datetime.now().strftime('%Y%m%d_%H%M')}.zip",
            mime="application/zip",
            use_container_width=True
        )
    with col_dl2:
        st.download_button(
            label="📊 Tải Caption (Excel)",
            data=st.session_state.excel_data,
            file_name=f"riviu_captions_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    with col_dl3:
        if st.session_state.partner_logs:
            log_content = f"DANH SÁCH ĐỐI TÁC XUẤT HIỆN\nNgày xuất: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
            log_content += "="*50 + "\n\n"
            all_set = set()
            for set_name, partners in st.session_state.partner_logs.items():
                log_content += f"{set_name}:\n"
                if partners:
                    for p in partners:
                        log_content += f"  - {p}\n"
                        all_set.add(p)
                else:
                    log_content += "  (Không có đối tác)\n"
                log_content += "\n"
            log_content += "="*50 + f"\nTỔNG: {len(all_set)} đối tác\n"
            st.download_button(
                label="📄 Tải Danh sách Đối tác (TXT)",
                data=log_content.encode('utf-8'),
                file_name=f"doi_tac_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain",
                use_container_width=True
            )

st.markdown("---")
st.caption("Made with ❤️ | Ảnh xuất ra chất lượng cao - Layout đa dạng - Màu sắc đồng bộ")