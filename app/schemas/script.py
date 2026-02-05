from typing import List, Optional
from pydantic import BaseModel, Field


class ScriptRequest(BaseModel):
    """블로그 글을 유튜브 대본으로 변환 요청"""
    text: str
    target_duration_minutes: int = Field(default=5, description="목표 영상 길이 (분)")


class Scene(BaseModel):
    """영상 장면 단위 데이터"""
    section_title: str = Field(..., description="섹션 제목 (예: 오프닝, 본론1, 클로징)")
    script_korean: str = Field(..., description="실제 읽을 대본 (구어체)")
    image_prompt_english: str = Field(
        ...,
        description="AI 이미지 생성용 영문 프롬프트 (구체적이고 묘사적으로)"
    )
    estimated_duration: int = Field(..., description="예상 소요 시간 (초)")


class ScriptResponse(BaseModel):
    """유튜브 대본 응답 - 장면 단위 리스트"""
    title: str = Field(..., description="영상 제목")
    total_duration: int = Field(..., description="총 예상 시간 (초)")
    total_characters: int = Field(..., description="총 글자 수")
    scenes: List[Scene] = Field(..., description="장면 리스트")


# Legacy 호환용 (기존 API 지원)
class LegacyScriptResponse(BaseModel):
    """기존 API 호환용 응답"""
    title: str
    script_content: str
