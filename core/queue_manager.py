from urllib.parse import urlparse, parse_qs
import re

def normalize_url(raw):
    url = raw.strip()
    if not url:
        return None
    if not re.match(r"^https?://", url, re.I):
        return None
    parsed = urlparse(url)
    host = parsed.netloc.lower().split(":")[0]
    if host in {"youtu.be", "www.youtu.be"}:
        video_id = parsed.path.strip("/").split("/")[0]
        return f"https://www.youtube.com/watch?v={video_id}" if video_id else None
    if host.endswith("youtube.com"):
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
            if video_id:
                return f"https://www.youtube.com/watch?v={video_id}"
        if parsed.path.startswith(("/shorts/", "/live/", "/embed/")):
            parts = parsed.path.strip("/").split("/")
            if len(parts) >= 2:
                return f"https://www.youtube.com/watch?v={parts[1]}"
        if parsed.path.startswith("/playlist"):
            list_id = parse_qs(parsed.query).get("list", [""])[0]
            if list_id:
                return f"https://www.youtube.com/playlist?list={list_id}"
    return None

def add_urls(text, existing_urls):
    existing = set(existing_urls)
    accepted, duplicates, invalid = [], [], []
    seen_input = set()
    for line in text.splitlines():
        raw = line.strip()
        if not raw:
            continue
        url = normalize_url(raw)
        if not url:
            invalid.append(raw)
        elif url in existing or url in seen_input:
            duplicates.append(url)
        else:
            accepted.append(url)
            seen_input.add(url)
    return accepted, duplicates, invalid
