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
        return True

    sha = get_github_file_sha()
    if not sha:
        st.error("❌ No SHA found. Aborting GitHub update.")
        return False

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    payload = {
        "message": "Update annotation feedback via Streamlit interface",
        "content": base64.b64encode(json.dumps(content, indent=2).encode()).decode(),
        "sha": sha,
        "branch": "main"
    }

    r = requests.put(GITHUB_API_URL, headers=headers, json=payload)

    if r.status_code in [200, 201]:
        st.success("✅ File successfully committed to GitHub.")
        return True
    else:
        st.error(f"❌ GitHub update failed: {r.status_code} {r.reason}")
        st.code(r.text)
        return False

st.set_page_config(layout="wide")
st.title("✅ Agree or Reject GPT-4o Annotations")

def get_next_table():
    for fname, entry in test_data.items():
        for colname, coldata in entry["columns"].items():
            explanations = [
                "pii_explanation",
                "pii_sensitivity_level_explanation",
                "non_pii_explanation",
                "non_pii_sensitivity_level_explanation"
            ]
            if any(coldata.get(f"{k}_agree", 0) + coldata.get(f"{k}_reject", 0) < 2 for k in explanations):
                return fname
    return None

selected_file = get_next_table()
if not selected_file:
    st.success("🎉 All tables fully annotated.")
    st.stop()

file_entry = test_data[selected_file]
columns = file_entry["columns"]
country = file_entry["metadata"]["country"].capitalize()
isp_used = file_entry["metadata"]["isp_used"]

left_col, right_col = st.columns([7, 3])

with left_col:
    st.subheader("📊 Preview of Table Records")
    df = pd.DataFrame({col: columns[col]['records'] for col in columns})
    st.dataframe(df, use_container_width=True)

    st.markdown("---")
    st.subheader(f"🧠 Annotations for File: `{selected_file}`")

    vote_changed = False

    for current_col, col_data in columns.items():
        st.markdown(f"### Column: `{current_col}`")

        def vote_block(label, key):
            explanation = col_data.get(key, "")
            if not explanation:
                return
            agree_key = f"{key}_agree"
            reject_key = f"{key}_reject"
            st.markdown(f"**{label}**")
            st.markdown(f"> {explanation}")
            if col_data.get(agree_key, 0) + col_data.get(reject_key, 0) < 2:
                c1, c2 = st.columns([1, 1])
                with c1:
                    if st.button(f"✅ Agree with {label}", key=f"agree_{current_col}_{key}"):
                        col_data[agree_key] = col_data.get(agree_key, 0) + 1
                        vote_changed = True
                with c2:
                    if st.button(f"❌ Reject {label}", key=f"reject_{current_col}_{key}"):
                        col_data[reject_key] = col_data.get(reject_key, 0) + 1
                        vote_changed = True
            else:
                st.info(f"Feedback already collected for {label} ✅")

        vote_block("PII Reasoning", "pii_explanation")
        vote_block("PII Sensitivity Level", "pii_sensitivity_level_explanation")
        vote_block("Non-PII Reasoning", "non_pii_explanation")
        vote_block("Non-PII Sensitivity Level", "non_pii_sensitivity_level_explanation")
        st.markdown("---")

    if vote_changed:
        if st.button("💾 Save and continue"):
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