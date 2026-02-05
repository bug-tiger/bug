# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Blog to YouTube Video Converter (blog2tube-backend) - FastAPI 백엔드로 블로그 글을 유튜브 동영상으로 자동 변환합니다.

## Development Commands

```bash
# 서버 실행 (개발 모드)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 의존성 설치
pip install -r requirements.txt

# 시스템 의존성 (영상 생성에 필요)
# Ubuntu: sudo apt-get install ffmpeg fonts-nanum
# macOS: brew install ffmpeg
```

## Architecture

```
app/
├── main.py              # FastAPI 앱 엔트리포인트
├── api/                 # 새로운 API 엔드포인트 (script 생성)
│   └── script.py        # POST /generate-script, /crawl-blog
├── core/                # 설정 및 공통 유틸리티
│   └── config.py        # pydantic-settings 기반 환경 설정
├── schemas/             # Pydantic 모델
│   └── script.py        # ScriptRequest, ScriptResponse, Scene
├── routers/             # 기존 라우터 (video 생성)
│   └── video.py         # /api/generate, /api/progress, /api/download
└── services/            # 비즈니스 로직
    ├── anthropic_script_generator.py  # Anthropic Claude 기반 대본 생성 (Scene 단위)
    ├── naver_crawler.py               # 네이버 블로그 크롤러
    ├── script_generator.py            # Google Gemini 기반 대본 생성
    ├── tts_service.py                 # ElevenLabs TTS (청크 분할 지원)
    ├── image_generator.py             # OpenAI DALL-E 3 이미지 생성 (병렬 처리)
    ├── video_creator.py               # MoviePy 영상 합성
    └── image_service.py               # Pexels B-roll 이미지
```

## API Endpoints

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/generate-script` | 블로그 → 유튜브 대본 변환 (Scene 단위, 이미지 프롬프트 포함) |
| POST | `/crawl-blog` | 네이버 블로그 URL에서 제목/본문 추출 |
| POST | `/api/generate` | 전체 영상 생성 파이프라인 |
| GET | `/api/progress/{video_id}` | 영상 생성 진행 상태 |
| GET | `/api/download/{video_id}` | 완료된 영상 다운로드 |
| GET | `/api/script/{video_id}` | 생성된 스크립트 조회 |

## Environment Variables

`.env` 파일에 설정 필요:
- `ANTHROPIC_API_KEY`: Anthropic Claude API (대본 생성)
- `OPENAI_API_KEY`: OpenAI API (DALL-E 3 이미지 생성)
- `GEMINI_API_KEY`: Google Gemini API (기존 대본 생성)
- `ELEVENLABS_API_KEY`: ElevenLabs TTS API (음성 합성)
- `ELEVENLABS_VOICE_ID`: ElevenLabs 음성 ID (클론 목소리 또는 기본 목소리)
- `PEXELS_API_KEY`: Pexels API (B-roll 이미지, 선택사항)

## Key Design Patterns

- **서비스 분리**: 각 기능(스크립트 생성, TTS, 영상 합성)은 독립된 서비스 모듈
- **비동기 처리**: 영상 생성은 BackgroundTasks로 비동기 처리, 진행 상태는 인메모리 저장소로 추적
- **환경 설정**: pydantic-settings를 사용한 타입 안전 환경 변수 관리
- **Scene 기반 대본**: 영상 편집을 위해 장면 단위로 대본과 이미지 프롬프트 분리

## Adding New Features

1. **새 API 엔드포인트**: `app/api/` 디렉토리에 라우터 모듈 생성 후 `app/api/__init__.py`에 등록
2. **새 Pydantic 모델**: `app/schemas/` 디렉토리에 정의
3. **새 서비스**: `app/services/` 디렉토리에 비즈니스 로직 모듈 생성
