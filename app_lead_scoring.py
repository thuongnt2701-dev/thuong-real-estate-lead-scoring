import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
import io
import os
import gspread
from google.oauth2.service_account import Credentials

# --- PAGE CONFIG ---
st.set_page_config(page_title="Mino AI Lead Scoring", layout="wide", page_icon="🏠")

# --- AUTHENTICATION & CREDENTIALS ---
CREDENTIALS_FILE = "ai-b7-credentials.json"
SKILL_FILE = "lead_scoring_skill.md"

# --- CUSTOM CSS (PREMIUM DESIGN) ---
def apply_custom_style():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        
        .main { background-color: #f0f2f6; }
        
        /* Custom Metric Cards */
        [data-testid="stMetricValue"] { font-size: 2.2rem; font-weight: 800; color: #1e3a8a; }
        
        /* Sidebar Logo */
        .sidebar-logo { text-align: center; margin-bottom: 20px; }
        
        /* Audit Table Styling */
        .audit-table {
            background-color: #ff4b4b;
            color: white;
            padding: 20px;
            border-radius: 15px;
            border: 2px solid #d32f2f;
        }
        
        /* Button Styling */
        .stButton>button {
            border-radius: 10px;
            height: 3em;
            font-weight: bold;
            text-transform: uppercase;
        }
    </style>
    """, unsafe_allow_html=True)

apply_custom_style()

# --- HELPER FUNCTIONS ---
def get_private_sheet_data(sheet_url):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # Priority: Streamlit Secrets
        if "gcp_service_account" in st.secrets:
            creds_info = dict(st.secrets["gcp_service_account"])
            if "private_key" in creds_info:
                creds_info["private_key"] = creds_info["private_key"].strip().replace("\\n", "\n")
            creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        # Fallback: Local File
        elif os.path.exists(CREDENTIALS_FILE):
            creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scope)
        else:
            st.error("⚠️ Thiếu thông tin xác thực!")
            return None
            
        client = gspread.authorize(creds)
        if "/d/" in sheet_url:
            sheet_id = sheet_url.split("/d/")[1].split("/")[0]
            sheet = client.open_by_key(sheet_id).sheet1
        else:
            sheet = client.open_by_url(sheet_url).sheet1
            
        return pd.DataFrame(sheet.get_all_records())
    except Exception as e:
        st.error(f"❌ Lỗi kết nối Google Sheet: {e}")
        return None

def score_leads_logic(df):
    scored_results = []
    vip_keywords = ["20 tỷ", "tài chính mạnh", "biệt thự", "penthouse", "shophouse", "quận 1", "ven sông", "chủ doanh nghiệp", "nhà đầu tư", "mua sỉ", "sổ hồng riêng"]
    junk_keywords = ["nhầm số", "không có nhu cầu", "dữ liệu cũ", "hỏi giá cho vui", "chưa có ý định", "bảo hiểm", "vay vốn", "thuê bao", "không bắt máy"]
    
    progress_bar = st.progress(0)
    for index, row in df.iterrows():
        desc = str(row.get('nhu_cau_mo_ta', '')).lower()
        score = 0
        reasons = []
        for kw in vip_keywords:
            if kw in desc:
                score += 50
                reasons.append(f"VIP: {kw}")
                break
        for kw in junk_keywords:
            if kw in desc:
                score -= 50
                reasons.append(f"Junk: {kw}")
                break
        
        status = "HOT" if score >= 50 else ("JUNK" if score < 0 else "WARM")
        scored_results.append({"id": row.get('id'), "score": score, "classification": status, "reason": "; ".join(reasons) or "Bình thường"})
        progress_bar.progress((index + 1) / len(df))
    return pd.DataFrame(scored_results)

def score_leads_with_ai(df, api_key):
    if not api_key: return score_leads_logic(df)
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    scored_results = []
    progress_bar = st.progress(0)
    for index, row in df.iterrows():
        prompt = f"Phân tích lead BĐS:\nNhu cầu: {row.get('nhu_cau_mo_ta')}\nTrả về JSON: id, score, classification, reason."
        try:
            response = model.generate_content(prompt)
            clean_json = response.text.strip().replace("```json", "").replace("```", "")
            scored_results.append(json.loads(clean_json))
        except:
            scored_results.append(score_leads_logic(df.iloc[[index]]).to_dict('records')[0])
        progress_bar.progress((index + 1) / len(df))
    return pd.DataFrame(scored_results)

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://mindx.edu.vn/images/logo.png", width=200) # Logo MindX
    st.divider()
    st.title("🛠️ Cấu hình")
    api_key = st.text_input("Gemini API Key", type="password", help="Để trống nếu muốn dùng Logic mặc định")
    sheet_url = st.text_input("Google Sheet URL", value="https://docs.google.com/spreadsheets/d/10yzDP9_uNPgzgMtZYIRYZXmaagXZtEXs_d6PJyB3T1A/edit")
    st.divider()
    st.info("🏠 Ứng dụng BĐS Premium")

# --- MAIN UI ---
st.title("🏠 Hệ thống AI Lead Scoring & Automation")
st.markdown("### Giải pháp tối ưu hóa dữ liệu khách hàng BĐS")
st.divider()

# One-Click Action
if st.button("🚀 Kích hoạt quy trình (Load & Score)", type="primary", use_container_width=True):
    with st.spinner("🤖 Hệ thống đang làm việc..."):
        df_raw = get_private_sheet_data(sheet_url)
        if df_raw is not None:
            st.session_state['df_raw'] = df_raw
            df_scored = score_leads_with_ai(df_raw, api_key)
            st.session_state['df_final'] = pd.merge(df_raw, df_scored, on='id', how='left')
            st.success("✅ Hoàn thành quy trình!")

if 'df_final' in st.session_state:
    st.divider()
    # Dashboard Metrics (3 columns as requested)
    st.subheader("📊 Dashboard Metrics")
    c1, c2, c3 = st.columns(3)
    counts = st.session_state['df_final']['classification'].value_counts()
    c1.metric("👥 Tổng khách hàng", len(st.session_state['df_final']))
    c2.metric("🔥 Khách VIP (+50đ)", counts.get('HOT', 0))
    c3.metric("🗑️ Khách Rác (-50đ)", counts.get('JUNK', 0))
    st.divider()

    st.subheader("📋 Bảng duyệt dữ liệu (Human-in-the-loop)")
    edited_df = st.data_editor(
        st.session_state['df_final'], 
        use_container_width=True,
        column_config={
            "classification": st.column_config.SelectboxColumn("Status", options=["HOT", "WARM", "JUNK"]),
            "nhu_cau_mo_ta": st.column_config.TextColumn("Description", width="large")
        }
    )
    
    st.divider()
    st.subheader("📦 Xuất kết quả bàn giao")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        edited_df.to_excel(writer, index=False, sheet_name='Report')
    
    st.download_button(
        label="📥 Tải File Excel Bàn Giao",
        data=output.getvalue(),
        file_name="Leads_BDS_Handover.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

# --- AUDIT TABLE SECTION ---
with st.expander("📋 Bảng Tổng kết Kiểm tra (Audit)"):
    st.markdown("""
    | Thành tố | Tên File/công cụ | Mô tả |
    | :--- | :--- | :--- |
    | **1. Input** | Google Sheets | 500 khách hàng BĐS |
    | **2. Agent** | Logic chấm điểm | Tự động quét mô tả |
    | **3. Tools** | Streamlit, Pandas, GitHub | Nền tảng xây dựng |
    | **4. Knowledge** | tieu_chi_cham_diem.txt | Quy tắc +50d / -50d |
    | **5. Memory** | st.session_state | Ghi nhớ trạng thái |
    | **6. Workflow** | AI -> Người duyệt -> Excel | Human Checkpoint |
    | **7. Output** | File Excel Bàn Giao | Dữ liệu sạch cho Sales |
    """)

st.divider()
st.caption("Developed with ❤️ for MindX Technology School")
