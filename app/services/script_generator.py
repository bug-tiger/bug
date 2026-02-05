import google.generativeai as genai


async def generate_script(blog_content: str, title: str, api_key: str) -> str:
    """
    블로그 글을 유튜브 동영상 스크립트로 변환 (Google Gemini 사용)
    10분 분량 (약 1,500-2,000 단어)의 스크립트 생성
    """

    # Gemini API 설정
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        generation_config={
            "temperature": 0.7,
            "max_output_tokens": 4000,
        }
    )

    prompt = f"""당신은 전문 유튜브 스크립트 작가입니다.
블로그 글을 10분 분량의 유튜브 동영상 스크립트로 변환해주세요.

다음 구조를 따라주세요:

1. **훅 (Hook)** - 처음 10초: 시청자의 관심을 끄는 강렬한 오프닝
2. **인트로** - 30초: 영상 주제 소개 및 시청자가 얻을 가치 설명
3. **본문** - 8분: 핵심 내용을 3-5개 섹션으로 나누어 설명
   - 각 섹션은 명확한 전환으로 구분
   - 구체적인 예시와 설명 포함
   - 시청자와 대화하듯 자연스러운 톤
4. **요약** - 30초: 핵심 포인트 정리
5. **CTA (Call to Action)** - 30초: 구독, 좋아요, 댓글 유도

작성 규칙:
- 구어체로 작성 (말하듯이)
- 짧은 문장 사용
- 전문 용어는 쉽게 풀어서 설명
- 감정을 담아 표현
- [섹션 제목]으로 섹션 구분
- 약 1,500-2,000 단어로 작성 (한국어 기준)

---

다음 블로그 글을 유튜브 동영상 스크립트로 변환해주세요.

제목: {title}

블로그 내용:
{blog_content}

위 내용을 바탕으로 10분 분량의 유튜브 스크립트를 작성해주세요.
시청자가 끝까지 볼 수 있도록 흥미롭고 유익하게 만들어주세요."""

    response = await model.generate_content_async(prompt)

    return response.text
