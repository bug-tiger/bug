from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import uuid
import os

from app.services.script_generator import generate_script
from app.services.tts_service import generate_audio
from app.services.video_creator import create_video

router = APIRouter()


class BlogToVideoRequest(BaseModel):
    blog_content: str
    title: Optional[str] = "YouTube Video"
    voice: Optional[str] = "ko-KR-SunHiNeural"
    background_color: Optional[str] = "#1a1a2e"
    text_color: Optional[str] = "#ffffff"
    openai_api_key: Optional[str] = None


class VideoResponse(BaseModel):
    status: str
    message: str
    video_id: Optional[str] = None
    script: Optional[str] = None


# 진행 상태 저장
progress_store = {}


@router.post("/generate", response_model=VideoResponse)
async def generate_video(request: BlogToVideoRequest, background_tasks: BackgroundTasks):
    """블로그 글을 유튜브 동영상으로 변환"""

    video_id = str(uuid.uuid4())[:8]
    progress_store[video_id] = {"status": "processing", "step": "시작", "progress": 0}

    # 백그라운드에서 영상 생성
    background_tasks.add_task(
        process_video_generation,
        video_id,
        request
    )

    return VideoResponse(
        status="processing",
        message="영상 생성을 시작했습니다.",
        video_id=video_id
    )


async def process_video_generation(video_id: str, request: BlogToVideoRequest):
    """백그라운드에서 영상 생성 처리"""
    try:
        # Step 1: 스크립트 생성
        progress_store[video_id] = {"status": "processing", "step": "스크립트 생성 중...", "progress": 20}

        api_key = request.openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            progress_store[video_id] = {"status": "error", "step": "OpenAI API 키가 필요합니다.", "progress": 0}
            return

        script = await generate_script(request.blog_content, request.title, api_key)
        progress_store[video_id]["script"] = script

        # Step 2: TTS 음성 생성
        progress_store[video_id] = {
            **progress_store[video_id],
            "status": "processing",
            "step": "음성 생성 중...",
            "progress": 50
        }

        audio_path = f"output/{video_id}_audio.mp3"
        await generate_audio(script, audio_path, request.voice)

        # Step 3: 영상 합성
        progress_store[video_id] = {
            **progress_store[video_id],
            "status": "processing",
            "step": "영상 합성 중...",
            "progress": 80
        }

        video_path = f"output/{video_id}_video.mp4"
        await create_video(
            script=script,
            audio_path=audio_path,
            output_path=video_path,
            title=request.title,
            background_color=request.background_color,
            text_color=request.text_color
        )

        # 완료
        progress_store[video_id] = {
            **progress_store[video_id],
            "status": "completed",
            "step": "완료!",
            "progress": 100,
            "video_path": video_path
        }

    except Exception as e:
        progress_store[video_id] = {
            "status": "error",
            "step": f"오류 발생: {str(e)}",
            "progress": 0
        }


@router.get("/progress/{video_id}")
async def get_progress(video_id: str):
    """영상 생성 진행 상태 확인"""
    if video_id not in progress_store:
        raise HTTPException(status_code=404, detail="Video ID not found")

    return progress_store[video_id]


@router.get("/download/{video_id}")
async def download_video(video_id: str):
    """생성된 영상 다운로드"""
    if video_id not in progress_store:
        raise HTTPException(status_code=404, detail="Video ID not found")

    if progress_store[video_id]["status"] != "completed":
        raise HTTPException(status_code=400, detail="Video is not ready yet")

    video_path = progress_store[video_id].get("video_path")
    if not video_path or not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")

    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=f"youtube_video_{video_id}.mp4"
    )


@router.get("/script/{video_id}")
async def get_script(video_id: str):
    """생성된 스크립트 조회"""
    if video_id not in progress_store:
        raise HTTPException(status_code=404, detail="Video ID not found")

    script = progress_store[video_id].get("script")
    if not script:
        raise HTTPException(status_code=400, detail="Script not ready yet")

    return {"script": script}
