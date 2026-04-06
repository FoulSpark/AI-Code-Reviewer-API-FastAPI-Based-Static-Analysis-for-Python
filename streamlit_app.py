import requests
import streamlit as st
import json

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Agentic AI Code Reviewer", page_icon="🧠", layout="wide")

st.title("🧠 Agentic AI Code Reviewer")
st.caption("Review Python code or generate/fix code using an agentic 4-stage pipeline.")

tab_review, tab_agentic, tab_history = st.tabs(["🔍 Code Reviewer", "🚀 Agentic Studio", "📜 History"])

# ── SHARED HELPERS ──────────────────────────────────────────
def display_agentic_result(data):
    st.subheader("Agentic Execution Result")
    col1, col2, col3 = st.columns(3)
    col1.metric("Status", data.get("status", "pass"))
    col2.metric("Retries", data.get("retry_count", 0))
    col3.metric("Model", data.get("model_used", "gemini-1.5-pro"))
    
    st.write(f"**Review ID:** `{data.get('review_id')}`")
    st.write(f"**Summary:** {data.get('summary')}")
    
    st.markdown("### Generated Code")
    st.code(data.get("code"), language=data.get("language", "python"))
    
    with st.expander("View Execution Metadata"):
        st.write("**Stages Run:**")
        st.write(" → ".join(data.get("stages_run", [])))
        if data.get("errors_encountered"):
            st.write("**Errors Encountered & Fixed:**")
            st.json(data.get("errors_encountered"))

# ── TAB: REVIEWER ───────────────────────────────────────────
with tab_review:
    code = st.text_area("Paste code for review", height=300, key="review_code")
    language = st.selectbox("Language", ["python"], key="review_lang")

    if st.button("Review Code"):
        if not code.strip():
            st.warning("Please enter some code first.")
        else:
            payload = {"code": code, "language": language}
            try:
                response = requests.post(f"{API_URL}/review", json=payload, timeout=60)
                if response.status_code == 200:
                    data = response.json()
                    st.session_state["last_review"] = data
                    st.session_state["last_code"] = code
                else:
                    st.error(f"Error: {response.status_code}")
            except Exception as e:
                st.error(f"Request failed: {e}")

    if "last_review" in st.session_state:
        data = st.session_state["last_review"]
        st.divider()
        st.subheader(f"Review: {data['status'].upper()} (Score: {data['overall_score']})")
        st.info(data['summary'])
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.write("**Issues Found:**")
            if data["issues"]:
                for i, issue in enumerate(data["issues"]):
                    with st.expander(f"L{issue['line']}: {issue['type']} - {issue['message']}"):
                        st.write(f"**Severity:** {issue['severity']}")
                        st.write(f"**Suggestion:** {issue['suggestion']}")
                
                if st.button("⚡ Fix All Issues with Agentic AI"):
                    with st.status("Running Agentic Pipeline...", expanded=True) as status:
                        payload = {
                            "code": st.session_state["last_code"],
                            "issues": data["issues"],
                            "language": language
                        }
                        try:
                            res = requests.post(f"{API_URL}/fix", json=payload, timeout=600)
                            if res.status_code == 200:
                                status.update(label="Fix Complete!", state="complete")
                                st.session_state["last_agentic"] = res.json()
                                st.success("Switch to 'Agentic Studio' tab to see the result!")
                            else:
                                status.update(label="Fix Failed", state="error")
                                st.error(res.text)
                        except Exception as e:
                            st.error(f"Pipeline error: {e}")
            else:
                st.success("No issues found.")
        
        with col2:
            st.write("**Metrics:**")
            st.json(data["metrics"])

# ── TAB: AGENTIC STUDIO ─────────────────────────────────────
with tab_agentic:
    st.subheader("Generate Code from Prompt")
    prompt = st.text_area("What should I build?", placeholder="e.g., A function to read a CSV and sort by price descending")
    gen_lang = st.selectbox("Target Language", ["python", "javascript", "typescript"], key="gen_lang")
    
    if st.button("Generate Code"):
        if not prompt.strip():
            st.warning("Describe your requirement first.")
        else:
            with st.status("Agentic AI is thinking & testing logic...", expanded=True) as status:
                try:
                    res = requests.post(f"{API_URL}/generate", json={"user_request": prompt, "language": gen_lang}, timeout=600)
                    if res.status_code == 200:
                        status.update(label="Logic Verified & Code Generated!", state="complete")
                        st.session_state["last_agentic"] = res.json()
                    else:
                        status.update(label="Generation Failed", state="error")
                        st.error(res.text)
                except Exception as e:
                    st.error(f"Pipeline error: {e}")

    if "last_agentic" in st.session_state:
        data = st.session_state["last_agentic"]
        st.divider()
        
        # --- SAFETY INTERLOCK DISPLAY ---
        if data.get("requires_confirmation"):
            st.warning("⚠️ **Safety Interlock Triggered**")
            st.error(f"Potential Security/Safety Risks: {data.get('safety_warning')}")
            st.info("The code was generated but has not been run through the 'Mechanical Execution Test' because it contains potentially dangerous operations.")
            
            with st.expander("Review Dangerous Code", expanded=True):
                st.code(data.get("code"), language=data.get("language", "python"))
            
            col1, col2 = st.columns(2)
            if col1.button("🛡️ Safe to Run: Proceed anyway", type="primary"):
                with st.status("Re-running with Safety Bypass...", expanded=True) as status:
                    # Decide which endpoint to call based on how we got here
                    # For simplicity, we'll use the prompt if available, or just the code
                    is_fix = "ISSUES ENCOUNTERED" in data.get("summary", "")
                    payload = {
                        "user_request": st.session_state.get("last_prompt", ""),
                        "language": data.get("language", "python"),
                        "force_run": True
                    }
                    endpoint = "generate"
                    
                    # If it was a fix task, we might need a different payload but 
                    # usually generate with force_run is enough if the prompt was the fix description
                    try:
                        res = requests.post(f"{API_URL}/{endpoint}", json=payload, timeout=600)
                        if res.status_code == 200:
                            status.update(label="Validation Complete!", state="complete")
                            st.session_state["last_agentic"] = res.json()
                            st.rerun()
                        else:
                            st.error(res.text)
                    except Exception as e:
                        st.error(f"Retry error: {e}")
            
            if col2.button("🚫 Cancel & Discard"):
                del st.session_state["last_agentic"]
                st.rerun()
        else:
            display_agentic_result(data)

# ── TAB: HISTORY ────────────────────────────────────────────
with tab_history:
    st.subheader("Fetch Historical Review")
    hist_id = st.text_input("Enter Review ID")
    if st.button("Retrieve"):
        try:
            res = requests.get(f"{API_URL}/reviews/{hist_id}")
            if res.status_code == 200:
                st.json(res.json())
            else:
                st.error("Not found.")
        except Exception as e:
            st.error(str(e))