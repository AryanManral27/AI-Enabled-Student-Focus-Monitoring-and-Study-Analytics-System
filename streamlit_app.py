import streamlit as st
import cv2
import numpy as np
import time
import io
import csv
from datetime import datetime
from focus_detector_logic import FocusDetectorLogic
from activity_tracker import ActivityTracker
from study_analytics_dashboard import (
    render_analytics_tab,
    log_session_and_usage,
)
from parental_teacher_dashboard import render_dashboard_tab

# Try to import reportlab for PDF generation
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib import colors
    from io import BytesIO
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

st.set_page_config(page_title="AI-ENABLED STUDENT FOCUS MONITORING AND STUDY ANALYTICS SYSTEM", layout="wide")

# Webcam preview size in the UI (pixels). Both are applied by resizing the frame before display.
# Lower WEBCAM_DISPLAY_WIDTH_PX / WEBCAM_DISPLAY_HEIGHT_PX to make the preview smaller.
WEBCAM_DISPLAY_WIDTH_PX = 1080
WEBCAM_DISPLAY_HEIGHT_PX = 580

# Custom CSS for a cleaner look
st.markdown("""
<style>
.stApp { background-color: #f0f2f6; } /* Light gray background */
.reportview-container .main .block-container{ padding-top: 2rem; padding-bottom: 2rem; } /* Adjust padding */
.css-1d391kg { padding-top: 2rem; } /* Adjust header padding */
.stButton>button { 
    border-radius: 20px;
    border: 1px solid #007bff;
    color: white;
    background-color: #007bff;
    padding: 10px 20px;
    font-size: 16px;
    transition: all 0.2s ease;
}
.stButton>button:hover {
    background-color: #0056b3;
    border-color: #0056b3;
}
.stSlider > div > div > div > div { background-color: #007bff; } /* Slider color */
.stCheckbox > label > div[data-testid="stCheckboxIcon"] { border: 2px solid #007bff; } /* Checkbox border */
.stCheckbox > label > div[data-testid="stCheckboxIcon"][aria-checked="true"] { background-color: #007bff; border-color: #007bff; } /* Checked checkbox */
</style>
""", unsafe_allow_html=True)

st.title("🎓 AI-ENABLED STUDENT FOCUS MONITORING AND STUDY ANALYTICS SYSTEM")
st.markdown("---")

# Initialize session state variables
if 'detector' not in st.session_state:
    st.session_state.detector = FocusDetectorLogic()
if 'is_running' not in st.session_state:
    st.session_state.is_running = False
if 'cap' not in st.session_state:
    st.session_state.cap = None
if 'video_placeholder' not in st.session_state:
    st.session_state.video_placeholder = None
if 'stop_clicked' not in st.session_state:
    st.session_state.stop_clicked = False
if "session_logged" not in st.session_state:
    st.session_state.session_logged = False
if "activity_tracker" not in st.session_state:
    st.session_state.activity_tracker = ActivityTracker()
    st.session_state.activity_tracker.start()
if "student_name" not in st.session_state:
    st.session_state.student_name = None
if "roll_number" not in st.session_state:
    st.session_state.roll_number = None
if "student_registered" not in st.session_state:
    st.session_state.student_registered = False
if "session_summary_text" not in st.session_state:
    st.session_state.session_summary_text = None
if "stats_placeholders" not in st.session_state:
    st.session_state.stats_placeholders = {}

def start_session():
    if not st.session_state.is_running:
        # Check if student is registered
        if not st.session_state.student_registered or not st.session_state.student_name or not st.session_state.roll_number:
            st.error("⚠️ Please register your student information first before starting a session!")
            return
        
        st.session_state.is_running = True
        st.session_state.stop_clicked = False
        st.session_state.session_logged = False
        st.session_state.session_summary_text = None  # Clear previous summary
        st.session_state.detector.session_data = st.session_state.detector.reset_session_data()
        
        st.session_state.cap = cv2.VideoCapture(0)
        if not st.session_state.cap.isOpened():
            st.error("Could not open camera!")
            st.session_state.is_running = False
            return

def stop_session():
    if st.session_state.is_running:
        st.session_state.is_running = False
        st.session_state.stop_clicked = True
        if st.session_state.cap:
            st.session_state.cap.release()
            st.session_state.cap = None

def reset_session():
    stop_session()
    st.session_state.detector = FocusDetectorLogic()
    st.session_state.activity_tracker.reset()
    st.session_state.is_running = False
    st.session_state.stop_clicked = False
    st.session_state.session_logged = False
    st.session_state.session_summary_text = None  # Clear summary

def display_session_summary(summary_text: str) -> None:
    """Display session summary in a vertical, line-by-line format."""
    lines = summary_text.strip().split('\n')
    with st.container():
        for line in lines:
            if line.strip():  # Skip empty lines
                st.markdown(line)
            else:
                st.markdown("")  # Preserve spacing for empty lines

def generate_activity_report_pdf(tracker: ActivityTracker, student_name: str = None, roll_number: str = None) -> bytes:
    """Generate PDF report for activity report containing platform usage and switch logs."""
    if not REPORTLAB_AVAILABLE:
        raise ImportError(
            "reportlab is not installed. Please install it using: pip install reportlab"
        )
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=18,
        textColor=colors.HexColor("#1f4788"),
        spaceAfter=30,
    )
    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.HexColor("#2c3e50"),
        spaceAfter=12,
    )

    # Title
    title_text = "Activity Report - Platform Usage & Switch Logs"
    story.append(Paragraph(title_text, title_style))
    story.append(Spacer(1, 0.2 * inch))

    # Student Info (if available)
    if student_name:
        story.append(Paragraph(f"<b>Student Name:</b> {student_name}", styles["Normal"]))
    if roll_number:
        story.append(Paragraph(f"<b>Roll Number:</b> {roll_number}", styles["Normal"]))
    story.append(Paragraph(f"<b>Report Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]))
    story.append(Spacer(1, 0.3 * inch))

    # Current Activity
    story.append(Paragraph("Current Activity", heading_style))
    snap = tracker.current_snapshot
    is_edu = tracker.is_educational(snap)
    edu_text = "Educational" if is_edu else "Non-educational"
    story.append(Paragraph(f"<b>Platform:</b> {snap.label}", styles["Normal"]))
    story.append(Paragraph(f"<b>Type:</b> {snap.kind}", styles["Normal"]))
    story.append(Paragraph(f"<b>Category:</b> {edu_text}", styles["Normal"]))
    story.append(Paragraph(f"<b>Points:</b> {tracker.points:.1f}", styles["Normal"]))
    if tracker.last_warning:
        story.append(Paragraph(f"<b>Last Warning:</b> {tracker.last_warning}", styles["Normal"]))
    story.append(Spacer(1, 0.3 * inch))

    # Platform Usage Durations
    story.append(Paragraph("Platform Usage Durations", heading_style))
    tb = dict(tracker.time_by_platform_sec)
    if snap.label:
        current_time = time.time()
        tb[snap.label] = tb.get(snap.label, 0.0) + tracker.get_live_time_for_current_platform_sec(now=current_time)
    
    if tb:
        # Sort by time (descending) and convert to hours/minutes/seconds
        sorted_platforms = sorted(tb.items(), key=lambda kv: kv[1], reverse=True)
        
        platform_data = [["Platform", "Time (Hours)", "Time (Minutes)", "Time (Seconds)"]]
        for platform, secs in sorted_platforms:
            hours = secs / 3600.0
            minutes = (secs % 3600) / 60.0
            seconds = secs % 60.0
            platform_data.append([
                platform,
                f"{hours:.2f}",
                f"{minutes:.2f}",
                f"{seconds:.2f}"
            ])
        
        platform_table = Table(platform_data)
        platform_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(platform_table)
    else:
        story.append(Paragraph("No platform usage data available.", styles["Normal"]))
    
    story.append(Spacer(1, 0.3 * inch))

    # Tab-Switch Activity Logs
    story.append(Paragraph("Tab-Switch Activity Logs", heading_style))
    if tracker.switch_events:
        switch_data = [["Time", "From", "To", "From Type", "To Type", "Educational"]]
        # Show all switch events (or last 50 if too many)
        events_to_show = tracker.switch_events[-50:] if len(tracker.switch_events) > 50 else tracker.switch_events
        for ev in events_to_show:
            switch_data.append([
                ev.get("time", ""),
                ev.get("from", ""),
                ev.get("to", ""),
                ev.get("from_kind", ""),
                ev.get("to_kind", ""),
                ev.get("to_educational", ""),
            ])
        
        switch_table = Table(switch_data)
        switch_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("FONTSIZE", (0, 1), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                ]
            )
        )
        story.append(switch_table)
        if len(tracker.switch_events) > 50:
            story.append(Paragraph(f"<i>Note: Showing last 50 of {len(tracker.switch_events)} switch events.</i>", styles["Normal"]))
    else:
        story.append(Paragraph("No switch events recorded.", styles["Normal"]))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# Layout with tabs
tab_live, tab_stats_settings, tab_activity, tab_analytics, tab_dashboard = st.tabs(
    ["📹 Live Camera Feed", "📊 Statistics & Settings", "🧭 Activity Report", "📈 Study Analytics", "👨‍👩‍👧👨‍🏫 Parent/Teacher Dashboard"]
)

with tab_live:
    st.subheader("📹 Live Camera Feed")
    
    # Student Registration Form
    if not st.session_state.student_registered:
        st.markdown("### 👤 Student Registration")
        st.info("⚠️ Please register your student information before starting a study session.")
        with st.form("student_registration_form"):
            student_name_input = st.text_input("Student Name *", placeholder="Enter your name", value=st.session_state.student_name or "")
            roll_number_input = st.text_input("Roll Number *", placeholder="Enter your roll number", value=st.session_state.roll_number or "")
            register_submitted = st.form_submit_button("✅ Register", type="primary")
            
            if register_submitted:
                if not student_name_input.strip() or not roll_number_input.strip():
                    st.error("Please fill in both Student Name and Roll Number.")
                else:
                    st.session_state.student_name = student_name_input.strip()
                    st.session_state.roll_number = roll_number_input.strip()
                    st.session_state.student_registered = True
                    st.success(f"✅ Registered as: {st.session_state.student_name} (Roll: {st.session_state.roll_number})")
                    st.rerun()
    else:
        st.success(f"✅ Registered as: **{st.session_state.student_name}** (Roll: **{st.session_state.roll_number}**)")
        if st.button("🔄 Change Registration"):
            st.session_state.student_registered = False
            st.session_state.student_name = None
            st.session_state.roll_number = None
            st.rerun()
        st.markdown("---")
    
    st.session_state.video_placeholder = st.empty()

    # Control buttons
    btn_col1, btn_col2, btn_col3 = st.columns(3)
    with btn_col1:
        st.button(
            "🚀 Start Session",
            on_click=start_session,
            disabled=st.session_state.is_running or not st.session_state.student_registered,
            help="Start the focus detection session.",
        )
    with btn_col2:
        st.button(
            "⏹️ Stop Session",
            on_click=stop_session,
            disabled=not st.session_state.is_running,
            help="Stop the current session.",
        )
    with btn_col3:
        st.button(
            "🔄 Reset Session",
            on_click=reset_session,
            help="Reset all session data.",
        )

with tab_stats_settings:
    st.subheader("📊 Session Statistics")
    
    # Display session summary if available (only shown in this tab)
    if st.session_state.get("session_summary_text"):
        display_session_summary(st.session_state.session_summary_text)
        st.markdown("---")

    # Real-time stats - only show entire sections when session is running
    if st.session_state.is_running:
        st.markdown("#### Time Tracking")
        study_time_ph = st.empty()
        focus_time_ph = st.empty()
        focus_rate_ph = st.empty()

        st.markdown("#### Progress")
        study_progress_ph = st.empty()
        focus_progress_ph = st.empty()

        st.markdown("#### Status & Rewards")
        status_ph = st.empty()
        tier_ph = st.empty()
        reward_ph = st.empty()

        st.markdown("--- ")
        st.subheader("Live Metrics")
        ear_label_ph = st.empty()
        fps_label_ph = st.empty()
        
        # Store placeholders in session state for access in video loop
        st.session_state.stats_placeholders = {
            'study_time': study_time_ph,
            'focus_time': focus_time_ph,
            'focus_rate': focus_rate_ph,
            'study_progress': study_progress_ph,
            'focus_progress': focus_progress_ph,
            'status': status_ph,
            'tier': tier_ph,
            'reward': reward_ph,
            'ear': ear_label_ph,
            'fps': fps_label_ph,
        }
    else:
        # Create empty placeholders that won't be used (for video loop compatibility)
        # but don't display any section headers
        study_time_ph = st.empty()
        focus_time_ph = st.empty()
        focus_rate_ph = st.empty()
        study_progress_ph = st.empty()
        focus_progress_ph = st.empty()
        status_ph = st.empty()
        tier_ph = st.empty()
        reward_ph = st.empty()
        ear_label_ph = st.empty()
        fps_label_ph = st.empty()
        
        # Store placeholders in session state (empty dict if not running)
        st.session_state.stats_placeholders = {
            'study_time': study_time_ph,
            'focus_time': focus_time_ph,
            'focus_rate': focus_rate_ph,
            'study_progress': study_progress_ph,
            'focus_progress': focus_progress_ph,
            'status': status_ph,
            'tier': tier_ph,
            'reward': reward_ph,
            'ear': ear_label_ph,
            'fps': fps_label_ph,
        }
        
        # Ensure all placeholders are empty when session is not running
        for ph in st.session_state.stats_placeholders.values():
            ph.empty()

    st.markdown("---")
    st.subheader("⚙️ Settings")
    ear_threshold = st.slider(
        "Eye Detection Sensitivity",
        min_value=0.10,
        max_value=0.30,
        value=st.session_state.detector.EAR_THRESHOLD,
        step=0.01,
        help="Adjust the sensitivity for eye closure detection. Lower values mean more sensitive.",
    )
    st.session_state.detector.EAR_THRESHOLD = ear_threshold

    debug_mode = st.checkbox(
        "Debug Mode",
        help="Reserved for additional visual debugging options.",
    )

with tab_activity:
    st.subheader("🧭 Activity Report")
    current_activity_ph = st.empty()
    activity_warning_ph = st.empty()
    points_ph = st.empty()
    activity_table_ph = st.empty()
    switch_log_ph = st.empty()
    st.markdown("---")
    
    # Download buttons section
    if "activity_tracker" in st.session_state:
        tracker = st.session_state.activity_tracker
        
        # PDF Download button (full report)
        col_pdf = st.columns(1)
        with col_pdf[0]:
            if tracker.time_by_platform_sec or tracker.switch_events:
                try:
                    student_name = st.session_state.get("student_name", "Unknown")
                    roll_number = st.session_state.get("roll_number", "Unknown")
                    pdf_bytes = generate_activity_report_pdf(tracker, student_name, roll_number)
                    st.download_button(
                        "📥 Download Activity Report (PDF)",
                        data=pdf_bytes,
                        file_name=f"activity_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf",
                        help="Download complete activity report with platform usage durations and switch logs",
                    )
                except ImportError as e:
                    st.warning(f"⚠️ PDF download unavailable: {e}")
                except Exception as e:
                    st.error(f"❌ Error generating PDF: {e}")
            else:
                st.info("No activity data available for download.")

with tab_analytics:
    render_analytics_tab()

with tab_dashboard:
    render_dashboard_tab()

def render_activity_report_ui(current_time: float | None = None) -> None:
    """Render current activity state into the tab placeholders.

    Called both while the session is running and after it stops so that
    the Activity Report always shows the latest data.
    """
    if "activity_tracker" not in st.session_state:
        return
    tracker = st.session_state.activity_tracker
    snap = tracker.current_snapshot
    if current_time is None:
        current_time = time.time()

    label = snap.label
    kind = snap.kind
    is_edu = tracker.is_educational(snap)

    edu_text = "✅ Educational" if is_edu else "⚠ Non-educational"
    current_activity_ph.markdown(f"**Current:** `{kind}` — **{label}** — {edu_text}")

    if tracker.last_warning:
        activity_warning_ph.warning(tracker.last_warning)
    else:
        activity_warning_ph.empty()

    points_ph.metric("Points", f"{tracker.points:.1f}")

    # time table
    tb = dict(tracker.time_by_platform_sec)
    tb[label] = tb.get(label, 0.0) + tracker.get_live_time_for_current_platform_sec(
        now=current_time
    )
    rows = sorted(tb.items(), key=lambda kv: kv[1], reverse=True)[:15]
    if rows:
        activity_table_ph.table(
            [{"Platform": k, "Time (sec)": f"{v:.1f}"} for k, v in rows]
        )
    else:
        activity_table_ph.info("No activity captured yet.")

    # switch log
    if tracker.switch_events:
        switch_log_ph.table(tracker.switch_events[-10:])
    else:
        switch_log_ph.info("No switches recorded yet.")

# Video processing loop
if st.session_state.is_running and st.session_state.cap:
    fps_counter = 0
    fps_start_time = time.time()
    
    while st.session_state.is_running and st.session_state.cap.isOpened() and not st.session_state.stop_clicked:
        ret, frame = st.session_state.cap.read()
        if not ret:
            st.session_state.cap.release()
            st.session_state.is_running = False
            st.warning("Failed to read frame from camera. Stopping session.")
            break

        current_time = time.time()
        delta_time = current_time - st.session_state.detector.session_data['last_frame_time']
        st.session_state.detector.session_data['last_frame_time'] = current_time
        st.session_state.detector.session_data['frame_count'] += 1

        # Track activity (active app; optional browser tab via extension)
        snap = st.session_state.activity_tracker.tick(now=current_time)
        is_edu = st.session_state.activity_tracker.is_educational(snap)

        # Process frame (focus detection)
        processed_frame, gaze_direction, _ = st.session_state.detector.process_frame(frame, delta_time)

        # Gate focused time + points on educational activity
        if st.session_state.detector.session_data["is_focused"]:
            st.session_state.activity_tracker.add_points_for_focus(
                delta_time_sec=delta_time, educational=is_edu
            )
            if is_edu:
                st.session_state.detector.session_data["total_focused_time"] += delta_time


        # Display video feed (resize to WEBCAM_DISPLAY_* before showing)
        rgb_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
        display_frame = cv2.resize(
            rgb_frame, (WEBCAM_DISPLAY_WIDTH_PX, WEBCAM_DISPLAY_HEIGHT_PX)
        )
        st.session_state.video_placeholder.image(
            display_frame,
            channels="RGB",
            width=WEBCAM_DISPLAY_WIDTH_PX,
            use_container_width=False,
        )

        # Update stats displays
        study_minutes = int(st.session_state.detector.session_data['total_study_time'] // 60)
        study_seconds = int(st.session_state.detector.session_data['total_study_time'] % 60)
        focus_minutes = int(st.session_state.detector.session_data['total_focused_time'] // 60)
        focus_seconds = int(st.session_state.detector.session_data['total_focused_time'] % 60)
        
        # Get placeholders from session state (only update if they exist and session is running)
        if 'stats_placeholders' in st.session_state and st.session_state.is_running:
            ph = st.session_state.stats_placeholders
            
            ph['study_time'].markdown(f"📚 **Study Time:** {study_minutes:02d}:{study_seconds:02d}")
            ph['focus_time'].markdown(f"👀 **Focus Time:** {focus_minutes:02d}:{focus_seconds:02d}", 
                                     help="Total time the student has been focused.")
            
            if st.session_state.detector.session_data['total_study_time'] > 0:
                focus_rate = (st.session_state.detector.session_data['total_focused_time'] / st.session_state.detector.session_data['total_study_time']) * 100
                ph['focus_rate'].markdown(f"📈 **Focus Rate:** {focus_rate:.1f}%")

            study_progress = min(st.session_state.detector.session_data['total_study_time'] / 120.0, 1.0)
            focus_progress = min(st.session_state.detector.session_data['total_focused_time'] / 120.0, 1.0)

            ph['study_progress'].progress(study_progress, text=f"Study: {study_progress*100:.1f}%")
            ph['focus_progress'].progress(focus_progress, text=f"Focus: {focus_progress*100:.1f}%")

            status_text = "🟢 FOCUSED" if st.session_state.detector.session_data['is_focused'] else "🔴 NOT FOCUSED"
            ph['status'].markdown(f"⚪ **Status:** {status_text}")
            ph['tier'].markdown(f"🏆 **Tier:** {st.session_state.detector.session_data['current_tier']}")
            clean_reward = st.session_state.detector.clean_reward_text(st.session_state.detector.session_data['current_reward'])
            ph['reward'].markdown(f"🎁 **Reward:** {clean_reward}")

        # Update activity UI (live)
        render_activity_report_ui(current_time=current_time)

        # Calculate FPS
        fps_counter += 1
        if 'stats_placeholders' in st.session_state and st.session_state.is_running:
            ph = st.session_state.stats_placeholders
            if current_time - fps_start_time >= 1.0:
                fps = fps_counter / (current_time - fps_start_time)
                ph['fps'].markdown(f"⚡ **FPS:** {fps:.1f}")
                fps_counter = 0
                fps_start_time = current_time
            
            # EAR display
            if st.session_state.detector.session_data['avg_ear'] > 0:
                ph['ear'].markdown(f"👁️ **EAR:** {st.session_state.detector.session_data['avg_ear']:.3f}")
            else:
                ph['ear'].markdown(f"👁️ **EAR:** N/A")

        # Session completion check
        if study_minutes >= 2.0 or focus_minutes >= 2.0:
            # Log session & usage once before stopping
            if not st.session_state.session_logged:
                log_session_and_usage(
                    tracker=st.session_state.activity_tracker,
                    detector=st.session_state.detector,
                    session_end_ts=current_time,
                    student_name=st.session_state.student_name,
                    roll_number=st.session_state.roll_number,
                )
                st.session_state.session_logged = True

            stop_session()
            base_summary = st.session_state.detector.get_session_summary()

            # Build brief activity summary
            activity_summary_lines = []
            tracker = st.session_state.activity_tracker
            if tracker.time_by_platform_sec:
                total_time = sum(tracker.time_by_platform_sec.values())
                if total_time > 0:
                    # Estimate most-used platform
                    top_platform, top_secs = max(
                        tracker.time_by_platform_sec.items(), key=lambda kv: kv[1]
                    )
                    activity_summary_lines.append(
                        f"🧭 Most-used platform: {top_platform} ({top_secs:.1f}s)"
                    )
                    # Rough split of educational vs other based on current classification rules
                    edu_time = 0.0
                    for label, secs in tracker.time_by_platform_sec.items():
                        # Treat label as website domain for classification
                        dummy_snap = type(
                            "S",
                            (),
                            {"kind": "website", "label": label, "details": {"domain": label}},
                        )()
                        if tracker.is_educational(dummy_snap):  # type: ignore[arg-type]
                            edu_time += secs
                    activity_summary_lines.append(
                        f"🎯 Time on educational platforms: {edu_time:.1f}s / {total_time:.1f}s"
                    )

            full_summary = base_summary
            if activity_summary_lines:
                full_summary += "\n" + "\n".join(activity_summary_lines)

            # Store summary in session state instead of displaying globally
            st.session_state.session_summary_text = full_summary
            
            # Clear stats placeholders when session ends
            if 'stats_placeholders' in st.session_state:
                for placeholder in st.session_state.stats_placeholders.values():
                    placeholder.empty()
            
            st.rerun()

        time.sleep(0.033) # ~30 FPS

elif st.session_state.stop_clicked:
    # Log session if user stopped manually and we have not logged yet
    if not st.session_state.session_logged:
        log_session_and_usage(
            tracker=st.session_state.activity_tracker,
            detector=st.session_state.detector,
            session_end_ts=time.time(),
            student_name=st.session_state.student_name,
            roll_number=st.session_state.roll_number,
        )
        st.session_state.session_logged = True

    st.session_state.video_placeholder.image(
        np.zeros((WEBCAM_DISPLAY_HEIGHT_PX, WEBCAM_DISPLAY_WIDTH_PX, 3), dtype=np.uint8),
        channels="RGB",
        width=WEBCAM_DISPLAY_WIDTH_PX,
        use_container_width=False,
    )
    st.session_state.video_placeholder.markdown("<h3 style='text-align: center; color: gray;'>Session Stopped.</h3>", unsafe_allow_html=True)
    # Store summary in session state instead of displaying globally
    st.session_state.session_summary_text = st.session_state.detector.get_session_summary()
    
    # Clear stats placeholders when session stops
    if 'stats_placeholders' in st.session_state:
        for placeholder in st.session_state.stats_placeholders.values():
            placeholder.empty()
    
    # Keep showing the last known activity information
    render_activity_report_ui()
else:
    st.session_state.video_placeholder.image(
        np.zeros((WEBCAM_DISPLAY_HEIGHT_PX, WEBCAM_DISPLAY_WIDTH_PX, 3), dtype=np.uint8),
        channels="RGB",
        width=WEBCAM_DISPLAY_WIDTH_PX,
        use_container_width=False,
    )
    st.session_state.video_placeholder.markdown("<h3 style='text-align: center; color: gray;'>Camera feed will appear here. Click 'Start Session' to begin.</h3>", unsafe_allow_html=True)
