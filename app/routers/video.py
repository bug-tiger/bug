from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import uuid
import os

from app.services.script_generator import generate_script
from app.services.tts_service import generate_audio_chunked
from app.services.video_creator import create_video
from app.services.image_service import get_images_for_script

router = APIRouter()


class BlogToVideoRequest(BaseModel):
    blog_content: str
    title: Optional[str] = "YouTube Video"
    voice: Optional[str] = "Lily"  # ElevenLabs 음성
    background_color: Optional[str] = "#1a1a2e"
    text_color: Optional[str] = "#ffffff"
    gemini_api_key: Optional[str] = None
    elevenlabs_api_key: Optional[str] = None
    pexels_api_key: Optional[str] = None
    use_broll: Optional[bool] = True  # B-roll 이미지 사용 여부


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
        # Step 1: 스크립트 생성 (10%)
        progress_store[video_id] = {
            "status": "processing",
            "step": "AI 스크립트 생성 중...",
            "progress": 10
        }

        gemini_key = request.gemini_api_key or os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            progress_store[video_id] = {
                "status": "error",
                "step": "Gemini API 키가 필요합니다.",
                "progress": 0
            }
            return

        script = await generate_script(request.blog_content, request.title, gemini_key)
        progress_store[video_id]["script"] = script

        # Step 2: B-roll 이미지 다운로드 (25%)
        broll_images = []
        if request.use_broll:
            progress_store[video_id] = {
                **progress_store[video_id],
                "status": "processing",
                "step": "배경 이미지 다운로드 중...",
                "progress": 25
            }

            pexels_key = request.pexels_api_key or os.getenv("PEXELS_API_KEY")
            if pexels_key:
                broll_images = await get_images_for_script(
                    script=script,
                    title=request.title,
                    api_key=pexels_key,
                    output_dir="output",
                    images_per_section=1
                )

        # Step 3: TTS 음성 생성 (50%)
        progress_store[video_id] = {
            **progress_store[video_id],
            "status": "processing",
            "step": "ElevenLabs 음성 생성 중... (10분 분량)",
            "progress": 40
        }

        elevenlabs_key = request.elevenlabs_api_key or os.getenv("ELEVENLABS_API_KEY")
        if not elevenlabs_key:
            progress_store[video_id] = {
                "status": "error",
                "step": "ElevenLabs API 키가 필요합니다.",
                "progress": 0
            }
            return

        audio_path = f"output/{video_id}_audio.mp3"
        await generate_audio_chunked(
            text=script,
            output_path=audio_path,
            voice=request.voice,
            api_key=elevenlabs_key
        )

        progress_store[video_id] = {
            **progress_store[video_id],
            "status": "processing",
            "step": "음성 생성 완료!",
            "progress": 60
        }

        # Step 4: 영상 합성 (80%)
        progress_store[video_id] = {
            **progress_store[video_id],
            "status": "processing",
            "step": "영상 합성 중... (시간이 걸릴 수 있습니다)",
            "progress": 70
        }

        video_path = f"output/{video_id}_video.mp4"
        await create_video(
            script=script,
            audio_path=audio_path,
            output_path=video_path,
            title=request.title,
            background_color=request.background_color,
            text_color=request.text_color,
            broll_images=broll_images
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
        import traceback
        error_detail = str(e)
        print(f"영상 생성 오류: {error_detail}")
        print(traceback.format_exc())

        progress_store[video_id] = {
            "status": "error",
            "step": f"오류 발생: {error_detail[:200]}",
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


@router.get("/voices")
async def get_voices():
    """사용 가능한 ElevenLabs 음성 목록"""
    return {
        "multilingual": {
            "Lily": "여성, 다국어 (추천)",
            "Aria": "여성, 다국어",
            "Roger": "남성, 다국어",
            "Laura": "여성, 다국어",
            "Charlie": "남성, 다국어",
            "George": "남성, 다국어",
            "River": "중성, 다국어",
            "Bill": "남성, 다국어",
        },
        "english": {
            "Rachel": "여성, 차분한 톤",
            "Domi": "여성, 강한 톤",
            "Bella": "여성, 부드러운 톤",
            "Antoni": "남성, 따뜻한 톤",
            "Josh": "남성, 깊은 톤",
            "Sam": "남성, 내레이션",
        }
    }
