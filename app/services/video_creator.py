import asyncio
import textwrap
import re
from moviepy.editor import (
    AudioFileClip,
    ColorClip,
    TextClip,
    CompositeVideoClip,
    concatenate_videoclips
)
from PIL import Image, ImageDraw, ImageFont
import numpy as np


async def create_video(
    script: str,
    audio_path: str,
    output_path: str,
    title: str = "YouTube Video",
    background_color: str = "#1a1a2e",
    text_color: str = "#ffffff",
    resolution: tuple = (1920, 1080)
) -> str:
    """
    스크립트와 오디오를 합성하여 동영상 생성

    Args:
        script: 영상 스크립트
        audio_path: 오디오 파일 경로
        output_path: 출력 영상 경로
        title: 영상 제목
        background_color: 배경색 (hex)
        text_color: 텍스트 색상 (hex)
        resolution: 영상 해상도

    Returns:
        생성된 영상 파일 경로
    """

    # asyncio에서 동기 함수 실행
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        _create_video_sync,
        script, audio_path, output_path, title,
        background_color, text_color, resolution
    )

    return output_path


def _create_video_sync(
    script: str,
    audio_path: str,
    output_path: str,
    title: str,
    background_color: str,
    text_color: str,
    resolution: tuple
):
    """동기 방식으로 영상 생성"""

    # 오디오 로드
    audio = AudioFileClip(audio_path)
    duration = audio.duration

    # 배경색 파싱
    bg_color = hex_to_rgb(background_color)
    txt_color = text_color

    # 스크립트를 섹션별로 분리
    sections = parse_script_sections(script)

    if not sections:
        sections = [{"title": title, "content": script}]

    # 각 섹션의 표시 시간 계산
    section_duration = duration / len(sections)

    clips = []

    for i, section in enumerate(sections):
        start_time = i * section_duration
        end_time = (i + 1) * section_duration
        clip_duration = end_time - start_time

        # 섹션 클립 생성
        section_clip = create_section_clip(
            section_title=section.get("title", ""),
            section_content=section.get("content", ""),
            duration=clip_duration,
            resolution=resolution,
            bg_color=bg_color,
            text_color=txt_color,
            section_number=i + 1,
            total_sections=len(sections)
        )

        clips.append(section_clip)

    # 모든 클립 연결
    final_video = concatenate_videoclips(clips, method="compose")

    # 오디오 추가
    final_video = final_video.set_audio(audio)

    # 영상 저장
    final_video.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile="temp-audio.m4a",
        remove_temp=True,
        threads=4,
        preset="medium"
    )

    # 리소스 정리
    audio.close()
    final_video.close()


def create_section_clip(
    section_title: str,
    section_content: str,
    duration: float,
    resolution: tuple,
    bg_color: tuple,
    text_color: str,
    section_number: int,
    total_sections: int
) -> CompositeVideoClip:
    """섹션별 클립 생성"""

    width, height = resolution

    # 배경 클립
    background = ColorClip(size=resolution, color=bg_color, duration=duration)

    clips = [background]

    # 제목이 있으면 상단에 표시
    if section_title:
        title_clip = TextClip(
            section_title,
            fontsize=60,
            color=text_color,
            font="NanumGothic-Bold",
            size=(width - 200, None),
            method="caption"
        ).set_position(("center", 100)).set_duration(duration)
        clips.append(title_clip)

    # 본문 내용 (줄바꿈 처리)
    if section_content:
        # 긴 텍스트를 적절히 자르기
        wrapped_content = wrap_text(section_content, max_chars=50, max_lines=12)

        content_clip = TextClip(
            wrapped_content,
            fontsize=40,
            color=text_color,
            font="NanumGothic",
            size=(width - 200, None),
            method="caption",
            align="center"
        ).set_position(("center", "center")).set_duration(duration)
        clips.append(content_clip)

    # 진행 표시 (하단)
    progress_text = f"{section_number} / {total_sections}"
    progress_clip = TextClip(
        progress_text,
        fontsize=30,
        color="#888888",
        font="NanumGothic"
    ).set_position(("center", height - 80)).set_duration(duration)
    clips.append(progress_clip)

    return CompositeVideoClip(clips, size=resolution)


def parse_script_sections(script: str) -> list:
    """스크립트를 섹션별로 파싱"""

    sections = []

    # [섹션 제목] 패턴으로 분리
    pattern = r'\[([^\]]+)\]'
    parts = re.split(pattern, script)

    if len(parts) <= 1:
        # 섹션 마커가 없으면 문단으로 분리
        paragraphs = [p.strip() for p in script.split('\n\n') if p.strip()]
        for i, para in enumerate(paragraphs[:10]):  # 최대 10개 섹션
            sections.append({
                "title": "",
                "content": para[:500]  # 최대 500자
            })
        return sections

    current_title = ""
    for i, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue

        if i % 2 == 1:  # 섹션 제목
            current_title = part
        else:  # 섹션 내용
            if current_title or part:
                sections.append({
                    "title": current_title,
                    "content": part[:500]
                })
                current_title = ""

    return sections


def wrap_text(text: str, max_chars: int = 50, max_lines: int = 12) -> str:
    """텍스트를 적절한 길이로 줄바꿈"""

    # 불필요한 공백 제거
    text = ' '.join(text.split())

    # 줄바꿈
    lines = textwrap.wrap(text, width=max_chars)

    # 최대 줄 수 제한
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][:max_chars-3] + "..."

    return '\n'.join(lines)


def hex_to_rgb(hex_color: str) -> tuple:
    """HEX 색상을 RGB 튜플로 변환"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
