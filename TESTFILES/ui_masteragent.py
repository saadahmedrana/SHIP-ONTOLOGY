# ===============================================================
# Streamlit UI for Ontology Alignment Pipeline (Master Agent)
# ===============================================================
import streamlit as st
import os
import time
import json
import subprocess

# -------------- PAGE CONFIG --------------
st.set_page_config(
    page_title="Ontology Harmonization UI",
    page_icon="⚙️",
    layout="wide"
)

st.title("🧠 Ontology Harmonization Dashboard")
st.markdown("Run the **full multi-agent pipeline** — extract, retrieve, reason, and rename OEM variables.")

# -------------- FILE UPLOAD --------------
uploaded_ttl = st.file_uploader("📤 Upload OEM .ttl file", type=["ttl"])
top_k = st.number_input("Top-K ontology candidates", min_value=1, max_value=10, value=5)
run_button = st.button("🚀 Run Full Pipeline")

# Paths
WORK_DIR = os.path.dirname(os.path.abspath(__file__))
TTL_SAVE_PATH = os.path.join(WORK_DIR, "uploaded.ttl")

if run_button:
    if not uploaded_ttl:
        st.warning("Please upload a TTL file first.")
    else:
        with open(TTL_SAVE_PATH, "wb") as f:
            f.write(uploaded_ttl.read())
        st.success(f"✅ Uploaded and saved as `{TTL_SAVE_PATH}`")

        # -------------- RUN PIPELINE --------------
        st.info("Running Master Agent pipeline... this may take a few minutes ⏳")
        start_time = time.time()

        # call the masteragent.py script directly
        process = subprocess.Popen(
            ["python", "masteragent.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=WORK_DIR,
            text=True
        )

        log_container = st.empty()
        logs = ""
        for line in process.stdout:
            logs += line
            log_container.text(logs)
        process.wait()

        elapsed = time.time() - start_time
        st.success(f"✅ Pipeline finished in {elapsed:.1f} seconds.")

        # -------------- RESULTS DISPLAY --------------
        base_name = "Engine_Test1" if "Engine_Test1" in logs else "uploaded"
        result_files = [f for f in os.listdir(WORK_DIR) if f.startswith(base_name)]

        st.markdown("### 📁 Output Files")
        for f in result_files:
            if f.endswith(".json") or f.endswith(".ttl") or f.endswith(".csv"):
                st.download_button(
                    label=f"⬇️ Download {f}",
                    data=open(os.path.join(WORK_DIR, f), "rb").read(),
                    file_name=f
                )

        # show summary
        if os.path.exists(os.path.join(WORK_DIR, f"{base_name}_Mappings.json")):
            with open(os.path.join(WORK_DIR, f"{base_name}_Mappings.json")) as f:
                mappings = json.load(f)
            st.markdown("### 🧩 Mapping Summary")
            st.dataframe(mappings)
