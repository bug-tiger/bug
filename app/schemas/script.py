from pydantic import BaseModel


class ScriptRequest(BaseModel):
    """블로그 글을 유튜브 대본으로 변환 요청"""
    text: str


class ScriptResponse(BaseModel):
    """유튜브 대본 응답"""
    title: str
    script_content: str
