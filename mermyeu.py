import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials

# --- CẤU HÌNH BẢO MẬT & SESSION ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "admin_id" not in st.session_state:
    st.session_state.admin_id = ""
if "search_query" not in st.session_state:
    st.session_state.search_query = ""
if "success_msg" not in st.session_state:
    st.session_state.success_msg = ""
if "just_delivered" not in st.session_state:
    st.session_state.just_delivered = False

VALID_PASSWORDS = {"CHECKIN-AN": "An", "CHECKIN-BINH": "Bình", "CHECKIN-CHAU": "Châu", "0519": "Lê Phương"}

if not st.session_state.authenticated:
    st.markdown("### 🔒 Cổng kiểm soát nội bộ (Trạm Nhập Liệu)")
    password = st.text_input("Nhập mã truy cập cá nhân:", type="password")
    
    if st.button("Đăng nhập"):
        if password in VALID_PASSWORDS: 
            st.session_state.authenticated = True
            st.session_state.admin_id = VALID_PASSWORDS[password] 
            st.rerun()
        else:
            st.error("Mã không hợp lệ hoặc đã bị vô hiệu hóa!")
    st.stop()

# --- CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="MYÊU MERCHANDISE - CHECKER", layout="centered")

st.markdown("""
<style>
    .main-title {
        color: #C71585;
        text-shadow: 2px 2px 0px #e6d3d3, 4px 4px 5px rgba(0,0,0,0.4);
        text-align: left;
        font-weight: 900;
        font-size: 2.5rem;
        line-height: 1.2;
        margin-bottom: 25px;
    }
    .main-title span { display: block; white-space: nowrap; }
    .highlight-text { color: #C71585; font-weight: bold; font-size: 1.1rem; }
    .section-title {
        background: linear-gradient(90deg, #C71585, #8B008B);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 900;
        font-size: 2.0rem;
        margin-top: 20px;
        margin-bottom: 15px;
        text-align: left;
    }
    div.stButton > button {
        background: linear-gradient(90deg, #C71585, #8B008B) !important;
        color: white !important;
        border: none !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        transition: 0.3s;
    }
    div.stButton > button:hover {
        background: linear-gradient(90deg, #8B008B, #C71585) !important;
        box-shadow: 0px 4px 10px rgba(139, 0, 139, 0.4) !important;
    }
    @media screen and (max-width: 768px) {
        .main-title { font-size: 1.6rem; }
        .section-title { font-size: 1.2rem; white-space: nowrap; }
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title"><span>MYÊU MERCHANDISE</span><span>PICK AT EVENT</span></div>', unsafe_allow_html=True)
st.caption(f"👤 Đang trực ca: **{st.session_state.admin_id}**")

if st.session_state.success_msg:
    st.success(st.session_state.success_msg)
    st.session_state.success_msg = "" 

# --- THIẾT LẬP DỮ LIỆU ---
GSHEET_URL = "https://docs.google.com/spreadsheets/d/1tHLQoD_HkU9l_aqXnidH840y_KjO-T9F_3lGpRfQqW4/export?format=csv&gid=724869545"
OUTPUT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1zSeYfiaSFJNdXMOZnwG7WsW0b33v-rbt0EruvMS_aA0/edit"

# --- KẾT NỐI GOOGLE SHEETS API ---
@st.cache_resource
def get_gspread_client():
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

client = get_gspread_client()

@st.cache_data(ttl=5)
def load_main_data():
    try:
        df = pd.read_csv(GSHEET_URL, dtype=str)
        df.columns = df.columns.str.strip()
        if '4 Số đuôi' in df.columns:
            df['4 Số đuôi'] = df['4 Số đuôi'].str.replace('.0', '', regex=False).str.zfill(4)
        if 'ĐT' in df.columns:
            df['ĐT'] = df['ĐT'].str.replace('.0', '', regex=False)
        return df
    except Exception as e:
        st.error("Chưa kết nối được Google Sheet Đầu Vào.")
        return pd.DataFrame()

def load_delivered_data():
    try:
        sheet = client.open_by_url(OUTPUT_SHEET_URL).sheet1
        records = sheet.get_all_records()
        if records:
            return pd.DataFrame(records)
        # Cập nhật đúng 10 cột như m set up
        return pd.DataFrame(columns=["Thời Gian", "ĐT", "Tên", "Mã đơn hàng", "Loại Merchandise", "Size áo", "SL", "Người Giao", "Status", "Link hình"])
    except Exception as e:
        st.warning(f"Chưa đọc được Sheet Đầu Ra: {e}")
        return pd.DataFrame(columns=["Thời Gian", "ĐT", "Tên", "Mã đơn hàng", "Loại Merchandise", "Size áo", "SL", "Người Giao", "Status", "Link hình"])

# HÀM UPDATE 10 CỘT LÊN SHEET (Bao gồm các biến m hỏi)
def mark_as_delivered(phone, user_name, order_code, merch_type, size, qty, admin_name):
    current_time = (datetime.utcnow() + timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")
    sheet = client.open_by_url(OUTPUT_SHEET_URL).sheet1
    
    # 10 cột chuẩn: Thời Gian - ĐT - Tên - Mã đơn hàng - Loại Merchandise - Size áo - SL - Người Giao - Status - Link hình
    row_data = [
        current_time, 
        str(phone), 
        str(user_name), 
        str(order_code), 
        str(merch_type), 
        str(size), 
        str(qty), 
        str(admin_name), 
        "Pending", 
        "" 
    ]
    sheet.append_row(row_data)

df_main = load_main_data()
df_delivered = load_delivered_data()

# --- TÍNH NĂNG TÌM KIẾM ---
search_mode = st.radio("Chọn chế độ tìm kiếm:", ["Tìm theo Mã đơn hàng", "Tìm theo Số điện thoại"], horizontal=True)
search_input = st.text_input("Nhập thông tin tìm kiếm vào đây", label_visibility="collapsed")

if st.button("Tìm giúp MYêu"):
    st.session_state.search_query = search_input
    st.session_state.search_mode = search_mode 
    st.session_state.just_delivered = False 

if st.session_state.search_query:
    clean_input = st.session_state.search_query.replace(" ", "").upper()
    
    df_main['Mã_Search'] = df_main['Mã đơn hàng'].astype(str).str.strip().str.replace(" ", "").str.upper()
    df_main['SĐT_Clean'] = df_main['ĐT'].astype(str).str.replace(" ", "", regex=False).str.lstrip("0")
    df_main['4_Số_Cuối'] = df_main['SĐT_Clean'].str[-4:]
    
    if st.session_state.search_mode == "Tìm theo Mã đơn hàng":
        if len(clean_input) <= 3:
            matched_df = df_main[df_main['Mã_Search'].str.endswith(clean_input, na=False)]
        else:
            matched_df = df_main[df_main['Mã_Search'].str.contains(clean_input, na=False)]
    else:
        matched_df = df_main[df_main['4_Số_Cuối'].str.endswith(clean_input, na=False) | df_main['SĐT_Clean'].str.contains(clean_input, na=False)]

    if matched_df.empty:
        st.warning("Không tìm thấy thông tin phù hợp!")
    else:
        is_duplicate = False
        if st.session_state.search_mode == "Tìm theo Số điện thoại":
            unique_phones = matched_df['ĐT'].unique()
            if len(unique_phones) > 1:
                is_duplicate = True

        if is_duplicate:
            st.error("⚠️ Có nhiều người trùng 4 số đuôi này! Vui lòng nhập FULL Số điện thoại.")
        else:
            user_name = matched_df.iloc[0].get('Tên', 'Không rõ')
            st.markdown(f"**Thông tin người nhận:** <span class='highlight-text'>{user_name}</span>", unsafe_allow_html=True)
            st.markdown("---")
            
            # --- LÀM SẠCH DATA ĐÃ GIAO DỰA TRÊN CỘT MỚI ---
            if not df_delivered.empty and 'ĐT' in df_delivered.columns and 'Loại Merchandise' in df_delivered.columns:
                df_delivered['ĐT_Clean'] = df_delivered['ĐT'].astype(str).str.strip().str.lstrip("0").str.replace(".0", "", regex=False)
                df_delivered['Merch_Clean'] = df_delivered['Loại Merchandise'].astype(str).str.strip()
                df_delivered['Size_Clean'] = df_delivered['Size áo'].astype(str).str.strip().str.replace("nan", "", case=False)
            
            # --- KIỂM TRA ĐÃ NHẬN ĐỦ CHƯA ---
            total_items = len(matched_df)
            delivered_count = 0
            for _, row in matched_df.iterrows():
                phone_val = str(row['ĐT']).strip().lstrip("0").replace(".0", "")
                merch_val = str(row.get('Loại Merchandise', '')).strip()
                
                size_val = str(row.get('Size áo', '')).strip()
                if size_val.lower().startswith('size'):
                    size_val = size_val[4:].strip()
                if size_val.lower() == 'nan': size_val = ""

                if not df_delivered.empty and 'ĐT_Clean' in df_delivered.columns:
                    check = df_delivered[(df_delivered['ĐT_Clean'] == phone_val) & 
                                         (df_delivered['Merch_Clean'] == merch_val) & 
                                         (df_delivered['Size_Clean'] == size_val)]
                    if not check.empty: delivered_count += 1
                        
            if delivered_count == total_items and not st.session_state.just_delivered:
                st.success("✅ BẠN NÀY ĐÃ NHẬN TOÀN BỘ HÀNG RỒI!")
                st.info("Hệ thống đã ẩn chi tiết để tránh nhầm lẫn. Chuyển sang quét bạn tiếp theo nha!")
            else:
                for index, row in matched_df.iterrows():
                    raw_phone = str(row['ĐT'])
                    phone_val = raw_phone.strip().lstrip("0").replace(".0", "")
                    order_code = str(row.get('Mã đơn hàng', '')).strip()
                    user_name_row = str(row.get('Tên', '')).strip()
                    
                    merch_val = str(row.get('Loại Merchandise', '')).strip()
                    qty_val = row.get('SL', '0')
                    size_val = str(row.get('Size áo', '')).strip()
                    if size_val.lower().startswith('size'):
                        size_val = size_val[4:].strip()
                    if size_val.lower() == 'nan': size_val = ""
                    
                    with st.container(border=True):
                        if st.session_state.search_mode == "Tìm theo Mã đơn hàng":
                            hidden_phone = "xxx" + str(raw_phone)[-4:] if len(str(raw_phone)) >= 4 else "xxx" + str(raw_phone)
                            st.markdown(f"**SĐT:** <span class='highlight-text'>{hidden_phone}</span>", unsafe_allow_html=True)
                        else:
                            if order_code and order_code.lower() != 'nan':
                                hidden_order = "xxx" + order_code
                                st.markdown(f"**Mã ĐH:** <span class='highlight-text'>{hidden_order}</span>", unsafe_allow_html=True)

                        st.markdown(f"**Merchandise:** <span class='highlight-text'>{merch_val}</span>", unsafe_allow_html=True)
                        if size_val != '':
                            st.markdown(f"**Size áo:** <span class='highlight-text'>{size_val}</span>", unsafe_allow_html=True)
                        st.markdown(f"**Số lượng:** <span class='highlight-text'>{qty_val}</span>", unsafe_allow_html=True)
                        
                        is_delivered = False
                        if not df_delivered.empty and 'ĐT_Clean' in df_delivered.columns:
                            check = df_delivered[(df_delivered['ĐT_Clean'] == phone_val) & 
                                                 (df_delivered['Merch_Clean'] == merch_val) & 
                                                 (df_delivered['Size_Clean'] == size_val)]
                            if not check.empty: is_delivered = True

                        if is_delivered:
                            st.button("✅ Đã nhận hàng", key=f"done_{index}", disabled=True)
                        else:
                            # ĐÂY LÀ ĐOẠN ĐÃ TRUYỀN ĐỦ BIẾN NHƯ M HỎI
                            if st.button("Đã giao hàng", key=f"deliver_{index}"):
                                mark_as_delivered(raw_phone, user_name_row, order_code, merch_val, size_val, qty_val, st.session_state.admin_id)
                                st.session_state.success_msg = "✅ Đã ghi nhận thành công!"
                                st.session_state.just_delivered = True 
                                st.rerun()

# --- THỐNG KÊ KHO ---
st.markdown("---")
st.markdown('<div class="section-title">📊 THỐNG KÊ KHO MERCHANDISE</div>', unsafe_allow_html=True)

if not df_main.empty:
    df_main['SL'] = pd.to_numeric(df_main.get('SL', 0), errors='coerce').fillna(0)
    
    html_table = "<table style='width: 100%; border-collapse: collapse; font-family: sans-serif; text-align: center; margin-bottom: 20px;'>"
    html_table += "<tr style='border-bottom: 2px solid #8B008B; color: #8B008B; background-color: #f9f9f9;'>"
    html_table += "<th style='text-align: left; padding: 12px;'>Loại Merchandise</th>"
    html_table += "<th style='padding: 12px;'>Tổng SL</th>"
    html_table += "<th style='padding: 12px;'>Đã nhận</th>"
    html_table += "<th style='padding: 12px;'>Còn lại</th></tr>"
    
    merch_list = df_main.get('Loại Merchandise', pd.Series(dtype=str)).dropna().unique()
    
    for merch in merch_list:
        merch_df = df_main[df_main['Loại Merchandise'] == merch]
        total_sl = merch_df['SL'].sum()
        
        sizes = merch_df['Size áo'].dropna().unique() if 'Size áo' in merch_df.columns else []
        valid_sizes = [s for s in sizes if str(s).strip() != '' and str(s).lower() != 'nan']
        
        def clean_size_for_sort(sz):
            sz = str(sz).strip()
            if sz.lower().startswith('size'): sz = sz[4:].strip()
            return sz.upper()
            
        size_order = {"S": 1, "M": 2, "L": 3, "XL": 4, "XXL": 5}
        valid_sizes.sort(key=lambda x: size_order.get(clean_size_for_sort(x), 99))
        
        size_rows_html = ""
        total_delivered_for_merch = 0
        
        for raw_size in valid_sizes:
            clean_size = clean_size_for_sort(raw_size)
            size_sl = merch_df[merch_df['Size áo'] == raw_size]['SL'].sum()
            
            size_delivered = 0
            if not df_delivered.empty and 'Loại Merchandise' in df_delivered.columns:
                # Đếm dựa trên 2 cột Merchandise và Size
                size_delivered = len(df_delivered[(df_delivered['Loại Merchandise'].astype(str).str.strip() == merch) & 
                                                  (df_delivered['Size áo'].astype(str).str.strip().str.replace("nan", "", case=False) == clean_size)])
            
            size_remain = size_sl - size_delivered
            total_delivered_for_merch += size_delivered
            
            size_rows_html += f"<tr style='border-bottom: 1px solid #eee;'>"
            size_rows_html += f"<td style='text-align: left; padding: 8px 10px 8px 30px; color: #444; font-size: 0.95rem;'>↳ Size {clean_size}</td>"
            size_rows_html += f"<td style='padding: 8px;'>{int(size_sl)}</td>"
            size_rows_html += f"<td style='padding: 8px;'>{int(size_delivered)}</td>"
            size_rows_html += f"<td style='padding: 8px;'>{int(size_remain)}</td></tr>"
            
        if not valid_sizes:
            no_size_delivered = len(df_delivered[df_delivered['Loại Merchandise'].astype(str).str.strip() == merch]) if (not df_delivered.empty and 'Loại Merchandise' in df_delivered.columns) else 0
            total_delivered_for_merch += no_size_delivered
            
        total_remain = total_sl - total_delivered_for_merch
        gradient_style = "padding: 12px; font-weight: bold; background: linear-gradient(90deg, #C71585, #8B008B); -webkit-background-clip: text; -webkit-text-fill-color: transparent;"
        
        html_table += f"<tr style='background-color: #fef5fa; border-top: 1px solid #ddd;'>"
        html_table += f"<td style='text-align: left; {gradient_style}'>{merch}</td>"
        html_table += f"<td style='{gradient_style}'>{int(total_sl)}</td>"
        html_table += f"<td style='{gradient_style}'>{int(total_delivered_for_merch)}</td>"
        html_table += f"<td style='{gradient_style}'>{int(total_remain)}</td></tr>"
        html_table += size_rows_html

    html_table += "</table>"
    st.markdown(html_table, unsafe_allow_html=True)
