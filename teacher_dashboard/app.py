import streamlit as st
import sys
import os
import pandas as pd
import plotly.express as px
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'student_portal'))
from database import (init_db, get_teacher, add_teacher, get_all_sessions,
                      get_pending_kb, update_kb_status, get_all_behaviour)

# Initialize database
init_db()

# Initialize session state
if "teacher_logged_in" not in st.session_state:
    st.session_state.teacher_logged_in = False
    st.session_state.teacher_id = None
    st.session_state.teacher_name = ""


def show_login():
    st.title("🎓 CodeLens AI — Teacher Portal")
    st.subheader("Teacher Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Login"):
            teacher = get_teacher(username, password)
            if teacher:
                st.session_state.teacher_logged_in = True
                st.session_state.teacher_id = teacher["id"]
                st.session_state.teacher_name = teacher["name"]
                st.rerun()
            else:
                st.error("❌ Invalid username or password")

    with col2:
        if st.button("Register"):
            if username and password:
                add_teacher(username, password, username, "General")
                st.success("✅ Teacher account created! Please login.")
            else:
                st.warning("⚠️ Enter username and password first")


def show_dashboard():
    st.title(f"👋 Welcome, {st.session_state.teacher_name}!")
    st.markdown("---")

    # ── SECTION 1: Metrics ──────────────────────────────────────────
    st.subheader("📊 Class Overview")

    sessions = get_all_sessions()
    behaviour = get_all_behaviour()
    pending_kb = get_pending_kb()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Sessions", len(sessions))
    col2.metric("Pending KB Reviews", len(pending_kb))
    col3.metric("Behaviour Records", len(behaviour))

    st.markdown("---")

    # ── SECTION 2: Session Monitoring ───────────────────────────────
    st.subheader("📋 Student Sessions")

    if sessions:
        df = pd.DataFrame([dict(s) for s in sessions])

        filter_option = st.selectbox(
            "Filter by", ["All Time", "Today", "This Week"])

        if filter_option == "Today":
            today = pd.Timestamp.now().strftime("%Y-%m-%d")
            df = df[df["timestamp"].str.startswith(today)]
        elif filter_option == "This Week":
            week_ago = (pd.Timestamp.now() -
                        pd.Timedelta(days=7)).strftime("%Y-%m-%d")
            df = df[df["timestamp"] >= week_ago]

        st.dataframe(df[[
            "student_name", "timestamp",
            "agent_used", "duration_seconds", "error_text"
        ]], use_container_width=True)

        st.subheader("🤖 Agent Usage")
        agent_counts = df["agent_used"].value_counts().reset_index()
        agent_counts.columns = ["Agent", "Count"]
        fig = px.bar(agent_counts, x="Agent", y="Count",
                     color="Agent", title="Queries per Agent")
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("No student sessions yet.")

    st.markdown("---")

    # ── SECTION 3: KB Approval ───────────────────────────────────────
    st.subheader("📚 Knowledge Base Approval")

    if pending_kb:
        st.warning(f"⚠️ {len(pending_kb)} KB items need your review")
        for item in pending_kb:
            with st.expander(f"📄 {item['source']} — {item['timestamp']}"):
                st.write("**Content:**", item["content"])
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"✅ Approve", key=f"approve_{item['id']}"):
                        update_kb_status(item["id"], "approved")
                        st.success("Approved!")
                        st.rerun()
                with col2:
                    if st.button(f"❌ Reject", key=f"reject_{item['id']}"):
                        update_kb_status(item["id"], "rejected")
                        st.error("Rejected!")
                        st.rerun()
    else:
        st.success("✅ No pending KB entries. All clear!")

    st.markdown("---")

    # ── SECTION 4: Behaviour Monitoring ─────────────────────────────
    st.subheader("🔍 Behaviour Monitoring")

    if behaviour:
        bdf = pd.DataFrame([dict(b) for b in behaviour])
        bdf["flagged"] = bdf["avg_wpm"] > 80

        def highlight_flagged(row):
            if row["flagged"]:
                return ["background-color: #ffcccc"] * len(row)
            return [""] * len(row)

        st.dataframe(
            bdf[["student_name", "avg_wpm",
                 "backspace_count", "duration", "flagged"]]
            .style.apply(highlight_flagged, axis=1),
            use_container_width=True
        )
    else:
        st.info("No behaviour data yet.")

    st.markdown("---")

    # ── SECTION 5: Student Drill-Down ────────────────────────────────
    st.subheader("🔎 Student Drill-Down")

    if sessions:
        df_all = pd.DataFrame([dict(s) for s in sessions])
        student_list = df_all["student_name"].unique().tolist()
        selected = st.selectbox("Select Student", student_list)

        student_df = df_all[df_all["student_name"] == selected]
        st.write(f"**Total sessions:** {len(student_df)}")
        st.dataframe(student_df[[
            "timestamp", "agent_used",
            "duration_seconds", "error_text"
        ]], use_container_width=True)

        csv = student_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Report",
            data=csv,
            file_name=f"{selected}_report.csv",
            mime="text/csv"
        )
    else:
        st.info("No sessions available for drill-down.")

    st.markdown("---")

    if st.button("Logout"):
        st.session_state.teacher_logged_in = False
        st.session_state.teacher_id = None
        st.session_state.teacher_name = ""
        st.rerun()


# Main router
if st.session_state.teacher_logged_in:
    show_dashboard()
else:
    show_login()