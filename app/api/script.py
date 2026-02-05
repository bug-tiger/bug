from fastapi import APIRouter, HTTPException

from app.schemas.script import ScriptRequest, ScriptResponse
from app.services.anthropic_script_generator import generate_script_with_anthropic
from app.core.config import settings

router = APIRouter()


@router.post("/generate-script", response_model=ScriptResponse)
async def generate_script(request: ScriptRequest):
    """
    블로그 글을 유튜브 촬영용 대본으로 변환

    - **text**: 변환할 블로그 글 내용
    """
    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="ANTHROPIC_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요."
        )

    if not request.text.strip():
        raise HTTPException(
            status_code=400,
            detail="변환할 텍스트를 입력해주세요."
        )

    try:
        title, script_content = await generate_script_with_anthropic(
            text=request.text,
            api_key=api_key
        )

        return ScriptResponse(
            title=title,
            script_content=script_content
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"대본 생성 중 오류가 발생했습니다: {str(e)}"
        )
