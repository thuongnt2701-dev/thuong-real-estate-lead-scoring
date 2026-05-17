import os
import json
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
import re

def test_credentials():
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
