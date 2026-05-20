import streamlit as st
import pandas as pd
import os
import random
import re
import io
import zipfile
import html
import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
import math
from datetime import datetime
import unicodedata
import hashlib
import tempfile
import shutil
from typing import Optional, Dict, List, Tuple
import google.generativeai as genai
import math
import xlrd
import openpyxl
from urllib.parse import urlparse, parse_qs
import mimetypes
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
import gspread
from google.oauth2.service_account import Credentials
import time
import json
import gc
import base64
from cryptography.fernet import Fernet
from functools import lru_cache
from pathlib import Path
# ===== HÀM ĐỌC EXCEL VỚI CACHE =====
@st.cache_data(ttl=3600, show_spinner="Đang đọc file Excel...")
def load_excel_data_cached(uploaded_file, sheet_name):
    """Đọc Excel với cache - chỉ đọc 1 lần"""
    sheets = read_excel_with_sheets(uploaded_file)
    df = sheets[sheet_name].copy()
    df = process_sheet_data(df, sheet_name)
    ten_col, dia_col, gio_col, doi_col, mon_col, style_col = find_required_columns(df)
    return df, ten_col, dia_col, gio_col, doi_col, mon_col, style_col

@st.cache_data(ttl=3600, show_spinner="Đang đọc Google Sheet...")
def load_gsheet_data_cached(sheet_url, selected_sheet, sheet_api_key):
    """Đọc Google Sheet với cache"""
    all_sheets_data = read_all_sheets_from_url(sheet_url, api_key=sheet_api_key if sheet_api_key else None)
    if selected_sheet in all_sheets_data:
        df = all_sheets_data[selected_sheet].copy()
        df = process_sheet_data(df, selected_sheet)
        ten_col, dia_col, gio_col, doi_col, mon_col, style_col = find_required_columns(df)
        return df, ten_col, dia_col, gio_col, doi_col, mon_col, style_col
    return None, None, None, None, None, None, None

# --- MÃ HÓA API KEY ---
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".riviu")
os.makedirs(CONFIG_DIR, exist_ok=True)
KEY_FILE = os.path.join(CONFIG_DIR, "secret.key")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.enc")

def get_or_create_key():
    """Lấy hoặc tạo key mã hóa"""
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, 'rb') as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        with open(KEY_FILE, 'wb') as f:
            f.write(key)
        return key

def encrypt_api_keys(keys_dict):
    """Mã hóa API keys"""
    key = get_or_create_key()
    fernet = Fernet(key)
    data = json.dumps(keys_dict).encode()
    encrypted = fernet.encrypt(data)
    with open(CONFIG_FILE, 'wb') as f:
        f.write(encrypted)

def decrypt_api_keys():
    """Giải mã API keys"""
    if not os.path.exists(CONFIG_FILE):
        return {}
    key = get_or_create_key()
    fernet = Fernet(key)
    with open(CONFIG_FILE, 'rb') as f:
        encrypted = f.read()
    decrypted = fernet.decrypt(encrypted)
    return json.loads(decrypted.decode())

# --- PAGE CONFIG ---
st.set_page_config(page_title="Riviu TikTok AI Pro", layout="wide", page_icon="🎬")

# --- HELPER STREAMLIT ---
def st_button_fix(label, key=None, use_container_width=True, **kwargs):
    """Wrapper để fix deprecated use_container_width"""
    version = getattr(st, "__version__", "0.0.0")
    try:
        version_tuple = tuple(int(x) for x in version.split('.')[:2])
    except:
        version_tuple = (0, 0)
    if version_tuple >= (1, 28):
        return st.button(label, key=key, **kwargs)
    return st.button(label, key=key, use_container_width=use_container_width, **kwargs)

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
if 'use_font_combo' not in st.session_state:
    st.session_state.use_font_combo = False
if 'auto_hyperlink_loaded' not in st.session_state:
    st.session_state.auto_hyperlink_loaded = False
if 'auto_image_dict' not in st.session_state:
    st.session_state.auto_image_dict = {}
if 'auto_all_images_list' not in st.session_state:
    st.session_state.auto_all_images_list = []
if 'max_workers' not in st.session_state:
    st.session_state.max_workers = 15
if 'use_cache' not in st.session_state:
    st.session_state.use_cache = True
if 'sheet_url' not in st.session_state:
    st.session_state.sheet_url = None
if 'selected_sheet_name' not in st.session_state:
    st.session_state.selected_sheet_name = None
if 'show_preview' not in st.session_state:
    st.session_state.show_preview = False
# --- CẤU HÌNH ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = tempfile.mkdtemp(prefix="riviu_")
LOGO_PATH = os.path.join(BASE_DIR, "logo_riviu.png")
HARD_HASHTAGS = "#riviudalat #dalat #dalatreview"

# --- CACHE CONFIG ---
CACHE_DIR = os.path.join(tempfile.gettempdir(), "riviu_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# Danh sách font ưu tiên có hỗ trợ tiếng Việt
FONT_PATHS = [
    # === FONT AN TOÀN - HỖ TRỢ TIẾNG VIỆT ===
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    
    # === WINDOWS - CHỈ GIỮ FONT TỒN TẠI ===
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/Arial.ttf",
    "C:/Windows/Fonts/calibri.ttf",
    "C:/Windows/Fonts/Calibri.ttf",
    "C:/Windows/Fonts/tahoma.ttf",
    "C:/Windows/Fonts/Tahoma.ttf",
    "C:/Windows/Fonts/verdana.ttf",
    "C:/Windows/Fonts/Verdana.ttf",
    "C:/Windows/Fonts/times.ttf",
    
    # === MacOS ===
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    
    # === FALLBACK ===
    "arial.ttf", "Arial.ttf", "DejaVuSans.ttf"
]
# ============================================================
# DANH SÁCH FONT - HỖ TRỢ TIẾNG VIỆT TỐT (GENZ EDITION)
# ============================================================
# ============================================================
# DANH SÁCH FONT - HỖ TRỢ TIẾNG VIỆT TỐT (GENZ EDITION)
# ============================================================
FONT_ARTISTIC = {
    # ===== ✍️ HANDWRITTEN / VIẾT TAY =====
    "Patrick Hand": "https://github.com/google/fonts/raw/main/ofl/patrickhand/PatrickHand-Regular.ttf",
    "Kalam": "https://github.com/google/fonts/raw/main/ofl/kalam/Kalam%5Bwght%5D.ttf",
    "Mali": "https://github.com/google/fonts/raw/main/ofl/mali/Mali%5Bwght%5D.ttf",
    "Allura": "https://github.com/google/fonts/raw/main/ofl/allura/Allura-Regular.ttf",
    "Pacifico": "https://github.com/google/fonts/raw/main/ofl/pacifico/Pacifico-Regular.ttf",
    
    # ===== 📱 SANS-SERIF (DỄ ĐỌC) =====
    "Be Vietnam Pro": None,  # Dùng font hệ thống
    "Poppins": "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins%5Bwght%5D.ttf",
    "Nunito": "https://github.com/google/fonts/raw/main/ofl/nunito/Nunito%5Bwght%5D.ttf",
    "Lexend": "https://github.com/google/fonts/raw/main/ofl/lexend/Lexend%5Bwght%5D.ttf",  # ĐÃ THÊM URL
    
    # ===== 🅱️ BOLD & IMPACT (CHỮ ĐẬM) =====
    "Anton": "https://github.com/google/fonts/raw/main/ofl/anton/Anton-Regular.ttf",
    "Oswald": "https://github.com/google/fonts/raw/main/ofl/oswald/Oswald%5Bwght%5D.ttf",  # ĐÃ THÊM URL
    
    # ===== 🎨 SERIF (SANG TRỌNG) =====
    "Playfair Display": "https://github.com/google/fonts/raw/main/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf",
    "Lora": "https://github.com/google/fonts/raw/main/ofl/lora/Lora%5Bwght%5D.ttf",
}

# Link tải font - CHỈ GIỮ NHỮNG FONT CÓ TRONG FONT_ARTISTIC
FONT_DOWNLOAD_URLS = {
    "Patrick Hand": "https://github.com/google/fonts/raw/main/ofl/patrickhand/PatrickHand-Regular.ttf",
    "Kalam": "https://github.com/google/fonts/raw/main/ofl/kalam/Kalam%5Bwght%5D.ttf",
    "Mali": "https://github.com/google/fonts/raw/main/ofl/mali/Mali%5Bwght%5D.ttf",
    "Allura": "https://github.com/google/fonts/raw/main/ofl/allura/Allura-Regular.ttf",
    "Pacifico": "https://github.com/google/fonts/raw/main/ofl/pacifico/Pacifico-Regular.ttf",
    "Poppins": "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins%5Bwght%5D.ttf",
    "Nunito": "https://github.com/google/fonts/raw/main/ofl/nunito/Nunito%5Bwght%5D.ttf",
    "Lexend": "https://github.com/google/fonts/raw/main/ofl/lexend/Lexend%5Bwght%5D.ttf",
    "Anton": "https://github.com/google/fonts/raw/main/ofl/anton/Anton-Regular.ttf",
    "Oswald": "https://github.com/google/fonts/raw/main/ofl/oswald/Oswald%5Bwght%5D.ttf",
    "Playfair Display": "https://github.com/google/fonts/raw/main/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf",
    "Lora": "https://github.com/google/fonts/raw/main/ofl/lora/Lora%5Bwght%5D.ttf",
}
# Thêm dòng này sau FONT_DOWNLOAD_URLS
FONT_DOWNLOAD_URL = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSans/NotoSans-Regular.ttf"
# ============================================================
# BỘ FONT THEME RIÊNG THEO YÊU CẦU
FONT_STYLE_PRESETS = [
    {"name": "TikTok Trending", "font": "Anton"},
    {"name": "Việt Nam Hiện Đại", "font": "Be Vietnam Pro"},
    {"name": "Sang Trọng", "font": "Playfair Display"},
    {"name": "Mộng Mơ Đà Lạt", "font": "Dancing Script"},
    {"name": "Minimalist", "font": "Montserrat"},
    {"name": "Thanh Lịch", "font": "Lora"},
    {"name": "Dễ Thương", "font": "Quicksand"},
    {"name": "Phá Cách", "font": "Lexend"},
    {"name": "Viết Tay Nghệ Thuật", "font": "Allura"},  # THÊM
    {"name": "Bold & Impact", "font": "Oswald"},  # THÊM
    {"name": "Vui Tươi", "font": "Pacifico"},  # THÊM
]
PRESET_FONTS = [preset["font"] for preset in FONT_STYLE_PRESETS]

# ============================================================
# COMBO FONT GỢI Ý THEO VIBE GENZ
# ============================================================
FONT_COMBOS = {
    "🎀 Dễ thương - TikTok GenZ": {
        "title": ["Patrick Hand", "Gochi Hand"],
        "body": ["Be Vietnam Pro", "Poppins"],
        "highlight": ["Mali"]
    },
    "🌸 Aesthetic - Cafe/Beauty": {
        "title": ["Mali", "Caveat"],
        "body": ["Be Vietnam Pro", "Nunito"],
        "highlight": ["Kalam"]
    },
    "✨ Sang trọng - Luxury": {
        "title": ["Kalam", "Montserrat"],
        "body": ["Be Vietnam Pro", "Lexend"],
        "highlight": ["Patrick Hand"]
    },
    "🎨 Năng động - Vui vẻ": {
        "title": ["Patrick Hand", "Gochi Hand"],
        "body": ["Outfit", "Quicksand"],
        "highlight": ["Caveat"]
    },
    "🌿 Chill - Nhẹ nhàng": {
        "title": ["Caveat", "Kalam"],
        "body": ["Be Vietnam Pro", "Nunito"],
        "highlight": ["Patrick Hand"]
    }
}
# ============================================================
# DANH MỤC FONT CHO SIDEBAR - GENZ EDITION
# ============================================================
FONT_CATEGORIES = {
    "✍️ Handwritten (Viết tay - GenZ)": ["Patrick Hand", "Kalam", "Mali", "Caveat", "Gochi Hand"],
    "📱 Sans-serif (Dễ đọc)": ["Be Vietnam Pro", "Poppins", "Nunito", "Montserrat", "Lexend", "Outfit", "Quicksand"],
}
# Trong phần sidebar, thay thế all_fonts
# Mở rộng danh sách font trong get_all_fonts_list()
def get_all_fonts_list() -> List[str]:
    """Trả về danh sách tất cả font hỗ trợ tiếng Việt hoặc dùng cho banner."""
    all_fonts = [
        # Bộ font theo yêu cầu của bạn
        "Anton", "Be Vietnam Pro", "Playfair Display", "Dancing Script", "Montserrat",
        "Lora", "Quicksand", "Lexend", "Cormorant Garamond",
        # Font mới thêm
        "Allura", "Pacifico", "Oswald",
        # Font dự phòng cũ
        "Patrick Hand", "Kalam", "Mali", "Caveat", "Gochi Hand", "Poppins", "Nunito", "Outfit"
    ]
    return all_fonts
# --- ĐỊNH NGHĨA LAYOUT VÀ HÌNH DẠNG NỀN ---
TEXT_POSITIONS = [
    "bottom-left",      # Góc dưới trái
    "bottom-right",     # Góc dưới phải  
    "top-left",         # Góc trên trái       
    "bottom-center",    # Dưới cùng giữa
    "top-center-edge",  # Trên cùng sát mép 
    "left-center",      # Giữa bên trái
]

BACKGROUND_SHAPES = [
    "auto-fit-box",      
    "rounded-rectangle",
    "rectangle",
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
# --- CẤU HÌNH CHO DRIVE SHEET ---
PREFERRED_WORKBOOK_NAME = "data.xlsx"
SHEET_DRIVE_MANIFEST_FILE = "sheet_drive_manifest.json"

SECTION_CONFIG = {
    "cafe": {},
    "quan_an": {},
    "khu_du_lich": {},
    "dia_diem_lich_su": {},
}

# ============================================================
# HÀM XỬ LÝ HYPERLINK VÀ DRIVE SHEET
# ============================================================
def read_all_sheets_from_url(sheet_url: str, api_key: str = None) -> Dict[str, pd.DataFrame]:
    """
    Đọc TẤT CẢ sheet từ Google Sheets URL công khai
    Dùng API v4 (không cần API key nếu sheet public)
    """
    try:
        # Lấy sheet_id từ URL
        sheet_id_match = re.search(r'/d/([a-zA-Z0-9_-]+)', sheet_url)
        if not sheet_id_match:
            st.error("❌ Không tìm thấy Sheet ID")
            return {}
        
        sheet_id = sheet_id_match.group(1)
        
        # Dùng Sheets API v4 để lấy danh sách sheet
        # Nếu có API key thì dùng, không thì thử public
        if api_key:
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}?key={api_key}&fields=sheets.properties.title"
        else:
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}?fields=sheets.properties.title"
        
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            sheets_info = data.get('sheets', [])
            
            all_sheets = {}
            for sheet_info in sheets_info:
                sheet_title = sheet_info.get('properties', {}).get('title', '')
                if sheet_title:
                    # Đọc từng sheet qua CSV export
                    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_title}"
                    try:
                        df = pd.read_csv(csv_url)
                        if not df.empty:
                            all_sheets[sheet_title] = df
                    except Exception as e:
                        st.warning(f"⚠️ Không đọc được sheet {sheet_title}: {e}")
            
            return all_sheets
        else:
            # Fallback: thử dùng CSV export trực tiếp với GID mặc định
            return read_sheets_by_common_gids(sheet_id)
            
    except Exception as e:
        st.warning(f"Không thể lấy danh sách sheet: {e}")
        # Thử fallback với GID phổ biến
        sheet_id_match = re.search(r'/d/([a-zA-Z0-9_-]+)', sheet_url)
        if sheet_id_match:
            return read_sheets_by_common_gids(sheet_id_match.group(1))
        return {}

def read_sheets_by_common_gids(sheet_id: str) -> Dict[str, pd.DataFrame]:
    """Đọc các sheet với GID phổ biến (dựa trên file mẫu của bạn)"""
    
    # Dựa trên file F&B ĐÀ LẠT.xlsx của bạn
    sheets_gid = {
        "Quan_an": "1236724598",
        "Cafe": "1062172898",  
        "Homestay": "1688708876",
        "Check_in": "1314951520",
        "Khu_du_lich": "546059515",
        "Dich_vu": "2955938",
        "Luu_y": "775578108",
        "Choi_dem": "409330830",
        "Hoat_dong": "1481016770"
    }
    
    all_sheets = {}
    for sheet_name, gid in sheets_gid.items():
        try:
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
            df = pd.read_csv(csv_url)
            if not df.empty:
                all_sheets[sheet_name] = df
                print(f"✅ Đã đọc sheet {sheet_name}: {len(df)} dòng")
        except Exception as e:
            print(f"⚠️ Không đọc được sheet {sheet_name}: {e}")
    
    return all_sheets
def normalize_text(text: str) -> str:
    """Chuẩn hóa text để dùng làm key"""
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize('NFKC', text).strip().lower()
    text = re.sub(r'[^\w\s]', '', text)
    return re.sub(r'\s+', ' ', text).strip()

def extract_drive_file_id_from_url(url: str) -> Optional[str]:
    """Trích xuất file ID từ Google Drive URL"""
    if not url:
        return None
    
    # Pattern cho drive.google.com
    patterns = [
        r'/file/d/([a-zA-Z0-9_-]+)',
        r'id=([a-zA-Z0-9_-]+)',
        r'/uc\?id=([a-zA-Z0-9_-]+)',
        r'/open\?id=([a-zA-Z0-9_-]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    # Nếu URL trực tiếp là file ID
    if re.match(r'^[a-zA-Z0-9_-]{25,}$', url):
        return url
    
    return None

def is_likely_link_header(header: str) -> bool:
    """Kiểm tra header có khả năng chứa link không"""
    link_keywords = ['link', 'url', 'drive', 'hinh', 'anh', 'image', 'photo', 'picture']
    header_lower = header.lower()
    return any(keyword in header_lower for keyword in link_keywords)

def first_value(row: dict, *keys) -> str:
    """Lấy giá trị đầu tiên tìm thấy từ các keys"""
    for key in keys:
        value = row.get(key)
        if value and isinstance(value, str) and value.strip():
            return value.strip()
    return ""

def preferred_image_link(row: dict) -> str:
    """Tìm link ảnh ưu tiên từ row"""
    priority_columns = [
        'link_drive', 'link_anh', 'link_hinh', 'link_hinh_anh',
        'hinh_anh', 'image_link', 'image_url', 'photo_link', 'picture_link'
    ]
    
    for col in priority_columns:
        # Kiểm tra cả hyperlink và value thường
        if col in row:
            value = row[col]
            if value and isinstance(value, str) and value.strip():
                # Kiểm tra nếu là hyperlink object
                if hasattr(value, 'startswith') and value.startswith('http'):
                    return value
    
    return ""

def workbook_rows_with_links(sheet):
    """Đọc rows từ sheet, xử lý hyperlinks"""
    if not sheet:
        return []
    
    rows = []
    if hasattr(sheet, 'get_rows'):
        # Đối với openpyxl
        for row in sheet.iter_rows(values_only=False):
            row_data = {}
            for cell in row:
                if cell.value:
                    col_name = cell.column_letter
                    # Kiểm tra hyperlink
                    if cell.hyperlink:
                        row_data[col_name] = cell.hyperlink.target
                        row_data[f"{col_name}__hyperlink"] = cell.hyperlink.target
                    else:
                        row_data[col_name] = cell.value
            if row_data:
                rows.append(row_data)
    else:
        # Đối với xlrd hoặc dict
        for row in sheet:
            if isinstance(row, dict):
                rows.append(row)
            else:
                rows.append({})
    
    return rows

async def resolve_drive_link_to_entries(drive_link: str, name: str, address: str, drive_api_key: str) -> List[dict]:
    """Resolve drive link thành thông tin ảnh"""
    file_id = extract_drive_file_id_from_url(drive_link)
    if not file_id:
        return []
    
    try:
        # Gọi API để lấy thông tin file
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
        params = {
            "key": drive_api_key,
            "fields": "id, name, mimeType, webContentLink, size"
        }
        
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            file_info = response.json()
            
            # Kiểm tra nếu là folder
            if file_info.get('mimeType') == 'application/vnd.google-apps.folder':
                # Lấy danh sách ảnh trong folder
                return await list_files_in_drive_folder(file_id, drive_api_key)
            else:
                # Là file đơn
                return [{
                    'fileId': file_id,
                    'fileName': file_info.get('name', 'unknown'),
                    'mimeType': file_info.get('mimeType', ''),
                    'webContentLink': file_info.get('webContentLink', ''),
                    'size': file_info.get('size', 0)
                }]
    except Exception as e:
        print(f"Lỗi resolve drive link: {e}")
    
    return []

async def list_files_in_drive_folder(folder_id: str, api_key: str) -> List[dict]:
    """Lấy danh sách file trong folder Drive"""
    url = "https://www.googleapis.com/drive/v3/files"
    params = {
        "q": f"'{folder_id}' in parents and trashed = false and (mimeType contains 'image/')",
        "key": api_key,
        "fields": "files(id, name, mimeType, webContentLink)",
        "pageSize": 100
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            files = response.json().get('files', [])
            return [{
                'fileId': f['id'],
                'fileName': f['name'],
                'mimeType': f.get('mimeType', ''),
                'webContentLink': f.get('webContentLink', '')
            } for f in files]
    except Exception as e:
        print(f"Lỗi list folder: {e}")
    
    return []

def read_sheet_from_url(sheet_url: str) -> Optional[pd.DataFrame]:
    """
    Đọc dữ liệu từ một Google Sheet công khai (Anyone with the link can view)
    Không cần API key.
    """
    try:
        # --- Bước 1: Lấy Sheet ID và GID từ URL ---
        # Tìm sheet ID (dãy ký tự dài trong URL)
        sheet_id_match = re.search(r'/d/([a-zA-Z0-9_-]+)', sheet_url)
        if not sheet_id_match:
            st.error("❌ Không tìm thấy Sheet ID trong URL. Vui lòng kiểm tra lại link.")
            return None
        
        sheet_id = sheet_id_match.group(1)
        
        # Tìm GID (tab ID). Nếu không có, mặc định là 0 (sheet đầu tiên)
        gid_match = re.search(r'gid=([0-9]+)', sheet_url)
        gid = gid_match.group(1) if gid_match else "0"

        # --- Bước 2: Tạo URL xuất CSV ---
        # Cấu trúc URL CSV export chuẩn từ Google
        csv_export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        
        # --- Bước 3: Đọc dữ liệu bằng pandas ---
        # pandas hoàn toàn có thể đọc trực tiếp từ một URL
        df = pd.read_csv(csv_export_url)
        
        return df
        
    except Exception as e:
        st.error(f"❌ Đã xảy ra lỗi khi đọc Google Sheet: {e}")
        st.info("💡 Hãy chắc chắn rằng sheet của bạn đã được chia sẻ ở chế độ 'Anyone with the link can view'")
        return None

def build_sheet_drive_manifest(workbook_path: str, drive_api_key: str) -> dict:
    """Xây dựng manifest từ workbook và drive links"""
    items = {}
    
    # Đọc file Excel
    if workbook_path.endswith('.csv'):
        df = pd.read_csv(workbook_path)
        sheets = {'Sheet1': df}
    else:
        sheets = pd.read_excel(workbook_path, sheet_name=None)
    
    for sheet_name, df in sheets.items():
        section_key = normalize_text(sheet_name)
        
        for idx, row in df.iterrows():
            # Lấy tên địa điểm
            name = None
            for col in ['ten_quan', 'ten_dia_diem', 'ten', 'name']:
                if col in df.columns and pd.notna(row[col]):
                    name = str(row[col])
                    break
            
            if not name:
                continue
            
            # Lấy địa chỉ
            address = ""
            for col in ['dia_chi', 'address', 'địa chỉ']:
                if col in df.columns and pd.notna(row[col]):
                    address = str(row[col])
                    break
            
            # Lấy link ảnh
            image_link = preferred_image_link(row.to_dict())
            if not image_link:
                # Thử tìm trong các cột khác
                for col in df.columns:
                    if is_likely_link_header(col) and pd.notna(row[col]):
                        image_link = str(row[col])
                        break
            
            if not image_link:
                continue
            
            # Resolve link drive
            file_id = extract_drive_file_id_from_url(image_link)
            if file_id:
                key = f"{section_key}_{normalize_text(name)}_{normalize_text(address)}"
                items[key] = {
                    'key': key,
                    'sectionKey': section_key,
                    'name': name,
                    'address': address,
                    'sourceLink': image_link,
                    'fileId': file_id,
                    'fileName': f"{name}.jpg"
                }
    
    return {
        'version': 1,
        'generatedAt': datetime.now().isoformat(),
        'workbookName': os.path.basename(workbook_path),
        'workbookMtimeMs': os.path.getmtime(workbook_path) * 1000 if os.path.exists(workbook_path) else 0,
        'items': items
    }
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
    """Gợi ý font dựa trên phong cách"""
    if not style_value or pd.isna(style_value):
        return "Be Vietnam Pro"
    
    style_lower = style_value.lower().strip()
    
    style_font_map = {
        "vintage": "Patrick Hand", "cổ điển": "Patrick Hand",
        "sang trọng": "Montserrat", "châu âu": "Montserrat",
        "hiện đại": "Poppins", "tối giản": "Lexend",
        "dễ thương": "Gochi Hand", "trẻ trung": "Mali",
        "chill": "Caveat", "thư giãn": "Kalam",
        "độc đáo": "Outfit", "năng động": "Patrick Hand",
        "mộc mạc": "Nunito",
    }
    
    for key, font_name in style_font_map.items():
        if key in style_lower:
            return font_name
    
    return "Be Vietnam Pro"
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
# Đường dẫn lưu font đã tải
FONT_CACHE_DIR = os.path.join(TEMP_DIR, "fonts")
os.makedirs(FONT_CACHE_DIR, exist_ok=True)
def download_google_font(font_name: str) -> Optional[str]:
    """Tải font từ Google Fonts về máy"""
    # Kiểm tra font Việt hóa (dùng font hệ thống)
    if font_name in ["Sugiono Việt hóa", "Be Vietnam Pro"]:
        # Tìm font hệ thống hỗ trợ tiếng Việt
        for path in FONT_PATHS:
            if os.path.exists(path):
                return path
        return None
    
    if font_name not in FONT_DOWNLOAD_URLS:
        return None
    
    font_url = FONT_DOWNLOAD_URLS.get(font_name)
    if not font_url:
        return None
        
    safe_name = re.sub(r'[^\w\-_]', '_', font_name)
    font_path = os.path.join(FONT_CACHE_DIR, f"{safe_name}.ttf")
    
    if os.path.exists(font_path):
        return font_path
    
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
    """Lấy font nghệ thuật - ƯU TIÊN FONT HỖ TRỢ TIẾNG VIỆT"""
    
    # DANH SÁCH FONT HỖ TRỢ TIẾNG VIỆT TỐT
    vietnamese_friendly_fonts = [
        "Sugiono Việt hóa", "Be Vietnam Pro", "Arial", "Calibri", 
        "Tahoma", "Verdana", "Times New Roman"
    ]
    
    # Font Việt hóa - dùng font hệ thống (HỖ TRỢ TIẾNG VIỆT)
    viet_fonts = ["Sugiono Việt hóa", "Be Vietnam Pro"]
    if font_name in viet_fonts or font_name in vietnamese_friendly_fonts:
        for path in FONT_PATHS:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except:
                    pass
        return load_font(size)
    
    # Font Google Fonts (CÓ THỂ KHÔNG HỖ TRỢ TIẾNG VIỆT)
    # Chỉ dùng cho tên quán không dấu hoặc chữ in hoa
    font_path = download_google_font(font_name)
    if font_path:
        try:
            # Thử tải font
            font = ImageFont.truetype(font_path, size)
            return font
        except:
            pass
    
    # Fallback về font hệ thống
    return load_font_safe(size)

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
    "Cafe Đà Lạt - Nơi giao thoa giữa ẩm thực và nghệ thuật",

    "Đà Lạt và những quán cafe đẹp đến mức chẳng muốn rời đi",
    "Lạc bước vào thiên đường cafe giữa lòng Đà Lạt mộng mơ",
    "Những quán cafe ở Đà Lạt khiến trái tim rung động ngay từ ánh nhìn đầu tiên",
    "Cafe Đà Lạt – nơi mỗi góc nhỏ đều là một khung hình nghệ thuật",
    "Chạm vào bình yên tại những quán cafe đẹp nhất Đà Lạt",
    "Đà Lạt có gì? Có những quán cafe đẹp như bước ra từ giấc mơ",
    "Chill hết nấc cùng những quán cafe “gây nghiện” ở Đà Lạt",
    "Những chiếc cafe mang linh hồn của Đà Lạt mờ sương",
    "Săn mây, ngắm hoàng hôn và thưởng cafe tại Đà Lạt",
    "Top quán cafe Đà Lạt khiến dân sống ảo mê mẩn quên lối về",
    "Cafe Đà Lạt – nơi thanh xuân được lưu giữ trong từng bức ảnh",
    "Một ngày ở Đà Lạt, ngồi cafe thôi cũng đủ hạnh phúc",
    "Đến Đà Lạt mà chưa ghé những quán cafe này thì thật tiếc",
    "Đà Lạt dịu dàng hơn qua ô cửa những quán cafe xinh xắn",
    "Khám phá những quán cafe “đốn tim” du khách tại Đà Lạt",
    "Ngồi giữa mây trời Đà Lạt, nhâm nhi một tách cafe nóng",
    "Những quán cafe mang vẻ đẹp rất riêng chỉ Đà Lạt mới có",
    "Cafe Đà Lạt – nơi mọi cảm xúc đều trở nên nhẹ nhàng",
    "Cùng nhau đi trốn tại những quán cafe cực chill ở Đà Lạt",
    "Từ vintage đến hiện đại – những quán cafe đẹp quên lối ở Đà Lạt",
    "Đà Lạt và hành trình chữa lành bắt đầu từ một quán cafe nhỏ",
    "Những tọa độ cafe đẹp mê hoặc giữa phố núi Đà Lạt",
    "Ghé Đà Lạt để tìm lại bình yên trong những quán cafe thơ mộng",
    "Không chỉ là cafe, đó còn là trải nghiệm rất Đà Lạt",
    "Đà Lạt – thành phố của những quán cafe đẹp hơn cả lời kể",
    "Mỗi quán cafe ở Đà Lạt là một câu chuyện đầy chất thơ",
    "Cafe Đà Lạt – nơi thời gian như chậm lại giữa mây trời",
    "Check-in những quán cafe hot nhất Đà Lạt dành cho tín đồ sống ảo",
    "Đi Đà Lạt chỉ để ngồi cafe và ngắm cả bầu trời bình yên",
    "Những quán cafe khiến Đà Lạt trở thành thành phố đáng nhớ nhất thanh xuân"
]
def get_safe_vietnamese_font(font_name: str, size: int) -> ImageFont.FreeTypeFont:
    """Lấy font - TẤT CẢ FONT ĐỀU HỖ TRỢ TIẾNG VIỆT"""
    
    # Font Be Vietnam Pro dùng hệ thống
    if font_name == "Be Vietnam Pro":
        for path in FONT_PATHS:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except:
                    pass
        return load_font(size)
    
    # Font hệ thống dự phòng
    system_fonts = ["Arial", "Calibri", "Tahoma", "Verdana"]
    if font_name in system_fonts:
        for path in FONT_PATHS:
            if os.path.exists(path) and font_name.lower() in path.lower():
                try:
                    return ImageFont.truetype(path, size)
                except:
                    continue
        return load_font(size)
    
    # Các font còn lại tải từ Google Fonts
    font_path = download_google_font(font_name)
    if font_path:
        try:
            return ImageFont.truetype(font_path, size)
        except:
            pass
    
    # Fallback
    return load_font_safe(size)

# Cache font đã tải
FONT_CACHE = {}

@lru_cache(maxsize=20)
def get_cached_font(font_name: str, size: int) -> ImageFont.FreeTypeFont:
    """Lấy font với cache"""
    cache_key = f"{font_name}_{size}"
    if cache_key in FONT_CACHE:
        return FONT_CACHE[cache_key]
    
    font = get_safe_vietnamese_font(font_name, size)
    FONT_CACHE[cache_key] = font
    return font


def load_font_safe(size: int, font_path: str = None) -> ImageFont.FreeTypeFont:
    """Load font an toàn với fallback"""
    try:
        if font_path and os.path.exists(font_path):
            return ImageFont.truetype(font_path, size)
        
        for path in FONT_PATHS:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except:
                    continue
        
        fallback = download_fallback_font()
        if fallback:
            return ImageFont.truetype(fallback, size)
    except:
        pass
    
    return ImageFont.load_default()

def process_and_save_image(img, ten, gio, dc, target_size, layout_config, color_theme, font_path, font_scale, artistic_font, font_style, highlight_color, jpeg_quality):
    """Xử lý ảnh và giải phóng bộ nhớ"""
    try:
        banner = add_text_with_layout(
            img, ten, gio, dc, target_size,
            layout_config, color_theme,
            font_path=font_path,
            font_scale=font_scale,
            artistic_font=artistic_font,
            font_style=font_style,
            highlight_color=highlight_color
        )
        
        buf = io.BytesIO()
        banner.save(buf, format='JPEG', quality=jpeg_quality, optimize=True)
        
        img.close()
        banner.close()
        del img, banner
        gc.collect()
        
        return buf
    except Exception as e:
        st.warning(f"⚠️ Lỗi ảnh {ten}: {e}")
        return None
# --- HÀM TIỆN ÍCH ---
def normalize_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize('NFKC', text).strip().lower()
    text = re.sub(r'[^\w\s]', '', text)
    return re.sub(r'\s+', ' ', text).strip()


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
    elif shape_type == "auto-fit-box":
        # Shape tự động co giãn theo text - LỰA CHỌN TỐT NHẤT
        # Vẽ hình chữ nhật bo góc với viền đẹp
        draw.rounded_rectangle([x1, y1, x2, y2], radius=30, fill=color_theme["bg"])
        # Thêm viền sáng
        draw.rounded_rectangle([x1+3, y1+3, x2-3, y2-3], radius=27, 
                            outline=(255,255,255,80), width=2)

    elif shape_type == "speech-bubble":
        # Bong bóng thoại - text luôn nằm gọn
        draw.rounded_rectangle([x1, y1, x2, y2], radius=25, fill=color_theme["bg"])
        # Thêm đuôi bong bóng
        tail_x = x1 + 30
        tail_y = y2
        points = [(tail_x, tail_y), (tail_x-15, tail_y+20), (tail_x+15, tail_y+20)]
        draw.polygon(points, fill=color_theme["bg"])
    else:
        # Mặc định là hình chữ nhật bo góc
        draw.rounded_rectangle([x1, y1, x2, y2], radius=20, fill=color_theme["bg"])

COLOR_THEMES = [
    {"name": "Đỏ Đen", "primary": "#0A0909DE", "secondary": "#FFFFFF", "bg": (10, 9, 9, 222), "text_light": True},  # Đỏ
    {"name": "Vàng Trắng", "primary": "#79734AFF", "secondary": "#000000", "bg": (121, 115, 74, 255), "text_light": False},  # Vàng
    {"name": "Cam Trắng", "primary": "#A75584", "secondary": "#000000", "bg": (167, 85, 132), "text_light": False},  # Cam
    {"name": "Xanh Dương", "primary": "#9EC7E9CE", "secondary": "#FFD700", "bg": (24, 132, 121, 200), "text_light": True},
    {"name": "Đỏ Rượu", "primary": "#440419", "secondary": "#FFD700", "bg": (69, 3, 25, 200), "text_light": True},
    {"name": "Xanh Rêu", "primary": "#023503", "secondary": "#FFD700", "bg": (2, 53, 3, 200), "text_light": True},
    {"name": "Nâu Gỗ", "primary": "#563705C2", "secondary": "#FFD700", "bg": (86, 55, 5, 194), "text_light": True},
     {"name": "Nâu Gỗ", "primary": "#1F2937", "secondary": "#FFD700", "bg": (31, 41, 55), "text_light": True},
]
def add_text_with_layout(image_pil, ten, gio, dc, target_size, layout_config, color_theme, font_path=None, font_scale=1.0, artistic_font=None, font_style="Bình thường", highlight_color=None):
    """
    Thêm text vào ảnh - KHÔNG TEXTBOX, có SHADOW EFFECT
    """
    try:
        # Resize ảnh
        img = ImageOps.fit(image_pil.convert("RGB"), target_size, centering=(0.5, 0.5))
        img = img.convert("RGBA")
        
        draw = ImageDraw.Draw(img)
        
        width, height = img.size
        scale_factor = (target_size[0] / 900.0) * font_scale * 0.5  # Tăng scale_factor
        
        # Xử lý ten_text
        if font_style == "In hoa toàn bộ":
            ten_text = ten.upper()
        elif font_style == "Viết hoa chữ cái đầu":
            ten_text = ten.title()
        else:
            ten_text = ten.upper()
        
        # TĂNG KÍCH THƯỚC FONT
        base_size_ten = 55 * scale_factor
        adjusted_size_ten = adjust_font_size_by_length(base_size_ten, ten_text, min_size=28, max_size=int(base_size_ten))
        font_size_ten = max(28, int(adjusted_size_ten))
        
        base_size_info = 45 * scale_factor
        adjusted_size_info = adjust_font_size_by_length(base_size_info, gio, min_size=22, max_size=int(base_size_info))
        font_size_info = max(22, int(adjusted_size_info))
        
        # Tải font
        if artistic_font:
            font_ten = get_cached_font(artistic_font, font_size_ten)
            font_info = get_cached_font(artistic_font, font_size_info)
        else:
            font_ten = load_font_safe(font_size_ten, font_path)
            font_info = load_font_safe(font_size_info, font_path)
        
        measure_font_ten = load_font_safe(font_size_ten)
        measure_font_info = load_font_safe(font_size_info)
        
        position = layout_config.get("position", "bottom-left")
        base_margin = int(40 * scale_factor)
        
        gio_text = f"Giờ mở cửa: {gio}"
        
        # Xử lý địa chỉ xuống dòng
        max_dc_width = width * 0.45
        dc_lines = []
        current_line = ""
        words = dc.split()
        for word in words:
            test_line = current_line + " " + word if current_line else word
            test_bbox = draw.textbbox((0, 0), test_line, font=measure_font_info)
            test_width = test_bbox[2] - test_bbox[0]
            if test_width <= max_dc_width:
                current_line = test_line
            else:
                if current_line:
                    dc_lines.append(current_line)
                current_line = word
        if current_line:
            dc_lines.append(current_line)
        
        # Đo kích thước
        ten_bbox = draw.textbbox((0, 0), ten_text, font=measure_font_ten)
        ten_width = ten_bbox[2] - ten_bbox[0]
        ten_height = ten_bbox[3] - ten_bbox[1]
        
        gio_bbox = draw.textbbox((0, 0), gio_text, font=measure_font_info)
        gio_width = gio_bbox[2] - gio_bbox[0]
        gio_height = gio_bbox[3] - gio_bbox[1]
        
        dc_line_widths = []
        dc_line_heights = []
        for line in dc_lines:
            line_bbox = draw.textbbox((0, 0), line, font=measure_font_info)
            dc_line_widths.append(line_bbox[2] - line_bbox[0])
            dc_line_heights.append(line_bbox[3] - line_bbox[1])
        dc_max_width = max(dc_line_widths) if dc_line_widths else 0
        
        pin_size = int(28 * scale_factor)
        line_spacing = int(25 * scale_factor)
        
        total_height = ten_height + gio_height + (len(dc_lines) * (font_size_info + 10)) + (line_spacing * 2)
        max_width = max(ten_width, gio_width, dc_max_width + pin_size) + 50
        
        margin = 60
        
        # Xác định vị trí
        if position == "bottom-left":
            x = margin
            y = height - total_height - margin
        elif position == "bottom-right":
            x = width - max_width - margin
            y = height - total_height - margin
        elif position == "top-left":
            x = margin
            y = margin
        elif position == "bottom-center":
            x = (width - max_width) // 2
            y = height - total_height - margin
        elif position == "top-center-edge":
            x = (width - max_width) // 2
            y = margin
        elif position == "left-center":
            x = margin
            y = (height - total_height) // 2
        else:
            x = margin
            y = height - total_height - margin
        
        x = max(20, min(x, width - max_width - 20))
        y = max(20, min(y, height - total_height - 20))
        
        # === HÀM VẼ TEXT CÓ SHADOW ===
        def draw_text_with_shadow(draw, xy, text, fill, font, shadow_offset=(4, 4), shadow_color="#000000"):
            """Vẽ text có bóng đổ"""
            x, y = xy
            offset_x, offset_y = shadow_offset
            
            # Vẽ shadow (bóng) trước
            draw.text(
                (x + offset_x, y + offset_y),
                text,
                fill=shadow_color,
                font=font
            )
            # Vẽ thêm shadow nhẹ ở góc đối diện để tạo hiệu ứng mờ
            draw.text(
                (x + offset_x - 2, y + offset_y - 2),
                text,
                fill=shadow_color,
                font=font
            )
            # Vẽ text chính
            draw.text(
                (x, y),
                text,
                fill=fill,
                font=font
            )
        
        def draw_text_with_stroke_and_shadow(draw, xy, text, fill, font, stroke_width=4, stroke_color="#000000", shadow_offset=(4, 4)):
            """Vẽ text có viền và bóng đổ"""
            x, y = xy
            offset_x, offset_y = shadow_offset
            
            # 1. Vẽ shadow
            draw.text((x + offset_x, y + offset_y), text, fill="#000000", font=font)
            draw.text((x + offset_x - 2, y + offset_y - 2), text, fill="#000000", font=font)
            
            # 2. Vẽ viền
            for off_x in range(-stroke_width, stroke_width + 1):
                for off_y in range(-stroke_width, stroke_width + 1):
                    if off_x == 0 and off_y == 0:
                        continue
                    draw.text((x + off_x, y + off_y), text, fill=stroke_color, font=font)
            
            # 3. Vẽ viền nhẹ lớp 2
            for off_x in range(-2, 3):
                for off_y in range(-2, 3):
                    if off_x == 0 and off_y == 0:
                        continue
                    draw.text((x + off_x, y + off_y), text, fill=stroke_color, font=font)
            
            # 4. Vẽ text chính
            draw.text((x, y), text, fill=fill, font=font)
        
        current_y = y
        
        # === Tên quán - CÓ SHADOW ===
        draw_text_with_stroke_and_shadow(
            draw, (x, current_y), ten_text, 
            fill="#FFFFFF", 
            font=font_ten, 
            stroke_width=0, 
            stroke_color="#000000",
            shadow_offset=(5, 5)
        )
        current_y += ten_height + line_spacing
        
        # === Giờ mở cửa - CÓ SHADOW ===
        draw_text_with_stroke_and_shadow(
            draw, (x, current_y), gio_text, 
            fill="#FFD700", 
            font=font_info, 
            stroke_width=0, 
            stroke_color="#000000",
            shadow_offset=(4, 4)
        )
        current_y += gio_height + line_spacing
        
        # === Địa chỉ - CÓ SHADOW ===
        for i, line in enumerate(dc_lines):
            line_height = dc_line_heights[i]
            if i == 0:
                # Vẽ icon pin
                pin_x = x
                pin_y = current_y + (line_height - pin_size) // 2
                draw_location_pin(draw, pin_x, pin_y, size=pin_size, color_theme=color_theme)
                # Vẽ text địa chỉ với shadow
                draw_text_with_stroke_and_shadow(
                    draw, (pin_x + pin_size + 12, current_y), line, 
                    fill="#E0E0E0", 
                    font=font_info, 
                    stroke_width=0, 
                    stroke_color="#000000",
                    shadow_offset=(3, 3)
                )
            else:
                indent = pin_size + 20
                draw_text_with_stroke_and_shadow(
                    draw, (x + indent, current_y), line, 
                    fill="#E0E0E0", 
                    font=font_info, 
                    stroke_width=0, 
                    stroke_color="#000000",
                    shadow_offset=(3, 3)
                )
            current_y += line_height + 12
        
        return img.convert("RGB")
        
    except Exception as e:
        print(f"Lỗi trong add_text_with_layout: {e}")
        import traceback
        traceback.print_exc()
        img = ImageOps.fit(image_pil.convert("RGB"), target_size, centering=(0.5, 0.5))
        return img

def draw_curved_text(draw, text, center_x, center_y, radius, font, start_angle=-90, color="#FFFFFF", stroke_color="#000000", stroke_width=3, arc_direction=-1):
    """
    Vẽ chữ cong theo vòng tròn
    
    Args:
        draw: ImageDraw object
        text: Chuỗi text cần vẽ
        center_x, center_y: Tâm của vòng tròn
        radius: Bán kính cong (càng nhỏ càng cong nhiều)
        font: Font chữ
        start_angle: Góc bắt đầu (độ)
        color: Màu chữ
        stroke_color: Màu viền
        stroke_width: Độ dày viền
        arc_direction: -1 = cong lên trên, 1 = cong xuống dưới
    """
    # Đo tổng chiều rộng của text
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    char_width = text_width / len(text)
    
    # Tính góc cho mỗi ký tự
    total_angle = 180  # Góc trải dài (độ)
    angle_per_char = total_angle / len(text)
    
    current_angle = start_angle
    for i, char in enumerate(text):
        # Tính vị trí cho từng ký tự
        angle_rad = math.radians(current_angle)
        
        # Tính tọa độ trên đường tròn
        x = center_x + radius * math.cos(angle_rad)
        y = center_y + radius * math.sin(angle_rad)
        
        # Tính góc xoay cho ký tự (tiếp tuyến với đường tròn)
        char_angle = math.degrees(math.atan2(
            math.sin(angle_rad), 
            math.cos(angle_rad)
        )) + 90
        
        # Tạo ảnh cho từng ký tự
        char_img = Image.new('RGBA', (font.size + 20, font.size + 20), (0, 0, 0, 0))
        char_draw = ImageDraw.Draw(char_img)
        
        # Vẽ ký tự có viền
        char_draw.text((10, 10), char, fill=color, font=font,
                      stroke_width=stroke_width, stroke_fill=stroke_color)
        
        # Xoay ký tự
        char_img = char_img.rotate(char_angle, expand=True, resample=Image.BICUBIC)
        
        # Dán lên ảnh chính
        draw.im.paste(char_img, (int(x - char_img.width//2), int(y - char_img.height//2)), char_img)
        
        # Tăng góc cho ký tự tiếp theo
        current_angle += angle_per_char * arc_direction

def draw_curved_text_arc(draw, text, center_x, center_y, radius, font, color="#FFFFFF", stroke_color="#000000", stroke_width=3):
    """
    Vẽ chữ cong hình vòng cung (phổ biến cho banner)
    """
    total_chars = len(text)
    angle_range = 140  # Độ trải dài của cung
    start_angle = -70  # Góc bắt đầu (từ trái sang phải)
    
    for i, char in enumerate(text):
        # Tính góc cho ký tự
        angle = start_angle + (i / max(1, total_chars - 1)) * angle_range
        angle_rad = math.radians(angle)
        
        # Tọa độ trên đường tròn
        x = center_x + radius * math.cos(angle_rad)
        y = center_y + radius * math.sin(angle_rad)
        
        # Góc xoay (vuông góc với bán kính)
        rot_angle = angle + 90
        
        # Tạo và xoay ký tự
        char_img = Image.new('RGBA', (font.size + 30, font.size + 30), (0, 0, 0, 0))
        char_draw = ImageDraw.Draw(char_img)
        
        # Vẽ ký tự với viền
        char_draw.text((15, 15), char, fill=color, font=font,
                      stroke_width=stroke_width, stroke_fill=stroke_color)
        
        char_img = char_img.rotate(rot_angle, expand=True, resample=Image.BICUBIC)
        
        # Dán lên ảnh
        paste_x = int(x - char_img.width//2)
        paste_y = int(y - char_img.height//2)
        
        # Đảm bảo không bị tràn
        if 0 <= paste_x < draw.im.width and 0 <= paste_y < draw.im.height:
            draw.im.paste(char_img, (paste_x, paste_y), char_img)
def add_curved_text_simple(img, text, center_x, center_y, font_size, color, stroke_color="#000000"):
    """Cách đơn giản: tạo từng chữ và xoay"""
    from PIL import Image, ImageDraw, ImageFont
    
    draw = ImageDraw.Draw(img)
    font = load_font(font_size)
    
    radius = 200  # Bán kính cong
    total = len(text)
    
    for i, char in enumerate(text):
        # Tính góc
        angle = -60 + (i / (total - 1)) * 120 if total > 1 else 0
        rad = math.radians(angle)
        
        # Vị trí
        x = center_x + radius * math.cos(rad)
        y = center_y + radius * math.sin(rad)
        
        # Góc xoay
        rot = angle + 90
        
        # Tạo ảnh tạm cho ký tự
        temp = Image.new('RGBA', (font_size + 20, font_size + 20), (0, 0, 0, 0))
        temp_draw = ImageDraw.Draw(temp)
        temp_draw.text((10, 10), char, fill=color, font=font,
                      stroke_width=3, stroke_fill=stroke_color)
        
        # Xoay
        temp = temp.rotate(rot, expand=True)
        
        # Dán lên ảnh chính
        img.paste(temp, (int(x - temp.width//2), int(y - temp.height//2)), temp)
    
    return img
def create_cover_image(background_img, quan_list, descriptions, target_size, color_theme, font_path=None, logo_path=None, cover_description=None, artistic_font=None, font_style="Bình thường"):
    """Tạo ảnh bìa cover - CHỮ THẲNG, TRÊN DƯỚI MÀU TRẮNG, ĐÀ LẠT MÀU THEME"""
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

        # Font cho chữ
        if artistic_font:
            font_main = get_safe_vietnamese_font(artistic_font, int(target_size[0] * 0.08))
            font_top = get_safe_vietnamese_font(artistic_font, int(target_size[0] * 0.035))
            font_bottom = get_safe_vietnamese_font(artistic_font, int(target_size[0] * 0.03))
        else:
            font_main = load_font(int(target_size[0] * 0.08), font_path)
            font_top = load_font(int(target_size[0] * 0.035), font_path)
            font_bottom = load_font(int(target_size[0] * 0.03), font_path)

        # Bộ màu
        cover_color_schemes = {
            "Đỏ Đen": {"accent": "#FF4444"},
            "Vàng Trắng": {"accent": "#FFD700"},
            "Xanh Dương": {"accent": "#2196F3"},
            "Đỏ Rượu": {"accent": "#FF4444"},
            "Xanh Rêu": {"accent": "#4CAF50"},
            "Nâu Gỗ": {"accent": "#FF9800"},
            "Cam Trắng": {"accent": "#FF9800"},
            "Hồng Pastel": {"accent": "#E91E63"},
        }
        
        theme_name = color_theme.get("name", "Đỏ Đen")
        cover_colors = cover_color_schemes.get(theme_name, cover_color_schemes["Đỏ Đen"])
        
       # === XỬ LÝ CÂU AI SINH - LẤY 5-6 TỪ ĐẦU CHO PHẦN TRÊN =====
        if cover_description:
            full_text = cover_description
        else:
            full_text = "Khám Phá Đà Lạt Hôm Nay"

        words = full_text.split()

        # Lấy 5-6 từ đầu cho phần trên, còn lại cho dưới
        if len(words) >= 7:
            # Nếu có 7 từ trở lên, lấy 6 từ đầu lên trên
            top_part = " ".join(words[:6])
            bottom_part = " ".join(words[6:])
        elif len(words) >= 6:
            # Nếu có 6 từ, lấy 5 từ đầu lên trên
            top_part = " ".join(words[:5])
            bottom_part = " ".join(words[5:])
        elif len(words) >= 5:
            # Nếu có 5 từ, lấy 4 từ đầu lên trên
            top_part = " ".join(words[:4])
            bottom_part = " ".join(words[4:])
        elif len(words) >= 4:
            # Nếu có 4 từ, lấy 3 từ đầu lên trên
            top_part = " ".join(words[:3])
            bottom_part = " ".join(words[3:])
        elif len(words) >= 3:
            # Nếu có 3 từ, lấy 2 từ đầu lên trên
            top_part = " ".join(words[:2])
            bottom_part = " ".join(words[2:])
        else:
            # Nếu ít hơn 3 từ, tất cả lên trên
            top_part = full_text
            bottom_part = "KHÁM PHÁ ĐÀ LẠT"

        # Đảm bảo phần dưới không bị trống
        if not bottom_part.strip() or len(bottom_part) < 3:
            bottom_part = "KHÁM PHÁ ĐÀ LẠT"
        
        # === TỌA ĐỘ TRUNG TÂM ===
        center_x = target_size[0] // 2
        center_y = target_size[1] // 2
        
        # ===== 1. CHỮ "ĐÀ LẠT" Ở GIỮA (MÀU THEME) =====
        text_main = "ĐÀ LẠT"
        
        main_bbox = draw.textbbox((0, 0), text_main, font=font_main)
        main_w = main_bbox[2] - main_bbox[0]
        main_h = main_bbox[3] - main_bbox[1]
        
        main_x = center_x - main_w // 2
        main_y = center_y - main_h // 2
        
        # Vẽ background cho chữ ĐÀ LẠT
        padding_x = 40
        padding_y = 25
        draw.rounded_rectangle(
            [main_x - padding_x, main_y - padding_y, 
             main_x + main_w + padding_x, main_y + main_h + padding_y],
            radius=30,
            fill=(0, 0, 0, 200),
            outline=cover_colors["accent"],
            width=3
        )
        
        # Vẽ chữ ĐÀ LẠT (màu theme)
        draw.text((main_x + 4, main_y + 4), text_main, fill="#000000", font=font_main)
        draw.text((main_x, main_y), text_main, fill=cover_colors["accent"], font=font_main,
                  stroke_width=2, stroke_fill="#000000")
        
        # ===== 2. CHỮ THẲNG PHÍA TRÊN (MÀU TRẮNG) =====
        text_top = top_part.upper()
        
        # Giới hạn độ dài
        if len(text_top) > 40:
            text_top = text_top[:40]
        
        top_bbox = draw.textbbox((0, 0), text_top, font=font_top)
        top_w = top_bbox[2] - top_bbox[0]
        top_h = top_bbox[3] - top_bbox[1]
        
        # Vị trí phía trên chữ ĐÀ LẠT
        top_x = center_x - top_w // 2
        top_y = main_y - top_h - 50
        
        # Vẽ background cho chữ trên
        draw.rounded_rectangle(
            [top_x - 25, top_y - 15, 
             top_x + top_w + 25, top_y + top_h + 15],
            radius=20,
            fill=(0, 0, 0, 180),
            outline="#FFFFFF",
            width=1
        )
        
        # Vẽ chữ trên (màu trắng)
        draw.text((top_x + 2, top_y + 2), text_top, fill="#000000", font=font_top)
        draw.text((top_x, top_y), text_top, fill="#FFFFFF", font=font_top,
                  stroke_width=1, stroke_fill="#000000")
        
        # ===== 3. CHỮ THẲNG PHÍA DƯỚI (MÀU TRẮNG) =====
        text_bottom = bottom_part.upper()
        
        if len(text_bottom) > 50:
            text_bottom = text_bottom[:47] + "..."
        
        bottom_bbox = draw.textbbox((0, 0), text_bottom, font=font_bottom)
        bottom_w = bottom_bbox[2] - bottom_bbox[0]
        bottom_h = bottom_bbox[3] - bottom_bbox[1]
        
        # Vị trí phía dưới chữ ĐÀ LẠT
        bottom_x = center_x - bottom_w // 2
        bottom_y = main_y + main_h + 60
        
        # Vẽ background cho chữ dưới
        draw.rounded_rectangle(
            [bottom_x - 25, bottom_y - 15, 
             bottom_x + bottom_w + 25, bottom_y + bottom_h + 15],
            radius=20,
            fill=(0, 0, 0, 180),
            outline="#FFFFFF",
            width=1
        )
        
        # Vẽ chữ dưới (màu trắng)
        draw.text((bottom_x + 2, bottom_y + 2), text_bottom, fill="#000000", font=font_bottom)
        draw.text((bottom_x, bottom_y), text_bottom, fill="#FFFFFF", font=font_bottom,
                  stroke_width=1, stroke_fill="#000000")
        
        # Merge layer text với background
        img = Image.alpha_composite(img, text_layer).convert("RGB")
        
        return img

    except Exception as e:
        print(f"Lỗi tạo cover: {e}")
        import traceback
        traceback.print_exc()
        img = Image.new('RGB', target_size, color=(30, 30, 40))
        draw = ImageDraw.Draw(img)
        draw.text((target_size[0]//2, target_size[1]//2), "COVER", 
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
def load_images_from_drive_links_in_sheet(df: pd.DataFrame, drive_api_key: str, folder_col_name: str = None) -> Tuple[Dict[str, List[bytes]], List[bytes]]:
    """
    Đọc link Drive folder từ sheet và tải ảnh về
    
    Args:
        df: DataFrame chứa dữ liệu sheet
        drive_api_key: Google Drive API key
        folder_col_name: Tên cột chứa link Drive (nếu None sẽ tự tìm)
    
    Returns:
        Tuple (image_dict, all_images_list)
        - image_dict: {tên_quán_normalized: [img_bytes, ...]}
        - all_images_list: danh sách tất cả ảnh bytes
    """
    image_dict = {}
    all_images = []
    
    # Tìm cột chứa link Drive
    if folder_col_name is None:
        for col in df.columns:
            col_lower = col.lower()
            if ('link' in col_lower or 'drive' in col_lower or 'folder' in col_lower
                    or 'anh' in col_lower or 'ảnh' in col_lower):
                folder_col_name = col
                break
    
    if folder_col_name is None:
        st.error("❌ Không tìm thấy cột chứa link Drive trong sheet")
        return image_dict, all_images
    
    # Lấy cột tên quán
    ten_col = None
    for col in df.columns:
        if 'ten' in col.lower() or 'name' in col.lower() or 'tên' in col.lower():
            ten_col = col
            break
    
    if ten_col is None:
        st.error("❌ Không tìm thấy cột tên quán")
        return image_dict, all_images
    
    prog = st.progress(0, "Đang tải ảnh từ Drive...")
    
    for idx, row in df.iterrows():
        ten_quan = str(row[ten_col]) if pd.notna(row[ten_col]) else ""
        drive_link = str(row[folder_col_name]) if pd.notna(row[folder_col_name]) else ""
        
        if not ten_quan or not drive_link:
            continue
        
        # Chuẩn hóa tên quán
        normalized_name = normalize_text(ten_quan)
        
        # Trích xuất folder ID
        folder_id = extract_drive_folder_id_from_url(drive_link)
        if not folder_id:
            st.warning(f"⚠️ Không thể lấy folder ID từ link của {ten_quan}")
            continue
        
        # Lấy danh sách ảnh từ folder
        files = list_files_in_drive_folder(folder_id, drive_api_key)
        
        images_for_quan = []
        for file in files:
            if file['mimeType'].startswith('image/'):
                # Tải ảnh về
                img_url = f"https://drive.google.com/uc?export=download&id={file['id']}"
                try:
                    response = requests.get(img_url, timeout=30)
                    if response.status_code == 200:
                        img_bytes = response.content
                        images_for_quan.append(img_bytes)
                        all_images.append(img_bytes)
                except Exception as e:
                    print(f"Lỗi tải ảnh {file['name']}: {e}")
        
        if images_for_quan:
            image_dict[normalized_name] = images_for_quan
            st.info(f"📸 {ten_quan}: Tải {len(images_for_quan)} ảnh")
        
        prog.progress((idx + 1) / len(df))
    
    prog.empty()
    return image_dict, all_images
def download_single_image(file_id: str, file_name: str = "") -> Optional[bytes]:
    """Tải một ảnh đơn lẻ từ Drive"""
    img_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    alt_url = f"https://drive.google.com/uc?export=download&confirm=1&id={file_id}"
    
    for url in [alt_url, img_url]:
        try:
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            response = session.get(url, timeout=15, stream=True)
            if response.status_code == 200:
                return response.content
        except:
            continue
    
    return None

def get_cache_key(folder_id: str) -> str:
    """Tạo cache key từ folder ID"""
    return hashlib.md5(folder_id.encode()).hexdigest()

def load_images_from_drive_links_fast(
    drive_links: Dict[str, str], 
    drive_api_key: str,
    max_workers: int = 15,
    use_cache: bool = True
) -> Tuple[Dict[str, List[bytes]], List[bytes]]:
    """
    Tải ảnh nhanh từ Drive folder với đa luồng
    
    Args:
        drive_links: {tên_quán: drive_folder_url}
        drive_api_key: Google Drive API key
        max_workers: Số luồng tải đồng thời (mặc định 15)
        use_cache: Có dùng cache hay không
    
    Returns:
        Tuple (image_dict, all_images_list)
    """
    image_dict = {}
    all_images = []
    
    if not drive_links:
        return image_dict, all_images
    
    # Tạo progress bar
    progress_container = st.empty()
    progress_bar = progress_container.progress(0)
    status_text = st.empty()
    
    total_quans = len(drive_links)
    processed_quans = 0
    
    # Xử lý từng quán một (tuần tự để không quá tải API)
    for ten_quan, drive_url in drive_links.items():
        folder_id = extract_drive_folder_id_from_url(drive_url)
        if not folder_id:
            status_text.warning(f"⚠️ Không thể lấy folder ID từ link của {ten_quan}")
            continue
        
        # Kiểm tra cache nếu bật
        cache_key = get_cache_key(folder_id)
        cache_path = os.path.join(CACHE_DIR, f"{cache_key}.json")
        
        images_for_quan = []
        
        if use_cache and os.path.exists(cache_path):
            try:
                with open(cache_path, 'r') as f:
                    cache_data = json.load(f)
                
                # Đọc ảnh từ cache
                for img_path in cache_data.get('files', []):
                    full_path = os.path.join(CACHE_DIR, img_path)
                    if os.path.exists(full_path):
                        try:
                            with open(full_path, 'rb') as img_f:
                                img_bytes = img_f.read()
                                images_for_quan.append(img_bytes)
                                all_images.append(img_bytes)
                        except:
                            pass
                
                if images_for_quan:
                    image_dict[ten_quan] = images_for_quan
                    status_text.success(f"✅ {ten_quan}: {len(images_for_quan)} ảnh (từ cache)")
                    processed_quans += 1
                    progress_bar.progress(processed_quans / total_quans)
                    continue
            except:
                pass
        
        # Lấy danh sách file trong folder (nhanh - chỉ 1 API call)
        files = list_files_in_drive_folder(folder_id, drive_api_key)
        
        # Lọc ra các file ảnh
        image_files = [f for f in files if f['mimeType'].startswith('image/')]
        
        if not image_files:
            processed_quans += 1
            progress_bar.progress(processed_quans / total_quans)
            continue
        
        # Tải ảnh song song với ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=min(max_workers, len(image_files))) as executor:
            # Tạo futures cho tất cả ảnh
            future_to_file = {
                executor.submit(download_single_image, f['id'], f.get('name', '')): f
                for f in image_files
            }
            
            # Thu thập kết quả khi hoàn thành
            for future in as_completed(future_to_file):
                file_info = future_to_file[future]
                try:
                    img_bytes = future.result()
                    if img_bytes:
                        images_for_quan.append(img_bytes)
                        all_images.append(img_bytes)
                except Exception as e:
                    pass
        
        # Lưu vào dict và cache
        if images_for_quan:
            image_dict[ten_quan] = images_for_quan
            
            # Lưu vào cache
            if use_cache:
                try:
                    cache_files = []
                    for idx, img_bytes in enumerate(images_for_quan):
                        cache_filename = f"{cache_key}_{idx}.jpg"
                        cache_full_path = os.path.join(CACHE_DIR, cache_filename)
                        with open(cache_full_path, 'wb') as f:
                            f.write(img_bytes)
                        cache_files.append(cache_filename)
                    
                    with open(cache_path, 'w') as f:
                        json.dump({'files': cache_files, 'timestamp': time.time()}, f)
                except:
                    pass
            
            status_text.info(f"📸 {ten_quan}: {len(images_for_quan)}/{len(image_files)} ảnh")
        
        # Cập nhật progress
        processed_quans += 1
        progress_bar.progress(processed_quans / total_quans)
        status_text.text(f"⏳ Đã tải: {processed_quans}/{total_quans} quán")
    
    # Dọn dẹp
    progress_container.empty()
    status_text.empty()
    
    return image_dict, all_images

def load_images_from_drive_links(drive_links: Dict[str, str], drive_api_key: str) -> Tuple[Dict[str, List[bytes]], List[bytes]]:
    """
    Tải ảnh từ các Drive folder (wrapper sử dụng phiên bản đa luồng nhanh)
    
    Args:
        drive_links: {tên_quán_normalized: drive_folder_url}
        drive_api_key: Google Drive API key
    
    Returns:
        Tuple (image_dict, all_images_list)
    """
    # Lấy cấu hình từ session state
    max_workers = getattr(st.session_state, 'max_workers', 15)
    use_cache = getattr(st.session_state, 'use_cache', True)
    
    return load_images_from_drive_links_fast(
        drive_links, 
        drive_api_key,
        max_workers=max_workers,
        use_cache=use_cache
    )
def extract_drive_folder_id_from_url(url: str) -> Optional[str]:
    """Trích xuất folder ID từ Google Drive URL"""
    if not url:
        return None
    
    patterns = [
        r'/folders/([a-zA-Z0-9_-]+)',
        r'id=([a-zA-Z0-9_-]+)',
        r'/drive/folders/([a-zA-Z0-9_-]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None
def read_hyperlink_from_google_sheets(sheet_url: str, sheet_name: str, api_key: str) -> Dict[str, str]:
    """
    Đọc hyperlink từ Google Sheets (lấy URL thực, không phải text hiển thị)
    
    Returns:
        Dict mapping từ tên quán -> drive URL
    """
    try:
        sheet_id_match = re.search(r'/d/([a-zA-Z0-9_-]+)', sheet_url)
        if not sheet_id_match:
            return {}
        
        sheet_id = sheet_id_match.group(1)
        
        # Dùng Google Sheets API v4 để lấy dữ liệu bao gồm cả hyperlink
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{sheet_name}?key={api_key}&valueRenderOption=FORMULA"
        
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            values = data.get('values', [])
            
            if not values:
                return {}
            
            headers = values[0]
            
            # Tìm cột tên quán và cột link
            ten_col_idx = None
            link_col_idx = None
            
            for idx, header in enumerate(headers):
                header_lower = header.lower()
                if 'ten' in header_lower or 'tên' in header_lower or 'name' in header_lower:
                    ten_col_idx = idx
                if ('link' in header_lower or 'drive' in header_lower or 'folder' in header_lower
                        or 'anh' in header_lower or 'ảnh' in header_lower):
                    link_col_idx = idx
            
            if ten_col_idx is None or link_col_idx is None:
                st.warning(f"Không tìm thấy cột tên quán hoặc cột link. Các cột có: {headers}")
                return {}
            
            # Đọc dữ liệu
            drive_links = {}
            for row in values[1:]:
                if len(row) > max(ten_col_idx, link_col_idx):
                    ten_quan = row[ten_col_idx] if ten_col_idx < len(row) else ""
                    link_value = row[link_col_idx] if link_col_idx < len(row) else ""
                    
                    if not ten_quan or not link_value:
                        continue
                    
                    # Xử lý link_value (có thể là HYPERLINK formula)
                    if link_value and link_value.startswith('=HYPERLINK'):
                        match = re.search(r'HYPERLINK\("([^"]+)"', link_value)
                        if match:
                            real_url = match.group(1)
                            drive_links[normalize_text(ten_quan)] = real_url
                    elif link_value and link_value.startswith('http'):
                        drive_links[normalize_text(ten_quan)] = link_value
            
            return drive_links
            
    except Exception as e:
        st.error(f"Lỗi đọc hyperlink: {e}")
        return {}

def read_hyperlink_from_public_sheet_html(sheet_url: str) -> Dict[str, str]:
    """Đọc hyperlink từ Google Sheet công khai qua HTML, hỗ trợ cả sheet import từ Excel."""
    try:
        sheet_id_match = re.search(r'/d/([a-zA-Z0-9_-]+)', sheet_url)
        if not sheet_id_match:
            st.warning("Không tìm thấy Sheet ID trong URL.")
            return {}

        sheet_id = sheet_id_match.group(1)
        gid_match = re.search(r'gid=([0-9]+)', sheet_url)
        gid = gid_match.group(1) if gid_match else '0'
        html_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?gid={gid}&tqx=out:html"

        response = requests.get(html_url, timeout=30)
        if response.status_code != 200:
            st.warning(f"Không thể đọc sheet qua HTML public. HTTP {response.status_code}")
            return {}

        html_text = response.text
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html_text, flags=re.S | re.I)
        if not rows or len(rows) < 2:
            st.warning("Không tìm thấy dữ liệu trong sheet HTML.")
            return {}

        def parse_cell(cell_html: str) -> str:
            # Ưu tiên lấy href từ thẻ <a>
            href_match = re.search(r'<a[^>]+href=["\']([^"\']+)["\']', cell_html, flags=re.I)
            if href_match:
                return href_match.group(1).strip()  # Trả về URL Drive, không phải text hiển thị
            text = re.sub(r'<[^>]+>', '', cell_html)
            return html.unescape(text).strip()

        header_cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', rows[0], flags=re.S | re.I)
        headers = [parse_cell(c) for c in header_cells]
        ten_col_idx = None
        link_col_idx = None
        for idx, header in enumerate(headers):
            header_lower = str(header).lower()
            if ten_col_idx is None and ('ten' in header_lower or 'tên' in header_lower or 'name' in header_lower):
                ten_col_idx = idx
            if link_col_idx is None and (
                'link' in header_lower or 'drive' in header_lower or 'folder' in header_lower
                or 'anh' in header_lower or 'ảnh' in header_lower
            ):
                link_col_idx = idx

        if ten_col_idx is None or link_col_idx is None:
            st.warning(f"Không tìm thấy cột tên quán hoặc cột link trong HTML. Các cột có: {headers}")
            return {}

        drive_links = {}
        for row_html in rows[1:]:
            cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row_html, flags=re.S | re.I)
            if len(cells) <= max(ten_col_idx, link_col_idx):
                continue
            ten_quan = parse_cell(cells[ten_col_idx])
            link_value = parse_cell(cells[link_col_idx])
            if not ten_quan or not link_value:
                continue
            if link_value.startswith('http'):
                drive_links[normalize_text(ten_quan)] = link_value
        return drive_links
    except Exception as e:
        st.warning(f"Lỗi khi đọc public sheet HTML: {e}")
        return {}


def read_hyperlink_from_google_sheets_v2(sheet_url: str, sheet_name: str, api_key: Optional[str] = None) -> Dict[str, str]:
    """
    Đọc hyperlink từ Google Sheets bằng API v4, bao gồm hyperlink ẩn dưới text.
    Nếu không có API key hoặc sheet không thể đọc bằng API, dùng fallback HTML công khai.
    """
    def cell_text(cell: dict) -> str:
        if not cell:
            return ""
        if 'formattedValue' in cell:
            return str(cell['formattedValue'])
        if 'userEnteredValue' in cell:
            user_value = cell['userEnteredValue']
            if 'stringValue' in user_value:
                return str(user_value['stringValue'])
            if 'formulaValue' in user_value:
                return str(user_value['formulaValue'])
        return ""

    def parse_hyperlink_formula(formula: str) -> Optional[str]:
        if not isinstance(formula, str):
            return None
        # Tìm trong HYPERLINK( "URL" , "text" ) hoặc HYPERLINK('URL','text')
        match = re.search(r'HYPERLINK\(\s*["\']([^"\']+)["\']', formula, re.IGNORECASE)
        return match.group(1) if match else None

    if not api_key:
        return read_hyperlink_from_public_sheet_html(sheet_url)

    try:
        sheet_id_match = re.search(r'/d/([a-zA-Z0-9_-]+)', sheet_url)
        if not sheet_id_match:
            return {}

        sheet_id = sheet_id_match.group(1)
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}"
        params = {
            'key': api_key,
            'ranges': sheet_name,
            'includeGridData': 'true',
            # Lấy hyperlink, userEnteredValue, formattedValue
            'fields': 'sheets/data/rowData/values(hyperlink,userEnteredValue,formattedValue)'
        }

        response = requests.get(url, params=params, timeout=30)
        if response.status_code != 200:
            if response.status_code in (400, 403):
                st.warning(
                    "Google Sheets API không thể đọc sheet này. "
                    "Thử fallback qua HTML public nếu sheet được chia sẻ công khai."
                )
                return read_hyperlink_from_public_sheet_html(sheet_url)
            st.warning(f"Lỗi Google Sheets API: {response.status_code} - {response.text}")
            return {}

        data = response.json()
        sheets = data.get('sheets', [])
        if not sheets:
            return read_hyperlink_from_public_sheet_html(sheet_url)

        row_data = sheets[0].get('data', [{}])[0].get('rowData', [])
        if not row_data:
            return read_hyperlink_from_public_sheet_html(sheet_url)

        all_rows = [row.get('values', []) for row in row_data]
        headers = [cell_text(cell) for cell in all_rows[0]] if all_rows else []

        ten_col_idx = None
        link_col_idx = None
        for idx, header in enumerate(headers):
            header_lower = str(header).lower()
            if ten_col_idx is None and ('ten' in header_lower or 'tên' in header_lower or 'name' in header_lower):
                ten_col_idx = idx
            if link_col_idx is None and (
                'link' in header_lower or 'drive' in header_lower or 'folder' in header_lower
                or 'anh' in header_lower or 'ảnh' in header_lower
            ):
                link_col_idx = idx

        if ten_col_idx is None or link_col_idx is None:
            st.warning(f"Không tìm thấy cột tên quán hoặc cột link. Các cột có: {headers}")
            return {}

        drive_links = {}
        # ===== BẮT ĐẦU VÒNG LẶP =====
        for row in all_rows[1:]:
            real_url = None  # Reset cho mỗi hàng
            if len(row) <= max(ten_col_idx, link_col_idx):
                continue

            ten_cell = row[ten_col_idx] if ten_col_idx < len(row) else None
            link_cell = row[link_col_idx] if link_col_idx < len(row) else None
            ten_quan = cell_text(ten_cell).strip()
            if not ten_quan:
                continue

            # Cách 1: Lấy từ trường hyperlink
            if isinstance(link_cell, dict):
                real_url = link_cell.get('hyperlink')
            
            # Cách 2: Kiểm tra công thức HYPERLINK hoặc text http
            if not real_url:
                link_text = cell_text(link_cell) if isinstance(link_cell, dict) else link_cell
                if isinstance(link_text, str):
                    if link_text.startswith('=HYPERLINK'):
                        real_url = parse_hyperlink_formula(link_text)
                    elif link_text.startswith('http'):
                        real_url = link_text
                    else:
                        # Cách 3: Tìm URL ẩn trong text
                        url_match = re.search(r'(https?://)?drive\.google\.com/[^\s]+', link_text)
                        if url_match:
                            real_url = url_match.group(0)
                            if not real_url.startswith('http'):
                                real_url = 'https://' + real_url

            # Nếu tìm được URL, thêm vào dict
            if real_url:
                drive_links[normalize_text(ten_quan)] = real_url
        # ===== KẾT THÚC VÒNG LẶP =====

        if drive_links:
            return drive_links
        return read_hyperlink_from_public_sheet_html(sheet_url)
    except Exception as e:
        st.warning(f"Lỗi đọc hyperlink: {e}. Thử fallback HTML public.")
        return read_hyperlink_from_public_sheet_html(sheet_url)
def extract_images_from_zip(zip_bytes: bytes) -> Tuple[Dict[str, List[Tuple[str, bytes]]], List[bytes]]:
    """Trích xuất ảnh từ file ZIP - XỬ LÝ TÊN CÓ SỐ THỨ TỰ"""
    image_dict = {}
    all_images = []
    
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            parts = info.filename.split('/')
            if len(parts) < 2:
                continue
            
            raw_folder_name = parts[0]
            
            cleaned_name = re.sub(r'^\d+\.\s*', '', raw_folder_name)  # Xóa "1. ", "2. " ở đầu
            cleaned_name = re.sub(r'^\d+\s+', '', cleaned_name)        # Xóa "1 " ở đầu
            
            folder_name = normalize_text(cleaned_name)  # Chuẩn hóa tên đã làm sạch
            
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
            all_images.append(img_bytes)
            
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
    - Không xuống dòng
    """
    
    if provider == 'gemini':
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(prompt)
            text = response.text.strip().strip('"').strip("'")
            if text and len(text) >= 3:
                words = text.split()
                if len(words) > 8:
                    text = ' '.join(words[:8])
                return text
        except Exception as e:
            print(f"Lỗi Gemini short_desc: {e}")
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
        except Exception as e:
            print(f"Lỗi DeepSeek short_desc: {e}")
    
    return f"{ten_quan} - Điểm đến tuyệt vời tại Đà Lạt ✨"

def generate_tiktok_caption(names: List[str], descriptions: List[str], api_key: str, provider: str = 'gemini') -> str:
    """Viết caption TikTok cho bài đăng - AI TỰ SINH NGÔN NGỮ GENZ"""
    names_str = ", ".join(names)
    desc_str = " ".join(descriptions[:3]) if descriptions else ""
    hashtags = f"{HARD_HASHTAGS} #cafedalat #checkindalat #reviewdalat"
    
    prompt = f"""
    Viết caption TikTok cho bài đăng về các quán: {names_str}.
    Đặc điểm nổi bật: {desc_str}
    
    YÊU CẦU VỀ NGÔN NGỮ:
    - SỬ DỤNG NGÔN NGỮ GENZ TỰ NHIÊN, SÁNG TẠO (có thể tự nghĩ ra các từ ngữ mới, vui nhộn)
    - Có thể biến tấu từ ngữ: "không" -> "khum", "ngon" -> "ngonnn", "đi" -> "đi nàooo"
    - Thêm các từ cảm thán: "ui trời", "ối", "wow", "ồ", "á", "ớ"
    - Có thể viết lặp chữ để tạo cảm xúc: "ngon quáaaaa", "thích thíiii", "đi liềnnnn"
    - Thêm các cụm từ GenZ phổ biến hoặc tự sáng tạo: "cực phẩm", "đỉnh nóc", "xịn xò", "cứ gọi là", "mlem mlem", "xỉu", "chill phê", "sương sương"
    - VIẾT HOA để nhấn mạnh: "RẤT ĐỈNH", "QUÁ NGON", "KHÔNG THỂ BỎ QUA"
    
    CẤU TRÚC:
    Dòng 1: TIÊU ĐỀ (VIẾT HOA, ngắn gọn, ấn tượng, có từ "Đà Lạt")
    Dòng 2: NỘI DUNG (giọng văn GenZ, tự nhiên, vui tươi, tối đa 200 ký tự)
    Dòng 3: HASHTAG (các hashtag liên quan)
    
    VÍ DỤ VỀ NGÔN NGỮ GENZ:
    - "Ui trời ơi, mấy quán này ngonnn khum thể tảaaaa"
    - "Chill phê nha mấy đứa ơiii ☕️"
    - "Xỉu luôn ớ, đỉnh nóc kịch trần"
    - "Mlem mlem, cứ gọi là ghiền luôn khum dứt ra đc"
    
    Hãy tự do sáng tạo ngôn ngữ GenZ của riêng bạn, miễn là vui nhộn, trẻ trung và thu hút!
    
    Trả về chính xác 3 dòng theo cấu trúc trên (TIÊU ĐỀ, NỘI DUNG, HASHTAG), không thêm dòng trống.
    """
    
    if provider == 'gemini' and api_key:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash', generation_config={
                "temperature": 0.95,  # Tăng temperature để AI sáng tạo hơn
                "top_p": 0.9,
                "top_k": 40
            })
            response = model.generate_content(prompt)
            text = response.text.strip()
            
            # Tách các dòng
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            title = ""
            content = ""
            hashtags_part = ""
            
            # Tìm và gán đúng thứ tự
            for i, line in enumerate(lines):
                if "TIÊU ĐỀ" in line or i == 0:
                    title = line.replace("TIÊU ĐỀ", "").replace(":", "").strip()
                elif "NỘI DUNG" in line or i == 1:
                    content = line.replace("NỘI DUNG", "").replace(":", "").strip()
                elif "HASHTAG" in line or i == 2:
                    hashtags_part = line.replace("HASHTAG", "").replace(":", "").strip()
            
            # Nếu không tách được, xử lý thông minh hơn
            if not title or not content:
                if len(lines) >= 3:
                    title = lines[0]
                    content = lines[1]
                    hashtags_part = lines[2] if len(lines) > 2 else hashtags
                else:
                    content = text
                    title = content[:40].upper() if len(content) > 40 else content.upper()
            
            # Đảm bảo có hashtag
            if not hashtags_part or HARD_HASHTAGS not in hashtags_part:
                hashtags_part = hashtags
            
            return f"{title}\n{content}\n{hashtags_part}"
            
        except Exception as e:
            print(f"Lỗi Gemini: {e}")
    
    # Fallback cực kỳ đơn giản - chỉ để phòng khi API lỗi
    return f"TOP QUÁN CAFE ĐÀ LẠT ĐỈNH CHÓP\nUi trời ơi, mấy quán này ngon khum thể tả luôn ớ! Ghé liền thôi mấy đứa ơiii ☕️\n{hashtags}"
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
def generate_cover_description(api_key: str, provider: str = 'gemini', user_prompt: str = None) -> str:
    """
    Dùng AI để sinh câu mô tả cho bìa.
    Nếu có API key và user_prompt, AI sẽ sinh câu mới.
    Nếu không có API key, dùng user_prompt làm câu mô tả.
    """
    
    # DEBUG: In ra để kiểm tra
    print(f"[DEBUG] generate_cover_description called - provider: {provider}, api_key: {bool(api_key)}, user_prompt: {user_prompt}")
    
    # TRƯỜNG HỢP 1: Không có API key - dùng user_prompt hoặc random
    if not api_key:
        if user_prompt:
            return user_prompt
        return random.choice(COVER_DESCRIPTIONS)
    
    # TRƯỜNG HỢP 2: Có user_prompt và API key - AI sẽ sinh câu mới
    if user_prompt:
        prompt = f"""
        Bạn là chuyên gia viết content về ẩm thực và du lịch Đà Lạt.
        
        Người dùng yêu cầu: "{user_prompt}"
        
        YÊU CẦU CỨNG:
        - Hãy viết LẠI câu trên theo phong cách hấp dẫn, thu hút hơn
        - Giữ NGUYÊN chủ đề (nếu là quán ăn thì viết về quán ăn, không đổi thành cafe)
        - Chỉ trả về DUY NHẤT 1 câu (tối đa 12 từ)
        - KHÔNG thêm ngoặc kép, KHÔNG giải thích
        
        Ví dụ:
        Input: "Những quán ăn ngon không thể bỏ lỡ tại Đà Lạt"
        Output: "Top quán ăn ngon nhất định phải thử ở Đà Lạt"
        """
    else:
        # Không có user_prompt - AI tự sinh
        prompt = """
        Viết một câu ngắn gọn (tối đa 12 từ) giới thiệu về các điểm đến tại Đà Lạt.
        Chỉ trả về 1 câu, không ngoặc kép.
        """
    
    try:
        if provider == 'gemini':
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash', generation_config={
                "temperature": 0.5,
                "top_p": 0.9
            })
            response = model.generate_content(prompt)
            text = response.text.strip().strip('"').strip("'")
            
            # Giới hạn độ dài
            if len(text.split()) > 15:
                text = ' '.join(text.split()[:12])
            
            if text and len(text) > 3:
                print(f"[DEBUG] Gemini generated: {text}")
                return text
            else:
                return user_prompt if user_prompt else random.choice(COVER_DESCRIPTIONS)
                
        else:  # DeepSeek
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 60
            }
            
            print(f"[DEBUG] Calling DeepSeek API...")
            resp = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            print(f"[DEBUG] DeepSeek response status: {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                text = data['choices'][0]['message']['content'].strip().strip('"').strip("'")
                
                # Giới hạn độ dài
                if len(text.split()) > 15:
                    text = ' '.join(text.split()[:12])
                
                print(f"[DEBUG] DeepSeek generated: {text}")
                
                if text and len(text) > 3:
                    return text
                else:
                    return user_prompt if user_prompt else random.choice(COVER_DESCRIPTIONS)
            else:
                print(f"[DEBUG] DeepSeek error: {resp.text}")
                # Fallback: dùng user_prompt
                return user_prompt if user_prompt else random.choice(COVER_DESCRIPTIONS)
                
    except Exception as e:
        print(f"[DEBUG] Lỗi sinh cover description: {e}")
        import traceback
        traceback.print_exc()
        # Fallback: dùng user_prompt
        return user_prompt if user_prompt else random.choice(COVER_DESCRIPTIONS)
def generate_facebook_caption(names: List[str], descriptions: List[str], api_key: str, provider: str = 'gemini') -> str:
    """Viết caption Facebook dài - AI TỰ SINH NGÔN NGỮ GENZ NHẸ NHÀNG"""
    names_str = ", ".join(names[:7])
    desc_str = " ".join(descriptions[:3]) if descriptions else ""
    
    prompt = f"""
    Viết caption Facebook cho bài review các quán: {names_str}.
    Đặc điểm nổi bật: {desc_str}
    
    YÊU CẦU VỀ NGÔN NGỮ:
    - Giọng văn thân thiện, gần gũi, có thể dùng ngôn ngữ GenZ NHẸ NHÀNG
    - TỰ DO SÁNG TẠO cách nói chuyện trẻ trung, vui vẻ
    - Có thể dùng: "nè", "nha", "nhe", "hihi", "haha", "wow", "ui", "ối"
    - Có thể biến tấu từ ngữ nhẹ: "không" -> "khum", "ngon" -> "ngonnn", "đi" -> "đi nè"
    - Thêm cảm xúc bằng cách lặp chữ nhẹ: "thích quáaa", "ngon quá nè"
    - KHÔNG cần quá nhiều từ lóng, giữ sự chân thành và dễ đọc
    
    CẤU TRÚC:
    - Mở đầu hấp dẫn (có thể chào hỏi thân thiện)
    - Nội dung chính: kể về trải nghiệm, mô tả không gian, đồ uống
    - Kết thúc: lời mời gọi tương tác, câu hỏi cho người đọc
    - Cuối cùng: hashtag {HARD_HASHTAGS}
    
    Hãy viết tự nhiên như đang trò chuyện với bạn bè, tối thiểu 100 từ, tối đa 250 từ.
    """
    
    if provider == 'gemini' and api_key:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash', generation_config={
                "temperature": 0.9,
                "top_p": 0.95
            })
            response = model.generate_content(prompt)
            content = response.text.strip()
            
            # Đảm bảo có hashtag
            if HARD_HASHTAGS not in content:
                content += f"\n\n{HARD_HASHTAGS} #reviewdalat #cafedalat #dalattrip"
            
            return content
            
        except Exception as e:
            print(f"Lỗi Facebook AI: {e}")
    
    # Fallback đơn giản
    return f"""Ghé Đà Lạt mà khum ghé mấy quán này thì phí quá mấy đứa ơi ✨

{names_str}

Không gian chill phê, đồ uống ngonnn, giá cả cũng dễ thương nữa nè ☕️

Mấy đứa đã thử chưa? Comment để tui biết với nhaaa 💬

{HARD_HASHTAGS} #reviewdalat #cafedalat"""
# ============================================================
# GIAO DIỆN CHÍNH
# ============================================================
st.title("🎬 Riviu AI Content Generator Pro")
st.caption("Tạo ảnh banner & caption tự động – Layout đa dạng, màu sắc đồng bộ")

with st.sidebar:
    st.header("🔑 Cấu hình API")
    saved_keys = decrypt_api_keys()
    with st.expander("⚙️ API Keys (đã mã hóa)", expanded=True):
        gemini_key = st.text_input(
            "Gemini API Key", 
            type="password", 
            value=saved_keys.get('gemini', ''),
            help="Dùng để sinh caption AI và mô tả ảnh"
        )
        deepseek_key = st.text_input(
            "DeepSeek API Key (dự phòng)", 
            type="password",
            value=saved_keys.get('deepseek', '')
        )
        sheet_api_key = st.text_input(
            "Google Sheets API Key", 
            type="password",
            value=saved_keys.get('sheets', ''),
            help="Dùng để đọc hyperlink ẩn trong Google Sheet"
        )
        drive_api_key = st.text_input(
            "Google Drive API Key", 
            type="password",
            value=saved_keys.get('drive', ''),
            help="Cần nếu dùng link Drive Folder"
        )
        if st_button_fix("💾 Lưu API Keys (mã hóa)", use_container_width=True):
            keys_to_save = {
                'gemini': gemini_key,
                'deepseek': deepseek_key,
                'sheets': sheet_api_key,
                'drive': drive_api_key
            }
            encrypt_api_keys(keys_to_save)
            st.success("✅ Đã lưu và mã hóa API keys!")
            st.rerun()

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
    
    # Lấy danh sách tất cả font
    all_fonts = get_all_fonts_list()
    
    # Chọn font đơn lẻ
    default_font_index = 0
    if st.session_state.suggested_font and st.session_state.suggested_font in all_fonts:
        default_font_index = all_fonts.index(st.session_state.suggested_font)
    
    selected_font = st.selectbox("Chọn font chữ cho banner:", all_fonts, index=default_font_index)
    font_style = st.radio("Phong cách chữ:", ["Bình thường", "In hoa toàn bộ", "Viết hoa chữ cái đầu"], index=0)
    random_font_per_set = st.checkbox(
        "🎲 Random font mỗi bộ", 
        value=True, 
        help="Mỗi bộ sẽ dùng 1 font khác nhau; cùng bộ sẽ dùng cùng 1 font"
    )

    st.markdown("---")
    st.markdown("### 📝 Cấu hình Cover")
    cover_mode = st.radio(
        "Mô tả cover:",
        ["🤖 AI tự sinh", "✍️ Tự nhập"],
        horizontal=True
    )

      # Luôn khai báo custom_cover_desc
    custom_cover_desc = None
    
    # LƯU Ý: Dù chọn chế độ nào, nếu có nhập text thì AI sẽ dùng để sinh câu mới
    if cover_mode == "🤖 AI tự sinh":
        custom_cover_desc = st.text_input(
            "Nhập chủ đề cho AI (để trống nếu muốn AI tự nghĩ):",
            value="",
            max_chars=100,
            placeholder="Ví dụ: quán ăn siêu ngon ở Đà Lạt"
        )
    else:  # "✍️ Tự nhập" - nhưng thực chất vẫn dùng AI để viết lại hay hơn
        custom_cover_desc = st.text_input(
            "Nhập ý tưởng của bạn (AI sẽ viết lại hay hơn):",
            value="",
            max_chars=100,
            placeholder="Ví dụ: quán ăn siêu ngon ở Đà Lạt đừng bỏ lỡ"
        )
        st.info("💡 AI sẽ viết lại câu của bạn theo phong cách hấp dẫn hơn!")

    st.markdown("---")
    st.markdown("### ⚡ Tối ưu tải ảnh")
    max_workers = st.slider(
        "Số luồng tải song song", 
        min_value=5, 
        max_value=30, 
        value=15,
        help="Càng nhiều luồng tải càng nhanh nhưng dễ bị giới hạn API"
    )
    use_cache = st.checkbox("💾 Dùng cache (tải nhanh hơn lần sau)", value=True)
    
    # Lưu vào session state
    st.session_state.max_workers = max_workers
    st.session_state.use_cache = use_cache
    
    if use_cache:
        cache_size = sum(os.path.getsize(os.path.join(CACHE_DIR, f)) for f in os.listdir(CACHE_DIR) if os.path.isfile(os.path.join(CACHE_DIR, f))) / (1024*1024)
        st.caption(f"📦 Cache hiện tại: {cache_size:.1f} MB")
        
        if st_button_fix("🗑️ Xóa cache", use_container_width=True):
            try:
                for f in os.listdir(CACHE_DIR):
                    file_path = os.path.join(CACHE_DIR, f)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                st.success("✅ Đã xóa cache")
            except Exception as e:
                st.error(f"❌ Lỗi xóa cache: {e}")
    
    st.markdown("---")
    st.markdown("### 🧹 Dọn dẹp")
    col_cache1, col_cache2, col_cache3 = st.columns(3)
    with col_cache1:
        if st_button_fix("🗑️ Xóa cache font", use_container_width=True):
            FONT_CACHE.clear()
            st.success("✅ Đã xóa cache font")
    with col_cache2:
        if st_button_fix("🧹 Giải phóng RAM", use_container_width=True):
            gc.collect()
            st.success("✅ Đã giải phóng bộ nhớ")
    with col_cache3:
        if st_button_fix("🗑️ Xóa cache Excel", use_container_width=True):
            try:
                load_excel_data_cached.clear()
                load_gsheet_data_cached.clear()
                st.success("✅ Đã xóa cache dữ liệu Excel/Sheet")
                st.rerun()
            except NameError:
                st.warning("⚠️ Chưa có cache nào để xóa")
            except Exception as e:
                st.error(f"Lỗi: {e}")
    
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

# --- BLOCK 1: DỮ LIỆU EXCEL (UPLOAD HOẶC GOOGLE SHEET) ---
st.markdown("### 📊 1. Dữ liệu Excel / Google Sheet")

# Khởi tạo session state cho dữ liệu sheet
if 'sheet_df' not in st.session_state:
    st.session_state.sheet_df = None
if 'sheet_columns' not in st.session_state:
    st.session_state.sheet_columns = {}
if 'sheet_loaded' not in st.session_state:
    st.session_state.sheet_loaded = False
if 'sheet_name_loaded' not in st.session_state:
    st.session_state.sheet_name_loaded = None
if 'last_sheet_url' not in st.session_state:
    st.session_state.last_sheet_url = None
if 'all_sheets_data' not in st.session_state:
    st.session_state.all_sheets_data = {}
if 'sheet_names_list' not in st.session_state:
    st.session_state.sheet_names_list = []

# Chọn nguồn dữ liệu
data_source = st.radio("Chọn nguồn dữ liệu:", ["Upload file Excel/CSV", "Google Sheet URL"], horizontal=True)

# NÚT RESET DỮ LIỆU
if st.session_state.sheet_loaded:
    col_reset1, col_reset2 = st.columns([3, 1])
    with col_reset2:
        if st.button("🔄 Đọc lại sheet (refresh)", key="refresh_sheet_data", use_container_width=True):
            st.session_state.sheet_loaded = False
            st.session_state.sheet_df = None
            st.session_state.last_sheet_url = None
            st.session_state.all_sheets_data = {}
            st.session_state.sheet_names_list = []
            st.rerun()
    with col_reset1:
        st.success(f"✅ Đang dùng dữ liệu đã lưu từ sheet `{st.session_state.sheet_name_loaded}` ({len(st.session_state.sheet_df)} dòng)")

excel_file = None
sheet_url = None
df = None
ten_col = dia_col = gio_col = doi_col = mon_col = style_col = None
selected_sheet = None

# KIỂM TRA NẾU ĐÃ CÓ DỮ LIỆU TRONG SESSION STATE
if st.session_state.sheet_loaded and st.session_state.sheet_df is not None:
    # Lấy dữ liệu từ session state
    df = st.session_state.sheet_df
    ten_col = st.session_state.sheet_columns.get('ten_col')
    dia_col = st.session_state.sheet_columns.get('dia_col')
    gio_col = st.session_state.sheet_columns.get('gio_col')
    doi_col = st.session_state.sheet_columns.get('doi_col')
    mon_col = st.session_state.sheet_columns.get('mon_col')
    style_col = st.session_state.sheet_columns.get('style_col')
    selected_sheet = st.session_state.sheet_name_loaded
    
    # Hiển thị preview
    preview_cols = [c for c in [ten_col, dia_col, gio_col, doi_col, mon_col, style_col] if c]
    if preview_cols:
        st.dataframe(df[preview_cols].head(10))
    
    st.info("💡 Dữ liệu đã được lưu, bạn có thể thoải mái xem preview mà không cần đọc lại sheet!")
    
else:
    # Nếu chưa có dữ liệu, TIẾP TỤC ĐỌC
    if data_source == "Upload file Excel/CSV":
        excel_file = st.file_uploader("Upload file Excel/CSV", type=['xlsx', 'csv'], key="excel")
        
        if excel_file:
            sheets = read_excel_with_sheets(excel_file)
            sheet_names = list(sheets.keys())
            
            priority_sheets = ['Quan_an', 'Cafe', 'Khu_du_lich', 'Địa điểm lịch sử', 'Dich_vu']
            default_idx = 0
            for i, sheet in enumerate(sheet_names):
                if sheet in priority_sheets:
                    default_idx = i
                    break
            
            selected_sheet = st.selectbox("Chọn sheet chứa dữ liệu:", sheet_names, index=default_idx)
            
            if selected_sheet:
                with st.spinner("Đang đọc dữ liệu..."):
                    df = sheets[selected_sheet].copy()
                    df = process_sheet_data(df, selected_sheet)
                    ten_col, dia_col, gio_col, doi_col, mon_col, style_col = find_required_columns(df)
                
                # LƯU VÀO SESSION STATE
                st.session_state.sheet_df = df
                st.session_state.sheet_columns = {
                    'ten_col': ten_col,
                    'dia_col': dia_col,
                    'gio_col': gio_col,
                    'doi_col': doi_col,
                    'mon_col': mon_col,
                    'style_col': style_col
                }
                st.session_state.sheet_name_loaded = selected_sheet
                st.session_state.sheet_loaded = True
                st.session_state.sheet_url = None
                st.session_state.selected_sheet_name = selected_sheet

                st.success(f"✅ Đã lưu sheet `{selected_sheet}` ({len(df)} dòng) - Sẵn sàng preview!")
                
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
    
    else:  # Google Sheet URL
        st.markdown("#### 🔗 Nhập link Google Sheet")
      
        # Ô nhập URL
        sheet_url_input = st.text_input(
            "Google Sheet URL",
            placeholder="https://docs.google.com/spreadsheets/d/1TAYu1fzHuwofNQ7ulBHEwTeE8ouYn9Lu/edit",
            value= "https://docs.google.com/spreadsheets/d/1TAYu1fzHuwofNQ7ulBHEwTeE8ouYn9Lu/edit?gid=1062172898#gid=1062172898",
            key="sheet_url_input"
        )
        
        # NÚT TẢI DANH SÁCH SHEET
        if st.button("📥 Tải danh sách sheet", key="load_sheet_list", use_container_width=True):
            if sheet_url_input:
                with st.spinner("Đang đọc danh sách sheet từ Google Sheets..."):
                    # Lấy API key từ sidebar
                    sheet_api_key = None
                    if 'sheet_api_key' in locals():
                        sheet_api_key = sheet_api_key
                    else:
                        # Lấy từ saved keys nếu có
                        saved_keys = decrypt_api_keys()
                        sheet_api_key = saved_keys.get('sheets', '')
                    
                    # Đọc tất cả sheet
                    all_sheets = read_all_sheets_from_url(sheet_url_input, api_key=sheet_api_key if sheet_api_key else None)
                    
                    if all_sheets:
                        st.session_state.all_sheets_data = all_sheets
                        st.session_state.sheet_names_list = list(all_sheets.keys())
                        st.session_state.last_sheet_url = sheet_url_input
                        st.success(f"✅ Tìm thấy {len(st.session_state.sheet_names_list)} sheets!")
                    else:
                        st.error("❌ Không thể đọc sheet. Kiểm tra URL và quyền chia sẻ (cần 'Anyone with the link can view')")
            else:
                st.warning("⚠️ Vui lòng nhập URL Google Sheet trước")
        
        # HIỂN THỊ DANH SÁCH SHEET ĐỂ CHỌN (nếu có)
        if st.session_state.sheet_names_list:
            st.markdown("#### 📄 Chọn sheet để đọc")
            
            # Tạo dictionary để hiển thị đẹp
            sheet_display = {}
            for sheet_name in st.session_state.sheet_names_list:
                # Lấy số dòng preview nếu có
                row_count = len(st.session_state.all_sheets_data.get(sheet_name, pd.DataFrame()))
                sheet_display[sheet_name] = f"{sheet_name} ({row_count} dòng)"
            
            selected_sheet = st.selectbox(
                "Chọn sheet:",
                options=st.session_state.sheet_names_list,
                format_func=lambda x: sheet_display.get(x, x),
                key="sheet_selector"
            )
            
            # NÚT XÁC NHẬN ĐỌC SHEET ĐÃ CHỌN
            if selected_sheet and st.button("✅ Đọc sheet này", key="confirm_sheet", use_container_width=True):
                with st.spinner(f"Đang đọc sheet '{selected_sheet}'..."):
                    df = st.session_state.all_sheets_data[selected_sheet].copy()
                    df = process_sheet_data(df, selected_sheet)
                    ten_col, dia_col, gio_col, doi_col, mon_col, style_col = find_required_columns(df)
                    
                    # Kiểm tra cột bắt buộc
                    missing_cols = []
                    if not ten_col:
                        missing_cols.append("Tên quán")
                    if not dia_col:
                        missing_cols.append("Địa chỉ")
                    if not gio_col:
                        missing_cols.append("Giờ mở cửa")
                    
                    if missing_cols:
                        st.error(f"❌ Sheet '{selected_sheet}' thiếu cột bắt buộc: {', '.join(missing_cols)}")
                        st.info(f"📋 Các cột có trong sheet: {', '.join(df.columns.tolist())}")
                        st.info("💡 Cần có cột: Tên quán (ten_quan/ten/tên), Địa chỉ (dia_chi/địa chỉ), Giờ mở cửa (gio_mo_cua)")
                    else:
                        # LƯU VÀO SESSION STATE
                        st.session_state.sheet_df = df
                        st.session_state.sheet_columns = {
                            'ten_col': ten_col,
                            'dia_col': dia_col,
                            'gio_col': gio_col,
                            'doi_col': doi_col,
                            'mon_col': mon_col,
                            'style_col': style_col
                        }
                        st.session_state.sheet_name_loaded = selected_sheet
                        st.session_state.sheet_loaded = True
                        st.session_state.sheet_url = sheet_url_input
                        st.session_state.selected_sheet_name = selected_sheet
                        
                        st.success(f"✅ Đã lưu sheet `{selected_sheet}` ({len(df)} dòng)!")
                        
                        # Hiển thị preview
                        preview_cols = [c for c in [ten_col, dia_col, gio_col, doi_col, mon_col, style_col] if c]
                        if preview_cols:
                            st.dataframe(df[preview_cols].head(10))
                        
                        st.balloons()
            
            # HIỂN THỊ PREVIEW NHANH CÁC SHEET (tùy chọn)
            with st.expander("👁️ Xem nhanh nội dung các sheet"):
                for sheet_name in st.session_state.sheet_names_list:
                    preview_df = st.session_state.all_sheets_data[sheet_name].head(3)
                    st.markdown(f"**📑 {sheet_name}** ({len(st.session_state.all_sheets_data[sheet_name])} dòng)")
                    st.dataframe(preview_df, use_container_width=True)
                    st.markdown("---")
# --- BLOCK 2: NGUỒN ẢNH ---
st.markdown("### 🖼️ 2. Nguồn ảnh")
src_option = st.radio(
    "Chọn cách cung cấp ảnh:", 
    ["🔗 Từ Hyperlink trong Sheet", "Upload file ZIP"], 
    horizontal=True
)

# Khởi tạo biến ảnh
image_dict = {}
all_images_list = []

# Kiểm tra nếu đã tự động tải ảnh từ hyperlink
if st.session_state.auto_hyperlink_loaded and st.session_state.auto_image_dict:
    st.success(f"✅ Đã tự động tải {len(st.session_state.auto_image_dict)} quán với tổng {sum(len(imgs) for imgs in st.session_state.auto_image_dict.values())} ảnh từ hyperlink!")
    image_dict = st.session_state.auto_image_dict
    all_images_list = st.session_state.auto_all_images_list
    src_option = "🔗 Từ Hyperlink trong Sheet"

if src_option == "🔗 Từ Hyperlink trong Sheet":
    # DEBUG
    #st.write(f"🔍 Debug: sheet_df = {st.session_state.sheet_df is not None}")
    #st.write(f"🔍 Debug: sheet_url = {st.session_state.sheet_url}")
    #st.write(f"🔍 Debug: selected_sheet_name = {st.session_state.selected_sheet_name}")
    # LẤY DỮ LIỆU TỪ SESSION STATE (QUAN TRỌNG)
    if st.session_state.sheet_df is None:
        st.warning("⚠️ Vui lòng nhập dữ liệu sheet trước (mục 1)")
    elif st.session_state.sheet_url is None:
        st.warning("⚠️ Vui lòng nhập Google Sheet URL và bấm 'Xác nhận đọc sheet'")
    elif not drive_api_key:
        st.warning("⚠️ Cần nhập Google Drive API Key để tải ảnh")
    else:
        if not st.session_state.auto_hyperlink_loaded:
            st.markdown("### 🔗 Đọc hyperlink từ sheet")
            if st.button("📥 Đọc hyperlink & tải ảnh từ sheet", key="manual_read_hyperlink"):
                with st.spinner("Đang đọc hyperlink từ Google Sheets..."):
                    drive_links = read_hyperlink_from_google_sheets_v2(
                        st.session_state.sheet_url,  # Dùng từ session state
                        st.session_state.selected_sheet_name,  # Dùng từ session state
                        sheet_api_key
                    )

                if drive_links:
                    st.success(f"✅ Đã đọc {len(drive_links)} link Drive từ sheet")
                    with st.spinner("Đang tải ảnh từ Drive..."):
                        image_dict, all_images_list = load_images_from_drive_links(drive_links, drive_api_key)

                    if image_dict:
                        total_images = sum(len(imgs) for imgs in image_dict.values())
                        st.success(f"✅ Đã tải ảnh cho {len(image_dict)} quán, tổng {total_images} ảnh")
                        st.session_state.auto_image_dict = image_dict
                        st.session_state.auto_all_images_list = all_images_list
                        st.session_state.auto_hyperlink_loaded = True
                    else:
                        st.error("❌ Không tải được ảnh nào. Kiểm lại link Drive và quyền chia sẻ.")
                else:
                    st.error("❌ Không đọc được hyperlink nào. Kiểm tra sheet và quyền chia sẻ.")
        else:
            st.success("✅ Ảnh đã được tải từ hyperlink Google Sheets.")

elif src_option == "Upload file ZIP":
    zip_file = st.file_uploader("Upload file ZIP chứa ảnh theo thư mục", type=['zip'])
    if zip_file:
        with st.spinner("Đang đọc chỉ mục ảnh từ ZIP..."):
            image_dict, all_images_list = extract_images_from_zip(zip_file.read())
        st.success(f"✅ Đã tìm thấy ảnh cho {len(image_dict)} thư mục, tổng {len(all_images_list)} ảnh")
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

if st_button_fix("🚀 XUẤT NỘI DUNG HÀNG LOẠT", type="primary", use_container_width=True):
    if st.session_state.sheet_df is None:
        st.error("Vui lòng đọc sheet trước (mục 1)")
        st.stop()
    df = st.session_state.sheet_df
    ten_col = st.session_state.sheet_columns.get('ten_col')
    dia_col = st.session_state.sheet_columns.get('dia_col')
    gio_col = st.session_state.sheet_columns.get('gio_col')
    doi_col = st.session_state.sheet_columns.get('doi_col')
    mon_col = st.session_state.sheet_columns.get('mon_col')
    style_col = st.session_state.sheet_columns.get('style_col')
    # ===== SỬA PHẦN NÀY: ƯU TIÊN DÙNG SESSION STATE =====
    # Kiểm tra session state trước
    if st.session_state.auto_hyperlink_loaded and st.session_state.auto_image_dict:
        image_dict = st.session_state.auto_image_dict
        all_images_list = st.session_state.auto_all_images_list
    elif not image_dict or not all_images_list:
        # Nếu không có trong session state và không có local
        st.error("❌ Chưa có ảnh. Vui lòng:")
        st.markdown("""
        1. **Upload file ZIP** chứa ảnh theo thư mục
        2. Hoặc **nhập Google Sheets API Key** và bấm "Đọc hyperlink & tải ảnh tự động"
        3. Hoặc **nhập Google Drive API Key** và dùng link Drive
        """)
        st.stop()
    
    # Debug: hiển thị thông tin ảnh đã tải
    total_images = sum(len(imgs) for imgs in image_dict.values()) if isinstance(image_dict, dict) else len(all_images_list)
    st.info(f"📸 Debug: Có {len(image_dict)} quán, tổng {total_images} ảnh")

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
    ai_provider = 'deepseek' if gemini_key else 'gemini'
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
                    "position": random.choice([p for p in TEXT_POSITIONS if p not in ["top-right", "right-center"]]),
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
            # Trong vòng lặp for set_idx in range(int(num_sets)):
            if random_font_per_set:
                random.seed(set_idx)
                current_font = random.choice(PRESET_FONTS)
                random.seed()
            else:
                current_font = selected_font
            # ✅ Luôn định nghĩa fixed_font_scale
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

                 # Debug
            #st.write(f"🔍 cover_mode: {cover_mode}")
            #st.write(f"🔍 custom_cover_desc: {custom_cover_desc}")
            #st.write(f"🔍 ai_enabled: {ai_enabled}")
            
                   # === SINH CÂU MÔ TẢ CHO COVER ===
            # LUÔN DÙNG AI NẾU CÓ API KEY, BẤT KỂ CHẾ ĐỘ NÀO
            if ai_enabled:
                # Luôn gọi AI để sinh câu mới từ prompt (nếu có prompt)
                cover_description = generate_cover_description(ai_key, ai_provider, user_prompt=custom_cover_desc)
                #st.info(f"🤖 AI đã sinh: {cover_description}")
            else:
                # Fallback khi không có AI
                cover_description = custom_cover_desc if custom_cover_desc else random.choice(COVER_DESCRIPTIONS)
                st.info(f"📝 Dùng mô tả: {cover_description}")  
            # === TẠO ẢNH BÌA COVER ===
            if all_images_list: 
                if src_option == "Upload file ZIP":
                    random_img_bytes = random.choice(all_images_list)
                else:
                    random_img_bytes = random.choice(all_images_list)

                cover_bg = Image.open(io.BytesIO(random_img_bytes))
                cover_color_theme = set_color_theme if use_consistent_layout else random.choice(COLOR_THEMES)
                
                # Tạo câu mô tả cho phần trên (từ AI hoặc mặc định)
                if ai_enabled and cover_description:
                    top_text = cover_description  # Dùng câu AI đã sinh
                else:
                    top_text = random.choice(COVER_DESCRIPTIONS)  # Câu mặc định
                
                cover_img = create_cover_image(
                    cover_bg, selected, set_descriptions, target_size, 
                    cover_color_theme, font_path, logo_path=LOGO_PATH,
                    cover_description=top_text,  # Câu cho phía trên
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
                        img = Image.open(io.BytesIO(img_item))

                    buf = process_and_save_image(
                        img, ten, gio, dc, target_size,
                        img_layout, img_color_theme,
                        font_path, font_scale,
                        current_font,
                        font_style,
                        None,
                        jpeg_quality
                    )
                    if buf is None:
                        continue
                except Exception as e:
                    st.warning(f"⚠️ Lỗi ảnh {ten}: {e}")
                    continue

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
    # ===== NÚT PREVIEW RIÊNG =====
st.markdown("---")
st.markdown("### 👁️ Xem trước kết quả")

col_preview1, col_preview2, col_preview3 = st.columns([1, 2, 1])
with col_preview2:
    if st_button_fix("🔍 XEM TRƯỚC KẾT QUẢ", type="primary", use_container_width=True):
        if st.session_state.zip_data is None:
            st.error("❌ Chưa có dữ liệu! Hãy nhấn 'XUẤT NỘI DUNG HÀNG LOẠT' trước.")
        else:
            st.session_state.show_preview = True

# Nút đóng preview
if st.session_state.get('show_preview', False):
    if st_button_fix("❌ Đóng preview", use_container_width=True):
        st.session_state.show_preview = False
        st.rerun()

# ===== PHẦN PREVIEW MỚI (CHỈ HIỆN KHI BẤM NÚT) =====
if st.session_state.get('show_preview', False) and st.session_state.caption_df is not None and not st.session_state.caption_df.empty:
    st.markdown("---")
    st.markdown("### 📋 Xem trước kết quả")
    
    # Tạo tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "🖼️ Preview Ảnh", 
        "📝 Captions", 
        "🤝 Danh sách đối tác", 
        "🎨 Layouts & Màu sắc"
    ])
    
    # ===== TAB 1: PREVIEW ẢNH =====
    with tab1:
        st.markdown("### 🖼️ Xem trước ảnh đã tạo")
        
        if st.session_state.zip_data:
            try:
                with zipfile.ZipFile(io.BytesIO(st.session_state.zip_data)) as zf:
                    all_files = sorted(zf.namelist())
                    if not all_files:
                        st.warning("Không có file nào trong ZIP")
                    else:
                        sets_dict = {}
                        for f in all_files:
                            parts = f.split('/')
                            if len(parts) >= 2:
                                set_name = parts[0]
                                if set_name not in sets_dict:
                                    sets_dict[set_name] = []
                                sets_dict[set_name].append(f)
                        
                        if sets_dict:
                            set_names = sorted(sets_dict.keys())
                            if len(set_names) > 0:
                                preview_set = st.selectbox(
                                    "Chọn bộ để xem trước:",
                                    set_names,
                                    format_func=lambda x: f"✨ {x.replace('Bo_', 'Bộ ')} ({len(sets_dict[x])} ảnh)"
                                )
                                
                                if preview_set:
                                    set_files = sets_dict[preview_set]
                                    cover_file = None
                                    normal_files = []
                                    for f in set_files:
                                        if 'COVER' in f.upper():
                                            cover_file = f
                                        else:
                                            normal_files.append(f)
                                    
                                    if cover_file:
                                        st.markdown("#### 🎨 Ảnh Bìa (Cover)")
                                        with zf.open(cover_file) as img_file:
                                            cover_img = Image.open(io.BytesIO(img_file.read()))
                                            # Resize ảnh bìa nhỏ hơn - chiều rộng tối đa 300px
                                            max_width = 300
                                            ratio = max_width / cover_img.width
                                            new_height = int(cover_img.height * ratio)
                                            cover_img_resized = cover_img.resize((max_width, new_height), Image.LANCZOS)
                                            st.image(cover_img_resized, caption="Ảnh bìa của bộ", use_container_width=False)
                                    
                                    if normal_files:
                                        st.markdown("#### 📸 Ảnh Banner từng quán")
                                        cols_per_row = st.slider("Số ảnh mỗi hàng:", min_value=2, max_value=5, value=3, key="preview_cols")
                                        
                                        for i in range(0, len(normal_files), cols_per_row):
                                            cols = st.columns(cols_per_row)
                                            for j in range(cols_per_row):
                                                idx = i + j
                                                if idx < len(normal_files):
                                                    with cols[j]:
                                                        try:
                                                            with zf.open(normal_files[idx]) as img_file:
                                                                img = Image.open(io.BytesIO(img_file.read()))
                                                                img.thumbnail((300, 400), Image.LANCZOS)
                                                                st.image(img, use_container_width=True)
                                                                file_name = os.path.basename(normal_files[idx]).replace('.jpg', '')
                                                                ten_quan = file_name.split('_', 1)[-1] if '_' in file_name else file_name
                                                                st.caption(ten_quan[:40] if len(ten_quan) > 40 else ten_quan)
                                                        except Exception as e:
                                                            st.error(f"Lỗi: {e}")
            except Exception as e:
                st.error(f"Lỗi đọc file ZIP: {e}")
        else:
            st.warning("Chưa có dữ liệu ZIP")
    
    # ===== TAB 2: CAPTIONS =====
    with tab2:
        st.markdown("### 📝 Caption đã tạo")
        for idx, row in st.session_state.caption_df.iterrows():
            with st.expander(f"🔥 {row['Bộ']} - {len(row['Quán'].split(','))} quán"):
                st.markdown(f"**📍 Quán:** {row['Quán']}")
                if row['Đối tác'] != "Không":
                    st.markdown(f"**🤝 Đối tác:** {row['Đối tác']}")
                st.markdown(f"**🎨 Layout:** {row.get('Layout & Màu', 'N/A')}")
                st.markdown(f"**📝 Cover mô tả:** {row.get('Cover Mô tả', 'N/A')}")
                
                col_tt, col_fb = st.columns(2)
                with col_tt:
                    st.markdown("**🎵 TikTok Caption:**")
                    st.text_area("", row['TikTok'], height=100, key=f"tt_{idx}", label_visibility="collapsed")
                    if st.button(f"📋 Copy TikTok", key=f"copy_tt_{idx}"):
                        st.toast("✅ Đã copy TikTok caption!")
                with col_fb:
                    st.markdown("**📘 Facebook Caption:**")
                    st.text_area("", row['Facebook'], height=150, key=f"fb_{idx}", label_visibility="collapsed")
                    if st.button(f"📋 Copy Facebook", key=f"copy_fb_{idx}"):
                        st.toast("✅ Đã copy Facebook caption!")
    
    # ===== TAB 3: ĐỐI TÁC =====
    with tab3:
        st.markdown("### 🤝 Danh sách đối tác xuất hiện")
        if st.session_state.partner_logs:
            all_partners = set()
            for set_name, partners in st.session_state.partner_logs.items():
                st.markdown(f"**{set_name}:**")
                if partners:
                    for p in partners:
                        st.markdown(f"  - {p}")
                        all_partners.add(p)
                else:
                    st.markdown(f"  *(Không có đối tác)*")
                st.markdown("")
            st.markdown("---")
            st.markdown(f"### 🏆 Tổng số đối tác: {len(all_partners)}")
            st.markdown(", ".join(sorted(all_partners)))
        else:
            st.info("Chưa có dữ liệu đối tác")
    
    # ===== TAB 4: THỐNG KÊ =====
    with tab4:
        st.markdown("### 🎨 Thống kê Layout & Màu sắc")
        if 'Layout & Màu' in st.session_state.caption_df.columns:
            layout_counts = st.session_state.caption_df['Layout & Màu'].value_counts()
            for layout, count in layout_counts.items():
                st.markdown(f"- **{layout}**: {count} bộ")
        else:
            st.info("Chưa có dữ liệu layout")
# ===== PHẦN TẢI XUỐNG =====
st.markdown("---")
st.markdown("### 📦 Tải xuống")

# Debug
if st.session_state.get('zip_data'):
    zip_size_mb = len(st.session_state.zip_data) / (1024*1024)
    st.info(f"📦 Dữ liệu ZIP: {zip_size_mb:.1f} MB")
else:
    st.error("❌ Không có dữ liệu để tải. Vui lòng tạo nội dung trước!")

col_dl1, col_dl2, col_dl3 = st.columns(3)

with col_dl1:
    if st.session_state.get('zip_data'):
        st.download_button(
            label="📥 Tải TẤT CẢ Ảnh (ZIP)",
            data=st.session_state.zip_data,
            file_name=f"riviu_banners_{datetime.now().strftime('%Y%m%d_%H%M')}.zip",
            mime="application/zip",
            key="download_zip",  # Thêm key cố định
            use_container_width=True
        )
    else:
        st.warning("⚠️ Chưa có dữ liệu")

with col_dl2:
    if st.session_state.get('excel_data'):
        st.download_button(
            label="📊 Tải Caption (Excel)",
            data=st.session_state.excel_data,
            file_name=f"riviu_captions_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_excel",
            use_container_width=True
        )
    else:
        st.warning("⚠️ Chưa có dữ liệu")

with col_dl3:
    if st.session_state.get('partner_logs'):
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
            key="download_log",
            use_container_width=True
        )
    else:
        st.warning("⚠️ Chưa có dữ liệu")

st.markdown("---")
st.caption("Made by Hữu Thiện | Ảnh xuất ra chất lượng cao - Layout đa dạng - Màu sắc đồng bộ")