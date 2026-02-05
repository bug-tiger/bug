from fastapi import APIRouter, HTTPException

from app.schemas.script import ScriptRequest, ScriptResponse
from app.services.anthropic_script_generator import generate_script_with_anthropic
from app.services.naver_crawler import crawl_naver_blog
from app.core.config import settings

router = APIRouter()


@router.post("/generate-script", response_model=ScriptResponse)
async def generate_script(request: ScriptRequest):
    """
    블로그 글을 유튜브 촬영용 대본으로 변환 (장면 단위)

    - **text**: 변환할 블로그 글 내용
    - **target_duration_minutes**: 목표 영상 길이 (분, 기본값: 5)

    Returns:
        장면(Scene) 단위로 구분된 대본과 이미지 프롬프트
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
        response = await generate_script_with_anthropic(
            text=request.text,
            api_key=api_key,
            target_duration_minutes=request.target_duration_minutes
        )
        return response

    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=f"대본 생성 결과 파싱 실패: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"대본 생성 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/crawl-blog")
async def crawl_blog(url: str):
    """
    네이버 블로그 URL에서 제목과 본문 추출

    - **url**: 네이버 블로그 URL
    """
    try:
        title, content = await crawl_naver_blog(url)
        return {
            "title": title,
            "content": content,
            "character_count": len(content)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"블로그 크롤링 중 오류가 발생했습니다: {str(e)}"
        )
