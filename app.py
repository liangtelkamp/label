import streamlit as st
import json
import pandas as pd
from pathlib import Path
import base64
import requests
import random

# Load test and ISP data
TEST_PATH = Path("test_gt.json")
ISPS_PATH = Path("isps.json")

test_data = json.load(TEST_PATH.open())
isps_data = json.load(ISPS_PATH.open())

# GitHub secrets (optional)
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN")
REPO_OWNER = st.secrets.get("REPO_OWNER")
REPO_NAME = st.secrets.get("REPO_NAME")
TARGET_FILE_PATH = st.secrets.get("TARGET_FILE_PATH", "test_gt.json")
GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{TARGET_FILE_PATH}"

def get_github_file_sha():
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(GITHUB_API_URL, headers=headers)
    if r.status_code == 200:
        return r.json()["sha"]
    else:
        st.error(f"❌ Failed to fetch SHA from GitHub: {r.text}")
        return None

def update_github_file(content: dict):
    if not GITHUB_TOKEN:
        st.warning("⚠️ GitHub token not found. Writing only locally.")
        return False

    sha = get_github_file_sha()
    if not sha:
        return False

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    data = {
        "message": "Update annotation feedback via Streamlit interface",
        "content": base64.b64encode(json.dumps(content, indent=2).encode()).decode(),
        "sha": sha
    }
    r = requests.put(GITHUB_API_URL, headers=headers, json=data)
    return r.status_code in [200, 201]

st.set_page_config(layout="wide")
st.title("✅ Agree or Reject GPT-4o Annotations")

def get_unconfirmed_column():
    for fname, entry in test_data.items():
        for colname, coldata in entry["columns"].items():
            if coldata.get("agreed", 0) + coldata.get("rejected", 0) < 2:
                return fname, colname
    return None, None

selected_file, current_col = get_unconfirmed_column()
if not selected_file:
    st.success("🎉 All columns have been confirmed or rejected at least twice.")
    st.stop()

file_entry = test_data[selected_file]
columns = file_entry["columns"]
col_data = columns[current_col]
country = file_entry["metadata"]["country"].capitalize()
isp_used = file_entry["metadata"]["isp_used"]

left_col, right_col = st.columns([7, 3])

with left_col:
    st.subheader("📊 Preview of Table Records")
    df = pd.DataFrame({col: columns[col]['records'] for col in columns})
    st.dataframe(df, use_container_width=True)

    st.markdown("---")
    st.subheader(f"🧠 Explanation for Column: `{current_col}`")

    def print_block(label, text):
        if text:
            st.markdown(f"**{label}**")
            st.markdown(f"> {text}")

    print_block("PII Reasoning", col_data.get("pii_explanation", ""))
    print_block("PII Sensitivity Level", col_data.get("pii_sensitivity_level_explanation", ""))
    print_block("Non-PII Reasoning", col_data.get("non_pii_explanation", ""))
    print_block("Non-PII Sensitivity Level", col_data.get("non_pii_sensitivity_level_explanation", ""))

    st.markdown("---")
    updated = False
    agree = st.button("✅ Agree with GPT-4o annotation")
    reject = st.button("❌ Reject GPT-4o annotation")

    if agree:
        col_data["agreed"] = col_data.get("agreed", 0) + 1
        updated = True
        st.success(f"You agreed with GPT-4o for column '{current_col}'")
    elif reject:
        col_data["rejected"] = col_data.get("rejected", 0) + 1
        updated = True
        st.warning(f"You rejected GPT-4o for column '{current_col}'")

    if updated:
        if GITHUB_TOKEN:
            success = update_github_file(test_data)
            if success:
                st.info("✅ Feedback saved to GitHub.")
        else:
            with open(TEST_PATH, "w") as f:
                json.dump(test_data, f, indent=2)
            st.info("✅ Feedback saved locally.")
        st.rerun()

with right_col:
    st.subheader(f"📜 ISP Guidelines: {isp_used}")
    if isp_used in isps_data:
        isp_info = isps_data[isp_used]
        for level in ["low/no sensitivity", "medium sensitivity", "high sensitivity", "severe sensitivity"]:
            st.markdown(f"**{level.capitalize()}**")
            for item in isp_info.get(level, []):
                st.markdown(f"- {item}")
    else:
        st.warning(f"No ISP data found for {isp_used}")
