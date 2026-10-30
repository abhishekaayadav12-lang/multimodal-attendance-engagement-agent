import os
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from database import (
    analytics,
    attendance,
    create_session,
    delete_session,
    init,
    save_analytics,
    save_attendance,
    sessions,
)
from vision import analyze_video
from audio import analyze_audio
from agent import fuse, suggestions


st.set_page_config(
    page_title="Multimodal Attendance & Engagement Agent",
    page_icon="🎓",
    layout="wide",
)

init()

if "visual" not in st.session_state:
    st.session_state.visual = []
if "audio" not in st.session_state:
    st.session_state.audio = []
if "fused" not in st.session_state:
    st.session_state.fused = []


def fmt_time(seconds):
    seconds = int(seconds or 0)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


st.title("🎓 Multimodal Attendance & Engagement Agent")
st.caption(
    "Local-first classroom analytics • Anonymous tracking • No speech transcription"
)

# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("Session")
    all_sessions = sessions()

    if all_sessions:
        labels = {
            f"#{x['id']} — {x['name']}": x["id"] for x in all_sessions
        }
        selected_label = st.selectbox("Select session", list(labels.keys()))
        session_id = labels[selected_label]
        current_session = next(
            x for x in all_sessions if x["id"] == session_id
        )
    else:
        st.info("Create a session to begin.")
        session_id = None
        current_session = None

    st.divider()
    page = st.radio(
        "Module",
        [
            "🏠 Dashboard",
            "➕ Create Session",
            "🎥 Vision & Attendance",
            "🎙️ Audio Analysis",
            "📊 Analytics",
            "🔒 Privacy",
        ],
    )

# ---------------- Dashboard ----------------
if page == "🏠 Dashboard":
    st.subheader("Project workflow")
    st.markdown(
        """
        **1. Create Session → 2. Upload Video → 3. Analyze Attendance →
        4. Upload WAV (optional) → 5. Fuse Signals → 6. Export Results**
        """
    )

    if current_session:
        att = attendance(session_id)
        an = analytics(session_id)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Current Session", current_session["name"])
        c2.metric("Present Tracks", len(att))
        c3.metric("Analytics Windows", len(an))
        c4.metric(
            "Avg Activity",
            f"{sum(x['engagement_score'] for x in an)/len(an):.1f}"
            if an
            else "—",
        )

        st.info(
            "Track IDs are anonymous. Results are activity proxies and should "
            "not be used for grading, discipline, or high-stakes decisions."
        )
    else:
        st.warning("No session selected. Use 'Create Session' in the sidebar.")

# ---------------- Create Session ----------------
elif page == "➕ Create Session":
    st.subheader("Create a classroom session")

    with st.form("create_session_form"):
        name = st.text_input(
            "Session name",
            placeholder="e.g. B.Tech AI Unit 4 — Morning Class",
        )
        submitted = st.form_submit_button(
            "Create Session", type="primary", use_container_width=True
        )

    if submitted:
        if not name.strip():
            st.error("Please enter a session name.")
        else:
            new_id = create_session(name.strip())
            st.success(f"Session #{new_id} created successfully.")
            st.rerun()

    st.divider()
    st.subheader("Existing sessions")

    if all_sessions:
        df = pd.DataFrame(all_sessions)
        st.dataframe(
            df[["id", "name", "started"]],
            use_container_width=True,
            hide_index=True,
        )

        if session_id and st.button("Delete selected session", type="secondary"):
            delete_session(session_id)
            st.session_state.visual = []
            st.session_state.audio = []
            st.session_state.fused = []
            st.success("Selected session deleted.")
            st.rerun()

# ---------------- Vision ----------------
elif page == "🎥 Vision & Attendance":
    st.subheader("🎥 Video → Anonymous Attendance")

    if not session_id:
        st.warning("Create a session first.")
    else:
        st.write(
            "Upload a classroom video. The system detects faces and tracks "
            "anonymous people across sampled frames."
        )

        uploaded = st.file_uploader(
            "Upload classroom video",
            type=["mp4", "mov", "avi", "mkv"],
            help="Use a short test video first.",
        )

        col1, col2 = st.columns(2)
        with col1:
            threshold = st.number_input(
                "Minimum presence (seconds)",
                min_value=1,
                max_value=300,
                value=8,
                step=1,
            )
        with col2:
            window = st.number_input(
                "Analytics window (seconds)",
                min_value=5,
                max_value=120,
                value=30,
                step=5,
            )

        if uploaded and st.button(
            "▶ Analyze Video", type="primary", use_container_width=True
        ):
            suffix = Path(uploaded.name).suffix or ".mp4"
            temp_path = None

            try:
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=suffix
                ) as tmp:
                    tmp.write(uploaded.getbuffer())
                    temp_path = tmp.name

                with st.spinner("Analyzing video locally..."):
                    rows, visual, meta = analyze_video(
                        temp_path,
                        threshold=float(threshold),
                        window_seconds=int(window),
                    )

                st.session_state.visual = visual
                st.session_state.fused = []

                save_attendance(session_id, rows)

                st.success(
                    f"Analysis complete: {len(rows)} anonymous track(s) "
                    f"met the presence threshold."
                )

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Video duration", fmt_time(meta["duration_seconds"]))
                m2.metric("Frames", meta["frames_processed"])
                m3.metric("Tracks", meta["tracks_detected"])
                m4.metric("Present", meta["present_tracks"])

                if rows:
                    st.subheader("Attendance output")
                    df = pd.DataFrame(rows)
                    st.dataframe(df, use_container_width=True, hide_index=True)

                    st.download_button(
                        "⬇ Download Attendance CSV",
                        df.to_csv(index=False).encode("utf-8"),
                        "attendance.csv",
                        "text/csv",
                        use_container_width=True,
                    )
                else:
                    st.warning(
                        "No track stayed visible for the selected threshold. "
                        "Try a shorter threshold or a clearer video."
                    )

                with st.expander("Technical processing details"):
                    st.json(meta)

            except Exception as exc:
                st.error(f"Video analysis failed: {exc}")
            finally:
                if temp_path and os.path.exists(temp_path):
                    os.unlink(temp_path)

        st.divider()
        existing = attendance(session_id)
        if existing:
            st.subheader("Saved attendance")
            st.dataframe(
                pd.DataFrame(existing),
                use_container_width=True,
                hide_index=True,
            )

# ---------------- Audio ----------------
elif page == "🎙️ Audio Analysis":
    st.subheader("🎙️ WAV → Acoustic Activity")

    if not session_id:
        st.warning("Create a session first.")
    else:
        st.write(
            "Upload WAV audio to estimate acoustic activity. The system does "
            "not transcribe speech or identify speakers."
        )

        uploaded = st.file_uploader(
            "Upload classroom WAV",
            type=["wav"],
        )

        threshold = st.number_input(
            "Energy threshold",
            min_value=0.001,
            max_value=0.2,
            value=0.015,
            step=0.001,
            format="%.3f",
        )

        if uploaded and st.button(
            "▶ Analyze Audio", type="primary", use_container_width=True
        ):
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".wav"
                ) as tmp:
                    tmp.write(uploaded.getbuffer())
                    temp_path = tmp.name

                with st.spinner("Analyzing audio locally..."):
                    audio_rows = analyze_audio(
                        temp_path,
                        window_seconds=30,
                        threshold=float(threshold),
                    )

                st.session_state.audio = audio_rows
                st.session_state.fused = []

                if audio_rows:
                    df = pd.DataFrame(audio_rows)
                    st.success(f"Analyzed {len(audio_rows)} time window(s).")
                    st.dataframe(
                        df, use_container_width=True, hide_index=True
                    )

                    st.download_button(
                        "⬇ Download Audio CSV",
                        df.to_csv(index=False).encode("utf-8"),
                        "audio_activity.csv",
                        "text/csv",
                        use_container_width=True,
                    )
                else:
                    st.warning("The audio file did not contain usable samples.")

            except Exception as exc:
                st.error(f"Audio analysis failed: {exc}")
            finally:
                if temp_path and os.path.exists(temp_path):
                    os.unlink(temp_path)

# ---------------- Analytics ----------------
elif page == "📊 Analytics":
    st.subheader("📊 Multimodal Analytics")

    if not session_id:
        st.warning("Create a session first.")
    else:
        visual = st.session_state.visual
        audio = st.session_state.audio

        # If Streamlit restarted, recover persisted analytics.
        saved = analytics(session_id)

        c1, c2, c3 = st.columns(3)
        c1.metric("Video windows", len(visual))
        c2.metric("Audio windows", len(audio))
        c3.metric("Saved analytics", len(saved))

        if st.button(
            "🔄 Fuse Signals & Generate Output",
            type="primary",
            use_container_width=True,
        ):
            rows = fuse(visual, audio)

            if not rows:
                rows = saved

            if rows:
                save_analytics(session_id, rows)
                st.session_state.fused = rows
                st.success("Multimodal analytics generated successfully.")
            else:
                st.warning(
                    "Analyze a video and/or WAV audio first."
                )

        rows = st.session_state.fused or analytics(session_id)

        if rows:
            df = pd.DataFrame(rows)

            st.subheader("Engagement/activity trend")
            chart_df = df[["window_start", "engagement_score"]].copy()
            chart_df = chart_df.set_index("window_start")
            st.line_chart(chart_df)

            st.subheader("Detailed output")
            st.dataframe(
                df, use_container_width=True, hide_index=True
            )

            avg = float(df["engagement_score"].mean())
            high = int((df["engagement_score"] >= 60).sum())
            low = int((df["engagement_score"] < 30).sum())

            m1, m2, m3 = st.columns(3)
            m1.metric("Average activity", f"{avg:.1f}/100")
            m2.metric("High windows", high)
            m3.metric("Low windows", low)

            st.subheader("Teaching suggestions")
            for item in suggestions(rows):
                st.write("• " + item)

            st.download_button(
                "⬇ Download Full Analytics CSV",
                df.to_csv(index=False).encode("utf-8"),
                "multimodal_analytics.csv",
                "text/csv",
                use_container_width=True,
            )

        attendance_rows = attendance(session_id)
        if attendance_rows:
            st.divider()
            st.subheader("Attendance export")
            adf = pd.DataFrame(attendance_rows)
            st.dataframe(adf, use_container_width=True, hide_index=True)
            st.download_button(
                "⬇ Download Attendance CSV",
                adf.to_csv(index=False).encode("utf-8"),
                "attendance.csv",
                "text/csv",
                use_container_width=True,
            )

# ---------------- Privacy ----------------
elif page == "🔒 Privacy":
    st.subheader("🔒 Privacy & limitations")
    st.markdown(
        """
        - Video/audio are processed locally from temporary files.
        - Media files are not stored in SQLite.
        - Track IDs are anonymous and are not linked to real identities.
        - Audio analysis uses acoustic energy only; it does not transcribe speech.
        - Activity/engagement scores are heuristic proxies, not objective measures of
          attention, emotion, learning, or participation.
        - Do not use these outputs for grading, punishment, or other high-stakes decisions.
        - Obtain informed consent, provide an opt-out, restrict access, and follow your
          institution's privacy/retention policy.
        """
    )
