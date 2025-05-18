import streamlit as st
import json
import pandas as pd
from pathlib import Path
import base64
import requests
import streamlit.components.v1 as components

# Load test and ISP data
TEST_PATH = Path("test.json")
ISPS_PATH = Path("isps.json")

test_data = json.load(TEST_PATH.open())
isps_data = json.load(ISPS_PATH.open())

# GitHub secrets (optional)
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN")
REPO_OWNER = st.secrets.get("REPO_OWNER")
REPO_NAME = st.secrets.get("REPO_NAME")
TARGET_FILE_PATH = st.secrets.get("TARGET_FILE_PATH", "test.json")
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
    """Commit updated test.json to GitHub"""
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
    if r.status_code == 200 or r.status_code == 201:
        return True
    else:
        st.error(f"❌ Failed to commit to GitHub: {r.status_code} - {r.text}")
        return False

st.set_page_config(layout="wide")
st.title("🔐 Column Labeling Interface for Sensitive Data")

# File selection
selected_file = st.selectbox("Select a file to annotate", list(test_data.keys()))

# Extract metadata and columns
file_entry = test_data[selected_file]
columns = file_entry["columns"]
country = file_entry["metadata"]["country"].capitalize()
isp_used = file_entry["metadata"]["isp_used"]

# Two-column layout for table and ISP
left_col, right_col = st.columns([7, 3])

with left_col:
    st.subheader("📊 Preview of Table Records")
    df = pd.DataFrame({col: columns[col]['records'] for col in columns})
    st.dataframe(df, use_container_width=True)

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

# Step-by-step annotation below
st.markdown("---")
st.subheader("📝 Step-by-Step Column Annotation")
updated = False

for col in columns:
    st.markdown(f"### 🔍 Annotate column: `{col}`")

    non_pii_expl = columns[col].get("non_pii_gpt-4o", "")
    non_pii_level_expl = columns[col].get("non_pii_gpt-4o_sensitivity_level_gpt-4o", "")

    if non_pii_expl:
        st.markdown(f"**Explanation by GPT-4o (Non-PII):**")
        st.markdown(f"> {non_pii_expl}")
    if non_pii_level_expl:
        st.markdown(f"**Sensitivity Level Justification by GPT-4o:**")
        st.markdown(f"> {non_pii_level_expl}")

    # Editable fields
    pii = st.selectbox(f"PII label for '{col}'", ["None", "GENERIC_ID", "PERSON_NAME", "ORGANIZATION_NAME", "PHONE_NUMBER", "EMAIL"], index=0, key=f"pii_{col}")
    pii_level = st.selectbox(f"PII sensitivity level for '{col}'", ["NON_SENSITIVE", "LOW_SENSITIVE", "MEDIUM_SENSITIVE", "HIGH_SENSITIVE"], index=0, key=f"pii_level_{col}")
    non_pii = st.selectbox(f"Non-PII label for '{col}'", ["NON_SENSITIVE", "SENSITIVE"], index=0, key=f"non_pii_{col}")
    non_pii_level = st.selectbox(f"Non-PII sensitivity level for '{col}'", ["NON_SENSITIVE", "MEDIUM_SENSITIVE", "HIGH_SENSITIVE"], index=0, key=f"non_pii_level_{col}")

    if st.button(f"✅ Save annotation for '{col}'"):
        columns[col]["pii_gt"] = pii
        columns[col]["pii_sensitivity_level"] = pii_level
        columns[col]["non_pii"] = non_pii
        columns[col]["non_pii_sensitivity_level"] = non_pii_level
        updated = True
        st.success(f"Saved annotations for column '{col}'")

# Save updated file
if updated:
    if GITHUB_TOKEN:
        success = update_github_file(test_data)
        if success:
            st.info("✅ Annotations saved to GitHub successfully.")
    else:
        with open(TEST_PATH, "w") as f:
            json.dump(test_data, f, indent=2)
        st.info("✅ test.json updated locally.")