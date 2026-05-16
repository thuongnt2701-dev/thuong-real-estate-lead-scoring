import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
import io
import os

# --- PAGE CONFIG ---
st.set_page_config(page_title="Real Estate Lead Scoring AI", layout="wide", page_icon="🏠")

# --- CONFIGURATION & RULES ---
SKILL_FILE = "lead_scoring_skill.md"
DEFAULT_RULES = """
# Skill: Lead Scoring for Real Estate Industry
- VIP (+50): Ngân sách > 20 tỷ, Biệt thự, Penthouse, Quận 1, Sổ hồng riêng.
- Junk (-50): Nhầm số, Không nhu cầu, Giá quá thấp vô lý (Q1 mà 1-2 tỷ), Spam.
- Normal: Chung cư 3-10 tỷ, cần tư vấn thêm.
"""

if os.path.exists(SKILL_FILE):
    with open(SKILL_FILE, "r", encoding="utf-8") as f:
        SKILL_CONTENT = f.read()
else:
    SKILL_CONTENT = DEFAULT_RULES

# --- SIDEBAR: CONFIGURATION ---
st.sidebar.header("⚙️ Cấu hình hệ thống")
api_key = st.sidebar.text_input("Gemini API Key (Tùy chọn)", type="password", help="Nếu để trống, hệ thống sẽ dùng Logic tự động.")
sheet_url = st.sidebar.text_input(
    "Google Sheet URL", 
    value="https://docs.google.com/spreadsheets/d/10yzDP9_uNPgzgMtZYIRYZXmaagXZtEXs_d6PJyB3T1A/edit#gid=0"
)

# --- FUNCTIONS ---
def get_sheet_data(url):
    try:
        if "/edit" in url:
            csv_url = url.split("/edit")[0] + "/export?format=csv"
            if "gid=" in url:
                gid = url.split("gid=")[1].split("&")[0]
                csv_url += f"&gid={gid}"
        else:
            csv_url = url
        df = pd.read_csv(csv_url)
        return df
    except Exception as e:
        st.error(f"Lỗi khi tải dữ liệu từ Google Sheet: {e}")
        return None

def score_leads_logic(df):
    scored_results = []
    vip_keywords = ["20 tỷ", "tài chính mạnh", "biệt thự đơn lập", "penthouse", "shophouse", "quận 1", "ven sông", "vinhomes ocean park", "phú mỹ hưng", "chủ doanh nghiệp", "nhà đầu tư", "mua sỉ", "sổ hồng riêng"]
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

        if score >= 50:
            classification = "HOT"
        elif score < 0:
            classification = "JUNK"
        else:
            score = 10
            classification = "WARM"
            reasons.append("Bình thường")

        scored_results.append({
            "id": row.get('id'),
            "score": score,
            "classification": classification,
            "reason": "; ".join(reasons)
        })
        progress_bar.progress((index + 1) / len(df))
    return pd.DataFrame(scored_results)

def score_leads_with_ai(df, api_key):
    if not api_key:
        return score_leads_logic(df)
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    scored_results = []
    progress_bar = st.progress(0)
    
    for index, row in df.iterrows():
        prompt = f"Dựa trên quy tắc:\n{SKILL_CONTENT}\n\nPhân tích lead:\nID: {row.get('id')}\nNhu cầu: {row.get('nhu_cau_mo_ta')}\n\nTrả về JSON: {{\"id\": \"...\", \"score\": ..., \"classification\": \"HOT/WARM/JUNK\", \"reason\": \"...\"}}"
        try:
            response = model.generate_content(prompt)
            clean_json = response.text.strip().replace("```json", "").replace("```", "")
            scored_results.append(json.loads(clean_json))
        except:
            scored_results.append(score_leads_logic(df.iloc[[index]]).to_dict('records')[0])
        progress_bar.progress((index + 1) / len(df))
    return pd.DataFrame(scored_results)

# --- PREMIUM UI/UX CUSTOM CSS ---
def apply_custom_style():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }
        
        .main {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #f8fafc;
        }
        
        /* Glassmorphism card */
        .stMetric {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }
        
        .stButton>button {
            background: linear-gradient(90deg, #3b82f6 0%, #2563eb 100%);
            color: white;
            border-radius: 8px;
            border: none;
            padding: 10px 24px;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(37, 99, 235, 0.4);
        }
        
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(37, 99, 235, 0.6);
            background: linear-gradient(90deg, #2563eb 0%, #1d4ed8 100%);
        }
        
        /* Header styling */
        .header-container {
            background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
            padding: 40px;
            border-radius: 20px;
            margin-bottom: 30px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
        }
        
        .header-title {
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 10px;
            letter-spacing: -1px;
        }
        
        .header-subtitle {
            font-size: 1.1rem;
            opacity: 0.9;
        }
    </style>
    """, unsafe_allow_html=True)

apply_custom_style()

# --- MAIN UI ---
st.markdown("""
<div class="header-container">
    <div class="header-title">🏛️ LEAD SCORING PREMIUM</div>
    <div class="header-subtitle">Hệ thống AI phân tích và phân loại khách hàng Bất Động Sản chuyên nghiệp</div>
</div>
""", unsafe_allow_html=True)

# One-Click Action
st.write("") # Spacer
if st.button("🚀 KÍCH HOẠT HỆ THỐNG & CHẤM ĐIỂM NGAY", type="primary", use_container_width=True):
    with st.spinner("🤖 Đang khởi động AI và xử lý dữ liệu..."):
        df_raw = get_sheet_data(sheet_url)
        if df_raw is not None:
            st.session_state['df_raw'] = df_raw
            df_scored = score_leads_with_ai(df_raw, api_key)
            if df_scored is not None:
                st.session_state['df_final'] = pd.merge(df_raw, df_scored, on='id', how='left')
                st.success("✅ Hệ thống đã hoàn thành phân tích!")

if 'df_final' in st.session_state:
    st.divider()
    st.subheader("📊 DASHBOARD THỐNG KÊ")
    
    # Dashboard Metrics
    counts = st.session_state['df_final']['classification'].value_counts()
    total_leads = len(st.session_state['df_final'])
    vip_count = counts.get('HOT', 0)
    warm_count = counts.get('WARM', 0)
    junk_count = counts.get('JUNK', 0)
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tổng Lead", total_leads, delta=None)
    m2.metric("🔥 Khách VIP (HOT)", vip_count, delta=f"{vip_count/total_leads:.1%}", delta_color="normal")
    m3.metric("⚖️ Tiềm năng (WARM)", warm_count)
    m4.metric("🗑️ Khách Rác (JUNK)", junk_count, delta=f"-{junk_count/total_leads:.1%}", delta_color="inverse")

    st.write("")
    st.subheader("📋 CHI TIẾT DANH SÁCH")
    st.info("💡 Bạn có thể trực tiếp chỉnh sửa các ô trong bảng bên dưới để tinh chỉnh kết quả AI.")
    
    # Modern data editor
    edited_df = st.data_editor(
        st.session_state['df_final'], 
        use_container_width=True,
        column_config={
            "classification": st.column_config.SelectboxColumn(
                "Phân loại",
                options=["HOT", "WARM", "JUNK"],
                required=True,
            ),
            "score": st.column_config.NumberColumn("Điểm số", format="%d"),
            "nhu_cau_mo_ta": st.column_config.TextColumn("Nhu cầu chi tiết", width="large")
        }
    )
    
    st.write("")
    # Export Section
    st.subheader("📦 KẾT XUẤT & BÀN GIAO")
    col_exp1, col_exp2 = st.columns([2, 1])
    
    with col_exp1:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            edited_df.to_excel(writer, index=False, sheet_name='Lead_Scored_Final')
        
        st.download_button(
            label="📥 TẢI FILE EXCEL BÀN GIAO (PREMIUM REPORT)",
            data=output.getvalue(),
            file_name=f"Lead_Scoring_Report_{pd.Timestamp.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    with col_exp2:
        if st.button("🔄 Làm mới hệ thống", use_container_width=True):
            del st.session_state['df_final']
            st.rerun()

elif 'df_raw' in st.session_state:
    st.subheader("📋 Dữ liệu thô hiện tại")
    st.dataframe(st.session_state['df_raw'], use_container_width=True)
    if st.button("🚀 Bắt đầu chấm điểm"):
        df_scored = score_leads_with_ai(st.session_state['df_raw'], api_key)
        st.session_state['df_final'] = pd.merge(st.session_state['df_raw'], df_scored, on='id', how='left')
        st.rerun()

st.divider()
st.caption("© 2026 AI Lead Scoring System | Premium Real Estate Edition")
