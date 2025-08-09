import streamlit as st
import requests

st.title("🧪 Repo Test Runner")
repo_url = st.text_input("🔗 Enter GitHub repo URL:")

if st.button("Run Tests"):
    if repo_url:
        with st.spinner("Running tests... Please wait."):
            try:
                response = requests.post(
                    "http://127.0.0.1:8000/run-tests",
                    json={"repo_url": repo_url}
                )
                if response.status_code == 200:
                    data = response.json()
                    st.success(f"✅ Status: {data['status']}")
                    st.text_area("📜 Test Output", data["output"], height=300)
                else:
                    st.error(f"❌ Error {response.status_code}: {response.text}")
            except Exception as e:
                st.error(f"⚠️ Request failed: {str(e)}")
    else:
        st.warning("Please enter a repository URL first.")
