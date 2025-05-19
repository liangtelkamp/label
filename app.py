import streamlit as st
import json
import pandas as pd
from pathlib import Path
import base64
import requests
import random

# Load test and ISP data
TEST_PATH = Path("test.json")
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
        "message": "Update column annotations via Streamlit interface",
        "content": base64.b64encode(json.dumps(content, indent=2).encode()).decode(),
        "sha": sha
    }
    r = requests.put(GITHUB_API_URL, headers=headers, json=data)
    return r.status_code in [200, 201]

st.set_page_config(layout="wide")
st.title("🔐 Column Labeling Interface for Sensitive Data")

# Select a random table with incomplete annotation (each column needs two annotations)
def get_incomplete_file():
    for fname, entry in test_data.items():
        incomplete = any(
            not all(
                f"pii_{i}" in col and f"pii_sensitivity_level_{i}" in col and f"non_pii_{i}" in col and f"non_pii_sensitivity_level_{i}" in col
                for i in [1, 2]
            )
            for col in entry["columns"].values()
        )
        if incomplete:
            return fname
    return None

selected_file = get_incomplete_file()
if not selected_file:
    st.success("🎉 All files and columns have been annotated twice!")
    st.stop()

file_entry = test_data[selected_file]
columns = file_entry["columns"]
column_names = [col for col, data in columns.items() if not (
    all(f"pii_{i}" in data and f"pii_sensitivity_level_{i}" in data and f"non_pii_{i}" in data and f"non_pii_sensitivity_level_{i}" in data for i in [1, 2])
)]

if not column_names:
    st.info("✅ All columns in this file have been annotated twice.")
    st.stop()

if "column_index" not in st.session_state:
    st.session_state.column_index = 0

current_index = st.session_state.column_index
if current_index >= len(column_names):
    current_index = 0
    st.session_state.column_index = 0

current_col = column_names[current_index]

country = file_entry["metadata"]["country"].capitalize()
isp_used = file_entry["metadata"]["isp_used"]

left_col, right_col = st.columns([7, 3])

with left_col:
    st.subheader("📊 Preview of Table Records")
    df = pd.DataFrame({col: columns[col]['records'] for col in columns})
    st.dataframe(df, use_container_width=True)

    st.markdown("---")
    st.subheader(f"📝 Annotation: `{current_col}`")
    updated = False

    non_pii_expl = columns[current_col].get("non_pii_gpt-4o", "")
    non_pii_level_expl = columns[current_col].get("non_pii_gpt-4o_sensitivity_level_gpt-4o", "")

    if non_pii_expl:
        st.markdown("**Explanation by GPT-4o (Non-PII):**")
        st.markdown(f"> {non_pii_expl}")
    if non_pii_level_expl:
        st.markdown("**Sensitivity Level Justification by GPT-4o:**")
        st.markdown(f"> {non_pii_level_expl}")

    # Choose which variant to annotate
    existing_keys = columns[current_col].keys()
    variant = 1 if not f"pii_1" in existing_keys else 2 if not f"pii_2" in existing_keys else None

    if variant:
        pii = st.selectbox(f"PII label for '{current_col}'", ["None", "GENERIC_ID", "PERSON_NAME", "ORGANIZATION_NAME", "PHONE_NUMBER", "EMAIL"], index=0, key=f"pii_{current_col}_{variant}")
        pii_level = st.selectbox(f"PII sensitivity level for '{current_col}'", ["NON_SENSITIVE", "LOW_SENSITIVE", "MEDIUM_SENSITIVE", "HIGH_SENSITIVE"], index=0, key=f"pii_level_{current_col}_{variant}")
        non_pii = st.selectbox(f"Non-PII label for '{current_col}'", ["NON_SENSITIVE", "SENSITIVE"], index=0, key=f"non_pii_{current_col}_{variant}")
        non_pii_level = st.selectbox(f"Non-PII sensitivity level for '{current_col}'", ["NON_SENSITIVE", "MEDIUM_SENSITIVE", "HIGH_SENSITIVE"], index=0, key=f"non_pii_level_{current_col}_{variant}")

        if st.button("✅ Save annotation"):
            columns[current_col][f"pii_{variant}"] = pii
            columns[current_col][f"pii_sensitivity_level_{variant}"] = pii_level
            columns[current_col][f"non_pii_{variant}"] = non_pii
            columns[current_col][f"non_pii_sensitivity_level_{variant}"] = non_pii_level
            updated = True
            st.success(f"Saved annotation variant {variant} for column '{current_col}'")

    else:
        st.info("✅ This column has already been annotated twice.")

    nav_col1, nav_col2 = st.columns([1, 1])
    with nav_col1:
        if st.button("⬅️ Previous") and current_index > 0:
            st.session_state.column_index -= 1
            st.rerun()
    with nav_col2:
        if st.button("Next ➡️") and current_index < len(column_names) - 1:
            st.session_state.column_index += 1
            st.rerun()

    if updated:
        if GITHUB_TOKEN:
            success = update_github_file(test_data)
            if success:
                st.info("✅ Annotations saved to GitHub successfully.")
        else:
            with open(TEST_PATH, "w") as f:
                json.dump(test_data, f, indent=2)
            st.info("✅ test.json updated locally.")

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