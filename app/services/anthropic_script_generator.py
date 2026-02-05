import anthropic
from typing import Tuple


async def generate_script_with_anthropic(text: str, api_key: str) -> Tuple[str, str]:
    """
    블로그 글을 유튜브 촬영용 대본으로 변환 (Anthropic Claude 사용)

    Args:
        text: 블로그 글 내용
        api_key: Anthropic API 키

    Returns:
        Tuple[str, str]: (제목, 대본 내용)
    """

    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""당신은 전문 유튜브 스크립트 작가입니다.
아래 블로그 글을 유튜브 촬영용 대본으로 변환해주세요.

## 대본 작성 규칙

### 톤 & 스타일
- **구어체**: 글을 읽는 것이 아니라 말하듯이 자연스럽게 작성
- **전문적이면서도 친근한 톤**: 정확한 정보 전달 + 시청자와 대화하는 느낌
- 짧은 문장 사용 (한 문장에 하나의 아이디어)
- 전문 용어는 쉽게 풀어서 설명

### 대본 구조 (오프닝-본론-클로징)

1. **[오프닝]** (약 30초~1분)
   - 강렬한 훅(Hook)으로 시작: 질문, 놀라운 사실, 또는 공감대 형성
   - 영상에서 다룰 내용 미리보기
   - 시청자가 끝까지 봐야 하는 이유 제시

2. **[본론]** (핵심 내용)
   - 3~5개의 섹션으로 명확하게 구분
   - 각 섹션마다 소제목 표시: [섹션 1: 제목]
   - 구체적인 예시와 비유 활용
   - 섹션 간 자연스러운 전환 멘트 포함

3. **[클로징]** (약 30초~1분)
   - 핵심 내용 요약 (3줄 정리)
   - 시청자에게 실천 가능한 액션 아이템 제안
   - 구독, 좋아요, 댓글 유도 (자연스럽게)

### 출력 형식
첫 줄에 대본 제목을 작성하고, 빈 줄 후 대본 내용을 작성해주세요.
제목은 유튜브 영상 제목으로 사용할 수 있도록 매력적이고 클릭하고 싶게 작성해주세요.

---

## 변환할 블로그 글

{text}

---

위 블로그 글을 유튜브 촬영용 대본으로 변환해주세요."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    response_text = message.content[0].text

    # 제목과 본문 분리 (첫 줄 = 제목, 나머지 = 본문)
    lines = response_text.strip().split("\n", 1)
    title = lines[0].strip().lstrip("#").strip()  # '#' 제거 (마크다운 형식일 경우)
    script_content = lines[1].strip() if len(lines) > 1 else ""

    return title, script_content
