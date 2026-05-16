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

# --- MAIN UI ---
st.title("🏠 AI Lead Scoring & Automation")
st.markdown("Hệ thống tự động hóa lấy dữ liệu từ Google Sheets và chấm điểm khách hàng.")

# One-Click Action
if st.button("⚡ TẢI DỮ LIỆU & CHẤM ĐIỂM NGAY", type="primary", use_container_width=True):
    with st.spinner("Đang xử lý..."):
        df_raw = get_sheet_data(sheet_url)
        if df_raw is not None:
            st.session_state['df_raw'] = df_raw
            df_scored = score_leads_with_ai(df_raw, api_key)
            if df_scored is not None:
                st.session_state['df_final'] = pd.merge(df_raw, df_scored, on='id', how='left')
                st.success("✅ Đã hoàn thành!")

if 'df_final' in st.session_state:
    st.divider()
    st.subheader("📊 Kết quả phân loại")
    
    c1, c2, c3 = st.columns(3)
    counts = st.session_state['df_final']['classification'].value_counts()
    c1.metric("🔥 HOT", counts.get('HOT', 0))
    c2.metric("⚖️ WARM", counts.get('WARM', 0))
    c3.metric("🗑️ JUNK", counts.get('JUNK', 0))

    st.info("💡 Bạn có thể chỉnh sửa trực tiếp thông tin trong bảng dưới đây.")
    edited_df = st.data_editor(st.session_state['df_final'], use_container_width=True)
    
    # Handover Excel Export
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        edited_df.to_excel(writer, index=False, sheet_name='Bàn_Giao_Leads')
    
    st.download_button(
        label="📥 TẢI FILE EXCEL BÀN GIAO",
        data=output.getvalue(),
        file_name="leads_scored_final.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
    
    if st.button("🔄 Chấm điểm lại"):
        del st.session_state['df_final']
        st.rerun()

elif 'df_raw' in st.session_state:
    st.subheader("📋 Dữ liệu thô đã tải")
    st.dataframe(st.session_state['df_raw'], use_container_width=True)
    if st.button("🚀 Chấm điểm dữ liệu này"):
        df_scored = score_leads_with_ai(st.session_state['df_raw'], api_key)
        st.session_state['df_final'] = pd.merge(st.session_state['df_raw'], df_scored, on='id', how='left')
        st.rerun()

st.divider()
st.caption("Developed by AI Assistant for Real Estate Industry")
