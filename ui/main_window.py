import uuid
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPlainTextEdit, QPushButton, QComboBox, QLineEdit, QFileDialog, QCheckBox,
    QTableWidget, QTableWidgetItem, QProgressBar, QMessageBox, QHeaderView,
    QGroupBox
)

from core.settings import load_settings, save_settings, load_queue, save_queue
from core.queue_manager import add_urls
from ui.worker import QueueWorker

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Downloader")
        self.resize(1120, 800)
        self.settings = load_settings()
        self.queue = []
        self.worker = None
        self._build_ui()
        self._load_saved_queue()
        self._apply_settings_to_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        url_group = QGroupBox("URL 입력")
        url_layout = QVBoxLayout(url_group)
        self.url_input = QPlainTextEdit()
        self.url_input.setPlaceholderText("유튜브 URL을 한 줄에 하나씩 입력하세요.")
        self.url_input.setMaximumHeight(110)
        url_layout.addWidget(self.url_input)
        add_row = QHBoxLayout()
        self.add_btn = QPushButton("URL 추가")
        self.clear_input_btn = QPushButton("입력 지우기")
        add_row.addWidget(self.add_btn)
        add_row.addWidget(self.clear_input_btn)
        add_row.addStretch()
        url_layout.addLayout(add_row)
        root.addWidget(url_group)

        options = QGroupBox("다운로드 설정")
        grid = QGridLayout(options)
        self.format_combo = QComboBox()
        self.format_combo.addItem("영상 (MP4)", "video")
        self.format_combo.addItem("음성만", "audio")
        self.quality_combo = QComboBox()
        for label, value in [("최고 화질", "best"), ("최대 4K / 2160p", "2160"),
                             ("최대 1080p", "1080"), ("최대 720p", "720")]:
            self.quality_combo.addItem(label, value)
        self.audio_combo = QComboBox()
        self.audio_combo.addItem("MP3", "mp3")
        self.audio_combo.addItem("M4A", "m4a")
        self.audio_combo.addItem("원본 음성", "original")
        self.policy_combo = QComboBox()
        self.policy_combo.addItem("기존 파일 건너뛰기", "skip")
        self.policy_combo.addItem("기존 파일 덮어쓰기", "overwrite")
        self.template_input = QLineEdit()
        self.template_input.setPlaceholderText("{channel} - {title}")
        self.subtitle_check = QCheckBox("자막 함께 다운로드 (한국어/영어)")
        self.playlist_check = QCheckBox("재생목록 전체 다운로드 허용")
        grid.addWidget(QLabel("형식"), 0, 0)
        grid.addWidget(self.format_combo, 0, 1)
        grid.addWidget(QLabel("영상 화질"), 0, 2)
        grid.addWidget(self.quality_combo, 0, 3)
        grid.addWidget(QLabel("음성 형식"), 1, 0)
        grid.addWidget(self.audio_combo, 1, 1)
        grid.addWidget(QLabel("기존 파일"), 1, 2)
        grid.addWidget(self.policy_combo, 1, 3)
        grid.addWidget(QLabel("파일명 템플릿"), 2, 0)
        grid.addWidget(self.template_input, 2, 1, 1, 3)
        grid.addWidget(self.subtitle_check, 3, 0, 1, 2)
        grid.addWidget(self.playlist_check, 3, 2, 1, 2)
        root.addWidget(options)

        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("저장 폴더"))
        self.folder_input = QLineEdit()
        self.folder_button = QPushButton("폴더 선택…")
        folder_row.addWidget(self.folder_input, 1)
        folder_row.addWidget(self.folder_button)
        root.addLayout(folder_row)

        controls = QHBoxLayout()
        self.start_btn = QPushButton("다운로드 시작")
        self.cancel_current_btn = QPushButton("현재 항목 취소")
        self.cancel_all_btn = QPushButton("대기열 전체 중단")
        self.retry_btn = QPushButton("실패/취소 항목 재시도")
        self.remove_btn = QPushButton("선택 항목 삭제")
        controls.addWidget(self.start_btn)
        controls.addWidget(self.cancel_current_btn)
        controls.addWidget(self.cancel_all_btn)
        controls.addWidget(self.retry_btn)
        controls.addWidget(self.remove_btn)
        root.addLayout(controls)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["URL", "상태", "진행률", "메시지/파일", "ID"])
        self.table.setColumnHidden(4, True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        root.addWidget(self.table, 1)

        root.addWidget(QLabel("로그"))
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(120)
        root.addWidget(self.log_view)

        self.add_btn.clicked.connect(self.add_urls)
        self.clear_input_btn.clicked.connect(self.url_input.clear)
        self.folder_button.clicked.connect(self.choose_folder)
        self.start_btn.clicked.connect(self.start_downloads)
        self.cancel_current_btn.clicked.connect(self.cancel_current)
        self.cancel_all_btn.clicked.connect(self.cancel_all)
        self.retry_btn.clicked.connect(self.retry_failed)
        self.remove_btn.clicked.connect(self.remove_selected)
        self.format_combo.currentIndexChanged.connect(self._update_option_enabled)
        self._update_option_enabled()

    def _apply_settings_to_ui(self):
        self._set_combo_data(self.format_combo, self.settings.get("format", "video"))
        self._set_combo_data(self.quality_combo, self.settings.get("quality", "best"))
        self._set_combo_data(self.audio_combo, self.settings.get("audio_format", "mp3"))
        self._set_combo_data(self.policy_combo, self.settings.get("existing_policy", "skip"))
        self.folder_input.setText(self.settings.get("output_dir", str(Path.home() / "Downloads")))
        self.template_input.setText(self.settings.get("filename_template", "{channel} - {title}"))
        self.subtitle_check.setChecked(bool(self.settings.get("download_subtitles", False)))
        self.playlist_check.setChecked(bool(self.settings.get("allow_playlist", False)))

    @staticmethod
    def _set_combo_data(combo, value):
        idx = combo.findData(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _current_settings(self):
        return {
            "format": self.format_combo.currentData(),
            "quality": self.quality_combo.currentData(),
            "audio_format": self.audio_combo.currentData(),
            "output_dir": self.folder_input.text().strip(),
            "filename_template": self.template_input.text().strip() or "{channel} - {title}",
            "existing_policy": self.policy_combo.currentData(),
            "download_subtitles": self.subtitle_check.isChecked(),
            "allow_playlist": self.playlist_check.isChecked(),
        }

    def _save_all(self):
        self.settings = self._current_settings()
        save_settings(self.settings)
        save_queue(self.queue)

    def _load_saved_queue(self):
        for item in load_queue():
            if not isinstance(item, dict) or not item.get("url"):
                continue
            item.setdefault("id", uuid.uuid4().hex)
            # A running state from a previous app session cannot still be active.
            if item.get("status") == "다운로드 중":
                item["status"] = "대기"
            item.setdefault("settings", self.settings.copy())
            self.queue.append(item)
        self._refresh_table()

    def add_urls(self):
        existing = [item["url"] for item in self.queue]
        accepted, duplicates, invalid = add_urls(self.url_input.toPlainText(), existing)
        if duplicates:
            QMessageBox.information(self, "중복 URL", "중복 URL은 추가하지 않았습니다:\n" + "\n".join(duplicates[:15]))
        if invalid:
            QMessageBox.warning(self, "잘못된 URL", "유효한 유튜브 URL이 아닌 항목:\n" + "\n".join(invalid[:15]))
        if not accepted:
            if not duplicates and not invalid:
                QMessageBox.information(self, "안내", "추가할 URL을 입력하세요.")
            return
        settings = self._current_settings()
        for url in accepted:
            self.queue.append({
                "id": uuid.uuid4().hex,
                "url": url,
                "status": "대기",
                "settings": settings.copy(),
            })
        self.url_input.clear()
        self._refresh_table()
        self._save_all()
        self._log(f"{len(accepted)}개 URL을 대기열에 추가했습니다.")

    def choose_folder(self):
        current = self.folder_input.text().strip() or str(Path.home() / "Downloads")
        folder = QFileDialog.getExistingDirectory(self, "저장 폴더 선택", current)
        if folder:
            self.folder_input.setText(folder)
            self._save_all()

    def start_downloads(self):
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "다운로드 중", "이미 다운로드 작업이 실행 중입니다.")
            return
        output_dir = self.folder_input.text().strip()
        if not output_dir:
            QMessageBox.warning(self, "저장 폴더", "저장 폴더를 선택하세요.")
            return
        pending = [x for x in self.queue if x.get("status") in ("대기", "취소됨", "실패")]
        if not pending:
            QMessageBox.information(self, "대기열", "다운로드할 대기 항목이 없습니다.")
            return
        current_settings = self._current_settings()
        for item in pending:
            # Use settings captured when added, so each batch retains its selected options.
            item.setdefault("settings", current_settings.copy())
            item["settings"]["output_dir"] = output_dir
            if item.get("status") in ("취소됨", "실패"):
                item["status"] = "대기"
        self._save_all()
        self.worker = QueueWorker(pending, output_dir)
        self.worker.item_update.connect(self._on_item_update)
        self.worker.log.connect(self._log)
        self.worker.finished_all.connect(self._on_finished)
        self._set_running(True)
        self.worker.start()

    def cancel_current(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel_one()
            self._log("현재 항목 취소를 요청했습니다.")

    def cancel_all(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel_queue()
            self._log("대기열 전체 중단을 요청했습니다.")

    def retry_failed(self):
        count = 0
        for item in self.queue:
            if item.get("status") in ("실패", "취소됨"):
                item["status"] = "대기"
                count += 1
        self._refresh_table()
        self._save_all()
        self._log(f"{count}개 항목을 재시도 대기 상태로 변경했습니다.")

    def remove_selected(self):
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "다운로드 중", "다운로드 중에는 항목을 삭제할 수 없습니다.")
            return
        rows = sorted({index.row() for index in self.table.selectionModel().selectedRows()}, reverse=True)
        for row in rows:
            item_id = self.table.item(row, 4).text()
            self.queue = [item for item in self.queue if item["id"] != item_id]
        self._refresh_table()
        self._save_all()

    def _refresh_table(self):
        self.table.setRowCount(len(self.queue))
        for row, item in enumerate(self.queue):
            self.table.setItem(row, 0, QTableWidgetItem(item.get("url", "")))
            self.table.setItem(row, 1, QTableWidgetItem(item.get("status", "대기")))
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(int(item.get("progress", 0)))
            self.table.setCellWidget(row, 2, bar)
            self.table.setItem(row, 3, QTableWidgetItem(item.get("message", "")))
            self.table.setItem(row, 4, QTableWidgetItem(item.get("id", "")))

    def _on_item_update(self, item_id, status, percent, message):
        for row, item in enumerate(self.queue):
            if item["id"] == item_id:
                item["status"] = status
                item["progress"] = percent
                item["message"] = message
                self.table.item(row, 1).setText(status)
                bar = self.table.cellWidget(row, 2)
                if bar:
                    bar.setValue(percent)
                self.table.item(row, 3).setText(message)
                break
        self._save_all()

    def _on_finished(self):
        self._set_running(False)
        self._save_all()
        self._log("대기열 작업이 종료되었습니다.")

    def _set_running(self, running):
        self.start_btn.setEnabled(not running)
        self.cancel_current_btn.setEnabled(running)
        self.cancel_all_btn.setEnabled(running)
        self.add_btn.setEnabled(not running)
        self.remove_btn.setEnabled(not running)

    def _update_option_enabled(self):
        is_video = self.format_combo.currentData() == "video"
        self.quality_combo.setEnabled(is_video)
        self.audio_combo.setEnabled(not is_video)

    def _log(self, message):
        self.log_view.appendPlainText(message)

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            answer = QMessageBox.question(
                self, "다운로드 진행 중",
                "다운로드가 진행 중입니다. 중단하고 종료할까요?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.worker.cancel_queue()
            self.worker.wait(5000)
        self._save_all()
        event.accept()
