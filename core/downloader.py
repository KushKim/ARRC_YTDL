import os
import re
import shutil
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

def download_one(url, settings, output_dir, progress_callback, cancel_check):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if shutil.which("ffmpeg") is None and (
        settings.get("format") == "audio" and settings.get("audio_format") == "mp3"
    ):
        raise RuntimeError("MP3 변환에는 FFmpeg가 필요합니다. README.md의 설치 안내를 확인하세요.")

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

        stem = build_name(settings.get("filename_template", "{channel} - {title}"), info)
        ext = "mp3" if settings.get("format") == "audio" and settings.get("audio_format") == "mp3" else (
            "m4a" if settings.get("format") == "audio" and settings.get("audio_format") == "m4a" else
            ("mp4" if settings.get("format") == "video" else (info.get("ext") or "webm"))
        )
        expected = output_dir / f"{stem}.{ext}"
        if expected.exists() and settings.get("existing_policy", "skip") == "skip":
            return "이미 존재하여 건너뜀", str(expected)

        # %(title)s 대신 사용자 템플릿을 적용하되, 제목/채널명은 안전한 파일명으로 만듭니다.
        opts["outtmpl"] = str(output_dir / f"{stem}.%(ext)s")
        # Use same configured options in the actual download call.
        with YoutubeDL(opts) as downloader:
            downloader.download([url])
        if cancel_check():
            raise DownloadCancelled("사용자가 다운로드를 취소했습니다.")
        return "완료", str(expected)
