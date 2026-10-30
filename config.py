from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
DB = DATA / "attendance.sqlite3"
PRESENCE_SECONDS = 8
VIDEO_WINDOW_SECONDS = 30
AUDIO_WINDOW_SECONDS = 30
