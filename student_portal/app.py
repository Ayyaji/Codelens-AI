import streamlit as st
from database import init_db, add_student, get_student, log_session, get_student_sessions

# Initialize database
init_db()

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.student_id = None
    st.session_state.student_name = ""


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
    st.markdown("---")

    st.subheader("🐛 Paste Your Error")
    error_text = st.text_area("Error Message", placeholder="Paste your error here...")
    code_snippet = st.text_area("Code Snippet", placeholder="Paste your code here...")

    if st.button("Ask CodeLens AI"):
        if error_text:
            with st.spinner("CodeLens AI is thinking..."):
                st.info("⚡ Answer will appear here once M1 API is ready")
                log_session(
                    st.session_state.student_id,
                    error_text,
                    "Pending M1 API",
                    "Unknown",
                    0
                )
                st.success("✅ Session logged successfully")
        else:
            st.warning("⚠️ Please paste an error message first")

    st.markdown("---")
    st.subheader("📋 Your Past Sessions")
    sessions = get_student_sessions(st.session_state.student_id)
    if sessions:
        for s in sessions:
            with st.expander(f"🕐 {s['timestamp']} — {s['agent_used']}"):
                st.write("**Error:**", s['error_text'])
                st.write("**Answer:**", s['answer'])
    else:
        st.info("No sessions yet. Ask your first question above!")

    st.markdown("---")
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.student_id = None
        st.session_state.student_name = ""
        st.rerun()


# Main app router
if st.session_state.logged_in:
    show_dashboard()
else:
    show_login()