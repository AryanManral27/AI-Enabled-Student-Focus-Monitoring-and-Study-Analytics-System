from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, List, Optional, Tuple


@dataclass
class ActivitySnapshot:
    kind: str  # "app" | "website" | "unknown"
    label: str  # app name or domain/title
    details: Dict[str, str]


def _safe_lower(s: Optional[str]) -> str:
    return (s or "").strip().lower()


def _extract_domain(url: str) -> str:
    # very small/robust domain extraction without extra deps
    u = url.strip()
    if "://" in u:
        u = u.split("://", 1)[1]
    u = u.split("/", 1)[0]
    u = u.split("?", 1)[0]
    u = u.split("#", 1)[0]
    if ":" in u:
        u = u.split(":", 1)[0]
    return u.lower()


class ActivityTracker:
    """
    Tracks current activity from:
    - Windows active window (polling)
    - Optional browser-extension POST events (local HTTP server)
    """

    def __init__(
        self,
        *,
        poll_interval_sec: float = 1.0,
        server_host: str = "127.0.0.1",
        server_port: int = 8765,
    ):
        self.poll_interval_sec = poll_interval_sec
        self.server_host = server_host
        self.server_port = server_port

        # classification lists (editable from Streamlit if you want later)
        self.educational_domains = {
            "coursera.org",
            "www.coursera.org",
            "geeksforgeeks.org",
            "www.geeksforgeeks.org",
            "khanacademy.org",
            "www.khanacademy.org",
            "leetcode.com",
            "www.leetcode.com",
            "stackoverflow.com",
            "www.stackoverflow.com",
            "wikipedia.org",
            "www.wikipedia.org",
        }
        self.distraction_domains = {
            "youtube.com",
            "www.youtube.com",
            "facebook.com",
            "www.facebook.com",
            "instagram.com",
            "www.instagram.com",
            "tiktok.com",
            "www.tiktok.com",
        }
        self.educational_apps = {
            "code.exe",  # VS Code
            "pycharm64.exe",
            "notepad++.exe",
            "winword.exe",
            "powerpnt.exe",
            "acrord32.exe",
            "acrobat.exe",
        }

        self._lock = threading.Lock()
        self._running = False

        self._last_snapshot: Optional[ActivitySnapshot] = None
        self._last_change_ts: float = time.time()
        self._last_poll_ts: float = 0.0
        self._current_platform_start_ts: float = self._last_change_ts

        self.time_by_platform_sec: Dict[str, float] = {}
        self.switch_events: List[Dict[str, str]] = []
        self.current_snapshot: ActivitySnapshot = ActivitySnapshot("unknown", "Unknown", {})
        self.current_is_educational: bool = False

        # Points model (simple + adjustable)
        self.points: float = 0.0
        self.last_warning: Optional[str] = None

        # browser events (set by HTTP server)
        self._latest_browser: Optional[Dict[str, str]] = None

        self._httpd: Optional[ThreadingHTTPServer] = None
        self._server_thread: Optional[threading.Thread] = None

    # -------------------------
    # Public API
    # -------------------------
    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._last_change_ts = time.time()

        # Start local HTTP server for browser extension (optional)
        self._start_server()

    def stop(self) -> None:
        with self._lock:
            self._running = False
        self._stop_server()

    def reset(self) -> None:
        with self._lock:
            self._last_snapshot = None
            self._last_change_ts = time.time()
            self._last_poll_ts = 0.0
            self.time_by_platform_sec = {}
            self.switch_events = []
            self.current_snapshot = ActivitySnapshot("unknown", "Unknown", {})
            self.current_is_educational = False
            self.points = 0.0
            self.last_warning = None
            self._latest_browser = None
            self._current_platform_start_ts = time.time()

    def get_live_time_for_current_platform_sec(self, *, now: Optional[float] = None) -> float:
        now = now or time.time()
        with self._lock:
            return max(0.0, now - self._current_platform_start_ts)

    def tick(self, *, now: Optional[float] = None) -> ActivitySnapshot:
        """Call this periodically (e.g. once per video frame loop)."""
        now = now or time.time()
        with self._lock:
            if not self._running:
                return self.current_snapshot

        # Poll at interval
        if now - self._last_poll_ts < self.poll_interval_sec:
            return self.current_snapshot
        self._last_poll_ts = now

        snap = self._get_best_snapshot()
        self._apply_snapshot(snap, now=now)
        return snap

    def is_educational(self, snapshot: Optional[ActivitySnapshot] = None) -> bool:
        snap = snapshot or self.current_snapshot
        if snap.kind == "website":
            domain = _safe_lower(snap.details.get("domain") or snap.label)
            # treat subdomains of known educational/distraction domains appropriately
            for base in self.educational_domains:
                if domain == base or domain.endswith("." + base):
                    return True
            for base in self.distraction_domains:
                if domain == base or domain.endswith("." + base):
                    return False
            # unknown domains default to non-educational (safer)
            return False
        if snap.kind == "app":
            exe = _safe_lower(snap.details.get("exe") or snap.label)
            return exe in self.educational_apps
        return False

    def add_points_for_focus(self, *, delta_time_sec: float, educational: bool) -> None:
        # Simple continuous points model:
        # - Focused + educational: +10 points / minute
        # - Focused + non-educational: -10 points / minute
        rate_per_sec = (10.0 / 60.0) if educational else (-10.0 / 60.0)
        with self._lock:
            self.points += rate_per_sec * max(0.0, float(delta_time_sec))

    # -------------------------
    # Internals
    # -------------------------
    def _start_server(self) -> None:
        # Start once; ignore failures (feature is optional)
        try:
            tracker = self

            class Handler(BaseHTTPRequestHandler):
                def log_message(self, format, *args):  # noqa: N802
                    return

                def do_POST(self):  # noqa: N802
                    if self.path != "/active-tab":
                        self.send_response(404)
                        self.end_headers()
                        return

                    length = int(self.headers.get("Content-Length", "0") or "0")
                    raw = self.rfile.read(length) if length > 0 else b"{}"
                    try:
                        payload = json.loads(raw.decode("utf-8"))
                        url = str(payload.get("url", "") or "")
                        title = str(payload.get("title", "") or "")
                        domain = _extract_domain(url) if url else ""
                        with tracker._lock:
                            tracker._latest_browser = {
                                "url": url,
                                "title": title,
                                "domain": domain,
                            }
                        self.send_response(200)
                        self.end_headers()
                        self.wfile.write(b"OK")
                    except Exception:
                        self.send_response(400)
                        self.end_headers()

            self._httpd = ThreadingHTTPServer((self.server_host, self.server_port), Handler)
            self._server_thread = threading.Thread(
                target=self._httpd.serve_forever, name="ActivityTrackerHTTP", daemon=True
            )
            self._server_thread.start()
        except Exception:
            self._httpd = None
            self._server_thread = None

    def _stop_server(self) -> None:
        try:
            if self._httpd:
                self._httpd.shutdown()
                self._httpd.server_close()
        finally:
            self._httpd = None
            self._server_thread = None

    def _get_best_snapshot(self) -> ActivitySnapshot:
        # Prefer browser event if present (more specific), otherwise fallback to Windows active window.
        with self._lock:
            latest_browser = dict(self._latest_browser) if self._latest_browser else None

        if latest_browser and latest_browser.get("domain"):
            domain = latest_browser["domain"]
            title = latest_browser.get("title", "")
            return ActivitySnapshot(
                kind="website",
                label=domain,
                details={"domain": domain, "title": title, "url": latest_browser.get("url", "")},
            )

        # Windows active window polling
        snap = self._get_active_window_snapshot()
        return snap or ActivitySnapshot("unknown", "Unknown", {})

    def _get_active_window_snapshot(self) -> Optional[ActivitySnapshot]:
        try:
            import psutil
            import win32gui
            import win32process
        except Exception:
            return None

        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            title = win32gui.GetWindowText(hwnd) or ""
            exe = ""
            try:
                exe = psutil.Process(pid).name()
            except Exception:
                exe = str(pid)

            label = exe or "UnknownApp"
            return ActivitySnapshot(kind="app", label=label, details={"exe": exe, "title": title})
        except Exception:
            return None

    def _apply_snapshot(self, snap: ActivitySnapshot, *, now: float) -> None:
        with self._lock:
            prev = self._last_snapshot
            prev_label = prev.label if prev else None

            # accumulate time for previous snapshot
            if prev:
                dt = max(0.0, now - self._last_change_ts)
                self.time_by_platform_sec[prev.label] = self.time_by_platform_sec.get(prev.label, 0.0) + dt

            # detect switch
            switched = prev_label is not None and prev_label != snap.label
            self._last_snapshot = snap
            self._last_change_ts = now
            self.current_snapshot = snap
            self._current_platform_start_ts = now

            is_edu = self.is_educational(snap)
            prev_is_edu = self.current_is_educational
            self.current_is_educational = is_edu

            self.last_warning = None
            if switched:
                evt = {
                    "time": time.strftime("%H:%M:%S"),
                    "from": prev_label or "",
                    "to": snap.label,
                    "from_kind": prev.kind if prev else "",
                    "to_kind": snap.kind,
                    "to_educational": str(is_edu),
                }
                self.switch_events.append(evt)
                if len(self.switch_events) > 200:
                    self.switch_events = self.switch_events[-200:]

                # penalty on switch to non-educational
                if not is_edu:
                    self.points -= 10.0
                    self.last_warning = "⚠ You switched to a distracting website/app."
                elif prev_is_edu is False and is_edu is True:
                    self.last_warning = "✅ Back to an educational website/app."

