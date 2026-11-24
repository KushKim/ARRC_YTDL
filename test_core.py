import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.downloader import build_name, build_output_template, ffmpeg_required, verify_dependencies
from core.queue_manager import add_urls, normalize_url


class QueueManagerTests(unittest.TestCase):
    def test_normalize_urls(self):
        self.assertEqual(
            normalize_url("https://youtu.be/dQw4w9WgXcQ"),
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )
        self.assertEqual(
            normalize_url("https://www.youtube.com/shorts/dQw4w9WgXcQ"),
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )
        self.assertIsNone(normalize_url("https://example.com/video"))

    def test_add_urls_removes_duplicates_and_invalid_entries(self):
        existing = ["https://www.youtube.com/watch?v=existing"]
        accepted, duplicates, invalid = add_urls(
            "https://youtu.be/dQw4w9WgXcQ\n"
            "https://youtu.be/dQw4w9WgXcQ\n"
            "https://youtube.com/watch?v=existing\n"
            "https://example.com/video",
            existing,
        )
        self.assertEqual(accepted, ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"])
        self.assertEqual(len(duplicates), 2)
        self.assertEqual(invalid, ["https://example.com/video"])


class DownloaderTests(unittest.TestCase):
    def test_safe_template_name(self):
        info = {"title": "A/B:C", "channel": "My Channel", "id": "abc"}
        self.assertEqual(build_name("{channel} - {title}", info), "My Channel - A_B_C")

    def test_output_template_is_yt_dlp_safe(self):
        with tempfile.TemporaryDirectory() as directory:
            template = build_output_template(directory, "{upload_date} - {title}")
            self.assertEqual(
                template,
                str(Path(directory) / "%(upload_date)s - %(title)s.%(ext)s"),
            )

    def test_ffmpeg_requirement(self):
        self.assertTrue(ffmpeg_required({"format": "video"}))
        self.assertTrue(ffmpeg_required({"format": "audio", "audio_format": "mp3"}))
        self.assertFalse(ffmpeg_required({"format": "audio", "audio_format": "m4a"}))

    def test_missing_ffmpeg_is_reported(self):
        with patch("core.downloader.find_ffmpeg", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "FFmpeg"):
                verify_dependencies({"format": "audio", "audio_format": "mp3"})


if __name__ == "__main__":
    unittest.main()
