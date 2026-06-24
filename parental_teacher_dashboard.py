from __future__ import annotations

import csv
import os
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from io import BytesIO

import streamlit as st

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    # Dummy values to prevent errors
    letter = None
    getSampleStyleSheet = None
    ParagraphStyle = None
    inch = None
    SimpleDocTemplate = None
    Paragraph = None
    Spacer = None
    Table = None
    TableStyle = None
    PageBreak = None
    colors = None

from study_analytics_dashboard import (
    build_daily_report,
    build_weekly_report,
    DailyReport,
    WeeklyReport,
    SESSIONS_LOG,
    WEBSITES_LOG,
)


def _load_session_rows() -> List[Dict[str, str]]:
    """Load all session rows from CSV."""
    if not os.path.exists(SESSIONS_LOG):
        return []
    rows: List[Dict[str, str]] = []
    with open(SESSIONS_LOG, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def _load_website_rows() -> List[Dict[str, str]]:
    """Load all website usage rows from CSV."""
    if not os.path.exists(WEBSITES_LOG):
        return []
    rows: List[Dict[str, str]] = []
    with open(WEBSITES_LOG, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def get_student_activity_report(
    student_name: str, roll_number: str
) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """
    Get activity report for a specific student.
    Returns: (sessions, website_usage) filtered by student_name and roll_number.
    """
    sessions = _load_session_rows()
    websites = _load_website_rows()

    # Filter by student_name and roll_number
    student_sessions = [
        s
        for s in sessions
        if s.get("student_name", "").strip().lower() == student_name.strip().lower()
        and s.get("roll_number", "").strip() == roll_number.strip()
    ]

    # Get dates from student sessions
    student_dates = {s.get("date", "") for s in student_sessions}

    # Filter website usage for those dates
    student_websites = [
        w
        for w in websites
        if w.get("date", "") in student_dates
        and w.get("student_name", "").strip().lower() == student_name.strip().lower()
        and w.get("roll_number", "").strip() == roll_number.strip()
    ]

    return student_sessions, student_websites


def build_student_daily_report(
    student_name: str, roll_number: str, target_date: date
) -> Optional[DailyReport]:
    """Build daily report for a specific student."""
    sessions, websites = get_student_activity_report(student_name, roll_number)
    target_str = target_date.isoformat()

    total_study_sec = 0.0
    total_focused_sec = 0.0
    for s in sessions:
        if s.get("date") == target_str:
            try:
                total_study_sec += float(s.get("total_study_sec", "0") or 0)
                total_focused_sec += float(s.get("total_focused_sec", "0") or 0)
            except ValueError:
                continue

    usage: Dict[str, float] = {}
    edu_breakdown: Dict[str, float] = {}
    non_edu_breakdown: Dict[str, float] = {}

    for w in websites:
        if w.get("date") != target_str:
            continue
        label = w.get("label") or "Unknown"
        try:
            secs = float(w.get("seconds", "0") or 0)
        except ValueError:
            continue
        usage[label] = usage.get(label, 0.0) + secs

        is_edu = w.get("is_educational") == "1"
        if is_edu:
            edu_breakdown[label] = edu_breakdown.get(label, 0.0) + secs
        else:
            non_edu_breakdown[label] = non_edu_breakdown.get(label, 0.0) + secs

    if not (total_study_sec or usage):
        return None

    max_site = max(usage.items(), key=lambda kv: kv[1]) if usage else None
    min_site = min(usage.items(), key=lambda kv: kv[1]) if usage else None

    return DailyReport(
        report_date=target_date,
        total_study_hours=total_study_sec / 3600.0,
        total_focused_hours=total_focused_sec / 3600.0,
        max_website=(max_site[0], max_site[1] / 3600.0) if max_site else None,
        min_website=(min_site[0], min_site[1] / 3600.0) if min_site else None,
        edu_breakdown={k: v / 3600.0 for k, v in edu_breakdown.items()},
        non_edu_breakdown={k: v / 3600.0 for k, v in non_edu_breakdown.items()},
    )


def build_student_weekly_report(
    student_name: str, roll_number: str, end_date: date, days: int = 5
) -> Optional[WeeklyReport]:
    """Build weekly report for a specific student."""
    sessions, websites = get_student_activity_report(student_name, roll_number)

    start_date = end_date - timedelta(days=days - 1)

    per_day_study: Dict[date, float] = {}
    per_day_focus: Dict[date, float] = {}

    for s in sessions:
        try:
            d = datetime.fromisoformat(s.get("date", "")).date()
        except Exception:
            continue
        if not (start_date <= d <= end_date):
            continue
        try:
            study_sec = float(s.get("total_study_sec", "0") or 0)
            focus_sec = float(s.get("total_focused_sec", "0") or 0)
        except ValueError:
            continue
        per_day_study[d] = per_day_study.get(d, 0.0) + study_sec
        per_day_focus[d] = per_day_focus.get(d, 0.0) + focus_sec

    if not per_day_study:
        return None

    usage: Dict[str, float] = {}
    edu_breakdown: Dict[str, float] = {}
    non_edu_breakdown: Dict[str, float] = {}

    for w in websites:
        try:
            d = datetime.fromisoformat(w.get("date", "")).date()
        except Exception:
            continue
        if not (start_date <= d <= end_date):
            continue
        label = w.get("label") or "Unknown"
        try:
            secs = float(w.get("seconds", "0") or 0)
        except ValueError:
            continue
        usage[label] = usage.get(label, 0.0) + secs
        is_edu = w.get("is_educational") == "1"
        if is_edu:
            edu_breakdown[label] = edu_breakdown.get(label, 0.0) + secs
        else:
            non_edu_breakdown[label] = non_edu_breakdown.get(label, 0.0) + secs

    total_study_sec = sum(per_day_study.values())
    total_focused_sec = sum(per_day_focus.values())

    non_zero_days = {d: s for d, s in per_day_study.items() if s > 0}
    if non_zero_days:
        most_day = max(non_zero_days.items(), key=lambda kv: kv[1])
        least_day = min(non_zero_days.items(), key=lambda kv: kv[1])
    else:
        most_day = least_day = None

    max_site = max(usage.items(), key=lambda kv: kv[1]) if usage else None
    min_site = min(usage.items(), key=lambda kv: kv[1]) if usage else None

    return WeeklyReport(
        start_date=start_date,
        end_date=end_date,
        day_most_study=(most_day[0], most_day[1] / 3600.0) if most_day else None,
        day_least_study=(least_day[0], least_day[1] / 3600.0) if least_day else None,
        total_study_hours=total_study_sec / 3600.0,
        total_focused_hours=total_focused_sec / 3600.0,
        max_website=(max_site[0], max_site[1] / 3600.0) if max_site else None,
        min_website=(min_site[0], min_site[1] / 3600.0) if min_site else None,
        edu_breakdown={k: v / 3600.0 for k, v in edu_breakdown.items()},
        non_edu_breakdown={k: v / 3600.0 for k, v in non_edu_breakdown.items()},
    )


def generate_pdf_report(
    report_type: str,
    student_name: str,
    roll_number: str,
    report: DailyReport | WeeklyReport,
    role: str,
    role_name: str,
) -> bytes:
    """Generate PDF report for download."""
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
    title_text = f"{report_type} - Student Study Analytics"
    story.append(Paragraph(title_text, title_style))
    story.append(Spacer(1, 0.2 * inch))

    # Student Info
    story.append(Paragraph(f"<b>Student Name:</b> {student_name}", styles["Normal"]))
    story.append(Paragraph(f"<b>Roll Number:</b> {roll_number}", styles["Normal"]))
    story.append(Paragraph(f"<b>Viewer Role:</b> {role} ({role_name})", styles["Normal"]))
    story.append(Paragraph(f"<b>Report Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]))
    story.append(Spacer(1, 0.3 * inch))

    if isinstance(report, DailyReport):
        story.append(Paragraph(f"<b>Report Date:</b> {report.report_date.isoformat()}", styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))

        # Summary Metrics
        story.append(Paragraph("Summary Metrics", heading_style))
        data = [
            ["Metric", "Value"],
            ["Total Study Hours", f"{report.total_study_hours:.2f}"],
            ["Total Focused Hours", f"{report.total_focused_hours:.2f}"],
            [
                "Focus Rate",
                f"{(report.total_focused_hours / report.total_study_hours * 100) if report.total_study_hours > 0 else 0:.1f}%",
            ],
        ]
        if report.max_website:
            data.append(["Max Time Website", f"{report.max_website[0]} ({report.max_website[1]:.2f} hrs)"])
        if report.min_website:
            data.append(["Min Time Website", f"{report.min_website[0]} ({report.min_website[1]:.2f} hrs)"])

        table = Table(data)
        table.setStyle(
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
        story.append(table)
        story.append(Spacer(1, 0.3 * inch))

        # Educational Websites
        if report.edu_breakdown:
            story.append(Paragraph("Educational Websites", heading_style))
            edu_data = [["Website", "Hours"]]
            for label, hrs in sorted(report.edu_breakdown.items(), key=lambda kv: kv[1], reverse=True):
                edu_data.append([label, f"{hrs:.2f}"])
            edu_table = Table(edu_data)
            edu_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.green),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )
            story.append(edu_table)
            story.append(Spacer(1, 0.2 * inch))

        # Non-educational Websites
        if report.non_edu_breakdown:
            story.append(Paragraph("Non-educational Websites", heading_style))
            non_edu_data = [["Website", "Hours"]]
            for label, hrs in sorted(report.non_edu_breakdown.items(), key=lambda kv: kv[1], reverse=True):
                non_edu_data.append([label, f"{hrs:.2f}"])
            non_edu_table = Table(non_edu_data)
            non_edu_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.red),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )
            story.append(non_edu_table)

    elif isinstance(report, WeeklyReport):
        story.append(
            Paragraph(
                f"<b>Report Period:</b> {report.start_date.isoformat()} to {report.end_date.isoformat()}",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 0.2 * inch))

        # Summary Metrics
        story.append(Paragraph("Summary Metrics", heading_style))
        data = [
            ["Metric", "Value"],
            ["Total Study Hours", f"{report.total_study_hours:.2f}"],
            ["Total Focused Hours", f"{report.total_focused_hours:.2f}"],
            [
                "Focus Rate",
                f"{(report.total_focused_hours / report.total_study_hours * 100) if report.total_study_hours > 0 else 0:.1f}%",
            ],
        ]
        if report.day_most_study:
            data.append(
                [
                    "Day with Most Study",
                    f"{report.day_most_study[0].isoformat()} ({report.day_most_study[1]:.2f} hrs)",
                ]
            )
        if report.day_least_study:
            data.append(
                [
                    "Day with Least Study",
                    f"{report.day_least_study[0].isoformat()} ({report.day_least_study[1]:.2f} hrs)",
                ]
            )
        if report.max_website:
            data.append(["Max Time Website", f"{report.max_website[0]} ({report.max_website[1]:.2f} hrs)"])
        if report.min_website:
            data.append(["Min Time Website", f"{report.min_website[0]} ({report.min_website[1]:.2f} hrs)"])

        table = Table(data)
        table.setStyle(
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
        story.append(table)
        story.append(Spacer(1, 0.3 * inch))

        # Educational Websites
        if report.edu_breakdown:
            story.append(Paragraph("Educational Websites (5-Day Total)", heading_style))
            edu_data = [["Website", "Hours"]]
            for label, hrs in sorted(report.edu_breakdown.items(), key=lambda kv: kv[1], reverse=True):
                edu_data.append([label, f"{hrs:.2f}"])
            edu_table = Table(edu_data)
            edu_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.green),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )
            story.append(edu_table)
            story.append(Spacer(1, 0.2 * inch))

        # Non-educational Websites
        if report.non_edu_breakdown:
            story.append(Paragraph("Non-educational Websites (5-Day Total)", heading_style))
            non_edu_data = [["Website", "Hours"]]
            for label, hrs in sorted(report.non_edu_breakdown.items(), key=lambda kv: kv[1], reverse=True):
                non_edu_data.append([label, f"{hrs:.2f}"])
            non_edu_table = Table(non_edu_data)
            non_edu_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.red),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )
            story.append(non_edu_table)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def render_parent_dashboard():
    """Render Parent Dashboard UI."""
    st.subheader("👨‍👩‍👧 Parent Dashboard")
    st.markdown("---")

    with st.form("parent_login_form"):
        st.markdown("### Parent Information")
        parent_name = st.text_input("Parent Name *", placeholder="Enter your name")
        parent_phone = st.text_input("Parent Phone Number *", placeholder="Enter your phone number")

        st.markdown("### Student Information")
        student_name = st.text_input("Student Name *", placeholder="Enter student name")
        roll_number = st.text_input("Student Roll Number *", placeholder="Enter roll number")

        submitted = st.form_submit_button("🔍 View Reports", type="primary")

        if submitted:
            if not all([parent_name, parent_phone, student_name, roll_number]):
                st.error("Please fill in all required fields.")
            else:
                st.session_state.parent_authenticated = True
                st.session_state.parent_name = parent_name
                st.session_state.parent_phone = parent_phone
                st.session_state.viewing_student_name = student_name
                st.session_state.viewing_roll_number = roll_number
                st.rerun()

    if st.session_state.get("parent_authenticated", False):
        student_name = st.session_state.viewing_student_name
        roll_number = st.session_state.viewing_roll_number
        parent_name = st.session_state.parent_name

        st.success(f"✅ Authenticated as Parent: {parent_name}")
        st.markdown(f"**Viewing reports for:** {student_name} (Roll: {roll_number})")
        st.markdown("---")

        # Report Type Selection
        report_type = st.radio(
            "Select Report Type:",
            options=["Daily Report", "Weekly Report (5 Days)"],
            horizontal=True,
            key="parent_report_type_radio",
        )

        today = datetime.now().date()

        if report_type == "Daily Report":
            selected_date = st.date_input("Select date", value=today, max_value=today, key="parent_daily_date_input")
            report = build_student_daily_report(student_name, roll_number, selected_date)

            if report:
                st.markdown(f"### 📅 Daily Report — {report.report_date.isoformat()}")

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Study Hours", f"{report.total_study_hours:.2f}")
                with col2:
                    st.metric("Total Focused Hours", f"{report.total_focused_hours:.2f}")
                with col3:
                    focus_rate = (
                        (report.total_focused_hours / report.total_study_hours * 100)
                        if report.total_study_hours > 0
                        else 0.0
                    )
                    st.metric("Focus Rate", f"{focus_rate:.1f}%")

                st.markdown("---")
                col4, col5 = st.columns(2)
                with col4:
                    st.markdown("#### 🌐 Websites (Daily Extremes)")
                    if report.max_website:
                        st.write(f"**Max Time:** {report.max_website[0]} — {report.max_website[1]:.2f} hrs")
                    if report.min_website:
                        st.write(f"**Min Time:** {report.min_website[0]} — {report.min_website[1]:.2f} hrs")
                with col5:
                    st.markdown("#### 🎯 Category Breakdown (Hours)")
                    edu_total = sum(report.edu_breakdown.values())
                    non_edu_total = sum(report.non_edu_breakdown.values())
                    st.write(f"**Educational Total:** {edu_total:.2f} hrs")
                    st.write(f"**Non-educational Total:** {non_edu_total:.2f} hrs")

                st.markdown("---")
                col6, col7 = st.columns(2)
                with col6:
                    st.markdown("#### 📘 Educational Websites")
                    if report.edu_breakdown:
                        st.table(
                            [
                                {"Website": label, "Hours": f"{hrs:.2f}"}
                                for label, hrs in sorted(
                                    report.edu_breakdown.items(), key=lambda kv: kv[1], reverse=True
                                )
                            ]
                        )
                    else:
                        st.info("No educational website usage recorded for this day.")
                with col7:
                    st.markdown("#### 📕 Non-educational Websites")
                    if report.non_edu_breakdown:
                        st.table(
                            [
                                {"Website": label, "Hours": f"{hrs:.2f}"}
                                for label, hrs in sorted(
                                    report.non_edu_breakdown.items(), key=lambda kv: kv[1], reverse=True
                                )
                            ]
                        )
                    else:
                        st.info("No non-educational website usage recorded for this day.")

                # PDF Download
                try:
                    pdf_bytes = generate_pdf_report(
                        "Daily Report",
                        student_name,
                        roll_number,
                        report,
                        "Parent",
                        parent_name,
                    )
                    st.download_button(
                        "📥 Download Daily Report (PDF)",
                        data=pdf_bytes,
                        file_name=f"daily_report_{student_name}_{roll_number}_{selected_date.isoformat()}.pdf",
                        mime="application/pdf",
                    )
                except ImportError as e:
                    st.warning(f"⚠️ PDF download unavailable: {e}")
                except Exception as e:
                    st.error(f"❌ Error generating PDF: {e}")
            else:
                st.info("No data available for the selected date yet.")

        else:  # Weekly Report
            end_date = st.date_input("Select end date for the 5‑day window", value=today, max_value=today, key="parent_weekly_date_input")
            report = build_student_weekly_report(student_name, roll_number, end_date, days=5)

            if report:
                st.markdown(
                    f"### 📆 Weekly Report (Last 5 Days)\n"
                    f"**From:** {report.start_date.isoformat()} **To:** {report.end_date.isoformat()}"
                )

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Study Hours", f"{report.total_study_hours:.2f}")
                with col2:
                    st.metric("Total Focused Hours", f"{report.total_focused_hours:.2f}")
                with col3:
                    focus_rate = (
                        (report.total_focused_hours / report.total_study_hours * 100)
                        if report.total_study_hours > 0
                        else 0.0
                    )
                    st.metric("Focus Rate", f"{focus_rate:.1f}%")

                st.markdown("---")
                col4, col5 = st.columns(2)
                with col4:
                    st.markdown("#### 🗓 Days with Most / Least Study")
                    if report.day_most_study:
                        st.write(
                            f"**Most Study:** {report.day_most_study[0].isoformat()} — {report.day_most_study[1]:.2f} hrs"
                        )
                    if report.day_least_study:
                        st.write(
                            f"**Least Study:** {report.day_least_study[0].isoformat()} — {report.day_least_study[1]:.2f} hrs"
                        )
                with col5:
                    st.markdown("#### 🌐 Websites (Weekly Extremes)")
                    if report.max_website:
                        st.write(f"**Max Time:** {report.max_website[0]} — {report.max_website[1]:.2f} hrs")
                    if report.min_website:
                        st.write(f"**Min Time:** {report.min_website[0]} — {report.min_website[1]:.2f} hrs")

                st.markdown("---")
                col6, col7 = st.columns(2)
                with col6:
                    st.markdown("#### 📘 Educational Websites (5‑Day Total)")
                    if report.edu_breakdown:
                        st.table(
                            [
                                {"Website": label, "Hours": f"{hrs:.2f}"}
                                for label, hrs in sorted(
                                    report.edu_breakdown.items(), key=lambda kv: kv[1], reverse=True
                                )
                            ]
                        )
                    else:
                        st.info("No educational website usage recorded in this window.")
                with col7:
                    st.markdown("#### 📕 Non-educational Websites (5‑Day Total)")
                    if report.non_edu_breakdown:
                        st.table(
                            [
                                {"Website": label, "Hours": f"{hrs:.2f}"}
                                for label, hrs in sorted(
                                    report.non_edu_breakdown.items(), key=lambda kv: kv[1], reverse=True
                                )
                            ]
                        )
                    else:
                        st.info("No non-educational website usage recorded in this window.")

                # PDF Download
                try:
                    pdf_bytes = generate_pdf_report(
                        "Weekly Report (5 Days)",
                        student_name,
                        roll_number,
                        report,
                        "Parent",
                        parent_name,
                    )
                    st.download_button(
                        "📥 Download Weekly Report (PDF)",
                        data=pdf_bytes,
                        file_name=f"weekly_report_{student_name}_{roll_number}_{end_date.isoformat()}.pdf",
                        mime="application/pdf",
                    )
                except ImportError as e:
                    st.warning(f"⚠️ PDF download unavailable: {e}")
                except Exception as e:
                    st.error(f"❌ Error generating PDF: {e}")
            else:
                st.info("No data available yet for the selected 5‑day window.")

        st.markdown("---")
        if st.button("🚪 Logout", key="parent_logout_button"):
            for key in ["parent_authenticated", "parent_name", "parent_phone", "viewing_student_name", "viewing_roll_number"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()


def render_teacher_dashboard():
    """Render Teacher Dashboard UI."""
    st.subheader("👨‍🏫 Teacher Dashboard")
    st.markdown("---")

    with st.form("teacher_login_form"):
        st.markdown("### Teacher Information")
        teacher_name = st.text_input("Teacher Name *", placeholder="Enter your name")
        teacher_subject = st.text_input("Subject *", placeholder="Enter subject name")
        teacher_id = st.text_input("Teacher ID *", placeholder="Enter your teacher ID")

        st.markdown("### Student Information")
        student_name = st.text_input("Student Name *", placeholder="Enter student name")
        roll_number = st.text_input("Student Roll Number *", placeholder="Enter roll number")

        submitted = st.form_submit_button("🔍 View Reports", type="primary")

        if submitted:
            if not all([teacher_name, teacher_subject, teacher_id, student_name, roll_number]):
                st.error("Please fill in all required fields.")
            else:
                st.session_state.teacher_authenticated = True
                st.session_state.teacher_name = teacher_name
                st.session_state.teacher_subject = teacher_subject
                st.session_state.teacher_id = teacher_id
                st.session_state.viewing_student_name = student_name
                st.session_state.viewing_roll_number = roll_number
                st.rerun()

    if st.session_state.get("teacher_authenticated", False):
        student_name = st.session_state.viewing_student_name
        roll_number = st.session_state.viewing_roll_number
        teacher_name = st.session_state.teacher_name
        teacher_subject = st.session_state.teacher_subject

        st.success(f"✅ Authenticated as Teacher: {teacher_name} ({teacher_subject})")
        st.markdown(f"**Viewing reports for:** {student_name} (Roll: {roll_number})")
        st.markdown("---")

        # Report Type Selection
        report_type = st.radio(
            "Select Report Type:",
            options=["Daily Report", "Weekly Report (5 Days)"],
            horizontal=True,
            key="teacher_report_type_radio",
        )

        today = datetime.now().date()

        if report_type == "Daily Report":
            selected_date = st.date_input("Select date", value=today, max_value=today, key="teacher_daily_date_input")
            report = build_student_daily_report(student_name, roll_number, selected_date)

            if report:
                st.markdown(f"### 📅 Daily Report — {report.report_date.isoformat()}")

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Study Hours", f"{report.total_study_hours:.2f}")
                with col2:
                    st.metric("Total Focused Hours", f"{report.total_focused_hours:.2f}")
                with col3:
                    focus_rate = (
                        (report.total_focused_hours / report.total_study_hours * 100)
                        if report.total_study_hours > 0
                        else 0.0
                    )
                    st.metric("Focus Rate", f"{focus_rate:.1f}%")

                st.markdown("---")
                col4, col5 = st.columns(2)
                with col4:
                    st.markdown("#### 🌐 Websites (Daily Extremes)")
                    if report.max_website:
                        st.write(f"**Max Time:** {report.max_website[0]} — {report.max_website[1]:.2f} hrs")
                    if report.min_website:
                        st.write(f"**Min Time:** {report.min_website[0]} — {report.min_website[1]:.2f} hrs")
                with col5:
                    st.markdown("#### 🎯 Category Breakdown (Hours)")
                    edu_total = sum(report.edu_breakdown.values())
                    non_edu_total = sum(report.non_edu_breakdown.values())
                    st.write(f"**Educational Total:** {edu_total:.2f} hrs")
                    st.write(f"**Non-educational Total:** {non_edu_total:.2f} hrs")

                st.markdown("---")
                col6, col7 = st.columns(2)
                with col6:
                    st.markdown("#### 📘 Educational Websites")
                    if report.edu_breakdown:
                        st.table(
                            [
                                {"Website": label, "Hours": f"{hrs:.2f}"}
                                for label, hrs in sorted(
                                    report.edu_breakdown.items(), key=lambda kv: kv[1], reverse=True
                                )
                            ]
                        )
                    else:
                        st.info("No educational website usage recorded for this day.")
                with col7:
                    st.markdown("#### 📕 Non-educational Websites")
                    if report.non_edu_breakdown:
                        st.table(
                            [
                                {"Website": label, "Hours": f"{hrs:.2f}"}
                                for label, hrs in sorted(
                                    report.non_edu_breakdown.items(), key=lambda kv: kv[1], reverse=True
                                )
                            ]
                        )
                    else:
                        st.info("No non-educational website usage recorded for this day.")

                # PDF Download
                try:
                    pdf_bytes = generate_pdf_report(
                        "Daily Report",
                        student_name,
                        roll_number,
                        report,
                        "Teacher",
                        f"{teacher_name} ({teacher_subject})",
                    )
                    st.download_button(
                        "📥 Download Daily Report (PDF)",
                        data=pdf_bytes,
                        file_name=f"daily_report_{student_name}_{roll_number}_{selected_date.isoformat()}.pdf",
                        mime="application/pdf",
                    )
                except ImportError as e:
                    st.warning(f"⚠️ PDF download unavailable: {e}")
                except Exception as e:
                    st.error(f"❌ Error generating PDF: {e}")
            else:
                st.info("No data available for the selected date yet.")

        else:  # Weekly Report
            end_date = st.date_input("Select end date for the 5‑day window", value=today, max_value=today, key="teacher_weekly_date_input")
            report = build_student_weekly_report(student_name, roll_number, end_date, days=5)

            if report:
                st.markdown(
                    f"### 📆 Weekly Report (Last 5 Days)\n"
                    f"**From:** {report.start_date.isoformat()} **To:** {report.end_date.isoformat()}"
                )

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Study Hours", f"{report.total_study_hours:.2f}")
                with col2:
                    st.metric("Total Focused Hours", f"{report.total_focused_hours:.2f}")
                with col3:
                    focus_rate = (
                        (report.total_focused_hours / report.total_study_hours * 100)
                        if report.total_study_hours > 0
                        else 0.0
                    )
                    st.metric("Focus Rate", f"{focus_rate:.1f}%")

                st.markdown("---")
                col4, col5 = st.columns(2)
                with col4:
                    st.markdown("#### 🗓 Days with Most / Least Study")
                    if report.day_most_study:
                        st.write(
                            f"**Most Study:** {report.day_most_study[0].isoformat()} — {report.day_most_study[1]:.2f} hrs"
                        )
                    if report.day_least_study:
                        st.write(
                            f"**Least Study:** {report.day_least_study[0].isoformat()} — {report.day_least_study[1]:.2f} hrs"
                        )
                with col5:
                    st.markdown("#### 🌐 Websites (Weekly Extremes)")
                    if report.max_website:
                        st.write(f"**Max Time:** {report.max_website[0]} — {report.max_website[1]:.2f} hrs")
                    if report.min_website:
                        st.write(f"**Min Time:** {report.min_website[0]} — {report.min_website[1]:.2f} hrs")

                st.markdown("---")
                col6, col7 = st.columns(2)
                with col6:
                    st.markdown("#### 📘 Educational Websites (5‑Day Total)")
                    if report.edu_breakdown:
                        st.table(
                            [
                                {"Website": label, "Hours": f"{hrs:.2f}"}
                                for label, hrs in sorted(
                                    report.edu_breakdown.items(), key=lambda kv: kv[1], reverse=True
                                )
                            ]
                        )
                    else:
                        st.info("No educational website usage recorded in this window.")
                with col7:
                    st.markdown("#### 📕 Non-educational Websites (5‑Day Total)")
                    if report.non_edu_breakdown:
                        st.table(
                            [
                                {"Website": label, "Hours": f"{hrs:.2f}"}
                                for label, hrs in sorted(
                                    report.non_edu_breakdown.items(), key=lambda kv: kv[1], reverse=True
                                )
                            ]
                        )
                    else:
                        st.info("No non-educational website usage recorded in this window.")

                # PDF Download
                try:
                    pdf_bytes = generate_pdf_report(
                        "Weekly Report (5 Days)",
                        student_name,
                        roll_number,
                        report,
                        "Teacher",
                        f"{teacher_name} ({teacher_subject})",
                    )
                    st.download_button(
                        "📥 Download Weekly Report (PDF)",
                        data=pdf_bytes,
                        file_name=f"weekly_report_{student_name}_{roll_number}_{end_date.isoformat()}.pdf",
                        mime="application/pdf",
                    )
                except ImportError as e:
                    st.warning(f"⚠️ PDF download unavailable: {e}")
                except Exception as e:
                    st.error(f"❌ Error generating PDF: {e}")
            else:
                st.info("No data available yet for the selected 5‑day window.")

        st.markdown("---")
        if st.button("🚪 Logout", key="teacher_logout_button"):
            for key in [
                "teacher_authenticated",
                "teacher_name",
                "teacher_subject",
                "teacher_id",
                "viewing_student_name",
                "viewing_roll_number",
            ]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()


def render_dashboard_tab():
    """Main entry point for Parental and Teacher Dashboard."""
    st.subheader("👨‍👩‍👧👨‍🏫 Parental & Teacher Dashboard")

    role = st.radio(
        "Select Your Role:",
        options=["Parent", "Teacher"],
        horizontal=True,
        key="dashboard_role_radio",
    )

    st.markdown("---")

    if role == "Parent":
        render_parent_dashboard()
    else:
        render_teacher_dashboard()
