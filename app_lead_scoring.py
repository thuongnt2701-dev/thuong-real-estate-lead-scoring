import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
import io
import os
import gspread
from google.oauth2.service_account import Credentials

# --- PAGE CONFIG ---
st.set_page_config(page_title="Lead Scoring Premium AI", layout="wide", page_icon="🏛️")

# --- AUTHENTICATION & CREDENTIALS ---
CREDENTIALS_FILE = "ai-b7-credentials.json"
SKILL_FILE = "lead_scoring_skill.md"

# --- PREMIUM UI/UX CUSTOM CSS ---
def apply_custom_style():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Outfit', sans-serif;
            background-color: #0b0e14;
        }
        
        .main {
            background: radial-gradient(circle at top right, #1e293b, #0f172a);
            color: #f8fafc;
        }
        
        /* Glassmorphism Metrics */
        .stMetric {
            background: rgba(255, 255, 255, 0.03) !important;
            backdrop-filter: blur(20px) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 24px !important;
            padding: 25px !important;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
        
        .stMetric:hover {
            transform: translateY(-5px);
            background: rgba(255, 255, 255, 0.06) !important;
            border-color: #3b82f6 !important;
            box-shadow: 0 10px 40px rgba(59, 130, 246, 0.2);
        }
        
        /* Custom Buttons */
        .stButton>button {
            background: linear-gradient(135deg, #6366f1 0%, #3b82f6 100%);
            color: white;
            border-radius: 12px;
            border: none;
            padding: 12px 30px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            transition: all 0.4s ease;
            width: 100%;
        }
        
        .stButton>button:hover {
            box-shadow: 0 0 30px rgba(59, 130, 246, 0.5);
            transform: scale(1.02);
            background: linear-gradient(135deg, #4f46e5 0%, #2563eb 100%);
        }
        
        /* Premium Banner */
        .premium-banner {
            background: linear-gradient(270deg, #1e3a8a, #3b82f6, #6366f1);
            background-size: 600% 600%;
            animation: gradient-animation 10s ease infinite;
            padding: 60px 20px;
            border-radius: 30px;
            text-align: center;
            margin-bottom: 40px;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.4);
        }
        
        @keyframes gradient-animation {
            0%{background-position:0% 50%}
            50%{background-position:100% 50%}
            100%{background-position:0% 50%}
        }
        
        .banner-title {
            font-size: 3.5rem;
            font-weight: 900;
            color: white;
            margin: 0;
            text-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }
        
        .banner-tagline {
            font-size: 1.2rem;
            color: rgba(255,255,255,0.9);
            font-weight: 400;
            margin-top: 10px;
        }

        /* Sidebar Glass */
        section[data-testid="stSidebar"] {
            background-color: rgba(15, 23, 42, 0.8) !important;
            backdrop-filter: blur(15px);
        }
    </style>
    """, unsafe_allow_html=True)

apply_custom_style()

# --- HELPER FUNCTIONS ---
def get_private_sheet_data(sheet_url):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        if not os.path.exists(CREDENTIALS_FILE):
            st.error(f"Không tìm thấy file {CREDENTIALS_FILE}. Vui lòng tải lên để truy cập Sheet riêng tư.")
            return None
            
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scope)
        client = gspread.authorize(creds)
        
        # Extract ID from URL
        if "/d/" in sheet_url:
            sheet_id = sheet_url.split("/d/")[1].split("/")[0]
            sheet = client.open_by_key(sheet_id).sheet1
        else:
            sheet = client.open_by_url(sheet_url).sheet1
            
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Lỗi kết nối Google Sheet riêng tư: {e}")
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
        if ("quận 1" in desc or "trung tâm" in desc) and any(x in desc for x in ["1 tỷ", "2 tỷ", "vài trăm triệu"]):
            score -= 50
            reasons.append("Giá phi thực tế")

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
        prompt = f"Analyze real estate lead:\nNhu cầu: {row.get('nhu_cau_mo_ta')}\nReturn JSON with id, score, classification, reason."
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
    st.image("https://cdn-icons-png.flaticon.com/512/1063/1063302.png", width=80) # Logo placeholder
    st.title("Settings")
    api_key = st.text_input("Gemini API Key", type="password")
    sheet_url = st.text_input("Google Sheet URL (Private)", value="https://docs.google.com/spreadsheets/d/10yzDP9_uNPgzgMtZYIRYZXmaagXZtEXs_d6PJyB3T1A/edit")
    st.divider()
    st.info("💡 Hệ thống đang sử dụng Service Account để truy cập Sheet riêng tư.")

# --- MAIN UI ---
st.markdown("""
<div class="premium-banner">
    <div class="banner-title">🏛️ MINO TECHNOLOGY</div>
    <div class="banner-tagline">AI Lead Scoring & Automation System for Real Estate</div>
</div>
""", unsafe_allow_html=True)

# Main Action
if st.button("🚀 KÍCH HOẠT HỆ THỐNG PHÂN TÍCH"):
    with st.spinner("🤖 Đang kết nối Google Sheet & Phân tích AI..."):
        df_raw = get_private_sheet_data(sheet_url)
        if df_raw is not None:
            st.session_state['df_raw'] = df_raw
            df_scored = score_leads_with_ai(df_raw, api_key)
            st.session_state['df_final'] = pd.merge(df_raw, df_scored, on='id', how='left')
            st.success("✅ Phân tích hoàn tất!")

if 'df_final' in st.session_state:
    st.divider()
    st.subheader("📊 CHIẾN DỊCH DASHBOARD")
    counts = st.session_state['df_final']['classification'].value_counts()
    total = len(st.session_state['df_final'])
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tổng Lead", total)
    m2.metric("🔥 VIP (HOT)", counts.get('HOT', 0), f"{counts.get('HOT', 0)/total:.1%}")
    m3.metric("⚖️ Tiềm năng", counts.get('WARM', 0))
    m4.metric("🗑️ Junk", counts.get('JUNK', 0), f"-{counts.get('JUNK', 0)/total:.1%}", delta_color="inverse")

    st.write("")
    st.subheader("📋 DANH SÁCH CHI TIẾT")
    edited_df = st.data_editor(
        st.session_state['df_final'], 
        use_container_width=True,
        column_config={
            "classification": st.column_config.SelectboxColumn("Status", options=["HOT", "WARM", "JUNK"]),
            "nhu_cau_mo_ta": st.column_config.TextColumn("Description", width="large")
        }
    )
    
    st.write("")
    st.subheader("📦 KẾT XUẤT BÀN GIAO")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        edited_df.to_excel(writer, index=False, sheet_name='Report')
    
    st.download_button(
        label="📥 TẢI BÁO CÁO PREMIUM (EXCEL)",
        data=output.getvalue(),
        file_name="Lead_Scoring_Report_Mino.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
    
    if st.button("🔄 Làm mới"):
        del st.session_state['df_final']
        st.rerun()

st.divider()
st.caption("© 2026 Mino Technology School | Premium AI Assistant")
