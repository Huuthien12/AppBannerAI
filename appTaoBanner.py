import streamlit as st
import pandas as pd
import os
import random
from PIL import Image, ImageDraw, ImageFont, ImageOps
import unicodedata
import io
import zipfile
import google.generativeai as genai

# --- PAGE CONFIG (BẮT BUỘC ĐẶT ĐẦU TIÊN) ---
st.set_page_config(page_title="Riviu TikTok AI", layout="wide")

# --- KHỞI TẠO SESSION STATE ---
if 'zip_data' not in st.session_state:
    st.session_state.zip_data = None
if 'excel_data' not in st.session_state:
    st.session_state.excel_data = None
if 'caption_df' not in st.session_state:
    st.session_state.caption_df = None
if 'processing' not in st.session_state:
    st.session_state.processing = False

# --- CẤU HÌNH ĐƯỜNG DẪN VÀ FONT ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.join(BASE_DIR, "20quanlocal")
LOGO_PATH = os.path.join(BASE_DIR, "logo_riviu.png")
TARGET_SIZE = (900, 1180)
FONTS_LIST = ["arial.ttf", "tahoma.ttf", "verdana.ttf", "times.ttf"]

# Cấu hình Gemini (Lưu ý: API Key cứng chỉ dùng cho demo, nên dùng st.secrets khi deploy)
genai.configure(api_key="AIzaSyDeI7pTn88ybzzK6zDnclofy5ZVLbkDRoU")
model = genai.GenerativeModel('gemini-1.5-flash')

def normalize_text(text):
    if not isinstance(text, str): return ""
    return unicodedata.normalize('NFKC', text).strip().lower()

# --- HÀM XỬ LÝ ẢNH (GIỮ NGUYÊN LOGIC CỦA BẠN) ---
def draw_location_pin(draw, x, y, size=23):
    """Vẽ icon ghim đỏ 📍: Chỉnh stick dài ra, dịch qua phải và xuống dưới"""
    red_color = "#FF1A1A"
    stick_color = "#0B0A0A"
    x_offset = 15 
    y_offset = 17 
    new_x = x + x_offset
    new_y = y + y_offset
    stick_length_factor = 0.7
    stick_height = size * stick_length_factor
    stick_w = 3
    circle_r = size * 0.35
    circle_center = (new_x + size / 2, new_y - stick_height)
    stick_start = (new_x + size / 2, new_y + size / 2)
    stick_end = (circle_center[0], circle_center[1] - circle_r - 5)
    draw.line([stick_start, stick_end], fill=stick_color, width=stick_w)
    draw.ellipse([circle_center[0] - circle_r, circle_center[1] - circle_r, 
                  circle_center[0] + circle_r, circle_center[1] + circle_r], fill=red_color)
    highlight_r = circle_r * 0.4
    draw.ellipse([circle_center[0] - highlight_r, circle_center[1] - highlight_r, 
                  circle_center[0], circle_center[1]], fill="#FF6666")

def add_text_to_image(image_pil, ten, gio, dc):
    img = ImageOps.fit(image_pil.convert("RGB"), TARGET_SIZE, centering=(0.5, 0.5))
    draw = ImageDraw.Draw(img, "RGBA")
    width, height = img.size
    
    chosen_font_path = random.choice(FONTS_LIST)
    try:
        font_ten = ImageFont.truetype(chosen_font_path, 52)
        font_info = ImageFont.truetype(chosen_font_path, 24)
    except:
        font_ten = font_info = ImageFont.load_default()

    overlay_h = 210
    draw.rectangle([0, height - overlay_h, width, height], fill=(0, 0, 0, 170))

    margin = 45
    draw.text((margin, height - 175), ten.upper(), fill="white", font=font_ten)
    draw.text((margin, height - 110), f"Giờ mở cửa: {gio}", fill="#FFD700", font=font_info)
    
    pin_y = height - 72
    draw_location_pin(draw, margin, pin_y, size=25)
    draw.text((margin + 50, height - 75), f"{dc}", fill="#E0E0E0", font=font_info)

    if os.path.exists(LOGO_PATH):
        logo = Image.open(LOGO_PATH).convert("RGBA")
        logo.thumbnail((110, 110))
        img.paste(logo, (width - logo.width - 30, 30), logo)
    return img

def generate_bulk_caption(list_quan):
    names_str = ", ".join(list_quan)
    prompt = f"""
    Viết nội dung review cho các quán cafe: {names_str}.
    1. FB: Viết dài, chém gió nghệ thuật, lôi cuốn về không gian Đà Lạt.
    2. TT: Viết cực ngắn, văn vở thả thính, súc tích.
    3. TikTok phải có đúng 5 hashtag ở cuối.
    Định dạng trả về duy nhất là:
    FB: [nội dung]
    TT: [nội dung]
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.replace("**", "").replace("###", "").strip()
        if "TT:" in text:
            parts = text.split("TT:")
            fb = parts[0].replace("FB:", "").strip()
            tt = parts[1].strip()
            return fb, tt
        else:
            return text, "Góc nhỏ cho kẻ mộng mơ. #dalat #cafe #chill #review #coffee"
    except Exception as e:
        st.error(f"Lỗi API: {e}")
        return "Đà Lạt luôn biết cách vỗ về tâm hồn bằng những góc nhỏ thân quen...", "Một chút ngọt ngào cho ngày xanh nắng nhẹ. #dalat #cafe #chill #review #coffee"

# --- GIAO DIỆN CHÍNH (LAYOUT GIỐNG ẢNH) ---

# Sidebar hoàn toàn trống để tập trung vào Main Layout
with st.sidebar:
    st.empty()

# Tiêu đề chính (Có thể ẩn đi nếu muốn)
# st.title("Riviu TikTok AI") 

# ==============================================
# BLOCK 1: DỮ LIỆU F&B (EXCEL/CSV)
# ==============================================
st.markdown("### 1. Dữ liệu F&B (Excel/CSV)")
st.caption("Tài liệu Excel (.xlsx) chứa dữ liệu quán án (Cột: TÊN QUÁN, Mô hình, ĐỊA CHỈ,...).")

col1_file, col2_status = st.columns([3, 1])
with col1_file:
    uploaded_file = st.file_uploader("Chọn file", type=['csv', 'xlsx'], label_visibility="collapsed", key="file_uploader")
with col2_status:
    if uploaded_file:
        st.success("✅ Đã tải file")
    else:
        st.warning("⏳ Chưa tải file")

# ==============================================
# BLOCK 2: THƯ MỤC HÌNH NỀN
# ==============================================
st.markdown("### 2. Thư mục Hình Nền")
st.caption("Chọn folder chứa ảnh nền chung cho toàn bộ các thiết kế.")

col1_folder, col2_status_folder = st.columns([3, 1])
with col1_folder:
    # Streamlit không hỗ trợ upload folder trực tiếp, chỉ hỗ trợ multiple files.
    # Nhưng để giống giao diện ảnh, ta dùng text input mô phỏng hoặc upload nhiều file.
    st.text_input("Đường dẫn thư mục", value=f"{ROOT_DIR}", disabled=True, key="folder_path", label_visibility="collapsed")
with col2_status_folder:
    if os.path.exists(ROOT_DIR) and len(os.listdir(ROOT_DIR)) > 0:
        st.success("✅ Đã kết nối")
    else:
        st.error("❌ Chưa có dữ liệu")

# ==============================================
# BLOCK 3: CẤU HÌNH & RENDER
# ==============================================
st.markdown("### 3. Cấu hình & Render")

col_left, col_right = st.columns([1, 1])
with col_left:
    num_sets = st.number_input("Số bộ ảnh xuất (Set):", min_value=1, value=2, step=1)
with col_right:
    imgs_per_set = st.number_input("Số ảnh mỗi bộ:", min_value=1, value=10, step=1)

st.markdown("**Tích hợp Trí tuệ AI (Gemini + Deepseek)**")
st.caption("Nhập API Key của Google Gemini và Deepseek. Nếu Gemini thất bại, hệ thống sẽ tự động chuyển sang Deepseek nếu có Key.")

# Giả lập input API Key (thực tế bạn có thể dùng st.text_input để nhập)
gemini_key = st.text_input("Gemini API Key", type="password", value="AIzaSyDeI7pTn88ybzzK6zDnclofy5ZVLbkDRoU"[:10] + "..." if st.session_state.get('gemini_hidden') else "", placeholder="Nhập Gemini API Key")

deepseek_key = st.text_input("Deepseek API Key", type="password", placeholder="Nhập Deepseek API Key (Tùy chọn)")

# Nút Lưu và Nút Render
col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
with col_btn1:
    st.button("💾 Lưu", use_container_width=True)
with col_btn2:
    render_btn = st.button("🚀 Xuất nội dung", type="primary", use_container_width=True)

st.divider()

# ==============================================
# BLOCK 4: BẢN XEM TRƯỚC (PREMIUM LIST)
# ==============================================
st.markdown("### Bản Xem Trước (Premium List)")

# Thanh công cụ nhỏ
col_copy, col_partner = st.columns([1, 5])
with col_copy:
    st.button("📋 Sao chép", use_container_width=True)
with col_partner:
    st.button("👥 Danh sách đối tác", use_container_width=True)

# Hiển thị nội dung Preview (Gợi ý quán cafe đẹp)
if st.session_state.caption_df is not None and not st.session_state.caption_df.empty:
    for _, row in st.session_state.caption_df.iterrows():
        with st.container(border=True):
            st.caption(f"🔥 Gợi ý quán cafe đẹp - {row['Bộ']}")
            st.write("**Facebook:**", row['FB'])
            st.code(row['TT'], language="markdown") # Hiển thị dạng code dễ copy
else:
    st.info("Chưa có dữ liệu xem trước. Vui lòng cấu hình và nhấn 'Xuất nội dung'.")

# ==============================================
# LOGIC XỬ LÝ KHI NHẤN NÚT "XUẤT NỘI DUNG"
# ==============================================
if render_btn:
    if uploaded_file and os.path.exists(ROOT_DIR):
        try:
            # Đọc file Excel/CSV
            df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file, encoding='utf-8-sig')
            df.columns = [c.strip() for c in df.columns]
            
            # Kiểm tra cột bắt buộc
            if 'Tên Quán' not in df.columns:
                st.error("File Excel cần có cột 'Tên Quán'")
                st.stop()
                
            existing_folders = {normalize_text(d): d for d in os.listdir(ROOT_DIR) if os.path.isdir(os.path.join(ROOT_DIR, d))}
            
            all_captions = []
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_f:
                progress_bar = st.progress(0, text="Đang tạo ảnh...")
                total_sets = int(num_sets)
                
                for set_idx in range(total_sets):
                    current_set_quans = []
                    # Lấy mẫu ngẫu nhiên từ dataframe
                    df_set = df.sample(n=min(len(df), imgs_per_set))
                    
                    for idx, (_, row) in enumerate(df_set.iterrows()):
                        ten = str(row['Tên Quán'])
                        gio = str(row.get('Thời gian mở cửa', '7:00 - 22:00'))
                        dc = str(row.get('Địa chỉ', 'Đà Lạt'))
                        
                        key = normalize_text(ten)
                        if key in existing_folders:
                            f_path = os.path.join(ROOT_DIR, existing_folders[key])
                            imgs = [f for f in os.listdir(f_path) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
                            if imgs:
                                img_path = os.path.join(f_path, random.choice(imgs))
                                banner = add_text_to_image(Image.open(img_path), ten, gio, dc)
                                buf = io.BytesIO()
                                banner.save(buf, format='JPEG', quality=90)
                                zip_f.writestr(f"Bo_{set_idx+1}/{ten}.jpg", buf.getvalue())
                                current_set_quans.append(ten)
                    
                    if current_set_quans:
                        fb, tt = generate_bulk_caption(current_set_quans)
                        all_captions.append({"Bộ": f"Bộ {set_idx+1}", "FB": fb, "TT": tt})
                    
                    progress_bar.progress((set_idx + 1) / total_sets, text=f"Đã xử lý bộ {set_idx+1}/{total_sets}")
                
                progress_bar.empty()

            # Lưu vào session state để hiển thị preview và download
            st.session_state.zip_data = zip_buffer.getvalue()
            st.session_state.caption_df = pd.DataFrame(all_captions)
            excel_buf = io.BytesIO()
            st.session_state.caption_df.to_excel(excel_buf, index=False)
            st.session_state.excel_data = excel_buf.getvalue()
            
            st.success("✅ Xử lý hoàn tất!")
            st.rerun() # Reload để hiển thị nút tải xuống

        except Exception as e:
            st.error(f"Lỗi hệ thống: {e}")
    else:
        if not uploaded_file:
            st.error("❌ Vui lòng tải file dữ liệu F&B ở mục 1.")
        if not os.path.exists(ROOT_DIR):
            st.error(f"❌ Không tìm thấy thư mục ảnh nền: {ROOT_DIR}")

# ==============================================
# NÚT TẢI XUỐNG (HIỂN THỊ KHI CÓ DỮ LIỆU)
# ==============================================
if st.session_state.zip_data:
    st.divider()
    st.markdown("### 📦 Tải xuống kết quả")
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        st.download_button(
            label="📥 Tải Ảnh Banners (Zip)",
            data=st.session_state.zip_data,
            file_name="riviu_banners.zip",
            mime="application/zip",
            use_container_width=True
        )
    with col_dl2:
        st.download_button(
            label="📊 Tải Caption (Excel)",
            data=st.session_state.excel_data,
            file_name="riviu_captions.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )