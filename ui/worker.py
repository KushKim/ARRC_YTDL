from PySide6.QtCore import QThread, Signal
from core.downloader import download_one, DownloadCancelled

class QueueWorker(QThread):
    item_update = Signal(str, str, int, str)
    log = Signal(str)
    finished_all = Signal()

    def __init__(self, items, output_dir):
        super().__init__()
        self.items = items
        self.output_dir = output_dir
        self.cancel_current = False
        self.cancel_all = False

    def cancel_one(self):
        self.cancel_current = True

    def cancel_queue(self):
        self.cancel_all = True
        self.cancel_current = True

    def run(self):
        for item in self.items:
            if self.cancel_all:
                break
            if item.get("status") in ("완료", "건너뜀"):
                continue
            self.cancel_current = False
            item_id = item["id"]
            item["status"] = "다운로드 중"
            self.item_update.emit(item_id, "다운로드 중", 0, "")
            self.log.emit(f"시작: {item['url']}")

            def progress(percent, speed, eta):
                details = []
                if speed:
                    details.append(f"{speed / 1024 / 1024:.2f} MB/s")
                if eta is not None:
                    details.append(f"남은 시간 {eta}초")
                self.item_update.emit(item_id, "다운로드 중", percent, " · ".join(details))

            try:
                result, path = download_one(
                    item["url"], item["settings"], self.output_dir,
                    progress, lambda: self.cancel_current or self.cancel_all
                )
                if result == "이미 존재하여 건너뜀":
                    item["status"] = "건너뜀"
                    self.item_update.emit(item_id, "건너뜀", 100, path)
                    self.log.emit(f"건너뜀: {path}")
                else:
                    item["status"] = "완료"
                    self.item_update.emit(item_id, "완료", 100, path)
                    self.log.emit(f"완료: {path}")
            except DownloadCancelled as exc:
                item["status"] = "취소됨"
                self.item_update.emit(item_id, "취소됨", 0, str(exc))
                self.log.emit(f"취소: {item['url']}")
            except Exception as exc:
                if self.cancel_all:
                    item["status"] = "취소됨"
                    self.item_update.emit(item_id, "취소됨", 0, "전체 대기열 중단")
                elif self.cancel_current:
                    item["status"] = "취소됨"
                    self.item_update.emit(item_id, "취소됨", 0, "사용자가 취소함")
                else:
                    item["status"] = "실패"
                    self.item_update.emit(item_id, "실패", 0, str(exc))
                    self.log.emit(f"실패: {item['url']} - {exc}")
        if self.cancel_all:
            for item in self.items:
                if item.get("status") == "대기":
                    item["status"] = "취소됨"
                    self.item_update.emit(item["id"], "취소됨", 0, "전체 대기열 중단")
        self.finished_all.emit()
