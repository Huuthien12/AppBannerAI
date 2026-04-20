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
if 'suggested_font' not in st.session_state:
    st.session_state.suggested_font = None
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
    "top-left",         # Góc trên trái
    "top-right",        # Góc trên phải (thêm mới)
    "bottom-center",    # Dưới cùng giữa
    "top-center-edge",  # Trên cùng sát mép (thay thế top-center)
    "left-center",      # Giữa bên trái
    "right-center"      # Giữa bên phải    # Dưới cùng giữa
]

BACKGROUND_SHAPES = [
    # Hình chữ nhật bo góc - an toàn nhất, text luôn vừa
    "rounded-rectangle",
    
    # Hình chữ nhật đơn giản
    "rectangle",
    
    # Hình viên thuốc - phù hợp với text ngắn
    "pill-shape",
    
    # Hình elip - phù hợp với text vừa phải
    "ellipse",
    
    # Hình thoi - text cần căn giữa
    "diamond",
    
    # Hình lục giác - text ngắn
    "hexagon",
    
    # Banner ruy băng - đẹp cho text dài
    "banner-ribbon",
    
    # Nhãn dán - text ngắn
    "tag-label",
    
    # Khung viền đôi - text dài cũng đẹp
    "double-border",
    
    # Hiệu ứng kính mờ - text dài vẫn đẹp
    "glass-morphism",
    
    # Bookmark - text ngắn
    "bookmark",
    
    # Hộp gradient - text dài
    "gradient-box",
    
    # Khung ngoặc - text dài
    "frame-bracket"
]
# Danh sách font nghệ thuật (cần tải từ Google Fonts)
FONT_ARTISTIC = {
    # Serif - Sang trọng
    "Playfair Display": "https://github.com/google/fonts/raw/main/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf",
    "Cormorant Garamond": "https://github.com/google/fonts/raw/main/ofl/cormorantgaramond/CormorantGaramond%5Bwght%5D.ttf",
    "Libre Baskerville": "https://github.com/google/fonts/raw/main/ofl/librebaskerville/LibreBaskerville-Regular.ttf",
    "DM Serif Display": "https://github.com/google/fonts/raw/main/ofl/dmserifdisplay/DMSerifDisplay-Regular.ttf",
    "Prata": "https://github.com/google/fonts/raw/main/ofl/prata/Prata-Regular.ttf",
    "Lora": "https://github.com/google/fonts/raw/main/ofl/lora/Lora%5Bwght%5D.ttf",
    
    # Sans-serif - Hiện đại
    "Be Vietnam Pro": "https://github.com/google/fonts/raw/main/ofl/bevietnampro/BeVietnamPro%5Bwght%5D.ttf",
    "Montserrat": "https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat%5Bwght%5D.ttf",
    "Poppins": "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins%5Bwght%5D.ttf",
    "Raleway": "https://github.com/google/fonts/raw/main/ofl/raleway/Raleway%5Bwght%5D.ttf",
    "Rubik": "https://github.com/google/fonts/raw/main/ofl/rubik/Rubik%5Bwght%5D.ttf",
    "Lexend": "https://github.com/google/fonts/raw/main/ofl/lexend/Lexend%5Bwght%5D.ttf",
    "Barlow Condensed": "https://github.com/google/fonts/raw/main/ofl/barlowcondensed/BarlowCondensed%5Bwght%5D.ttf",
    "Oswald": "https://github.com/google/fonts/raw/main/ofl/oswald/Oswald%5Bwght%5D.ttf",
    
    # Script - Viết tay
    "Great Vibes": "https://github.com/google/fonts/raw/main/ofl/greatvibes/GreatVibes-Regular.ttf",
    "Allura": "https://github.com/google/fonts/raw/main/ofl/allura/Allura-Regular.ttf",
    "Satisfy": "https://github.com/google/fonts/raw/main/ofl/satisfy/Satisfy-Regular.ttf",
    "Parisienne": "https://github.com/google/fonts/raw/main/ofl/parisienne/Parisienne-Regular.ttf",
    "Sacramento": "https://github.com/google/fonts/raw/main/ofl/sacramento/Sacramento-Regular.ttf",
    
    # Stylized - Độc lạ
    "Bungee": "https://github.com/google/fonts/raw/main/ofl/bungee/Bungee-Regular.ttf",
    "Fredoka": "https://github.com/google/fonts/raw/main/ofl/fredoka/Fredoka%5Bwght%5D.ttf",
    "Baloo 2": "https://github.com/google/fonts/raw/main/ofl/baloo2/Baloo2%5Bwght%5D.ttf",
    "Comfortaa": "https://github.com/google/fonts/raw/main/ofl/comfortaa/Comfortaa%5Bwght%5D.ttf",
    "Chakra Petch": "https://github.com/google/fonts/raw/main/ofl/chakrapetch/ChakraPetch%5Bwght%5D.ttf",
}

# Đường dẫn lưu font đã tải
FONT_CACHE_DIR = os.path.join(TEMP_DIR, "fonts")
os.makedirs(FONT_CACHE_DIR, exist_ok=True)
def download_google_font(font_name: str) -> Optional[str]:
    """Tải font từ Google Fonts về máy"""
    if font_name not in FONT_ARTISTIC:
        return None
    
    font_url = FONT_ARTISTIC[font_name]
    # Tạo tên file an toàn
    safe_name = re.sub(r'[^\w\-_]', '_', font_name)
    font_path = os.path.join(FONT_CACHE_DIR, f"{safe_name}.ttf")
    
    # Nếu font đã có trong cache thì dùng
    if os.path.exists(font_path):
        return font_path
    
    # Tải font về
    try:
        response = requests.get(font_url, timeout=30)
        if response.status_code == 200:
            with open(font_path, 'wb') as f:
                f.write(response.content)
            return font_path
    except Exception as e:
        print(f"Lỗi tải font {font_name}: {e}")
    
    return None

def get_artistic_font(font_name: str, size: int) -> ImageFont.FreeTypeFont:
    """Lấy font nghệ thuật, nếu không có thì dùng fallback"""
    font_path = download_google_font(font_name)
    if font_path:
        try:
            return ImageFont.truetype(font_path, size)
        except:
            pass
    # Fallback về font mặc định
    return load_font(size)
# Màu sắc cho các theme
COLOR_THEMES = [
    {"name": "Đỏ Đen", "primary": "#FF1A1A", "secondary": "#FFFFFF", "bg": (0, 0, 0, 200), "text_light": True},
    {"name": "Vàng Trắng", "primary": "#FFD700", "secondary": "#000000", "bg": (255, 255, 255, 220), "text_light": False},
    {"name": "Xanh lá Đen", "primary": "#4CAF50", "secondary": "#FFFFFF", "bg": (0, 0, 0, 190), "text_light": True},
    {"name": "Xanh dương Đen", "primary": "#2196F3", "secondary": "#FFFFFF", "bg": (0, 0, 0, 190), "text_light": True},
    {"name": "Tím Đen", "primary": "#9C27B0", "secondary": "#FFFFFF", "bg": (0, 0, 0, 190), "text_light": True},
    {"name": "Cam Trắng", "primary": "#FF9800", "secondary": "#000000", "bg": (255, 255, 255, 210), "text_light": False},
    {"name": "Hồng Pastel", "primary": "#E91E63", "secondary": "#FFFFFF", "bg": (255, 235, 238, 220), "text_light": False},
    {"name": "Xanh Mint", "primary": "#009688", "secondary": "#FFFFFF", "bg": (0, 0, 0, 190), "text_light": True},
]
# Thêm vào đầu file, sau các định nghĩa khác
COVER_DESCRIPTIONS = [
    "Những quán cafe nhất định phải đi khi đến Đà Lạt",
    "Top quán cafe view đẹp nhất Đà Lạt",
    "Check-in ngay những quán cafe sống ảo bậc nhất Đà Lạt",
    "Trải nghiệm không gian cafe độc đáo giữa lòng Đà Lạt",
    "Cơn mê cafe - Những quán không thể bỏ lỡ tại Đà Lạt",
    "Hành trình khám phá những quán cafe đẹp như mơ ở Đà Lạt",
    "Cafe Đà Lạt - Nơi tâm hồn được thảnh thơi",
    "Những tọa độ cafe gây thương nhớ nhất Đà Lạt",
    "Cùng chill tại những quán cafe xịn sò nhất Đà Lạt",
    "Điểm danh những quán cafe phải đến khi du lịch Đà Lạt",
    "Cafe Đà Lạt - Hương vị của núi rừng và tình yêu",
    "Những quán cafe có view triệu view tại Đà Lạt",
    "Khám phá thiên đường cafe giữa lòng Đà Lạt mộng mơ",
    "Top những quán cafe cực chất cho dân nghiện sống ảo",
    "Cafe Đà Lạt - Nơi giao thoa giữa ẩm thực và nghệ thuật"
]
# --- HÀM TIỆN ÍCH ---
def normalize_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize('NFKC', text).strip().lower()
    text = re.sub(r'[^\w\s]', '', text)
    return re.sub(r'\s+', ' ', text).strip()
def adjust_font_size_by_length(base_size: int, text: str, min_size: int = 30, max_size: int = None) -> int:
    """Điều chỉnh kích thước font dựa trên độ dài text"""
    if max_size is None:
        max_size = base_size
    length = len(text)
    if length <= 10:
        ratio = 1.0
    elif length <= 15:
        ratio = 0.9
    elif length <= 20:
        ratio = 0.8
    elif length <= 25:
        ratio = 0.7
    elif length <= 30:
        ratio = 0.6
    else:
        ratio = 0.5
    new_size = int(base_size * ratio)
    return max(min_size, min(new_size, max_size))
def suggest_font_by_style(style_value: str) -> str:
    """Gợi ý font dựa trên phong cách (Vintage, Hiện đại, Châu Âu, ...)"""
    if not style_value or pd.isna(style_value):
        return "Poppins"
    
    style_lower = style_value.lower().strip()
    
    style_font_map = {
        "vintage": "Playfair Display",
        "cổ điển": "Playfair Display",
        "retro": "Playfair Display",
        "hiện đại": "Montserrat",
        "modern": "Montserrat",
        "contemporary": "Montserrat",
        "châu âu": "Great Vibes",
        "european": "Great Vibes",
        "pháp": "Parisienne",
        "hàn quốc": "Poppins",
        "korean": "Poppins",
        "tây nguyên": "Comfortaa",
        "mộc mạc": "Lora",
        "rustic": "Lora",
        "độc đáo": "Bungee",
        "unique": "Bungee",
        "tối giản": "Rubik",
        "minimalist": "Rubik",
        "nhật bản": "Chakra Petch",
        "japanese": "Chakra Petch",
    }
    
    for key, font_name in style_font_map.items():
        if key in style_lower:
            return font_name
    
    return "Poppins"
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
    """Vẽ icon pin với kích thước phù hợp"""
    red_color = "#FF1A1A"
    stick_color = "#0B0A0A"
    
    # Điều chỉnh kích thước để icon không quá to
    pin_size = size
    stick_height = int(pin_size * 0.6)
    stick_w = max(2, int(pin_size * 0.1))
    circle_r = int(pin_size * 0.3)

    # Vị trí vẽ
    circle_center = (x + circle_r + 5, y + stick_height - 5)
    stick_start = (circle_center[0], circle_center[1] + circle_r + 5)
    stick_end = (circle_center[0], stick_start[1] + stick_height)
    
    # Vẽ que
    draw.line([stick_start, stick_end], fill=stick_color, width=stick_w)
    
    # Vẽ hình tròn
    draw.ellipse([
        circle_center[0] - circle_r, circle_center[1] - circle_r,
        circle_center[0] + circle_r, circle_center[1] + circle_r
    ], fill=red_color)
    
    # Highlight
    highlight_r = int(circle_r * 0.3)
    highlight_color = "#FF6666" if color_theme and color_theme["text_light"] else "#FF9999"
    draw.ellipse([
        circle_center[0] - highlight_r, circle_center[1] - highlight_r,
        circle_center[0], circle_center[1]
    ], fill=highlight_color)
    
    # Trả về vị trí bắt đầu của text (sau icon)
    return circle_center[0] + circle_r + 10

def draw_background_shape(draw, bbox, shape_type, color_theme):
    """Vẽ hình dạng nền cho text - chỉ các shape text fit vừa"""
    x1, y1, x2, y2 = bbox
    padding = 30
    
    # Đảm bảo tọa độ hợp lệ
    x1 = max(0, x1 - padding)
    y1 = max(0, y1 - padding)
    x2 = min(draw.im.size[0], x2 + padding)
    y2 = min(draw.im.size[1], y2 + padding)
    
    if x1 >= x2 or y1 >= y2:
        draw.rectangle([x1, y1, x2, y2], fill=color_theme["bg"])
        return
    
    width = x2 - x1
    height = y2 - y1
    center_x = (x1 + x2) // 2
    center_y = (y1 + y2) // 2
    
    # === CÁC SHAPE TEXT FIT TỐT ===
    
    if shape_type == "rounded-rectangle":
        # Hình chữ nhật bo góc - text luôn vừa
        draw.rounded_rectangle([x1, y1, x2, y2], radius=25, fill=color_theme["bg"])
    
    elif shape_type == "rectangle":
        # Hình chữ nhật đơn giản
        draw.rectangle([x1, y1, x2, y2], fill=color_theme["bg"])
    
    elif shape_type == "pill-shape":
        # Hình viên thuốc - bo tròn hoàn toàn 2 đầu
        radius = height // 2
        draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=color_theme["bg"])
    
    elif shape_type == "ellipse":
        # Hình elip - text nên ngắn
        # Điều chỉnh elip để không quá hẹp
        ellipse_width = max(width, height * 1.5)
        ellipse_x1 = center_x - ellipse_width // 2
        ellipse_x2 = center_x + ellipse_width // 2
        draw.ellipse([ellipse_x1, y1, ellipse_x2, y2], fill=color_theme["bg"])
    
    elif shape_type == "diamond":
        # Hình thoi - text cần căn giữa
        points = [
            (center_x, y1),
            (x2, center_y),
            (center_x, y2),
            (x1, center_y)
        ]
        draw.polygon(points, fill=color_theme["bg"])
    
    elif shape_type == "hexagon":
        # Hình lục giác - text ngắn
        points = []
        for i in range(6):
            angle = math.pi * 2 * i / 6 - math.pi / 2
            x = center_x + width/2 * math.cos(angle)
            y = center_y + height/2 * math.sin(angle)
            points.append((x, y))
        draw.polygon(points, fill=color_theme["bg"])
    
    elif shape_type == "banner-ribbon":
        # Banner ruy băng - đẹp cho mọi độ dài text
        ribbon_height = height // 4
        points = [
            (x1, y1),
            (x2, y1),
            (x2, y2 - ribbon_height),
            (center_x, y2),
            (x1, y2 - ribbon_height)
        ]
        draw.polygon(points, fill=color_theme["bg"])
        # Thêm đuôi ruy băng nhỏ
        tail_width = min(30, width // 4)
        draw.polygon([
            (center_x, y2),
            (center_x - tail_width//2, y2 + tail_width),
            (center_x, y2 + tail_width//2),
            (center_x + tail_width//2, y2 + tail_width)
        ], fill=color_theme["bg"])
    
    elif shape_type == "tag-label":
        # Nhãn dán - text ngắn
        draw.rounded_rectangle([x1, y1, x2, y2], radius=20, fill=color_theme["bg"])
        # Đuôi nhãn bên trái
        tail_size = min(20, height // 3)
        tail_x = x1 - tail_size
        tail_y = (y1 + y2) // 2
        draw.polygon([
            (tail_x, tail_y - tail_size//2),
            (x1, tail_y),
            (tail_x, tail_y + tail_size//2)
        ], fill=color_theme["bg"])
    
    elif shape_type == "double-border":
        # Viền đôi - text dài cũng đẹp
        draw.rounded_rectangle([x1, y1, x2, y2], radius=20, 
                              fill=color_theme["bg"])
        # Viền ngoài
        draw.rounded_rectangle([x1, y1, x2, y2], radius=20, 
                              outline=color_theme["primary"], width=3)
        # Viền trong
        draw.rounded_rectangle([x1+8, y1+8, x2-8, y2-8], radius=15, 
                              outline=color_theme["secondary"], width=2)
    
    elif shape_type == "glass-morphism":
        # Kính mờ - text dài vẫn đẹp
        draw.rounded_rectangle([x1, y1, x2, y2], radius=25, fill=color_theme["bg"])
        # Hiệu ứng viền sáng
        draw.rounded_rectangle([x1, y1, x2, y2], radius=25, 
                              outline=(255,255,255,100), width=2)
        # Thêm hiệu ứng highlight góc
        highlight_size = min(40, width // 5)
        draw.ellipse([x1+5, y1+5, x1+highlight_size, y1+highlight_size], 
                    fill=(255,255,255,50))
    
    elif shape_type == "bookmark":
        # Bookmark - text ngắn đến trung bình
        bookmark_tail = min(40, height // 4)
        points = [
            (x1, y1),
            (x2, y1),
            (x2, y2 - bookmark_tail),
            (center_x, y2),
            (x1, y2 - bookmark_tail)
        ]
        draw.polygon(points, fill=color_theme["bg"])
        # Thêm lỗ tròn nhỏ ở đuôi
        hole_radius = 8
        draw.ellipse([center_x - hole_radius, y2 - bookmark_tail//2 - hole_radius,
                      center_x + hole_radius, y2 - bookmark_tail//2 + hole_radius],
                     fill=(255,255,255,200))
    
    elif shape_type == "gradient-box":
        # Hộp gradient - text dài
        # Vẽ nhiều lớp tạo hiệu ứng gradient
        for i in range(8):
            alpha = 255 - i * 30
            if isinstance(color_theme["bg"], tuple) and len(color_theme["bg"]) >= 3:
                r, g, b = color_theme["bg"][:3]
                gradient_color = (r, g, b, max(alpha, 30))
            else:
                gradient_color = color_theme["bg"]
            offset = i * 3
            if offset * 2 < min(width, height):
                draw.rounded_rectangle([x1+offset, y1+offset, x2-offset, y2-offset], 
                                      radius=20, fill=gradient_color)
    
    elif shape_type == "frame-bracket":
        # Khung ngoặc - text dài
        draw.rectangle([x1, y1, x2, y2], fill=color_theme["bg"])
        bracket_size = min(20, width // 10, height // 10)
        # Vẽ ngoặc ở 4 góc
        # Góc trên trái
        draw.line([(x1, y1+bracket_size), (x1, y1), (x1+bracket_size, y1)], 
                 fill=color_theme["primary"], width=4)
        # Góc trên phải
        draw.line([(x2-bracket_size, y1), (x2, y1), (x2, y1+bracket_size)], 
                 fill=color_theme["primary"], width=4)
        # Góc dưới trái
        draw.line([(x1, y2-bracket_size), (x1, y2), (x1+bracket_size, y2)], 
                 fill=color_theme["primary"], width=4)
        # Góc dưới phải
        draw.line([(x2-bracket_size, y2), (x2, y2), (x2, y2-bracket_size)], 
                 fill=color_theme["primary"], width=4)
    
    else:
        # Mặc định là hình chữ nhật bo góc
        draw.rounded_rectangle([x1, y1, x2, y2], radius=20, fill=color_theme["bg"])

def add_text_with_layout(image_pil, ten, gio, dc, target_size, layout_config, color_theme, font_path=None, font_scale=1.0, artistic_font=None, font_style="Bình thường"):
    """
    Thêm text vào ảnh với layout - TRÁNH ĐẶT Ở TRUNG TÂM
    """
    try:
        # Resize ảnh
        img = ImageOps.fit(image_pil.convert("RGB"), target_size, centering=(0.5, 0.5))
        
        # Tạo layer overlay cho background shape
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Convert to RGBA
        img = img.convert("RGBA")
        draw = ImageDraw.Draw(img)
        
        width, height = img.size
        scale_factor = (target_size[0] / 900.0) * font_scale
        
        # Xử lý ten_text theo font_style
        if font_style == "In hoa toàn bộ":
            ten_text = ten.upper()
        elif font_style == "Viết hoa chữ cái đầu":
            ten_text = ten.title()
        else:
            ten_text = ten.upper()
        
        # Điều chỉnh kích thước font dựa trên độ dài tên
        base_size_ten = 65 * scale_factor
        adjusted_size_ten = adjust_font_size_by_length(base_size_ten, ten_text, min_size=32, max_size=int(base_size_ten))
        font_size_ten = max(32, int(adjusted_size_ten))
        
        # Điều chỉnh kích thước font cho info
        info_text = gio + " " + dc
        base_size_info = 48 * scale_factor
        adjusted_size_info = adjust_font_size_by_length(base_size_info, info_text, min_size=24, max_size=int(base_size_info))
        font_size_info = max(20, int(adjusted_size_info))
        
        # Tải font (ưu tiên artistic_font)
        if artistic_font:
            font_ten = get_artistic_font(artistic_font, font_size_ten)
            font_info = get_artistic_font(artistic_font, font_size_info)
        else:
            font_ten = load_font(font_size_ten, font_path)
            font_info = load_font(font_size_info, font_path)
        
        position = layout_config.get("position", "bottom-left")
        shape = layout_config.get("shape", "rounded-rectangle")
        
        # Margin cơ bản - tránh xa trung tâm
        base_margin = int(80 * scale_factor / font_scale)
        
        gio_text = f"Giờ mở cửa: {gio}"
        
        # Xử lý địa chỉ xuống dòng
        max_dc_width = width * 0.45
        dc_lines = []
        current_line = ""
        words = dc.split()
        for word in words:
            test_line = current_line + " " + word if current_line else word
            test_bbox = draw.textbbox((0, 0), test_line, font=font_info)
            test_width = test_bbox[2] - test_bbox[0]
            if test_width <= max_dc_width:
                current_line = test_line
            else:
                if current_line:
                    dc_lines.append(current_line)
                current_line = word
        if current_line:
            dc_lines.append(current_line)
        
        # Đo kích thước text
        ten_bbox = draw.textbbox((0, 0), ten_text, font=font_ten)
        ten_width = ten_bbox[2] - ten_bbox[0]
        ten_height = ten_bbox[3] - ten_bbox[1]
        
        gio_bbox = draw.textbbox((0, 0), gio_text, font=font_info)
        gio_width = gio_bbox[2] - gio_bbox[0]
        gio_height = gio_bbox[3] - gio_bbox[1]
        
        dc_line_widths = []
        for line in dc_lines:
            line_bbox = draw.textbbox((0, 0), line, font=font_info)
            dc_line_widths.append(line_bbox[2] - line_bbox[0])
        dc_max_width = max(dc_line_widths) if dc_line_widths else 0
        
        pin_size = int(22 * scale_factor / font_scale)
        pin_width = pin_size + 15
        line_spacing = int(15 * scale_factor)
        
        total_height = ten_height + gio_height + (len(dc_lines) * (font_size_info + 8)) + (line_spacing * 3)
        max_width = max(ten_width, gio_width + 30, dc_max_width + pin_width + 10)
        
        # Xác định vị trí
        if position == "bottom-left":
            x = base_margin
            y = height - total_height - base_margin
        elif position == "bottom-right":
            x = width - max_width - base_margin
            y = height - total_height - base_margin
        elif position == "top-left":
            x = base_margin
            y = base_margin
        elif position == "top-right":
            x = width - max_width - base_margin
            y = base_margin
        elif position == "bottom-center":
            x = (width - max_width) // 2
            y = height - total_height - base_margin // 2
        elif position == "top-center-edge":
            x = (width - max_width) // 2
            y = base_margin // 2
        elif position == "left-center":
            x = base_margin
            y = (height - total_height) // 3
        elif position == "right-center":
            x = width - max_width - base_margin
            y = (height - total_height) // 3
        else:
            x = base_margin
            y = height - total_height - base_margin
        
        x = max(20, min(x, width - max_width - 20))
        y = max(20, min(y, height - total_height - 20))
        
        # Tránh trung tâm
        center_x_start = width * 0.3
        center_x_end = width * 0.7
        center_y_start = height * 0.3
        center_y_end = height * 0.7
        if (center_x_start < x + max_width/2 < center_x_end and 
            center_y_start < y + total_height/2 < center_y_end):
            if x < width/2:
                x = base_margin
            else:
                x = width - max_width - base_margin
            if y < height/2:
                y = base_margin
            else:
                y = height - total_height - base_margin
        
        padding = int(30 * scale_factor)
        text_bbox = [x - padding, y - padding, x + max_width + padding, y + total_height + padding]
        draw_background_shape(overlay_draw, text_bbox, shape, color_theme)
        
        img = Image.alpha_composite(img, overlay)
        draw = ImageDraw.Draw(img)
        
        text_color = "#FFFFFF" if color_theme["text_light"] else "#000000"
        hour_color = "#FFD700" if color_theme["text_light"] else "#FF8C00"
        secondary_text_color = "#E0E0E0" if color_theme["text_light"] else "#333333"
        outline_color = (0, 0, 0) if color_theme["text_light"] else (255, 255, 255)
        
        current_y = y + 15
        
        if position in ["bottom-center", "top-center-edge"]:
            text_x = x + (max_width - ten_width) // 2
        elif position in ["left-center", "right-center"]:
            text_x = x + 20
        else:
            text_x = x + 20
        
        for offset_x, offset_y in [(-2,-2), (-2,2), (2,-2), (2,2)]:
            draw.text((text_x + offset_x, current_y + offset_y), ten_text, fill=outline_color, font=font_ten)
        draw.text((text_x, current_y), ten_text, fill=text_color, font=font_ten)
        current_y += ten_height + line_spacing
        
        draw.text((text_x, current_y), gio_text, fill=hour_color, font=font_info)
        current_y += gio_height + line_spacing
        
        for i, line in enumerate(dc_lines):
            if i == 0:
                pin_x = text_x + 7
                pin_y = current_y + (font_size_info - pin_size) // 2
                draw_location_pin(draw, pin_x, pin_y, size=pin_size, color_theme=color_theme)
                text_after_pin_x = pin_x + pin_size + 15
                draw.text((text_after_pin_x, current_y), line, fill=secondary_text_color, font=font_info)
            else:
                indent = pin_size + 15
                draw.text((text_x + indent, current_y), line, fill=secondary_text_color, font=font_info)
            current_y += font_size_info + 8
        
        # Logo
        if os.path.exists(LOGO_PATH):
            try:
                logo = Image.open(LOGO_PATH).convert("RGBA")
                desired_width = 300
                w_percent = desired_width / float(logo.width)
                h_size = int(float(logo.height) * w_percent)
                logo = logo.resize((desired_width, h_size), Image.Resampling.LANCZOS)
                margin_logo = int(40 * target_size[0] / 900.0)
                logo_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
                logo_x = width - logo.width - margin_logo
                logo_y = margin_logo
                logo_layer.paste(logo, (logo_x, logo_y), logo)
                img = Image.alpha_composite(img, logo_layer)
            except Exception as e:
                print(f"Lỗi khi thêm logo: {e}")
        
        return img.convert("RGB")
        
    except Exception as e:
        print(f"Lỗi trong add_text_with_layout: {e}")
        img = ImageOps.fit(image_pil.convert("RGB"), target_size, centering=(0.5, 0.5))
        draw = ImageDraw.Draw(img)
        draw.text((50, 50), f"Lỗi: {str(e)[:100]}", fill="red")
        return img

def draw_text_with_spacing(draw, position, text, font, fill, spacing=0):
    """Vẽ text với khoảng cách giữa các chữ - GIÃN CÁCH ĐỀU"""
    x, y = position
    total_width = 0
    
    # Tính tổng chiều rộng của text với spacing
    char_widths = []
    for char in text:
        bbox = draw.textbbox((0, 0), char, font=font)
        char_width = bbox[2] - bbox[0]
        char_widths.append(char_width)
        total_width += char_width
    
    # Thêm spacing giữa các chữ
    total_width += spacing * (len(text) - 1)
    
    # Vẽ từng chữ
    current_x = x
    for i, char in enumerate(text):
        draw.text((current_x, y), char, fill=fill, font=font)
        current_x += char_widths[i] + spacing
def create_cover_image(background_img, quan_list, descriptions, target_size, color_theme, font_path=None, logo_path=None, cover_description=None, artistic_font=None, font_style="Bình thường"):
    """Tạo ảnh bìa cover với câu mô tả động và hỗ trợ font nghệ thuật"""
    try:
        # Fit ảnh background
        img = ImageOps.fit(background_img.convert("RGB"), target_size, centering=(0.5, 0.5))
        img = img.convert("RGBA")

        # Overlay tối
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 180))
        img = Image.alpha_composite(img, overlay)

        # Layer text
        text_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_layer)

        # --- SỬ DỤNG FONT NGHỆ THUẬT NẾU CÓ ---
        if artistic_font:
            font_title = get_artistic_font(artistic_font, int(target_size[0] * 0.08))
            font_subtitle = get_artistic_font(artistic_font, int(target_size[0] * 0.038))
            font_body = get_artistic_font(artistic_font, int(target_size[0] * 0.04))
            font_number = get_artistic_font(artistic_font, int(target_size[0] * 0.045))
        else:
            font_title = load_font(int(target_size[0] * 0.08), font_path)
            font_subtitle = load_font(int(target_size[0] * 0.038), font_path)
            font_body = load_font(int(target_size[0] * 0.048), font_path)
            font_number = load_font(int(target_size[0] * 0.045), font_path)

        # Lấy màu từ color_theme
        primary_color = color_theme.get("primary", "#FF6B6B")
        
        # Bộ màu phụ cho cover
        cover_color_schemes = {
            "Đỏ Đen": {"accent": "#FF4444", "highlight": "#FF8888", "secondary": "#FFD700"},
            "Vàng Trắng": {"accent": "#FFD700", "highlight": "#FFE44D", "secondary": "#FF8C00"},
            "Xanh lá Đen": {"accent": "#4CAF50", "highlight": "#81C784", "secondary": "#FFD700"},
            "Xanh dương Đen": {"accent": "#2196F3", "highlight": "#64B5F6", "secondary": "#FFD700"},
            "Tím Đen": {"accent": "#9C27B0", "highlight": "#CE93D8", "secondary": "#FFD700"},
            "Cam Trắng": {"accent": "#FF9800", "highlight": "#FFB74D", "secondary": "#FF5722"},
            "Hồng Pastel": {"accent": "#E91E63", "highlight": "#F48FB1", "secondary": "#FFD700"},
            "Xanh Mint": {"accent": "#009688", "highlight": "#4DB6AC", "secondary": "#FFD700"},
        }
        
        theme_name = color_theme.get("name", "Đỏ Đen")
        cover_colors = cover_color_schemes.get(theme_name, cover_color_schemes["Đỏ Đen"])
        
        primary_rgb = hex_to_rgb(cover_colors["accent"])
        highlight_rgb = hex_to_rgb(cover_colors["highlight"])
        secondary_rgb = hex_to_rgb(cover_colors["secondary"])

        # ===== TITLE =====
        # Xử lý theo font_style
        if font_style == "Viết hoa chữ cái đầu":
            title_text = "Khám Phá Đà Lạt"
        else:  # "Bình thường" hoặc "In hoa toàn bộ" đều dùng in hoa
            title_text = "KHÁM PHÁ ĐÀ LẠT"
        
        title_bbox = draw.textbbox((0, 0), title_text, font=font_title)
        title_w = title_bbox[2] - title_bbox[0]
        title_h = title_bbox[3] - title_bbox[1]

        title_x = (target_size[0] - title_w) // 2
        title_y = int(target_size[1] * 0.07)

        # Khung title
        draw.rounded_rectangle(
            [title_x - 50, title_y - 40, title_x + title_w + 50, title_y + title_h + 40],
            radius=35,
            fill=(0, 0, 0, 200),
            outline=primary_rgb,
            width=3
        )
        
        # Hiệu ứng glow
        for offset in range(3, 0, -1):
            draw.text((title_x, title_y - offset), title_text, fill=(*primary_rgb, 100), font=font_title)
        
        draw.text((title_x, title_y), title_text, fill=primary_rgb, font=font_title)

        # ===== CÂU MÔ TẢ PHỤ (thay đổi theo từng bộ) =====
             # ===== CÂU MÔ TẢ PHỤ (thay đổi theo từng bộ) =====
        if cover_description is None:
            cover_description = "Những quán cafe nhất định phải đi khi đến Đà Lạt"
        
        # Xuống dòng nếu câu quá dài
        max_subtitle_width = target_size[0] * 0.7
        subtitle_lines = []
        current_line = ""
        words = cover_description.split()
        
        for word in words:
            test_line = current_line + " " + word if current_line else word
            test_bbox = draw.textbbox((0, 0), test_line, font=font_subtitle)
            test_width = test_bbox[2] - test_bbox[0]
            if test_width <= max_subtitle_width:
                current_line = test_line
            else:
                if current_line:
                    subtitle_lines.append(current_line)
                current_line = word
        if current_line:
            subtitle_lines.append(current_line)
        
        # Vẽ câu mô tả
        subtitle_y = title_y + title_h + 100
        line_spacing = 45  # Khoảng cách giữa các dòng
        
        for idx, line in enumerate(subtitle_lines):
            line_bbox = draw.textbbox((0, 0), line, font=font_subtitle)
            line_w = line_bbox[2] - line_bbox[0]
            line_x = (target_size[0] - line_w) // 2
            
            # Tính vị trí y dựa trên số thứ tự dòng
            current_y = subtitle_y + idx * (font_subtitle.size + line_spacing)
            
            # Background mờ cho subtitle
            draw.rounded_rectangle(
                [line_x - 20, current_y - 8, line_x + line_w + 20, current_y + font_subtitle.size + 8],
                radius=15,
                fill=(0, 0, 0, 150)
            )
            draw.text((line_x, current_y), line, fill=secondary_rgb, font=font_subtitle)
        
        # Cập nhật subtitle_y cho phần tiếp theo (vị trí sau khi vẽ xong tất cả dòng)
        if subtitle_lines:
            # Lấy vị trí cuối cùng của dòng cuối + padding
            last_line_y = subtitle_y + (len(subtitle_lines) - 1) * (font_subtitle.size + line_spacing)
            final_subtitle_y = last_line_y + font_subtitle.size + 30
        else:
            final_subtitle_y = subtitle_y + font_subtitle.size + 30

        # ===== TÍNH TOÁN KÍCH THƯỚC THỰC TẾ CỦA TỪNG ITEM =====
        max_actual_height = 0
        for i in range(min(len(quan_list), 8)):
            name_text = quan_list[i].upper()
            if len(name_text) > 30:
                name_text = name_text[:27] + "..."
            name_bbox = draw.textbbox((0, 0), name_text, font=font_body)
            name_h = name_bbox[3] - name_bbox[1]
            max_actual_height = max(max_actual_height, name_h)
        
        padding_y = 18
        actual_item_height = max_actual_height + padding_y * 2 + 10
        item_spacing = 35
        subtitle_to_first_item = 120
        start_y = final_subtitle_y + subtitle_to_first_item
        available_height = target_size[1] - start_y - 90
        max_items = int(available_height / (actual_item_height + item_spacing))
        max_items = min(max_items, len(quan_list), 8)
        
        circle_r = 32
        padding_x = 35

        # Tìm chiều rộng lớn nhất của tên quán
        max_name_width = 0
        for i in range(max_items):
            name_text = quan_list[i].upper()
            if len(name_text) > 30:
                name_text = name_text[:27] + "..."
            name_bbox = draw.textbbox((0, 0), name_text, font=font_body)
            name_w = name_bbox[2] - name_bbox[0]
            max_name_width = max(max_name_width, name_w)

        total_item_width = (circle_r * 2) + 25 + (max_name_width + padding_x * 2)
        center_start_x = (target_size[0] - total_item_width) // 2

        # Vẽ từng item
        for i in range(max_items):
            y_pos = start_y + i * (actual_item_height + item_spacing)
            if y_pos + actual_item_height > target_size[1] - 80:
                break

            circle_x = center_start_x + circle_r
            circle_y = y_pos + actual_item_height // 2

            # Bóng đổ
            draw.ellipse(
                [circle_x - circle_r - 2, circle_y - circle_r - 2,
                 circle_x + circle_r + 2, circle_y + circle_r + 2],
                fill=(0, 0, 0, 80)
            )
            # Vòng tròn chính
            draw.ellipse(
                [circle_x - circle_r, circle_y - circle_r,
                 circle_x + circle_r, circle_y + circle_r],
                fill=primary_rgb,
                outline=highlight_rgb,
                width=3
            )

            # Số thứ tự
            number_text = str(i + 1)
            left, top, right, bottom = draw.textbbox((0, 0), number_text, font=font_number)
            tw = right - left
            th = bottom - top
            number_x = circle_x - tw // 2
            number_y = circle_y - th // 2
            draw.text((number_x, number_y), number_text, fill=(255, 255, 255), font=font_number)

            # Tên quán
            name_text = quan_list[i].upper()
            if len(name_text) > 30:
                name_text = name_text[:27] + "..."
            name_bbox = draw.textbbox((0, 0), name_text, font=font_body)
            name_w = name_bbox[2] - name_bbox[0]
            name_h = name_bbox[3] - name_bbox[1]

            name_bg_w = name_w + padding_x * 2
            name_bg_h = name_h + padding_y * 2
            name_bg_x = circle_x + circle_r + 25
            name_bg_y = y_pos + (actual_item_height - name_bg_h) // 2

            # Khung nền cho tên quán
            draw.rounded_rectangle(
                [name_bg_x, name_bg_y, name_bg_x + name_bg_w, name_bg_y + name_bg_h],
                radius=28,
                fill=(0, 0, 0, 220),
                outline=(primary_rgb[0], primary_rgb[1], primary_rgb[2], 150),
                width=2
            )
            # Thanh highlight bên trái
            draw.rounded_rectangle(
                [name_bg_x, name_bg_y + 10, name_bg_x + 5, name_bg_y + name_bg_h - 10],
                radius=3,
                fill=primary_rgb
            )
            # Vẽ text
            text_x = name_bg_x + padding_x + 12
            text_y = name_bg_y + padding_y
            draw_text_with_spacing(draw, (text_x, text_y), name_text, font_body, (255, 255, 255), spacing=7)

        # ===== FOOTER =====
        footer_text = "Riviu • Khám phá Đà Lạt cùng chúng tôi"
        f_bbox = draw.textbbox((0, 0), footer_text, font=font_body)
        f_w = f_bbox[2] - f_bbox[0]
        f_h = f_bbox[3] - f_bbox[1]
        f_x = (target_size[0] - f_w) // 2
        f_y = target_size[1] - 180
        draw.rounded_rectangle(
            [f_x - 35, f_y - 15, f_x + f_w + 35, f_y + f_h + 15],
            radius=20,
            fill=(0, 0, 0, 180),
            outline=primary_rgb,
            width=2
        )
        draw.text((f_x, f_y), footer_text, fill=primary_rgb, font=font_body)

        # Merge layer text với background
        img = Image.alpha_composite(img, text_layer).convert("RGB")

        # ===== LOGO =====
        if logo_path and os.path.exists(logo_path):
            try:
                logo = Image.open(logo_path).convert("RGBA")
                w = 250
                ratio = w / logo.width
                h = int(logo.height * ratio)
                logo = logo.resize((w, h), Image.Resampling.LANCZOS)
                layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
                margin = 30
                layer.paste(logo, (target_size[0] - w - margin, margin), logo)
                img = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")
            except Exception as e:
                print(f"Lỗi khi thêm logo: {e}")

        return img

    except Exception as e:
        print(f"Lỗi tạo cover: {e}")
        import traceback
        traceback.print_exc()
        img = Image.new('RGB', target_size, color=(30, 30, 40))
        draw = ImageDraw.Draw(img)
        draw.text((target_size[0]//2, target_size[1]//2), f"COVER - {len(quan_list)} quán", 
                 fill=(255, 255, 255), anchor="mm")
        return img
    
# Hàm hỗ trợ hex to rgb
def hex_to_rgb(hex_color):
    """Chuyển đổi hex color sang rgb tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
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
    """Tìm cột phù hợp với các tên cột khác nhau trong file Excel"""
    cols = {normalize_text(c): c for c in df.columns}
    
    # Tìm cột Tên quán (hỗ trợ nhiều tên cột khác nhau)
    ten = None
    for key in ['ten_quan', 'ten quan', 'tên quán', 'ten', 'tên', 'tên địa điểm', 'TÊN ĐỊA ĐIỂM']:
        if key in cols:
            ten = cols[key]
            break
    
    # Tìm cột Địa chỉ
    dia = None
    for key in ['dia_chi', 'dia chi', 'địa chỉ', 'diachi', 'address', 'địa chỉ', 'ĐỊA CHỈ']:
        if key in cols:
            dia = cols[key]
            break
    
    # Tìm cột Giờ mở cửa
    gio = None
    for key in ['gio_mo_cua', 'gio mo cua', 'giờ mở cửa', 'thoi gian mo cua', 
                'thời gian mở cửa', 'gio', 'GIỜ MỞ CỬA']:
        if key in cols:
            gio = cols[key]
            break
    
    # Tìm cột Đối tác
    doi = None
    for key in ['doi_tac', 'doi tac', 'đối tác', 'doitac', 'ĐỐI TÁC CÔNG TY', 'Doi_tac']:
        if key in cols:
            doi = cols[key]
            break
    
    # Tìm cột Món ăn nổi bật
    mon = None
    for key in ['mon_an_noi_bat', 'mon an noi bat', 'món ăn nổi bật', 'mon an', 'mon', 'Noi_bat']:
        if key in cols:
            mon = cols[key]
            break
    
    # Tìm cột Phong cách
    style = None
    for key in ['phong_cach', 'phong cach', 'phong cách', 'style', 'PHONG CÁCH']:
        if key in cols:
            style = cols[key]
            break
    
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
#Xử lý excel
def process_sheet_data(df: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
    """Xử lý dữ liệu theo từng sheet"""
    df_processed = df.copy()
    
    if sheet_name == "Quan_an":
        if 'Mo_hinh' in df.columns:
            st.info(f"🍽️ Loại hình: {df['Mo_hinh'].unique().tolist()}")
    
    elif sheet_name == "Cafe":
        if 'MÓN ĂN NỔI BẬT' in df.columns:
            df_processed = df_processed.rename(columns={'MÓN ĂN NỔI BẬT': 'Mon_an_noi_bat'})
    
    elif sheet_name == "Khu_du_lich":
        if 'Noi_bat' in df.columns:
            df_processed = df_processed.rename(columns={'Noi_bat': 'Mon_an_noi_bat'})
    
    elif sheet_name == "Homestay":
        if 'Gia' in df.columns and 'Gio_mo_cua' not in df.columns:
            df_processed['Gio_mo_cua'] = 'Check-in: 14:00, Check-out: 12:00'
    
    elif sheet_name == "Check_in":
        if 'Gia' in df.columns and 'Gio_mo_cua' not in df.columns:
            df_processed['Gio_mo_cua'] = 'Mở cửa cả ngày'
    
    elif sheet_name == "Địa điểm lịch sử":
        # Đổi tên cột TÊN ĐỊA ĐIỂM thành Ten_quan
        if 'TÊN ĐỊA ĐIỂM' in df.columns:
            df_processed = df_processed.rename(columns={'TÊN ĐỊA ĐIỂM': 'Ten_quan'})
        if 'ĐỊA CHỈ' in df.columns:
            df_processed = df_processed.rename(columns={'ĐỊA CHỈ': 'Dia_chi'})
        if 'GIỜ MỞ CỬA' in df.columns:
            df_processed = df_processed.rename(columns={'GIỜ MỞ CỬA': 'Gio_mo_cua'})
        if 'ĐỐI TÁC CÔNG TY' in df.columns:
            df_processed = df_processed.rename(columns={'ĐỐI TÁC CÔNG TY': 'Doi_tac'})
    
    elif sheet_name == "Dich_vu":
        if 'Loai_dich_vu' in df.columns:
            df_processed['Mon_an_noi_bat'] = df_processed['Loai_dich_vu']
    
    elif sheet_name == "Choi_đem":
        if 'Loai_dich_vu' in df.columns:
            df_processed['Mon_an_noi_bat'] = df_processed['Loai_dich_vu']
        if 'Gio_mo_cua' not in df.columns:
            df_processed['Gio_mo_cua'] = '19:00 - 02:00'
    
    elif sheet_name == "Xe_khach":
        if 'Gio_mo_cua' not in df.columns:
            df_processed['Gio_mo_cua'] = 'Liên hệ trực tiếp'
    
    elif sheet_name == "Hoat_dong":
        # Sheet hoạt động không có địa chỉ và giờ, tạo dữ liệu mẫu
        if 'Gio_mo_cua' not in df.columns:
            df_processed['Gio_mo_cua'] = 'Theo lịch trình'
        if 'Dia_chi' not in df.columns:
            df_processed['Dia_chi'] = 'Đà Lạt'
    
    return df_processed
def generate_cover_description(api_key: str, provider: str = 'gemini') -> str:
    """Dùng AI để sinh câu mô tả cho bìa, nếu lỗi thì dùng câu có sẵn"""
    if not api_key:
        return random.choice(COVER_DESCRIPTIONS)
    
    prompt = """
    Viết một câu ngắn gọn (tối đa 12 từ) giới thiệu về các quán cafe/ăn uống tại Đà Lạt.
    Câu nên hấp dẫn, kêu gọi khám phá. Không được trùng lặp với các câu sau:
    - "Những quán cafe nhất định phải đi khi đến Đà Lạt"
    - "Top quán cafe view đẹp nhất Đà Lạt"
    - "Check-in ngay những quán cafe sống ảo bậc nhất Đà Lạt"
    
    Chỉ trả về 1 câu duy nhất, không có dấu ngoặc kép, không giải thích thêm.
    Ví dụ: "Cafe Đà Lạt - Nơi tâm hồn được thảnh thơi"
    """
    
    try:
        if provider == 'gemini':
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            text = response.text.strip().strip('"').strip("'")
            # Kiểm tra độ dài
            if len(text.split()) > 15:
                text = ' '.join(text.split()[:12])
            return text
        else:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.8,
                "max_tokens": 50
            }
            resp = requests.post("https://api.deepseek.com/v1/chat/completions", 
                                headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                text = resp.json()['choices'][0]['message']['content'].strip().strip('"')
                if len(text.split()) > 15:
                    text = ' '.join(text.split()[:12])
                return text
            else:
                return random.choice(COVER_DESCRIPTIONS)
    except Exception as e:
        print(f"Lỗi sinh cover description: {e}")
        return random.choice(COVER_DESCRIPTIONS)
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
    st.markdown("### ✨ Cấu hình Font chữ")
    
    # Danh sách font
    font_categories = {
        "Serif (Sang trọng)": ["Playfair Display", "Cormorant Garamond", "Libre Baskerville", "DM Serif Display", "Prata", "Lora"],
        "Sans-serif (Hiện đại)": ["Be Vietnam Pro", "Montserrat", "Poppins", "Raleway", "Rubik", "Lexend", "Barlow Condensed", "Oswald"],
        "Script (Viết tay)": ["Great Vibes", "Allura", "Satisfy", "Parisienne", "Sacramento"],
        "Stylized (Độc lạ)": ["Bungee", "Fredoka", "Baloo 2", "Comfortaa", "Chakra Petch"],
    }
    all_fonts = []
    for fonts in font_categories.values():
        all_fonts.extend(fonts)
    
    default_font_index = 0
    if st.session_state.suggested_font and st.session_state.suggested_font in all_fonts:
        default_font_index = all_fonts.index(st.session_state.suggested_font)
    
    selected_font = st.selectbox("Chọn font chữ cho banner:", all_fonts, index=default_font_index)
    font_style = st.radio("Phong cách chữ:", ["Bình thường", "In hoa toàn bộ", "Viết hoa chữ cái đầu"], index=0)
    random_font_per_set = st.checkbox("🎲 Random font mỗi bộ", value=False, help="Mỗi bộ sẽ dùng 1 font ngẫu nhiên khác nhau")
    
    # Preview font
    st.markdown("**🔤 Mẫu chữ:**")
    preview_text = "Riviu Đà Lạt 123"
    st.markdown(f"""
    <div style="font-family: '{selected_font}', sans-serif; font-size: 24px; padding: 10px; border: 1px solid #ddd; border-radius: 10px; background-color: #f0f2f6; margin-bottom: 10px;">
        {preview_text}
    </div>
    """, unsafe_allow_html=True)
    
    # Gợi ý font dựa trên phong cách (nếu có Excel và cột Phong_cach)
    if 'df' in locals() and df is not None and style_col:
        styles = df[style_col].dropna().unique()
        if len(styles) > 0:
            most_common_style = df[style_col].mode()[0] if not df[style_col].mode().empty else styles[0]
            suggested = suggest_font_by_style(most_common_style)
            if suggested != selected_font:
                st.info(f"💡 Gợi ý font cho phong cách '{most_common_style}': **{suggested}**")
                if st.button(f"✨ Dùng font {suggested}"):
                    st.session_state.suggested_font = suggested
                    st.rerun()
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
    
    # Ưu tiên các sheet có dữ liệu
    priority_sheets = ['Quan_an', 'Cafe', 'Khu_du_lich', 'Địa điểm lịch sử', 'Dich_vu']
    default_idx = 0
    for i, sheet in enumerate(sheet_names):
        if sheet in priority_sheets:
            default_idx = i
            break
    
    selected_sheet = st.selectbox("Chọn sheet chứa dữ liệu:", sheet_names, index=default_idx)
    df = sheets[selected_sheet].copy()
    
    # Xử lý dữ liệu theo từng sheet
    df = process_sheet_data(df, selected_sheet)
    
    st.success(f"✅ Đã đọc sheet `{selected_sheet}` ({len(df)} dòng)")
    
    # Tìm cột sau khi đã xử lý
    ten_col, dia_col, gio_col, doi_col, mon_col, style_col = find_required_columns(df)
    
    # Kiểm tra các cột bắt buộc
    missing_cols = []
    if not ten_col:
        missing_cols.append("Tên quán")
    if not dia_col:
        missing_cols.append("Địa chỉ")
    if not gio_col:
        missing_cols.append("Giờ mở cửa")
    
    if missing_cols:
        st.error(f"❌ Thiếu cột bắt buộc: {', '.join(missing_cols)}")
        st.info("📋 Các cột hiện có trong file: " + ", ".join(df.columns.tolist()))
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
    
    # Thông báo về các cột tùy chọn
    if not mon_col:
        st.info("💡 Tip: Thêm cột 'Mon_an_noi_bat' để AI tạo mô tả hay hơn!")
    if not style_col:
        st.info("💡 Tip: Thêm cột 'Phong_cach' để AI tạo mô tả chính xác hơn!")
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
            # ===== 1. KHỞI TẠO LAYOUT CHO BỘ =====
            if layout_mode == "Cố định cho tất cả":
                theme_idx = [i for i, t in enumerate(COLOR_THEMES) if t["name"] == fixed_theme][0]
                set_color_theme = COLOR_THEMES[theme_idx]
                set_layout = {
                    "position": fixed_position,
                    "shape": fixed_shape
                }
                use_consistent_layout = True  # Dùng chung layout cho cả bộ
            elif layout_mode == "Random mỗi bộ (đồng bộ màu)":
                set_color_theme = random.choice(COLOR_THEMES)
                set_layout = {
                    "position": random.choice(TEXT_POSITIONS),
                    "shape": random.choice(BACKGROUND_SHAPES)
                }
                use_consistent_layout = True  # Dùng chung layout cho cả bộ
            else:  # Random mỗi ảnh
                set_layout = None
                set_color_theme = None
                use_consistent_layout = False  # Mỗi ảnh random khác nhau
            
            # Chọn quán cho bộ
            selected = priority_shuffle(available_quans, partner_dict, int(imgs_per_set), allow_repeat)
            set_partners = [q for q in selected if partner_dict.get(normalize_text(q), False)]
            partner_logs[f"Bộ {set_idx+1}"] = set_partners

            font_path = get_random_font_path(seed=set_idx)
            set_quans = []
            set_descriptions = []
               # Chọn font cho bộ này
            if random_font_per_set:
                current_font = random.choice(all_fonts)
            else:
                current_font = selected_font
                fixed_font_scale = font_scale
            # Tạo mô tả ngắn cho từng quán bằng AI
            for ten in selected:
                if ai_enabled:
                    mon = mon_map.get(ten, "") if mon_map else ""
                    style = style_map.get(ten, "") if style_map else ""
                    desc = generate_short_description(ten, mon, style, ai_key, ai_provider)
                else:
                    desc = f"{ten} - Điểm đến tuyệt vời tại Đà Lạt ✨"
                set_descriptions.append(desc)

            # === SINH CÂU MÔ TẢ CHO COVER ===
            if ai_enabled:
                cover_description = generate_cover_description(ai_key, ai_provider)
            else:
                cover_description = random.choice(COVER_DESCRIPTIONS)

            # === TẠO ẢNH BÌA COVER ===
            if all_images_list:
                if src_option == "Upload file ZIP":
                    random_img_bytes = random.choice(all_images_list)
                    cover_bg = Image.open(io.BytesIO(random_img_bytes))
                else:
                    random_img_path = random.choice(all_images_list)
                    cover_bg = Image.open(random_img_path)
                
                cover_color_theme = set_color_theme if use_consistent_layout else random.choice(COLOR_THEMES)
                
                cover_img = create_cover_image(
                    cover_bg, selected, set_descriptions, target_size, 
                    cover_color_theme, font_path, logo_path=LOGO_PATH,
                    cover_description=cover_description,
                    artistic_font=current_font,
                    font_style=font_style
                )
                cover_buf = io.BytesIO()
                cover_img.save(cover_buf, format='JPEG', quality=jpeg_quality)
                zf.writestr(f"Bo_{set_idx+1}/00_COVER.jpg", cover_buf.getvalue())

            # === TẠO ẢNH CHO TỪNG QUÁN ===
            layout_info_list = []

            # TẠO LAYOUT CỐ ĐỊNH CHO CẢ BỘ TRƯỚC VÒNG LẶP (nếu dùng chung)
            if use_consistent_layout:
                fixed_layout_for_set = set_layout.copy()  # Tạo bản sao cố định
                fixed_theme_for_set = set_color_theme
            else:
                fixed_layout_for_set = None
                fixed_theme_for_set = None

            for idx, ten in enumerate(selected):
                key = normalize_text(ten)
                if key not in image_dict or not image_dict[key]:
                    continue

                img_item = random.choice(image_dict[key])
                gio = gio_map.get(ten, "7:00 - 22:00")
                dc = dia_map.get(ten, "Đà Lạt")
                
                # QUAN TRỌNG: Chọn layout dựa trên chế độ
                if use_consistent_layout:
                    # DÙNG CHUNG layout cho cả bộ (dùng bản sao cố định)
                    img_layout = fixed_layout_for_set
                    img_color_theme = fixed_theme_for_set
                else:
                    # Random mỗi ảnh khác nhau
                    img_layout = {
                        "position": random.choice(TEXT_POSITIONS),
                        "shape": random.choice(BACKGROUND_SHAPES)
                    }
                    img_color_theme = random.choice(COLOR_THEMES)
                
                # Lưu layout của ảnh đầu tiên
                if idx == 0:
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
                            font_scale=fixed_font_scale,
                            artistic_font=current_font,
                            font_style=font_style)
                except Exception as e:
                    st.warning(f"⚠️ Lỗi ảnh {ten}: {e}")
                    continue

                buf = io.BytesIO()
                banner.save(buf, format='JPEG', quality=jpeg_quality)
                safe_name = re.sub(r'[<>:"/\\|?*]', '_', ten)
                zf.writestr(f"Bo_{set_idx+1}/{idx+1:02d}_{safe_name}.jpg", buf.getvalue())
                set_quans.append(ten)

            # Sinh caption
            if ai_enabled and set_quans:
                tt_cap = generate_tiktok_caption(set_quans, set_descriptions, ai_key, ai_provider)
                fb_cap = generate_facebook_caption(set_quans, set_descriptions, ai_key, ai_provider)
                all_captions.append({
                    "Bộ": f"Bộ {set_idx+1}",
                    "Quán": ", ".join(set_quans),
                    "Đối tác": ", ".join(set_partners) if set_partners else "Không",
                    "Layout & Màu": layout_info_list[0] if layout_info_list else "N/A",
                    "Cover Mô tả": cover_description,
                    "TikTok": tt_cap,
                    "Facebook": fb_cap
                })
            else:
                all_captions.append({
                    "Bộ": f"Bộ {set_idx+1}",
                    "Quán": ", ".join(set_quans),
                    "Đối tác": ", ".join(set_partners) if set_partners else "Không",
                    "Layout & Màu": layout_info_list[0] if layout_info_list else "N/A",
                    "Cover Mô tả": cover_description,
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
st.caption("Made by Hữu Thiện | Ảnh xuất ra chất lượng cao - Layout đa dạng - Màu sắc đồng bộ")