import os
import re
import shutil
import sys
from pathlib import Path
from yt_dlp import YoutubeDL

class DownloadCancelled(Exception):
    pass

def safe_filename(value):
    value = str(value or "").strip()
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    value = value.rstrip(". ")
    return value[:180] or "video"

def build_name(template, info):
    values = {
        "title": info.get("title") or "video",
        "channel": info.get("channel") or info.get("uploader") or "unknown_channel",
        "uploader": info.get("uploader") or info.get("channel") or "unknown_channel",
        "upload_date": info.get("upload_date") or "unknown_date",
        "id": info.get("id") or "unknown_id",
    }
    try:
        raw = template.format(**values)
    except (KeyError, ValueError):
        raw = "{channel} - {title}".format(**values)
    return safe_filename(raw)

def build_output_template(output_dir, template):
    values = {
        "{title}": "%(title)s",
        "{channel}": "%(channel)s",
        "{uploader}": "%(uploader)s",
        "{upload_date}": "%(upload_date)s",
        "{id}": "%(id)s",
    }
    raw = template or "{channel} - {title}"
    for key, replacement in values.items():
        raw = raw.replace(key, replacement)
    raw = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", raw)
    return str(Path(output_dir) / f"{raw}.%(ext)s")

def get_options(settings, output_dir, progress_hook, cancel_check):
    fmt = settings.get("format", "video")
    quality = settings.get("quality", "best")
    audio_format = settings.get("audio_format", "mp3")
    template = settings.get("filename_template", "{channel} - {title}")
    policy = settings.get("existing_policy", "skip")
    outtmpl = os.path.join(str(output_dir), "%(title)s.%(ext)s")

    opts = {
        "outtmpl": outtmpl,
        "noplaylist": not bool(settings.get("allow_playlist", False)),
        "ignoreerrors": False,
        "continuedl": True,
        "overwrites": policy == "overwrite",
        "nopart": False,
        "quiet": True,
        "no_warnings": False,
        "progress_hooks": [progress_hook],
        "windowsfilenames": True,
        "retries": 2,
        "fragment_retries": 2,
    }
    if fmt == "audio":
        if audio_format == "mp3":
            opts.update({"format": "bestaudio/best", "postprocessors": [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3",
                 "preferredquality": "0"}
            ]})
        elif audio_format == "m4a":
            opts.update({"format": "bestaudio[ext=m4a]/bestaudio/best"})
        else:
            opts.update({"format": "bestaudio/best"})
    else:
        if quality == "best":
            opts["format"] = "bestvideo*+bestaudio/best"
        else:
            opts["format"] = f"bestvideo[height<={int(quality)}]+bestaudio/best[height<={int(quality)}]"
        opts["merge_output_format"] = "mp4"

    if settings.get("download_subtitles"):
        opts.update({
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitlesformat": "best",
            "subtitleslangs": ["ko", "en"],
        })
    return opts

def find_ffmpeg():
    bundled = Path(sys.executable).with_name("ffmpeg")
    bundled_windows = bundled.with_suffix(".exe")
    candidates = (
        bundled,
        bundled_windows,
        Path(sys._MEIPASS) / "ffmpeg" if hasattr(sys, "_MEIPASS") else None,
        Path(sys._MEIPASS) / "ffmpeg.exe" if hasattr(sys, "_MEIPASS") else None,
    )
    for candidate in candidates:
        if candidate and candidate.is_file():
            return str(candidate)
    return shutil.which("ffmpeg")

def ffmpeg_required(settings):
    fmt = settings.get("format", "video")
    if fmt == "audio":
        return settings.get("audio_format", "mp3") == "mp3"
    return True

def verify_dependencies(settings):
    if ffmpeg_required(settings) and find_ffmpeg() is None:
        if settings.get("format") == "audio":
            raise RuntimeError("MP3 변환에는 FFmpeg가 필요합니다. README.md의 설치 안내를 확인하세요.")
        raise RuntimeError("영상 다운로드에는 FFmpeg가 필요합니다. 고화질 영상 병합을 위해 FFmpeg를 설치하세요.")

def download_one(url, settings, output_dir, progress_callback, cancel_check):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    verify_dependencies(settings)

    def hook(data):
        if cancel_check():
            raise DownloadCancelled("사용자가 다운로드를 취소했습니다.")
        status = data.get("status")
        if status == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            downloaded = data.get("downloaded_bytes") or 0
            percent = int(downloaded * 100 / total) if total else 0
            progress_callback(percent, data.get("speed"), data.get("eta"))
        elif status == "finished":
            progress_callback(100, None, None)

    opts = get_options(settings, output_dir, hook, cancel_check)
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if not info:
            raise RuntimeError("영상 정보를 가져오지 못했습니다.")
        if info.get("_type") == "playlist" and not settings.get("allow_playlist"):
            raise RuntimeError("재생목록 URL입니다. 재생목록 다운로드 옵션을 켜거나 개별 영상 URL을 입력하세요.")

        entries = info.get("entries") if info.get("_type") == "playlist" else [info]
        entries = [entry for entry in (entries or []) if entry]
        if not entries:
            raise RuntimeError("다운로드할 영상을 찾지 못했습니다.")

        template = settings.get("filename_template", "{channel} - {title}")
        opts["outtmpl"] = build_output_template(output_dir, template)
        ydl.params.update(opts)

        if settings.get("existing_policy", "skip") == "skip":
            downloadable_entries = []
            skipped_paths = []
            for entry in entries:
                stem = build_name(template, entry)
                candidates = list(output_dir.glob(f"{stem}.*"))
                if candidates:
                    existing = next((path for path in candidates if path.is_file()), None)
                    if existing:
                        if len(entries) == 1:
                            return "이미 존재하여 건너뜀", str(existing)
                        skipped_paths.append(str(existing))
                        continue
                downloadable_entries.append(entry)
            if info.get("_type") == "playlist":
                if not downloadable_entries:
                    return "이미 존재하여 건너뜀", ", ".join(skipped_paths)
                info["entries"] = downloadable_entries

        ydl.process_ie_result(info, download=True)
        if len(entries) == 1:
            stem = build_name(template, entries[0])
            if settings.get("format") == "audio" and settings.get("audio_format") == "mp3":
                expected = output_dir / f"{stem}.mp3"
            elif settings.get("format") == "video":
                expected = output_dir / f"{stem}.mp4"
            else:
                prepared = ydl.prepare_filename(entries[0])
                expected = Path(prepared)
            if not expected.exists():
                candidates = list(output_dir.glob(f"{stem}.*"))
                if candidates:
                    expected = max(candidates, key=lambda path: path.stat().st_mtime)
        else:
            expected = output_dir
        if cancel_check():
            raise DownloadCancelled("사용자가 다운로드를 취소했습니다.")
        return "완료", str(expected)
