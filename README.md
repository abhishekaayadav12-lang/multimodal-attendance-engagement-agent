# Multimodal Attendance & Engagement Agent — Functional Version

A local Streamlit project for anonymous classroom video attendance/activity analysis and optional WAV acoustic activity analysis.

## Features

- Create/delete classroom sessions
- Upload MP4/MOV/AVI/MKV classroom video
- Anonymous face detection and centroid tracking
- Sustained-presence attendance output
- Upload PCM WAV audio
- Acoustic activity windows without speech transcription
- Multimodal fusion with explainable heuristic score
- Activity trend chart
- Teaching suggestions
- SQLite persistence
- CSV exports
- Privacy/limitations page

## Windows setup

Open PowerShell in this folder:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

If PowerShell blocks activation, you can skip activation and use:

```powershell
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe -m streamlit run app.py
```

## How to test

1. Open the Streamlit URL shown in the terminal.
2. Go to **Create Session**.
3. Enter a class name and create it.
4. Go to **Vision & Attendance**.
5. Upload a short classroom video.
6. Set presence threshold to 2–5 seconds for a quick test.
7. Click **Analyze Video**.
8. Review the anonymous attendance table and download CSV.
9. Optionally go to **Audio Analysis** and upload a WAV file.
10. Go to **Analytics** and click **Fuse Signals & Generate Output**.
11. Review the chart, detailed table, suggestions, and CSV export.

## Important limitation

This project intentionally does NOT perform biometric identity recognition. `Person-01`, `Person-02`, etc. are anonymous temporary tracks. The attendance result means that a face-like track was visible for the configured duration; it does not identify a named student.

The engagement score is only an activity proxy derived from motion and/or acoustic energy. It is not a scientific measure of attention or learning and should not be used for grading or discipline.
