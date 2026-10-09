# YouTube Downloader

Windows용 PySide6 + yt-dlp 기반 다운로드 GUI.

## 요구 사항
- Python 3.10 이상 권장
- FFmpeg: MP3 변환 및 고화질 영상/음성 병합에 필요
- 다운로드 권한이 있는 콘텐츠에만 사용하세요.

## 설치
PowerShell 또는 PyCharm 터미널에서 프로젝트 폴더로 이동한 뒤:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

실행:
```powershell
python main.py
```

## FFmpeg 설치
1. https://www.gyan.dev/ffmpeg/builds/ 에서 Windows용 FFmpeg 빌드를 받습니다.
2. 압축을 풀고 `bin` 폴더 안에 `ffmpeg.exe`와 `ffprobe.exe`가 있는지 확인합니다.
3. `bin` 폴더를 Windows PATH에 추가합니다.
4. 새 터미널을 열고 `ffmpeg -version` 명령으로 확인합니다.

FFmpeg가 PATH에 없으면 MP3 변환이나 일부 고화질 다운로드 병합이 실패할 수 있습니다.

## 포함 기능
- 여러 URL 일괄 다운로드 및 중복 검사
- 영상/음성, 화질, 파일명 템플릿 설정
- 다운로드 대기열 및 진행률
- 현재 항목 취소 / 전체 대기열 중단
- 기존 파일 건너뛰기 / 덮어쓰기
- 실패 후 다음 URL 계속 진행, 실패 항목 재시도
- 설정 및 대기열 저장/복원

설정과 대기열은 Windows 사용자 프로필의 `.youtube_downloader` 폴더에 저장됩니다.
