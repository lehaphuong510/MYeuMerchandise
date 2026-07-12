import streamlit as st
import pandas as pd
import os
import time

# --- KHỞI TẠO BIẾN TRẠNG THÁI (SESSION STATE) ---
if "search_query" not in st.session_state:
    st.session_state.search_query = ""
if "success_msg" not in st.session_state:
    st.session_state.success_msg = ""

# --- CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="MYÊU MERCHANDISE", layout="centered")

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
    .main-title span {
        display: block;
        white-space: nowrap; 
    }
    .highlight-text {
        color: #C71585;
        font-weight: bold;
        font-size: 1.1rem;
    }
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

# Hiển thị Title
st.markdown('<div class="main-title"><span>MYÊU MERCHANDISE</span><span>PICK AT EVENT</span></div>', unsafe_allow_html=True)

if st.session_state.success_msg:
    st.success(st.session_state.success_msg)
    st.session_state.success_msg = "" 

# --- THIẾT LẬP DỮ LIỆU ---
GSHEET_URL = "https://docs.google.com/spreadsheets/d/1tHLQoD_HkU9l_aqXnidH840y_KjO-T9F_3lGpRfQqW4/export?format=csv&gid=724869545"
DELIVERED_FILE = "delivered_log.csv"

@st.cache_data(ttl=5)
def load_main_data():
    try:
        df = pd.read_csv(GSHEET_URL, dtype=str)
        
        # BẢO HIỂM 1: Gọt sạch các khoảng trắng dư thừa ở tên cột
        df.columns = df.columns.str.strip()
        
        if '4 Số đuôi' in df.columns:
            df['4 Số đuôi'] = df['4 Số đuôi'].str.replace('.0', '', regex=False).str.zfill(4)
        if 'ĐT' in df.columns:
            df['ĐT'] = df['ĐT'].str.replace('.0', '', regex=False)
        return df
    except Exception as e:
        st.error("Chưa kết nối được Google Sheet. Vui lòng kiểm tra lại link.")
        return pd.DataFrame()

def load_delivered_data():
    if os.path.exists(DELIVERED_FILE):
        return pd.read_csv(DELIVERED_FILE)
    return pd.DataFrame(columns=["ĐT", "Tên Hàng"])

def mark_as_delivered(phone, item_name):
    new_record = pd.DataFrame([{"ĐT": str(phone), "Tên Hàng": item_name}])
    if os.path.exists(DELIVERED_FILE):
        new_record.to_csv(DELIVERED_FILE, mode='a', header=False, index=False)
    else:
        new_record.to_csv(DELIVERED_FILE, index=False)

df_main = load_main_data()
df_delivered = load_delivered_data()

# Tạo cột Tên Hàng (gộp Tên + Size)
if not df_main.empty:
    def get_full_item(row):
        merch = str(row.get('Loại Merchandise', '')).strip()
        size = str(row.get('Size áo', '')).strip()
        
        # BẢO HIỂM TỰ ĐỘNG GỌT CHỮ SIZE ĐỂ KHÔNG BỊ LẶP
        if size.lower().startswith('size'):
            size = size[4:].strip()

        if pd.notna(row.get('Size áo')) and size != '' and size.lower() != 'nan':
            return f"{merch} (Size {size})"
        return merch
    df_main['Tên Hàng'] = df_main.apply(get_full_item, axis=1)

# --- TÍNH NĂNG TÌM KIẾM ---
st.markdown('**Số điện thoại của người nhận:**')
st.markdown('*Chỉ cần gõ 4 số đuôi điện thoại, trong trường hợp có người trùng 4 số đuôi, hệ thống sẽ hiện yêu cầu nhập full số điện thoại*')

search_input = st.text_input("Nhập số điện thoại vào đây", label_visibility="collapsed")

if st.button("Tìm giúp MYêu"):
    st.session_state.search_query = search_input

if st.session_state.search_query:
    clean_input = st.session_state.search_query.replace(" ", "")
    if len(clean_input) <= 4:
        matched_df = df_main[df_main['4 Số đuôi'].str.contains(clean_input, na=False)]
    else:
        core_phone = clean_input.lstrip("0")
        matched_df = df_main[df_main['ĐT'].astype(str).str.replace(" ", "", regex=False).str.contains(core_phone, na=False)]

    if matched_df.empty:
        st.warning("Không tìm thấy thông tin phù hợp!")
    else:
        unique_phones = matched_df['ĐT'].unique()
        if len(unique_phones) > 1:
            st.error("⚠️ Nhập full số điện thoại nha (Có nhiều người trùng 4 số đuôi này)")
        else:
            user_name = matched_df.iloc[0].get('Tên', 'Không rõ')
            st.markdown(f"**Thông tin người nhận:** <span class='highlight-text'>{user_name}</span>", unsafe_allow_html=True)
            st.markdown("---")
            
            for index, row in matched_df.iterrows():
                phone_val = str(row['ĐT'])
                merch_val = str(row.get('Loại Merchandise', ''))
                qty_val = row.get('SL', '0')
                size_val = str(row.get('Size áo', '')).strip()
                
                # Làm sạch size_val trên giao diện người nhận
                if size_val.lower().startswith('size'):
                    size_val = size_val[4:].strip()
                    
                full_item_name = row['Tên Hàng'] 
                
                is_delivered = False
                if not df_delivered.empty:
                    check = df_delivered[(df_delivered['ĐT'] == phone_val) & (df_delivered['Tên Hàng'] == full_item_name)]
                    if not check.empty:
                        is_delivered = True

                with st.container(border=True):
                    st.markdown(f"**Merchandise:** <span class='highlight-text'>{merch_val}</span>", unsafe_allow_html=True)
                    if pd.notna(row.get('Size áo')) and size_val != '' and size_val.lower() != 'nan':
                        st.markdown(f"**Size áo:** <span class='highlight-text'>{size_val}</span>", unsafe_allow_html=True)
                    st.markdown(f"**Số lượng:** <span class='highlight-text'>{qty_val}</span>", unsafe_allow_html=True)
                    
                    if is_delivered:
                        st.button("✅ Đã nhận hàng", key=f"done_{index}", disabled=True)
                    else:
                        if st.button("Đã giao hàng", key=f"deliver_{index}"):
                            mark_as_delivered(phone_val, full_item_name)
                            st.session_state.success_msg = "✅ Đã ghi nhận và cập nhật Kho thành công!"
                            st.rerun()

# --- THỐNG KÊ KHO (CUSTOM HTML TABLE) ---
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
        
        # BẢO HIỂM 2 & 3: Dùng .get() và gom logic xử lý an toàn
        if 'Size áo' in merch_df.columns:
            sizes = merch_df['Size áo'].dropna().unique()
        else:
            sizes = []
            
        valid_sizes = [s for s in sizes if str(s).strip() != '' and str(s).lower() != 'nan']
        
        # Hàm làm sạch size cho việc sort và hiển thị
        def clean_size_for_sort(sz):
            sz = str(sz).strip()
            if sz.lower().startswith('size'):
                sz = sz[4:].strip()
            return sz.upper()
            
        size_order = {"S": 1, "M": 2, "L": 3, "XL": 4, "XXL": 5}
        valid_sizes.sort(key=lambda x: size_order.get(clean_size_for_sort(x), 99))
        
        size_rows_html = ""
        total_delivered_for_merch = 0
        
        for raw_size in valid_sizes:
            clean_size = clean_size_for_sort(raw_size)
            full_item_name = f"{merch} (Size {clean_size})"
            size_df = merch_df[merch_df['Size áo'] == raw_size]
            size_sl = size_df['SL'].sum()
            
            size_delivered = len(df_delivered[df_delivered['Tên Hàng'] == full_item_name]) if not df_delivered.empty else 0
            size_remain = size_sl - size_delivered
            total_delivered_for_merch += size_delivered
            
            size_rows_html += f"<tr style='border-bottom: 1px solid #eee;'>"
            size_rows_html += f"<td style='text-align: left; padding: 8px 10px 8px 30px; color: #444; font-size: 0.95rem;'>↳ Size {clean_size}</td>"
            size_rows_html += f"<td style='padding: 8px;'>{int(size_sl)}</td>"
            size_rows_html += f"<td style='padding: 8px;'>{int(size_delivered)}</td>"
            size_rows_html += f"<td style='padding: 8px;'>{int(size_remain)}</td></tr>"
            
        no_size_delivered = len(df_delivered[df_delivered['Tên Hàng'] == merch]) if not df_delivered.empty else 0
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

# --- ADMIN VIEW ---
st.markdown("---")
with st.expander("🛠️ Admin: Quản lý File Giao Hàng & Reset"):
    st.markdown("**Cách lấy file data đầu ra:** Chỉ cần bấm vào nút tải xuống bên dưới.")
    
    # ÉP CHUẨN UTF-8-SIG (CÓ BOM) ĐỂ EXCEL KHÔNG BỊ LỖI FONT TIẾNG VIỆT
    if not df_delivered.empty:
        csv_data = df_delivered.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Tải file Danh sách Đã giao hàng (.csv)",
            data=csv_data,
            file_name="danh_sach_da_giao.csv",
            mime="text/csv"
        )
    else:
        st.info("Chưa có ai nhận hàng nên chưa có file.")
        
    st.warning("⚠️ Nút này sẽ xóa toàn bộ lịch sử test!")
    if st.button("Xóa trắng dữ liệu Test"):
        if os.path.exists(DELIVERED_FILE):
            os.remove(DELIVERED_FILE)
            st.session_state.success_msg = "✅ Đã reset thành công! Bắt đầu test mới."
            st.rerun()
