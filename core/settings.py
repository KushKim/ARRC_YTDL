import json
import os
from pathlib import Path

APP_DIR = Path.home() / ".youtube_downloader"
APP_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = APP_DIR / "settings.json"
QUEUE_FILE = APP_DIR / "queue.json"

DEFAULTS = {
    "format": "video",
    "quality": "best",
    "audio_format": "mp3",
    "output_dir": str(Path.home() / "Downloads" / "YouTube"),
    "filename_template": "{channel} - {title}",
    "existing_policy": "skip",
    "allow_playlist": False,
    "download_subtitles": False,
}

def load_settings():
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        return {**DEFAULTS, **data}
    except (OSError, json.JSONDecodeError, TypeError):
        return DEFAULTS.copy()

def save_settings(settings):
    SETTINGS_FILE.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8"
    )

def load_queue():
    try:
        data = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []

def save_queue(items):
    QUEUE_FILE.write_text(
        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
    )
