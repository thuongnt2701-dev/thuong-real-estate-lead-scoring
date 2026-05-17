import os
import json
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
import re

# --- TỰ ĐỘNG ĐỒNG BỘ credentials.json SANG st.secrets / secrets.toml (TRÁNH LỖI PHIÊN BẢN st-gsheets-connection) ---
def auto_configure_local_secrets():
    try:
        creds_file = None
        for f_name in ["credentials.json", "ai-b7-credentials.json"]:
            if os.path.exists(f_name):
                creds_file = f_name
                break
        
        if creds_file:
            # Tạo thư mục .streamlit nếu chưa có
            os.makedirs(".streamlit", exist_ok=True)
            secrets_path = os.path.join(".streamlit", "secrets.toml")
            
            # Đọc credentials.json
            with open(creds_file, "r") as f:
                creds_data = json.load(f)
                
            # Chuẩn hóa private key
            if "private_key" in creds_data:
                pk = creds_data["private_key"]
                import re
                if "-----BEGIN PRIVATE KEY-----" in pk:
                    match = re.search(r'-----BEGIN PRIVATE KEY-----(.*?)-----END PRIVATE KEY-----', pk, re.DOTALL)
                    if match:
                        raw_base64 = match.group(1)
                        clean_base64 = re.sub(r'[^A-Za-z0-9+/=]', '', raw_base64)
                        wrapped_key = "\\n".join([clean_base64[i:i+64] for i in range(0, len(clean_base64), 64)])
                        creds_data["private_key"] = f"-----BEGIN PRIVATE KEY-----\\n{wrapped_key}\\n-----END PRIVATE KEY-----\\n"
            
            # Nạp trực tiếp vào st.secrets để hoạt động tức thì trong phiên chạy này
            import streamlit as st
            if "connections" not in st.secrets:
                try:
                    st.secrets._secrets["connections"] = {"gsheets": creds_data, "gsheets_test": creds_data}
                except:
                    st.secrets["connections"] = {"gsheets": creds_data, "gsheets_test": creds_data}
            else:
                try:
                    st.secrets._secrets["connections"]["gsheets"] = creds_data
                    st.secrets._secrets["connections"]["gsheets_test"] = creds_data
                except:
                    st.secrets["connections"]["gsheets"] = creds_data
                    st.secrets["connections"]["gsheets_test"] = creds_data
                    
            # Đồng bộ ghi vào .streamlit/secrets.toml cho các lần chạy sau
            has_gsheets = False
            if os.path.exists(secrets_path):
                with open(secrets_path, "r") as sf:
                    if "[connections.gsheets]" in sf.read():
                        has_gsheets = True
            
            if not has_gsheets:
                with open(secrets_path, "a" if os.path.exists(secrets_path) else "w") as sf:
                    sf.write("\n[connections.gsheets]\n")
                    for k, v in creds_data.items():
                        escaped_v = str(v).replace('"', '\\"').replace('\n', '\\n')
                        sf.write(f'{k} = "{escaped_v}"\n')
                    
                    sf.write("\n[connections.gsheets_test]\n")
                    for k, v in creds_data.items():
                        escaped_v = str(v).replace('"', '\\"').replace('\n', '\\n')
                        sf.write(f'{k} = "{escaped_v}"\n')
    except Exception:
        pass

def test_credentials():
    auto_configure_local_secrets()
    sheet_url = "https://docs.google.com/spreadsheets/d/10yzDP9_uNPgzgMtZYIRYZXmaagXZtEXs_d6PJyB3T1A/edit"
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    with open("credentials.json", "r") as f:
        creds_info = json.load(f)
        
    print("--- Test 1: Original Credentials ---")
    try:
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        client = gspread.authorize(creds)
        sheet_id = sheet_url.split("/d/")[1].split("/")[0]
        sheet = client.open_by_key(sheet_id).sheet1
        df = pd.DataFrame(sheet.get_all_records())
        print("✅ SUCCESS without cleaning!")
        return
    except Exception as e:
        print(f"❌ FAILED: {e}")

    print("\n--- Test 2: With PEM Cleaning ---")
    try:
        # Copy to avoid modifying the original dict
        cleaned_info = creds_info.copy()
        pk = cleaned_info["private_key"]
        if "-----BEGIN PRIVATE KEY-----" in pk:
            match = re.search(r'-----BEGIN PRIVATE KEY-----(.*?)-----END PRIVATE KEY-----', pk, re.DOTALL)
            if match:
                raw_base64 = match.group(1)
                clean_base64 = re.sub(r'[^A-Za-z0-9+/=]', '', raw_base64)
                wrapped_key = "\n".join([clean_base64[i:i+64] for i in range(0, len(clean_base64), 64)])
                cleaned_info["private_key"] = f"-----BEGIN PRIVATE KEY-----\n{wrapped_key}\n-----END PRIVATE KEY-----\n"
                
        creds = Credentials.from_service_account_info(cleaned_info, scopes=scope)
        client = gspread.authorize(creds)
        sheet_id = sheet_url.split("/d/")[1].split("/")[0]
        sheet = client.open_by_key(sheet_id).sheet1
        df = pd.DataFrame(sheet.get_all_records())
        print("✅ SUCCESS with PEM cleaning!")
    except Exception as e:
        print(f"❌ FAILED with PEM cleaning: {e}")

    print("\n--- Test 3: With st-gsheets-connection ---")
    try:
        from streamlit_gsheets import GSheetsConnection
        import streamlit as st
        
        cleaned_info = creds_info.copy()
        pk = cleaned_info["private_key"]
        if "-----BEGIN PRIVATE KEY-----" in pk:
            match = re.search(r'-----BEGIN PRIVATE KEY-----(.*?)-----END PRIVATE KEY-----', pk, re.DOTALL)
            if match:
                raw_base64 = match.group(1)
                clean_base64 = re.sub(r'[^A-Za-z0-9+/=]', '', raw_base64)
                wrapped_key = "\n".join([clean_base64[i:i+64] for i in range(0, len(clean_base64), 64)])
                cleaned_info["private_key"] = f"-----BEGIN PRIVATE KEY-----\n{wrapped_key}\n-----END PRIVATE KEY-----\n"
                
        # Nạp credentials vào st.secrets trước để tránh lỗi phiên bản st-gsheets-connection
        if "connections" not in st.secrets:
            try:
                st.secrets._secrets["connections"] = {"gsheets_test": cleaned_info}
            except:
                st.secrets["connections"] = {"gsheets_test": cleaned_info}
        else:
            try:
                st.secrets._secrets["connections"]["gsheets_test"] = cleaned_info
            except:
                st.secrets["connections"]["gsheets_test"] = cleaned_info
                
        conn = st.connection("gsheets_test", type=GSheetsConnection)
        df = conn.read(spreadsheet=sheet_url, ttl="0")
        print(f"✅ SUCCESS with st-gsheets-connection! Loaded {len(df)} rows.")
    except Exception as e:
        print(f"❌ FAILED with st-gsheets-connection: {e}")

if __name__ == "__main__":
    test_credentials()
