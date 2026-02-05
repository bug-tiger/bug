import aiohttp
import asyncio
import re
import os


# ElevenLabs 한국어 음성 목록
ELEVENLABS_VOICES = {
    "Rachel": "21m00Tcm4TlvDq8ikWAM",  # 여성, 차분한 톤
    "Domi": "AZnzlk1XvdvUeBnXmlld",     # 여성, 강한 톤
    "Bella": "EXAVITQu4vr4xnSDxMaL",    # 여성, 부드러운 톤
    "Antoni": "ErXwobaYiN019PkySvjV",   # 남성, 따뜻한 톤
    "Josh": "TxGEqnHWrfWFTfGW9XjX",     # 남성, 깊은 톤
    "Arnold": "VR6AewLTigWG4xSOukaG",   # 남성, 강한 톤
    "Adam": "pNInz6obpgDQGcFmaJgB",     # 남성, 깊은 톤
    "Sam": "yoZ06aMxZJJ28mfd3POQ",      # 남성, 내레이션
}

# ElevenLabs 다국어 지원 음성 (한국어 가능)
MULTILINGUAL_VOICES = {
    "Aria": "9BWtsMINqrJLrRacOk9x",     # 여성, 다국어
    "Roger": "CwhRBWXzGAHq8TQ4Fs17",    # 남성, 다국어
    "Sarah": "EXAVITQu4vr4xnSDxMaL",    # 여성, 다국어
    "Laura": "FGY2WhTYpPnrIDTdsKH5",    # 여성, 다국어
    "Charlie": "IKne3meq5aSn9XLyUdCD",  # 남성, 다국어
    "George": "JBFqnCBsd6RMkjVDRZzb",   # 남성, 다국어
    "Callum": "N2lVS1w4EtoT3dr4eOWO",   # 남성, 다국어
    "River": "SAz9YHcvj6GT2YYXdXww",    # 논바이너리, 다국어
    "Lily": "pFZP5JQG7iQjIQuC4Bku",     # 여성, 다국어
    "Bill": "pqHfZKP75CvOlQylNhV4",     # 남성, 다국어
}


async def generate_audio(
    text: str,
    output_path: str,
    voice: str = "Lily",
    api_key: str = None,
    model_id: str = "eleven_multilingual_v2"
) -> str:
    """
    ElevenLabs API를 사용하여 텍스트를 음성으로 변환

    Args:
        text: 변환할 텍스트
        output_path: 출력 파일 경로
        voice: 사용할 음성 이름 또는 voice_id
        api_key: ElevenLabs API 키
        model_id: 사용할 모델 (eleven_multilingual_v2 권장)

    Returns:
        생성된 오디오 파일 경로
    """

    api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise ValueError("ElevenLabs API 키가 필요합니다.")

    # 텍스트 정리
    clean_text = _clean_script_for_tts(text)

    # voice_id 결정
    voice_id = MULTILINGUAL_VOICES.get(voice) or ELEVENLABS_VOICES.get(voice) or voice

    # API 호출
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }

    data = {
        "text": clean_text,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True
        }
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"ElevenLabs API 오류: {response.status} - {error_text}")

            audio_content = await response.read()

            with open(output_path, 'wb') as f:
                f.write(audio_content)

    return output_path


def _clean_script_for_tts(text: str) -> str:
    """TTS용 텍스트 정리"""
    clean_text = text

    # [섹션 제목] 형식의 마커를 짧은 pause로 대체
    clean_text = re.sub(r'\[.*?\]', '... ', clean_text)

    # **굵은 글씨** 마크다운 제거
    clean_text = re.sub(r'\*\*(.*?)\*\*', r'\1', clean_text)

    # 기타 마크다운 제거
    clean_text = re.sub(r'#{1,6}\s*', '', clean_text)
    clean_text = re.sub(r'\*', '', clean_text)

    # 여러 줄바꿈을 하나로
    clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)

    # 너무 긴 텍스트 경고 (ElevenLabs 제한: 약 5000자)
    if len(clean_text) > 5000:
        print(f"경고: 텍스트가 {len(clean_text)}자입니다. 긴 텍스트는 청크로 나눕니다.")

    return clean_text


async def generate_audio_chunked(
    text: str,
    output_path: str,
    voice: str = "Lily",
    api_key: str = None,
    chunk_size: int = 4500
) -> str:
    """
    긴 텍스트를 청크로 나누어 음성 생성 후 합치기
    10분 영상용 긴 스크립트에 적합
    """
    from pydub import AudioSegment
    import tempfile

    api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
    clean_text = _clean_script_for_tts(text)

    # 텍스트를 문장 단위로 청크 분할
    chunks = _split_text_into_chunks(clean_text, chunk_size)

    if len(chunks) == 1:
        # 청크가 하나면 그냥 생성
        return await generate_audio(text, output_path, voice, api_key)

    # 여러 청크 처리
    audio_segments = []
    temp_files = []

    for i, chunk in enumerate(chunks):
        temp_path = f"{output_path}.chunk_{i}.mp3"
        temp_files.append(temp_path)

        await generate_audio(chunk, temp_path, voice, api_key)
        audio_segments.append(AudioSegment.from_mp3(temp_path))

        # API 레이트 리밋 방지
        await asyncio.sleep(0.5)

    # 오디오 합치기
    combined = audio_segments[0]
    for segment in audio_segments[1:]:
        combined += segment

    combined.export(output_path, format="mp3")

    # 임시 파일 삭제
    for temp_file in temp_files:
        if os.path.exists(temp_file):
            os.remove(temp_file)

    return output_path


def _split_text_into_chunks(text: str, max_chars: int = 4500) -> list:
    """텍스트를 문장 단위로 청크 분할"""
    sentences = re.split(r'(?<=[.!?])\s+', text)

    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) < max_chars:
            current_chunk += sentence + " "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + " "

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


async def get_audio_duration(audio_path: str) -> float:
    """오디오 파일의 길이를 초 단위로 반환"""
    from moviepy.editor import AudioFileClip

    audio = AudioFileClip(audio_path)
    duration = audio.duration
    audio.close()

    return duration


def get_available_voices() -> dict:
    """사용 가능한 음성 목록 반환"""
    return {**MULTILINGUAL_VOICES, **ELEVENLABS_VOICES}
