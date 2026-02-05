import json
import re
from typing import List, Tuple

import anthropic

from app.schemas.script import Scene, ScriptResponse


async def generate_script_with_anthropic(
    text: str,
    api_key: str,
    target_duration_minutes: int = 5
) -> ScriptResponse:
    """
    블로그 글을 유튜브 촬영용 대본으로 변환 (Anthropic Claude 사용)
    5분 분량의 장면(Scene) 단위 대본 생성

    Args:
        text: 블로그 글 내용
        api_key: Anthropic API 키
        target_duration_minutes: 목표 영상 길이 (분)

    Returns:
        ScriptResponse: 장면 단위 대본 응답
    """
    client = anthropic.Anthropic(api_key=api_key)

    # 목표 글자 수 계산 (1분당 약 400자 기준)
    target_characters = target_duration_minutes * 400

    prompt = f"""당신은 20년 차 전문의이자 100만 구독자 유튜버입니다.
의학적 전문성을 유지하되, 이웃집 아저씨처럼 친근하게 설명해야 합니다.

## 핵심 임무
아래 블로그 글을 **{target_duration_minutes}분 분량(약 {target_characters}자)**의 유튜브 촬영용 대본으로 변환하세요.

## 분량 확장 규칙 (중요!)
- 입력된 텍스트가 짧더라도 **반드시 {target_characters}자 이상**이 되도록 내용을 풍성하게 확장할 것
- 관련 의학 지식, 환자 에피소드, 일상적 비유를 추가하여 내용 확장
- 시청자가 공감할 수 있는 구체적인 상황 묘사 포함

## 대본 구조
1. **오프닝** (30초, ~200자): 강렬한 훅으로 시작. 질문 또는 놀라운 사실
2. **본론1** (~60초, ~400자): 핵심 개념 설명
3. **본론2** (~60초, ~400자): 구체적 예시와 사례
4. **본론3** (~60초, ~400자): 실천 방법 또는 주의사항
5. **클로징** (30초, ~200자): 요약 + 병원 슬로건 + CTA

## 톤 & 스타일
- **구어체**: 말하듯이 자연스럽게 (예: "~거든요", "~잖아요", "사실은요")
- **친근함**: 전문 용어는 쉽게 풀어서 설명
- **짧은 문장**: 한 문장에 하나의 아이디어

## 출력 형식 (매우 중요!)
반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요.

```json
{{
  "title": "매력적인 유튜브 영상 제목",
  "scenes": [
    {{
      "section_title": "오프닝",
      "script_korean": "안녕하세요, 여러분! 오늘은...",
      "image_prompt_english": "A friendly Korean doctor in white coat smiling at camera, modern clinic background, warm lighting, professional yet approachable atmosphere",
      "estimated_duration": 30
    }},
    {{
      "section_title": "본론1",
      "script_korean": "자, 먼저 이것부터 알아볼까요?...",
      "image_prompt_english": "Detailed medical illustration showing..., clean white background, educational style, high quality 3D render",
      "estimated_duration": 60
    }}
  ]
}}
```

## 이미지 프롬프트 작성 규칙
- 영어로 작성
- 구체적이고 묘사적으로 (카메라 앵글, 조명, 분위기 포함)
- 의료 영상에 적합한 전문적이면서도 친근한 이미지
- 예시: "A hyper-realistic close-up of a doctor's hands holding a stethoscope, warm soft lighting, blurred hospital background, professional medical photography style"

---

## 변환할 블로그 글

{text}

---

위 블로그 글을 {target_duration_minutes}분 분량의 유튜브 대본으로 변환하세요. JSON 형식으로만 응답하세요."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    response_text = message.content[0].text

    # JSON 파싱
    parsed = _parse_json_response(response_text)

    # Scene 객체 생성
    scenes = [
        Scene(
            section_title=scene["section_title"],
            script_korean=scene["script_korean"],
            image_prompt_english=scene["image_prompt_english"],
            estimated_duration=scene["estimated_duration"]
        )
        for scene in parsed["scenes"]
    ]

    # 총 시간 및 글자 수 계산
    total_duration = sum(scene.estimated_duration for scene in scenes)
    total_characters = sum(len(scene.script_korean) for scene in scenes)

    return ScriptResponse(
        title=parsed["title"],
        total_duration=total_duration,
        total_characters=total_characters,
        scenes=scenes
    )


def _parse_json_response(text: str) -> dict:
    """Claude 응답에서 JSON 추출 및 파싱"""
    # 코드 블록 안의 JSON 추출
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if json_match:
        json_str = json_match.group(1).strip()
    else:
        # 코드 블록 없이 JSON만 있는 경우
        json_str = text.strip()

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 파싱 실패: {e}\n응답: {text[:500]}")


# Legacy 함수 (기존 API 호환)
async def generate_script_legacy(text: str, api_key: str) -> Tuple[str, str]:
    """
    기존 API 호환용 - 단순 제목과 대본 반환

    Returns:
        Tuple[str, str]: (제목, 대본 내용)
    """
    response = await generate_script_with_anthropic(text, api_key)

    # Scene들을 하나의 대본으로 합침
    script_content = "\n\n".join(
        f"[{scene.section_title}]\n{scene.script_korean}"
        for scene in response.scenes
    )

    return response.title, script_content
