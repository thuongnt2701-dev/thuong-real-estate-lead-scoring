import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
import io
import os

# --- PAGE CONFIG ---
st.set_page_config(page_title="Real Estate Lead Scoring AI", layout="wide")

# --- LOAD SKILL DEFINITION ---
SKILL_FILE = "lead_scoring_skill.md"
if os.path.exists(SKILL_FILE):
    with open(SKILL_FILE, "r", encoding="utf-8") as f:
        SKILL_CONTENT = f.read()
else:
    SKILL_CONTENT = "Lead scoring logic not found."

# --- SIDEBAR: CONFIGURATION ---
st.sidebar.header("⚙️ Cấu hình hệ thống")
api_key = st.sidebar.text_input("Gemini API Key", type="password")
sheet_url = st.sidebar.text_input(
    "Google Sheet URL", 
    value="https://docs.google.com/spreadsheets/d/10yzDP9_uNPgzgMtZYIRYZXmaagXZtEXs_d6PJyB3T1A/edit#gid=0"
)

# --- FUNCTIONS ---
def get_sheet_data(url):
    try:
        # Convert Google Sheet URL to CSV export link
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

def score_leads_with_ai(df, api_key):
    if not api_key:
        st.warning("Vui lòng nhập Gemini API Key ở thanh bên.")
        return None
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    scored_results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Batch processing or individual processing? 
    # For accuracy and simplicity in a demo, we'll do row by row or small batches.
    # Here we send the description and ask for JSON response.
    
    for index, row in df.iterrows():
        status_text.text(f"Đang phân tích khách hàng: {row.get('ten_khach', 'N/A')}...")
        
        prompt = f"""
        Dựa trên quy tắc chấm điểm sau đây:
        {SKILL_CONTENT}
        
        Hãy phân tích khách hàng sau:
        - ID: {row.get('id')}
        - Tên: {row.get('ten_khach')}
        - Nhu cầu: {row.get('nhu_cau_mo_ta')}
        
        Trả về kết quả dưới định dạng JSON duy nhất như sau:
        {{
            "id": "{row.get('id')}",
            "score": <số điểm>,
            "classification": "<HOT/WARM/JUNK>",
            "reason": "<lý do ngắn gọn>"
        }}
        """
        
        try:
            response = model.generate_content(prompt)
            # Clean response text (remove markdown backticks if any)
            clean_json = response.text.strip().replace("```json", "").replace("```", "")
            result = json.loads(clean_json)
            scored_results.append(result)
        except Exception as e:
            st.error(f"Lỗi khi xử lý dòng {index}: {e}")
            scored_results.append({
                "id": row.get('id'),
                "score": 0,
                "classification": "ERROR",
                "reason": str(e)
            })
            
        progress_bar.progress((index + 1) / len(df))
    
    status_text.text("✅ Hoàn thành phân tích!")
    return pd.DataFrame(scored_results)

# --- MAIN UI ---
st.title("🏠 Hệ thống AI Lead Scoring Bất Động Sản")
st.markdown("Hệ thống tự động hóa chấm điểm khách hàng tiềm năng dựa trên AI và quy tắc nghiệp vụ.")

if st.button("📥 Tải dữ liệu từ Google Sheet"):
    df_raw = get_sheet_data(sheet_url)
    if df_raw is not None:
        st.session_state['df_raw'] = df_raw
        st.success(f"Đã tải {len(df_raw)} bản ghi.")

if 'df_raw' in st.session_state:
    st.subheader("📋 Dữ liệu thô")
    st.dataframe(st.session_state['df_raw'], use_container_width=True)
    
    if st.button("🚀 Bắt đầu chấm điểm bằng AI"):
        with st.spinner("AI đang làm việc..."):
            df_scored = score_leads_with_ai(st.session_state['df_raw'], api_key)
            if df_scored is not None:
                # Merge results back to original data
                df_final = pd.merge(st.session_state['df_raw'], df_scored, on='id', how='left')
                st.session_state['df_final'] = df_final

if 'df_final' in st.session_state:
    st.subheader("📊 Kết quả chấm điểm (Human-in-the-loop)")
    st.info("Bạn có thể chỉnh sửa trực tiếp kết quả bên dưới nếu cần trước khi xuất dữ liệu.")
    
    # Editable dataframe
    edited_df = st.data_editor(st.session_state['df_final'], use_container_width=True, num_rows="dynamic")
    
    # Export options
    col1, col2 = st.columns(2)
    with col1:
        # Excel Export
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            edited_df.to_excel(writer, index=False, sheet_name='Leads_Scored')
        processed_data = output.getvalue()
        
        st.download_button(
            label="📥 Xuất file Excel bàn giao",
            data=processed_data,
            file_name="leads_scored_final.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    with col2:
        # Statistics
        st.write("📈 Thống kê nhanh:")
        stats = edited_df['classification'].value_counts()
        st.bar_chart(stats)

else:
    st.info("Vui lòng tải dữ liệu từ Google Sheet để bắt đầu.")

st.divider()
st.caption("Phát triển bởi AI Assistant - Ngành Bất Động Sản")
