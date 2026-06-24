# 🎯 AI-Enabled Student Focus Monitoring and Study Analytics System

RS9 is an AI-powered study monitoring platform designed to help students improve concentration, productivity, and study discipline. The system combines **webcam-based focus detection**, **browser and system activity tracking**, **study analytics**, and **performance dashboards** into a single integrated application.

Built using **Python** and **Streamlit**, RS9 provides real-time insights into student behavior and generates meaningful reports for students, parents, and teachers.

---

## 📌 Project Overview

With the rapid growth of online learning and self-study environments, maintaining student focus has become increasingly challenging. Traditional classrooms provide direct supervision, but digital learning environments often lack effective monitoring mechanisms.

RS9 addresses this problem by using Artificial Intelligence and behavioral analytics to:

- Monitor student attention using webcam input.
- Track browser and application usage.
- Analyze study patterns and productivity.
- Generate reports and performance insights.
- Encourage disciplined learning through a reward mechanism.

---

## ✨ Features

### 🎥 Real-Time Focus Detection
- Detects face and eyes using OpenCV Haar Cascades.
- Estimates attention levels during study sessions.
- Calculates focused study time.

### 🌐 Browser Activity Tracking
- Uses a custom Chrome/Edge extension.
- Tracks active tabs and visited websites.
- Sends URL and title information to the local Python server.

### 💻 System Activity Monitoring
- Monitors active applications running on Windows.
- Records time spent on different platforms.

### 📊 Study Analytics Dashboard
- Displays:
  - Total study time
  - Focused time
  - Productivity score
  - Daily and weekly reports

### 👨‍🏫 Parent & Teacher Dashboard
- Allows monitoring of student performance.
- Supports date-based report generation.
- Enables PDF report download (optional).

### 🏆 Reward System
- Assigns rewards based on focus level.
- Generates warnings for excessive distractions.
- Encourages consistent study habits.

### 📁 CSV-Based Data Logging
- Stores:
  - Study session details
  - Website usage history
  - Focus statistics

---

### Workflow Summary

1. Student starts a study session.
2. Webcam captures video frames.
3. Face and eyes are detected.
4. Browser extension monitors active tabs.
5. Activity data is classified.
6. Information is stored in CSV files.
7. Analytics are generated.
8. Dashboards display performance reports.

---

# 🛠 Technologies Used

## Programming Language
- Python

## Frontend
- Streamlit

## Computer Vision
- OpenCV

## Data Processing
- Pandas
- NumPy

## Reporting
- ReportLab (optional)

## Browser Extension
- JavaScript
- Chrome/Edge Manifest V3

## Data Storage
- CSV Files

---

# 📂 Project Structure

```text
RS9/
│
├── streamlit_app.py
├── focus_detector_logic.py
├── activity_tracker.py
├── study_analytics_dashboard.py
├── parental_teacher_dashboard.py
├── Reward_System.py
│
├── study_sessions_log.csv
├── website_usage_log.csv
│
├── haarcascade_frontalface_default.xml
├── haarcascade_eye.xml
│
├── browser_extension/
│   ├── manifest.json
│   ├── background.js
│   └── README.txt
│
└── .vscode/
    └── settings.json
```

---

# 📄 File Description

| File | Description |
|--------|------------|
| `streamlit_app.py` | Main application entry point |
| `focus_detector_logic.py` | Webcam-based focus detection logic |
| `activity_tracker.py` | Browser and system activity tracking |
| `study_analytics_dashboard.py` | Analytics and report generation |
| `parental_teacher_dashboard.py` | Parent and teacher monitoring dashboard |
| `Reward_System.py` | Reward mechanism |
| `study_sessions_log.csv` | Stores study session records |
| `website_usage_log.csv` | Stores website usage history |
| `manifest.json` | Browser extension configuration |
| `background.js` | Sends active tab information to backend |

---

# 🚀 Installation

## 1. Clone the Repository

```bash
git clone https://github.com/your-username/RS9.git
cd RS9
```

---

## 2. Create Virtual Environment (Optional)

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / Mac

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Run the Application

```bash
streamlit run streamlit_app.py
```

The application will open in your browser.

---

# 🌐 Browser Extension Setup

The browser extension tracks active tabs and sends website information to the local Python server.

### Steps:

1. Open:

```text
chrome://extensions
```

or

```text
edge://extensions
```

2. Enable **Developer Mode**.

3. Click **Load unpacked**.

4. Select:

```text
browser_extension/
```

5. Keep the Streamlit application running.

---

# 📈 Generated Reports

RS9 automatically generates:

- Daily study reports
- Weekly performance reports
- Website usage reports
- Focus statistics
- Productivity scores
- Parent and teacher summaries

---

# 📊 Data Files

### `study_sessions_log.csv`

Stores:

- Student name
- Roll number
- Date
- Start time
- End time
- Study duration
- Focused duration

### `website_usage_log.csv`

Stores:

- Website name
- Time spent
- Educational status
- Student details

---

# 🧠 Focus Detection Method

RS9 uses:

- OpenCV Haar Cascade Classifiers
- Face Detection
- Eye Detection
- Eye Aspect Ratio (EAR)

The system estimates whether the student is focused based on eye behavior and continuously updates session statistics.

---

# 🌍 Activity Tracking Method

The browser extension:

- Detects active tabs.
- Captures URL and title.
- Sends information to:

```text
http://127.0.0.1:8765/active-tab
```

The backend classifies activities as:

- Educational
- Distracting

and records the time spent on each platform.

---

# 🏆 Reward Mechanism

The system encourages productive behavior by:

- Awarding points for focused study.
- Generating warnings for excessive distractions.
- Promoting self-discipline and consistency.

---

# 🎯 Applications

RS9 can be used in:

- Schools
- Colleges
- Online learning platforms
- Self-study environments
- Coaching institutes
- Smart classroom systems

---

# ⚠ Limitations

- Performance depends on camera quality and lighting.
- Website classification is rule-based.
- Runs locally and does not use cloud storage.
- Does not yet use deep learning models.

---

# 🔮 Future Enhancements

- Deep learning-based focus detection.
- Mobile application support.
- Cloud database integration.
- Personalized recommendations.
- Adaptive learning analytics.
- LMS integration.
- Smart classroom deployment.

---

# 📚 Research Domain

- Artificial Intelligence
- Computer Vision
- Learning Analytics
- Educational Technology
- Human-Computer Interaction

---

# 📜 License

This project is developed for educational and research purposes only.

---

