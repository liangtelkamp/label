import streamlit as st
import json
import pandas as pd
from pathlib import Path

# Load test data
TEST_PATH = Path("test.json")
ISPS_PATH = Path("isps.json")

test_data = json.load(TEST_PATH.open())
isps_data = json.load(ISPS_PATH.open())

st.title("🔐 Column Labeling Interface for Sensitive Data")

# File selection
selected_file = st.selectbox("Select a file to annotate", list(test_data.keys()))

# Extract metadata and columns
file_entry = test_data[selected_file]
columns = file_entry["columns"]
country = file_entry["metadata"]["country"].capitalize()
isp_used = file_entry["metadata"]["isp_used"]

# Display ISP policy for this file
st.subheader(f"📜 ISP Guidelines: {isp_used}")
if isp_used in isps_data:
    isp_info = isps_data[isp_used]
    for level in ["low/no sensitivity", "medium sensitivity", "high sensitivity", "severe sensitivity"]:
        st.markdown(f"**{level.capitalize()}**")
        for item in isp_info.get(level, []):
            st.markdown(f"- {item}")
else:
    st.warning(f"No ISP data found for {isp_used}")

# Show table
st.subheader("📊 Preview of Table Records")
df = pd.DataFrame({col: columns[col]['records'] for col in columns})
st.dataframe(df, use_container_width=True)

# Editable labeling form
st.subheader("📝 Column Annotations")
updated = False

for col in columns:
    st.markdown(f"### Column: `{col}`")

    # Explanation from GPT-4o if available
    explanation = columns[col].get("non_pii_gpt-4o", "")
    if explanation:
        st.markdown(f"**GPT-4o Explanation:**")
        st.markdown(f"> {explanation}")

    # Editable fields
    pii = st.selectbox(f"PII label for '{col}'", ["None", "GENERIC_ID", "PERSON_NAME", "ORGANIZATION_NAME", "PHONE_NUMBER", "EMAIL"], index=0, key=f"pii_{col}")
    pii_level = st.selectbox(f"PII sensitivity level for '{col}'", ["NON_SENSITIVE", "LOW_SENSITIVE", "MEDIUM_SENSITIVE", "HIGH_SENSITIVE"], index=0, key=f"pii_level_{col}")
    non_pii = st.selectbox(f"Non-PII label for '{col}'", ["NON_SENSITIVE", "SENSITIVE"], index=0, key=f"non_pii_{col}")
    non_pii_level = st.selectbox(f"Non-PII sensitivity level for '{col}'", ["NON_SENSITIVE", "MEDIUM_SENSITIVE", "HIGH_SENSITIVE"], index=0, key=f"non_pii_level_{col}")

    # Update dictionary
    if st.button(f"✅ Save annotation for '{col}'"):
        columns[col]["pii"] = pii
        columns[col]["pii_sensitivity_level"] = pii_level
        columns[col]["non_pii"] = non_pii
        columns[col]["non_pii_sensitivity_level"] = non_pii_level
        updated = True
        st.success(f"Saved annotations for column '{col}'")

# Save updated file
if updated:
    with open(TEST_PATH, "w") as f:
        json.dump(test_data, f, indent=2)
    st.info("✅ test.json updated with new labels.")
