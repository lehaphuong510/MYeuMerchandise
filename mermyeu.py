import streamlit as st
import pandas as pd
import os
import time

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
    
    /* FIX 1: Chống rớt chữ cho tiêu đề Thống kê trên mobile */
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

    /* Style cho Nút bấm */
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

    /* Ép size chữ nhỏ lại trên điện thoại để vừa 1 dòng */
    @media screen and (max-width: 768px) {
        .main-title { font-size: 1.6rem; }
        .section-title { 
            font-size: 1.2rem; 
            white-space: nowrap; 
        }
    }
</style>
""", unsafe_allow_html=True)

# Hiển thị Title
st.markdown('<div class="main-title"><span>MYÊU MERCHANDISE</span><span>PICK AT EVENT</span></div>', unsafe_allow_html=True)

# --- THIẾT LẬP DỮ LIỆU ---
GSHEET_URL = "https://docs.google.com/spreadsheets/d/1tHLQoD_HkU9l_aqXnidH840y_KjO-T9F_3lGpRfQqW4/export?format=csv&gid=724869545"
DELIVERED_FILE = "delivered_log.csv"

@st.cache_data(ttl=5)
def load_main_data():
    try:
        df = pd.read_csv(GSHEET_URL, dtype=str)
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

# FIX 2: Tạo cột Tên Hàng (gộp Tên + Size) cho df_main để thống kê chia size
if not df_main.empty:
    def get_full_item(row):
        merch = str(row.get('Loại Merchandise', '')).strip()
        size = str(row.get('Size áo', '')).strip()
        if pd.notna(row.get('Size áo')) and size != '' and size.lower() != 'nan':
            return f"{merch} (Size {size})"
        return merch
    df_main['Tên Hàng'] = df_main.apply(get_full_item, axis=1)

# --- TÍNH NĂNG TÌM KIẾM ---
st.markdown('**Số điện thoại của người nhận:**')
st.markdown('*Chỉ cần gõ 4 số đuôi điện thoại, trong trường hợp có người trùng 4 số đuôi, hệ thống sẽ hiện yêu cầu nhập full số điện thoại*')

search_input = st.text_input("Nhập số điện thoại vào đây", label_visibility="collapsed")

if st.button("Tìm giúp MYêu"):
    if search_input:
        clean_input = search_input.replace(" ", "")
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
                    full_item_name = row['Tên Hàng'] # Tên đã kẹp size
                    
                    is_delivered = False
                    if not df_delivered.empty:
                        check = df_delivered[(df_delivered['ĐT'] == phone_val) & (df_delivered['Tên Hàng'] == full_item_name)]
                        if not check.empty:
                            is_delivered = True

                    with st.container(border=True):
                        st.markdown(f"**Merchandise:** <span class='highlight-text'>{merch_val}</span>", unsafe_allow_html=True)
                        st.markdown(f"**Số lượng:** <span class='highlight-text'>{qty_val}</span>", unsafe_allow_html=True)
                        if pd.notna(size_val) and size_val != '' and size_val.lower() != 'nan':
                            st.markdown(f"**Size áo:** <span class='highlight-text'>{size_val}</span>", unsafe_allow_html=True)
                        
                        if is_delivered:
                            st.button("✅ Đã nhận hàng", key=f"done_{index}", disabled=True)
                        else:
                            if st.button("Đã giao hàng", key=f"deliver_{index}"):
                                mark_as_delivered(phone_val, full_item_name)
                                # FIX 3: Hiện chữ cập nhật thành công và reload lại app
                                st.success("✅ Đã ghi nhận và cập nhật Kho")
                                time.sleep(1.5)
                                st.rerun()

# --- THỐNG KÊ KHO ---
st.markdown("---")
st.markdown('<div class="section-title">📊 THỐNG KÊ KHO MERCHANDISE</div>', unsafe_allow_html=True)

if not df_main.empty:
    # Gom nhóm số liệu theo Tên Hàng (đã phân rã Size)
    df_main['SL'] = pd.to_numeric(df_main['SL'], errors='coerce').fillna(0)
    summary_df = df_main.groupby('Tên Hàng')['SL'].sum().reset_index()
    summary_df.rename(columns={'SL': 'Tổng SL'}, inplace=True)
    
    if not df_delivered.empty:
        delivered_counts = df_delivered.groupby('Tên Hàng').size().reset_index(name='Đã nhận')
        summary_df = pd.merge(summary_df, delivered_counts, on='Tên Hàng', how='left')
    else:
        summary_df['Đã nhận'] = 0
        
    summary_df['Đã nhận'] = summary_df['Đã nhận'].fillna(0).astype(int)
    summary_df['Còn lại'] = summary_df['Tổng SL'] - summary_df['Đã nhận']
    
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

# --- ADMIN VIEW: CÁCH XEM FILE ĐẦU RA ---
st.markdown("---")
with st.expander("🛠️ Admin: Quản lý File Giao Hàng & Reset (Click để mở)"):
    # FIX 4: Hướng dẫn m cách lấy file đầu ra siêu dễ
    st.markdown("""
    **Cách lấy file data đầu ra:** 
    Chỉ cần bấm vào nút tải xuống bên dưới, app sẽ trút toàn bộ data những người đã nhận hàng thành 1 file CSV về máy cho m. Không cần mò lên Cloud tìm chi cho mệt.
    """)
    
    if os.path.exists(DELIVERED_FILE):
        with open(DELIVERED_FILE, "rb") as file:
            st.download_button(
                label="📥 Tải file Danh sách Đã giao hàng (.csv)",
                data=file,
                file_name="danh_sach_da_giao.csv",
                mime="text/csv"
            )
    else:
        st.info("Chưa có ai nhận hàng nên chưa có file.")
        
    st.warning("⚠️ Nút này sẽ xóa toàn bộ lịch sử. Phải bấm 1 lần trước khi test code mới!")
    if st.button("Xóa trắng dữ liệu Test"):
        if os.path.exists(DELIVERED_FILE):
            os.remove(DELIVERED_FILE)
            st.success("Đã reset thành công! Bắt đầu test mới.")
            time.sleep(1)
            st.rerun()
