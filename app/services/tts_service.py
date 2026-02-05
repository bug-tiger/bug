import edge_tts
import asyncio


# 사용 가능한 한국어 음성 목록
KOREAN_VOICES = {
    "ko-KR-SunHiNeural": "선희 (여성, 따뜻한 톤)",
    "ko-KR-InJoonNeural": "인준 (남성, 차분한 톤)",
    "ko-KR-BongJinNeural": "봉진 (남성)",
    "ko-KR-GookMinNeural": "국민 (남성)",
    "ko-KR-JiMinNeural": "지민 (여성)",
    "ko-KR-SeoHyeonNeural": "서현 (여성)",
    "ko-KR-SoonBokNeural": "순복 (여성, 나이든 톤)",
    "ko-KR-YuJinNeural": "유진 (여성)",
}


async def generate_audio(
    text: str,
    output_path: str,
    voice: str = "ko-KR-SunHiNeural",
    rate: str = "+0%",
    pitch: str = "+0Hz"
) -> str:
    """
    텍스트를 음성으로 변환하여 MP3 파일로 저장

    Args:
        text: 변환할 텍스트
        output_path: 출력 파일 경로
        voice: 사용할 음성 (기본: ko-KR-SunHiNeural)
        rate: 말하기 속도 (예: "+10%", "-10%")
        pitch: 음높이 (예: "+5Hz", "-5Hz")

    Returns:
        생성된 오디오 파일 경로
    """

    # 스크립트에서 섹션 마커 제거 (읽지 않도록)
    clean_text = text
    # [섹션 제목] 형식의 마커를 짧은 pause로 대체
    import re
    clean_text = re.sub(r'\[.*?\]', '...', clean_text)
    # **굵은 글씨** 마크다운 제거
    clean_text = re.sub(r'\*\*(.*?)\*\*', r'\1', clean_text)
    # 기타 마크다운 제거
    clean_text = re.sub(r'#{1,6}\s*', '', clean_text)
    clean_text = re.sub(r'\*', '', clean_text)

    communicate = edge_tts.Communicate(
        text=clean_text,
        voice=voice,
        rate=rate,
        pitch=pitch
    )

    await communicate.save(output_path)

    return output_path


async def get_audio_duration(audio_path: str) -> float:
    """오디오 파일의 길이를 초 단위로 반환"""
    from moviepy.editor import AudioFileClip

    audio = AudioFileClip(audio_path)
    duration = audio.duration
    audio.close()

    return duration


def get_available_voices() -> dict:
    """사용 가능한 음성 목록 반환"""
    return KOREAN_VOICES
