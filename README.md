# Blog to YouTube Video Converter

블로그 글을 10분 분량의 유튜브 동영상으로 자동 변환하는 웹 앱입니다.

## 주요 기능

- **AI 스크립트 생성**: OpenAI GPT-4o를 활용하여 블로그 글을 유튜브 스크립트로 변환
- **TTS 음성 합성**: Edge TTS를 사용한 자연스러운 한국어 음성 생성
- **영상 자동 생성**: MoviePy를 활용한 MP4 영상 자동 합성
- **실시간 진행 상태**: 영상 생성 과정을 실시간으로 확인

## 기술 스택

- **Backend**: FastAPI (Python)
- **AI**: OpenAI GPT-4o
- **TTS**: Microsoft Edge TTS
- **Video**: MoviePy
- **Frontend**: Vanilla HTML/CSS/JavaScript

## 설치 방법

### 1. 저장소 클론

```bash
git clone <repository-url>
cd blog-to-youtube
```

### 2. 가상환경 생성 및 활성화

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate  # Windows
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. 시스템 의존성 설치 (Linux)

```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg fonts-nanum

# macOS
brew install ffmpeg
```

### 5. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 열고 OpenAI API 키 입력 (선택사항 - 웹 UI에서도 입력 가능)
```

## 실행 방법

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

브라우저에서 http://localhost:8000 접속

## 사용 방법

1. OpenAI API 키 입력
2. 영상 제목 입력
3. 블로그 글 내용 붙여넣기
4. 음성 및 색상 옵션 선택 (선택사항)
5. "영상 생성하기" 버튼 클릭
6. 완료 후 영상 다운로드

## API 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/` | 메인 페이지 |
| POST | `/api/generate` | 영상 생성 시작 |
| GET | `/api/progress/{video_id}` | 진행 상태 확인 |
| GET | `/api/download/{video_id}` | 영상 다운로드 |
| GET | `/api/script/{video_id}` | 생성된 스크립트 조회 |

## 프로젝트 구조

```
blog-to-youtube/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 앱
│   ├── routers/
│   │   └── video.py         # 비디오 생성 API
│   ├── services/
│   │   ├── script_generator.py  # AI 스크립트 변환
│   │   ├── tts_service.py       # TTS 음성 생성
│   │   └── video_creator.py     # 영상 합성
│   └── templates/
│       └── index.html       # 프론트엔드
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
├── output/                  # 생성된 영상 저장
├── requirements.txt
├── .env.example
└── README.md
```

## 사용 가능한 음성

| 음성 코드 | 설명 |
|-----------|------|
| ko-KR-SunHiNeural | 선희 (여성, 따뜻한 톤) |
| ko-KR-InJoonNeural | 인준 (남성, 차분한 톤) |
| ko-KR-YuJinNeural | 유진 (여성) |
| ko-KR-BongJinNeural | 봉진 (남성) |

## 라이선스

MIT License
