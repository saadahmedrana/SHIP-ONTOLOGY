# ===============================================================
# Streamlit UI for Ontology Harmonization Pipeline (Professional)
# ===============================================================
import streamlit as st
import os
import time
import json
import subprocess

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Ontology Harmonization",
    page_icon="⚙️",
    layout="wide"
)

st.title("Ontology Harmonization Platform")
st.markdown("Run the full **multi-agent pipeline** — extract, retrieve, reason, and rename OEM variables against the canonical ontology.")

# ---------------- SESSION STATE ----------------
if "run_complete" not in st.session_state:
    st.session_state.run_complete = False
if "logs" not in st.session_state:
    st.session_state.logs = ""
if "elapsed" not in st.session_state:
    st.session_state.elapsed = 0
if "result_files" not in st.session_state:
    st.session_state.result_files = []
if "base_name" not in st.session_state:
    st.session_state.base_name = ""

# ---------------- FILE UPLOAD ----------------
uploaded_ttl = st.file_uploader("Upload an OEM `.ttl` file", type=["ttl"])
top_k = st.number_input("Top-K ontology candidates", min_value=1, max_value=10, value=5)

col1, col2 = st.columns([1, 1])
with col1:
    run_button = st.button("Run Pipeline")
with col2:
    reset_button = st.button("Reset Session")

# Paths
WORK_DIR = os.path.dirname(os.path.abspath(__file__))
TTL_SAVE_PATH = os.path.join(WORK_DIR, "uploaded.ttl")

# ---------------- RESET HANDLER ----------------
if reset_button:
    st.session_state.run_complete = False
    st.session_state.logs = ""
    st.session_state.elapsed = 0
    st.session_state.result_files = []
    st.session_state.base_name = ""
    st.success("Session reset successfully. You can upload and run a new file.")

# ---------------- RUN HANDLER ----------------
if run_button and uploaded_ttl:
    with open(TTL_SAVE_PATH, "wb") as f:
        f.write(uploaded_ttl.read())
    st.success(f"File uploaded as `{TTL_SAVE_PATH}`")

    st.info("Running Master Agent pipeline... this may take several minutes.")
    start_time = time.time()

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
    st.session_state.logs = logs
    st.session_state.elapsed = elapsed
    st.session_state.run_complete = True

    base_name = "Engine_Test1" if "Engine_Test1" in logs else "uploaded"
    st.session_state.base_name = base_name
    st.session_state.result_files = [
        f for f in os.listdir(WORK_DIR) if f.startswith(base_name)
    ]

# ---------------- DISPLAY RESULTS ----------------
if st.session_state.run_complete:
    st.success(f"Pipeline completed in {st.session_state.elapsed:.1f} seconds.")

    st.subheader("Output Files")
    for f in st.session_state.result_files:
        if f.endswith((".json", ".ttl", ".csv")):
            file_path = os.path.join(WORK_DIR, f)
            with open(file_path, "rb") as data:
                st.download_button(
                    label=f"Download {f}",
                    data=data,
                    file_name=f,
                    mime="application/octet-stream",
                    key=f"download_{f}"
                )

    mapping_path = os.path.join(WORK_DIR, f"{st.session_state.base_name}_Mappings.json")
    if os.path.exists(mapping_path):
        with open(mapping_path, "r", encoding="utf-8") as f:
            mappings = json.load(f)
        st.subheader("Mapping Summary")
        st.dataframe(mappings)
