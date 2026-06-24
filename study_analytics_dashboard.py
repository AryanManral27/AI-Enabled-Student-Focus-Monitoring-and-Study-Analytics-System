from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple

import streamlit as st

from activity_tracker import ActivityTracker, ActivitySnapshot
from focus_detector_logic import FocusDetectorLogic


LOG_DIR = "."
SESSIONS_LOG = os.path.join(LOG_DIR, "study_sessions_log.csv")
WEBSITES_LOG = os.path.join(LOG_DIR, "website_usage_log.csv")


@dataclass
class DailyReport:
    report_date: date
    total_study_hours: float
    total_focused_hours: float
    max_website: Optional[Tuple[str, float]]  # (label, hours)
    min_website: Optional[Tuple[str, float]]  # (label, hours)
    edu_breakdown: Dict[str, float]  # label -> hours (educational)
    non_edu_breakdown: Dict[str, float]  # label -> hours (non-educational)


@dataclass
class WeeklyReport:
    start_date: date
    end_date: date
    day_most_study: Optional[Tuple[date, float]]  # (date, hours)
    day_least_study: Optional[Tuple[date, float]]  # (date, hours)
    total_study_hours: float
    total_focused_hours: float
    max_website: Optional[Tuple[str, float]]
    min_website: Optional[Tuple[str, float]]
    edu_breakdown: Dict[str, float]
    non_edu_breakdown: Dict[str, float]


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def log_session_and_usage(
    tracker: ActivityTracker,
    detector: FocusDetectorLogic,
    session_end_ts: Optional[float] = None,
    student_name: Optional[str] = None,
    roll_number: Optional[str] = None,
) -> None:
    """Persist one finished session and its website/app usage."""
    if session_end_ts is None:
        session_end_ts = datetime.now().timestamp()

    # Default values if not provided
    student_name = student_name or "Unknown"
    roll_number = roll_number or "Unknown"

    # ---- Session-level summary ----
    sess = detector.session_data
    total_study_sec = float(sess.get("total_study_time", 0.0))
    total_focused_sec = float(sess.get("total_focused_time", 0.0))
    session_start_ts = float(sess.get("session_start_time", session_end_ts))

    end_dt = datetime.fromtimestamp(session_end_ts)
    start_dt = datetime.fromtimestamp(session_start_ts)
    session_date = end_dt.date().isoformat()

    _ensure_parent_dir(SESSIONS_LOG)
    file_exists = os.path.exists(SESSIONS_LOG)
    
    # Check if header needs student_name and roll_number
    needs_header_update = False
    if file_exists:
        with open(SESSIONS_LOG, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames and "student_name" not in reader.fieldnames:
                needs_header_update = True
    
    with open(SESSIONS_LOG, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists or needs_header_update:
            # If file exists but lacks new columns, we need to rewrite it
            if needs_header_update:
                # Read existing data
                with open(SESSIONS_LOG, "r", encoding="utf-8", newline="") as rf:
                    old_reader = csv.DictReader(rf)
                    old_rows = list(old_reader)
                
                # Write new header and data with student info
                f.seek(0)
                f.truncate()
                writer.writerow(
                    [
                        "date",
                        "session_start",
                        "session_end",
                        "total_study_sec",
                        "total_focused_sec",
                        "student_name",
                        "roll_number",
                    ]
                )
                for old_row in old_rows:
                    writer.writerow(
                        [
                            old_row.get("date", ""),
                            old_row.get("session_start", ""),
                            old_row.get("session_end", ""),
                            old_row.get("total_study_sec", "0"),
                            old_row.get("total_focused_sec", "0"),
                            "Unknown",  # Default for old records
                            "Unknown",
                        ]
                    )
            else:
                writer.writerow(
                    [
                        "date",
                        "session_start",
                        "session_end",
                        "total_study_sec",
                        "total_focused_sec",
                        "student_name",
                        "roll_number",
                    ]
                )
        writer.writerow(
            [
                session_date,
                start_dt.isoformat(timespec="seconds"),
                end_dt.isoformat(timespec="seconds"),
                f"{total_study_sec:.1f}",
                f"{total_focused_sec:.1f}",
                student_name,
                roll_number,
            ]
        )

    # ---- Website/app usage breakdown ----
    tb: Dict[str, float] = dict(tracker.time_by_platform_sec)

    # Add live time for current platform if any
    if tracker.current_snapshot:
        label = tracker.current_snapshot.label
        live_sec = tracker.get_live_time_for_current_platform_sec(now=session_end_ts)
        tb[label] = tb.get(label, 0.0) + live_sec

    _ensure_parent_dir(WEBSITES_LOG)
    w_exists = os.path.exists(WEBSITES_LOG)
    
    # Check if header needs student_name and roll_number
    needs_header_update_web = False
    if w_exists:
        with open(WEBSITES_LOG, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames and "student_name" not in reader.fieldnames:
                needs_header_update_web = True
    
    with open(WEBSITES_LOG, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not w_exists or needs_header_update_web:
            if needs_header_update_web:
                # Read existing data
                with open(WEBSITES_LOG, "r", encoding="utf-8", newline="") as rf:
                    old_reader = csv.DictReader(rf)
                    old_rows = list(old_reader)
                
                # Write new header and data with student info
                f.seek(0)
                f.truncate()
                writer.writerow(
                    [
                        "date",
                        "label",
                        "kind",
                        "seconds",
                        "is_educational",
                        "student_name",
                        "roll_number",
                    ]
                )
                for old_row in old_rows:
                    writer.writerow(
                        [
                            old_row.get("date", ""),
                            old_row.get("label", ""),
                            old_row.get("kind", "website"),
                            old_row.get("seconds", "0"),
                            old_row.get("is_educational", "0"),
                            "Unknown",  # Default for old records
                            "Unknown",
                        ]
                    )
            else:
                writer.writerow(
                    [
                        "date",
                        "label",
                        "kind",
                        "seconds",
                        "is_educational",
                        "student_name",
                        "roll_number",
                    ]
                )

        for label, secs in tb.items():
            if secs <= 0:
                continue

            # Construct a minimal snapshot so we can reuse existing classification logic
            snap = ActivitySnapshot(kind="website", label=label, details={"domain": label})
            is_edu = tracker.is_educational(snap)
            writer.writerow(
                [
                    session_date,
                    label,
                    "website",
                    f"{secs:.1f}",
                    "1" if is_edu else "0",
                    student_name,
                    roll_number,
                ]
            )


def _load_session_rows() -> List[Dict[str, str]]:
    if not os.path.exists(SESSIONS_LOG):
        return []
    rows: List[Dict[str, str]] = []
    with open(SESSIONS_LOG, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def _load_website_rows() -> List[Dict[str, str]]:
    if not os.path.exists(WEBSITES_LOG):
        return []
    rows: List[Dict[str, str]] = []
    with open(WEBSITES_LOG, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def build_daily_report(target_date: date) -> Optional[DailyReport]:
    sessions = _load_session_rows()
    websites = _load_website_rows()
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

    # Website usage for the day
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

        is_edu = (w.get("is_educational") == "1")
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


def build_weekly_report(end_date: date, days: int = 5) -> Optional[WeeklyReport]:
    sessions = _load_session_rows()
    websites = _load_website_rows()

    start_date = end_date - timedelta(days=days - 1)

    # Study time per day
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

    # Website usage in the window
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
        is_edu = (w.get("is_educational") == "1")
        if is_edu:
            edu_breakdown[label] = edu_breakdown.get(label, 0.0) + secs
        else:
            non_edu_breakdown[label] = non_edu_breakdown.get(label, 0.0) + secs

    total_study_sec = sum(per_day_study.values())
    total_focused_sec = sum(per_day_focus.values())

    # Only consider days that actually have study time when finding max/min
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


def render_daily_report_ui(target_date: date) -> None:
    report = build_daily_report(target_date)
    if not report:
        st.info("No data available for the selected date yet.")
        return

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
                    for label, hrs in sorted(report.edu_breakdown.items(), key=lambda kv: kv[1], reverse=True)
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
                    for label, hrs in sorted(report.non_edu_breakdown.items(), key=lambda kv: kv[1], reverse=True)
                ]
            )
        else:
            st.info("No non-educational website usage recorded for this day.")


def render_weekly_report_ui(end_date: date, days: int = 5) -> None:
    report = build_weekly_report(end_date, days=days)
    if not report:
        st.info("No data available yet for the selected 5‑day window.")
        return

    st.markdown(
        f"### 📆 Weekly Report (Last {days} Days)\n"
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
                    for label, hrs in sorted(report.edu_breakdown.items(), key=lambda kv: kv[1], reverse=True)
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
                    for label, hrs in sorted(report.non_edu_breakdown.items(), key=lambda kv: kv[1], reverse=True)
                ]
            )
        else:
            st.info("No non-educational website usage recorded in this window.")


def render_analytics_tab() -> None:
    """Main entry point for the Study Analytics & Performance Report Dashboard."""
    st.subheader("📈 Study Analytics & Performance Report Dashboard")

    mode = st.radio(
        "Select Report Type:",
        options=["Daily Report", "Weekly Report (5 Days)"],
        horizontal=True,
    )

    today = datetime.now().date()

    if mode == "Daily Report":
        selected_date = st.date_input("Select date", value=today, max_value=today)
        render_daily_report_ui(selected_date)
    else:
        end_date = st.date_input(
            "Select end date for the 5‑day window", value=today, max_value=today
        )
        render_weekly_report_ui(end_date, days=5)

