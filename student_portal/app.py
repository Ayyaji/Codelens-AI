import streamlit as st
import time
import requests
from database import init_db, add_student, get_student, log_session, get_student_sessions
from behaviour import render_behaviour_tracker

# Initialize database
init_db()

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.student_id = None
    st.session_state.student_name = ""
    st.session_state.uploaded_code = ""


def show_login():
    st.title("🔍 CodeLens AI")
    st.subheader("Student Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Login"):
            student = get_student(username, password)
            if student:
                st.session_state.logged_in = True
                st.session_state.student_id = student["id"]
                st.session_state.student_name = student["name"]
                st.rerun()
            else:
                st.error("❌ Invalid username or password")

    with col2:
        if st.button("Register"):
            if username and password:
                add_student(username, password, username)
                st.success("✅ Account created! Please login.")
            else:
                st.warning("⚠️ Enter username and password first")


def show_dashboard():
    st.title(f"👋 Welcome, {st.session_state.student_name}!")

    # Behaviour tracker runs silently in background
    render_behaviour_tracker()

    # Start tracking time when dashboard loads
    if "typing_start" not in st.session_state:
        st.session_state.typing_start = time.time()

    st.markdown("---")

    # ── SECTION 1: Ask Question ──────────────────────────────────────
    st.subheader("🐛 Paste Your Error")
    error_text = st.text_area("Error Message", placeholder="Paste your error here...")
    code_snippet = st.text_area("Code Snippet", placeholder="Paste your code here...")

    # File upload option
    st.markdown("**Or upload a .py file:**")
    uploaded_file = st.file_uploader("Upload Python file", type=["py"])
    if uploaded_file is not None:
        file_content = uploaded_file.read().decode("utf-8")
        st.code(file_content, language="python")
        if not code_snippet:
            st.session_state.uploaded_code = file_content
            st.info("✅ File uploaded. Add an error message above and click Ask CodeLens AI.")

    if st.button("Ask CodeLens AI"):
        if error_text:
            with st.spinner("CodeLens AI is thinking..."):

                # Calculate behaviour on Python side
                duration = int(time.time() - st.session_state.get("typing_start", time.time()))
                words = len(error_text.split())
                wpm = int((words / max(duration, 1)) * 60)
                backspaces = max(0, len(error_text) // 10)

                # Combine error + uploaded code for richer context
                uploaded_code = st.session_state.get("uploaded_code", "")
                full_query = error_text
                if uploaded_code:
                    full_query = f"{error_text}\n\nCode:\n{uploaded_code}"
                elif code_snippet:
                    full_query = f"{error_text}\n\nCode:\n{code_snippet}"

                # Call M1's API
                try:
                    response = requests.post(
                        "http://localhost:8000/ask",
                        json={
                            "student_id": str(st.session_state.student_id),
                            "query": full_query
                        },
                        timeout=120
                    )

                    if response.status_code == 200:
                        data = response.json()
                        answer = data["answer"]
                        agent_used = data["agent_used"]

                        # Show answer
                        st.chat_message("assistant").write(answer)
                        st.badge(f"⚡ Answered by: {agent_used}")

                    else:
                        answer = "API returned an error"
                        agent_used = "Unknown"
                        st.error(f"❌ API error: {response.status_code}")

                except requests.exceptions.ConnectionError:
                    answer = "M1 API not reachable"
                    agent_used = "Unknown"
                    st.warning("⚠️ M1 API is not running. Start it with: uvicorn rag_core.api:app")

                except Exception as e:
                    answer = "Unexpected error"
                    agent_used = "Unknown"
                    st.error(f"❌ Error: {str(e)}")

                # Log session to database
                session_id = log_session(
                    st.session_state.student_id,
                    error_text,
                    answer,
                    agent_used,
                    duration
                )

                # Reset uploaded code and typing timer
                st.session_state.uploaded_code = ""
                if "typing_start" in st.session_state:
                    del st.session_state.typing_start

                st.success("✅ Session logged successfully")
                st.caption(f"📊 Your typing — WPM: {wpm} | Backspaces: {backspaces} | Duration: {duration}s")

        else:
            st.warning("⚠️ Please paste an error message first")

    st.markdown("---")

    # ── SECTION 2: History ───────────────────────────────────────────
    st.subheader("📋 Your Past Sessions")
    sessions = get_student_sessions(st.session_state.student_id)
    if sessions:
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Sessions", len(sessions))

        agents = [s["agent_used"] for s in sessions]
        most_common = max(set(agents), key=agents.count)
        col2.metric("Most Used Agent", most_common)

        avg_duration = sum(s["duration_seconds"] for s in sessions) // len(sessions)
        col3.metric("Avg Duration", f"{avg_duration}s")

        st.markdown("---")

        # Session cards
        for s in sessions:
            with st.expander(f"🕐 {s['timestamp']} — {s['agent_used']}"):
                st.write("**Error:**", s['error_text'])
                st.write("**Answer:**", s['answer'])
                st.caption(f"⏱ Duration: {s['duration_seconds']}s")
    else:
        st.info("No sessions yet. Ask your first question above!")

    st.markdown("---")

    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.student_id = None
        st.session_state.student_name = ""
        st.session_state.uploaded_code = ""
        st.rerun()


# Main app router
if st.session_state.logged_in:
    show_dashboard()
else:
    show_login()