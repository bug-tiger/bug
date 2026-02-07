"""
Asset Kit 생성 API

Vrew, CapCut 등에서 편집 가능한 영상 소스 패키지 생성
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List
import os
import uuid
import zipfile
import shutil

from app.services.asset_generator import AssetKitGenerator

router = APIRouter()


# ============================================================
# Pydantic 모델
# ============================================================

class AssetKitRequest(BaseModel):
    """Asset Kit 생성 요청"""
    text: str = Field(..., description="블로그 글 텍스트")
    project_name: str = Field(default="project", description="프로젝트 이름")


class AssetKitResponse(BaseModel):
    """Asset Kit 생성 응답"""
    status: str
    message: str
    job_id: Optional[str] = None


class AssetKitProgress(BaseModel):
    """진행 상황"""
    status: str  # pending, processing, completed, error
    step: str
    progress: int  # 0-100
    output_dir: Optional[str] = None
    files: Optional[dict] = None
    error: Optional[str] = None


# ============================================================
# 진행 상황 저장소
# ============================================================

progress_store: dict = {}


# ============================================================
# API 엔드포인트
# ============================================================

@router.post("/generate-assets", response_model=AssetKitResponse)
async def generate_assets(request: AssetKitRequest, background_tasks: BackgroundTasks):
    """
    Asset Kit 생성 시작

    블로그 글을 입력받아 문장별 이미지와 오디오를 생성합니다.
    백그라운드에서 처리되며, /assets/progress/{job_id}로 진행 상황을 확인할 수 있습니다.
    """
    job_id = str(uuid.uuid4())[:8]

    progress_store[job_id] = {
        "status": "pending",
        "step": "대기 중...",
        "progress": 0
    }

    # 백그라운드에서 생성 시작
    background_tasks.add_task(
        process_asset_generation,
        job_id,
        request.text,
        request.project_name
    )

    return AssetKitResponse(
        status="processing",
        message="Asset Kit 생성을 시작했습니다.",
        job_id=job_id
    )


async def process_asset_generation(job_id: str, text: str, project_name: str):
    """백그라운드에서 Asset Kit 생성"""

    def progress_callback(message: str, percentage: int):
        progress_store[job_id] = {
            "status": "processing",
            "step": message,
            "progress": percentage
        }

    try:
        generator = AssetKitGenerator()
        result = await generator.generate_asset_kit(
            text=text,
            project_name=project_name,
            progress_callback=progress_callback
        )

        progress_store[job_id] = {
            "status": "completed",
            "step": "Asset Kit 생성 완료!",
            "progress": 100,
            "output_dir": result["output_dir"],
            "files": result["files"]
        }

    except Exception as e:
        import traceback
        error_detail = str(e)
        print(f"Asset Kit 생성 오류: {error_detail}")
        print(traceback.format_exc())

        progress_store[job_id] = {
            "status": "error",
            "step": f"오류 발생: {error_detail[:200]}",
            "progress": 0,
            "error": error_detail
        }


@router.get("/assets/progress/{job_id}")
async def get_progress(job_id: str):
    """Asset Kit 생성 진행 상황 확인"""
    if job_id not in progress_store:
        raise HTTPException(status_code=404, detail="Job ID not found")

    return progress_store[job_id]


@router.get("/assets/download/{job_id}")
async def download_assets(job_id: str):
    """
    생성된 Asset Kit 다운로드 (ZIP 파일)
    """
    if job_id not in progress_store:
        raise HTTPException(status_code=404, detail="Job ID not found")

    job = progress_store[job_id]

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Asset Kit is not ready yet")

    output_dir = job.get("output_dir")
    if not output_dir or not os.path.exists(output_dir):
        raise HTTPException(status_code=404, detail="Output directory not found")

    # ZIP 파일 생성
    zip_path = f"{output_dir}.zip"

    if not os.path.exists(zip_path):
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(output_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, output_dir)
                    zipf.write(file_path, arcname)

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=os.path.basename(zip_path)
    )


@router.get("/assets/files/{job_id}")
async def list_files(job_id: str):
    """생성된 파일 목록 조회"""
    if job_id not in progress_store:
        raise HTTPException(status_code=404, detail="Job ID not found")

    job = progress_store[job_id]

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Asset Kit is not ready yet")

    output_dir = job.get("output_dir")
    if not output_dir or not os.path.exists(output_dir):
        raise HTTPException(status_code=404, detail="Output directory not found")

    # 파일 목록 생성
    files = []
    for filename in sorted(os.listdir(output_dir)):
        file_path = os.path.join(output_dir, filename)
        if os.path.isfile(file_path):
            files.append({
                "name": filename,
                "size": os.path.getsize(file_path),
                "path": file_path
            })

    return {
        "output_dir": output_dir,
        "files": files,
        "total": len(files)
    }
