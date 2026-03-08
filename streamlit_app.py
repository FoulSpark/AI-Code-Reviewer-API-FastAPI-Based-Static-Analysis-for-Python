import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="AI Code Reviewer", page_icon="🧠", layout="wide")

st.title("🧠 AI Code Reviewer")
st.caption("Submit Python code and get syntax, security, style, and complexity feedback.")

code = st.text_area("Paste your Python code here", height=300)
language = st.selectbox("Language", ["python"])

if st.button("Review Code"):
    if not code.strip():
        st.warning("Please enter some code first.")
    else:
        payload = {
            "code": code,
            "language": language
        }

        try:
            response = requests.post(f"{API_URL}/review", json=payload, timeout=30)

            if response.status_code == 200:
                data = response.json()

                st.subheader("Review Result")
                st.write(f"**Review ID:** {data['review_id']}")
                st.write(f"**Status:** {data['status']}")
                st.write(f"**Overall Score:** {data['overall_score']}")
                st.write(f"**Summary:** {data['summary']}")

                st.subheader("Metrics")
                st.json(data["metrics"])

                st.subheader("Issues")
                if data["issues"]:
                    for issue in data["issues"]:
                        st.markdown(f"**Type:** {issue['type']}")
                        st.markdown(f"**Severity:** {issue['severity']}")
                        st.markdown(f"**Line:** {issue['line']}")
                        st.markdown(f"**Message:** {issue['message']}")
                        st.markdown(f"**Suggestion:** {issue['suggestion']}")
                        st.markdown("---")
                else:
                    st.success("No issues found.")
            else:
                st.error(f"API Error: {response.status_code}")
                st.text(response.text)

        except requests.RequestException as e:
            st.error(f"Request failed: {e}")


st.subheader("Fetch Review by ID")
review_id = st.text_input("Enter review ID")

if st.button("Get Review"):
    if not review_id.strip():
        st.warning("Please enter a review ID.")
    else:
        try:
            response = requests.get(f"{API_URL}/reviews/{review_id}", timeout=30)

            if response.status_code == 200:
                data = response.json()
                st.json(data)
            elif response.status_code == 404:
                st.error("Review not found.")
            else:
                st.error(f"API Error: {response.status_code}")
                st.text(response.text)
        except requests.RequestException as e:
            st.error(f"Request failed: {e}")