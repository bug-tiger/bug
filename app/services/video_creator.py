import asyncio
import textwrap
import re
import os
from moviepy.editor import (
    AudioFileClip,
    ColorClip,
    ImageClip,
    CompositeVideoClip,
    concatenate_videoclips,
    vfx
)
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np


def create_text_image(
    text: str,
    fontsize: int = 40,
    color: str = "#ffffff",
    bg_color: tuple = None,
    size: tuple = None,
    align: str = "center"
) -> np.ndarray:
    """PIL을 사용하여 텍스트 이미지 생성 (ImageMagick 불필요)"""

    # 색상 파싱
    if isinstance(color, str):
        color = color.lstrip('#')
        text_color = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
    else:
        text_color = color

    # 폰트 설정 (시스템 기본 폰트 사용)
    try:
        # Windows 한글 폰트
        font = ImageFont.truetype("malgun.ttf", fontsize)
    except:
        try:
            # macOS/Linux
            font = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", fontsize)
        except:
            try:
                font = ImageFont.truetype("NanumGothic.ttf", fontsize)
            except:
                # 기본 폰트
                font = ImageFont.load_default()

    # 텍스트 크기 계산
    dummy_img = Image.new('RGBA', (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_img)

    # 멀티라인 텍스트 크기 계산
    lines = text.split('\n')
    line_heights = []
    line_widths = []

    for line in lines:
        bbox = dummy_draw.textbbox((0, 0), line, font=font)
        line_widths.append(bbox[2] - bbox[0])
        line_heights.append(bbox[3] - bbox[1])

    text_width = max(line_widths) if line_widths else 100
    line_height = max(line_heights) if line_heights else fontsize
    text_height = line_height * len(lines) + (len(lines) - 1) * 5  # 줄 간격

    # 패딩 추가
    padding = 20
    img_width = size[0] if size else text_width + padding * 2
    img_height = text_height + padding * 2

    # 이미지 생성 (투명 배경)
    if bg_color:
        img = Image.new('RGBA', (img_width, img_height), (*bg_color, 255))
    else:
        img = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))

    draw = ImageDraw.Draw(img)

    # 텍스트 그리기
    y_offset = padding
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]

        if align == "center":
            x = (img_width - line_width) // 2
        elif align == "right":
            x = img_width - line_width - padding
        else:
            x = padding

        draw.text((x, y_offset), line, font=font, fill=(*text_color, 255))
        y_offset += line_height + 5

    return np.array(img)


def create_text_clip(
    text: str,
    fontsize: int = 40,
    color: str = "#ffffff",
    size: tuple = None,
    align: str = "center",
    duration: float = 1.0
) -> ImageClip:
    """PIL 기반 텍스트 클립 생성"""
    text_img = create_text_image(text, fontsize, color, size=size, align=align)
    clip = ImageClip(text_img, ismask=False).set_duration(duration)
    return clip


async def create_video(
    script: str,
    audio_path: str,
    output_path: str,
    title: str = "YouTube Video",
    background_color: str = "#1a1a2e",
    text_color: str = "#ffffff",
    resolution: tuple = (1920, 1080),
    broll_images: list = None
) -> str:
    """
    스크립트와 오디오를 합성하여 동영상 생성 (개선 버전)

    Args:
        script: 영상 스크립트
        audio_path: 오디오 파일 경로
        output_path: 출력 영상 경로
        title: 영상 제목
        background_color: 배경색 (hex)
        text_color: 텍스트 색상 (hex)
        resolution: 영상 해상도
        broll_images: B-roll 이미지 경로 리스트

    Returns:
        생성된 영상 파일 경로
    """

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        _create_video_enhanced,
        script, audio_path, output_path, title,
        background_color, text_color, resolution, broll_images
    )

    return output_path


def _create_video_enhanced(
    script: str,
    audio_path: str,
    output_path: str,
    title: str,
    background_color: str,
    text_color: str,
    resolution: tuple,
    broll_images: list
):
    """개선된 영상 생성"""

    # 오디오 로드
    audio = AudioFileClip(audio_path)
    duration = audio.duration

    # 색상 파싱
    bg_color = hex_to_rgb(background_color)
    accent_color = get_accent_color(bg_color)

    # 스크립트 섹션 파싱
    sections = parse_script_sections(script)
    if not sections:
        sections = [{"title": title, "content": script}]

    # B-roll 이미지 준비
    if broll_images is None:
        broll_images = []

    # 각 섹션 클립 생성
    section_duration = duration / len(sections)
    clips = []

    for i, section in enumerate(sections):
        # 해당 섹션에 사용할 B-roll 이미지
        section_image = None
        if broll_images and i < len(broll_images):
            img_info = broll_images[i]
            if isinstance(img_info, dict):
                section_image = img_info.get("path")
            else:
                section_image = img_info

        clip = create_enhanced_section_clip(
            section_title=section.get("title", ""),
            section_content=section.get("content", ""),
            duration=section_duration,
            resolution=resolution,
            bg_color=bg_color,
            text_color=text_color,
            accent_color=accent_color,
            section_number=i + 1,
            total_sections=len(sections),
            total_duration=duration,
            start_time=i * section_duration,
            broll_image=section_image
        )
        clips.append(clip)

    # 모든 클립 연결
    final_video = concatenate_videoclips(clips, method="compose")

    # 오디오 추가
    final_video = final_video.set_audio(audio)

    # 영상 저장
    final_video.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile="temp-audio.m4a",
        remove_temp=True,
        threads=4,
        preset="medium",
        bitrate="8000k"
    )

    # 리소스 정리
    audio.close()
    final_video.close()


def create_enhanced_section_clip(
    section_title: str,
    section_content: str,
    duration: float,
    resolution: tuple,
    bg_color: tuple,
    text_color: str,
    accent_color: tuple,
    section_number: int,
    total_sections: int,
    total_duration: float,
    start_time: float,
    broll_image: str = None
) -> CompositeVideoClip:
    """개선된 섹션 클립 생성"""

    width, height = resolution
    clips = []

    # 1. 배경 (B-roll 이미지 또는 그라데이션)
    if broll_image and os.path.exists(broll_image):
        # B-roll 이미지를 배경으로 사용 (어둡게 처리)
        bg_clip = create_image_background(broll_image, resolution, duration)
    else:
        # 그라데이션 배경
        bg_clip = create_gradient_background(bg_color, resolution, duration)

    clips.append(bg_clip)

    # 2. 반투명 오버레이 (텍스트 가독성 향상)
    overlay = ColorClip(
        size=resolution,
        color=(0, 0, 0)
    ).set_opacity(0.5).set_duration(duration)
    clips.append(overlay)

    # 3. 상단 진행 바
    progress_bar = create_progress_bar(
        width=width,
        height=6,
        progress=(start_time + duration) / total_duration,
        accent_color=accent_color,
        duration=duration
    )
    progress_bar = progress_bar.set_position(("center", 0))
    clips.append(progress_bar)

    # 4. 섹션 제목 (상단)
    if section_title:
        # 제목 배경 박스
        title_bg = ColorClip(
            size=(width - 100, 80),
            color=accent_color
        ).set_opacity(0.9).set_duration(duration)
        title_bg = title_bg.set_position(("center", 60))
        clips.append(title_bg)

        # 제목 텍스트
        title_clip = TextClip(
            section_title,
            fontsize=48,
            color="#ffffff",
            font="NanumGothic-Bold",
            size=(width - 150, None),
            method="caption"
        ).set_position(("center", 75)).set_duration(duration)
        clips.append(title_clip)

    # 5. 본문 자막 (중앙 하단)
    if section_content:
        # 자막 배경 박스
        subtitle_bg = ColorClip(
            size=(width - 200, 250),
            color=(0, 0, 0)
        ).set_opacity(0.7).set_duration(duration)
        subtitle_bg = subtitle_bg.set_position(("center", height - 320))
        clips.append(subtitle_bg)

        # 자막 텍스트
        wrapped_content = wrap_text(section_content, max_chars=45, max_lines=4)
        content_clip = TextClip(
            wrapped_content,
            fontsize=38,
            color="#ffffff",
            font="NanumGothic",
            size=(width - 250, None),
            method="caption",
            align="center"
        ).set_position(("center", height - 300)).set_duration(duration)
        clips.append(content_clip)

    # 6. 섹션 번호 표시 (좌측 상단)
    section_indicator = TextClip(
        f"{section_number}/{total_sections}",
        fontsize=28,
        color="#888888",
        font="NanumGothic"
    ).set_position((50, 30)).set_duration(duration)
    clips.append(section_indicator)

    # 7. 타임스탬프 (우측 상단)
    time_text = format_time(start_time)
    timestamp = TextClip(
        time_text,
        fontsize=28,
        color="#888888",
        font="NanumGothic"
    ).set_position((width - 120, 30)).set_duration(duration)
    clips.append(timestamp)

    return CompositeVideoClip(clips, size=resolution)


def create_gradient_background(bg_color: tuple, resolution: tuple, duration: float) -> ColorClip:
    """그라데이션 배경 생성"""
    width, height = resolution

    # PIL로 그라데이션 이미지 생성
    gradient = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(gradient)

    # 상단에서 하단으로 어두워지는 그라데이션
    for y in range(height):
        ratio = y / height
        r = int(bg_color[0] * (1 - ratio * 0.3))
        g = int(bg_color[1] * (1 - ratio * 0.3))
        b = int(bg_color[2] * (1 - ratio * 0.3))
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # numpy 배열로 변환
    gradient_array = np.array(gradient)

    # ImageClip 생성
    clip = ImageClip(gradient_array).set_duration(duration)

    return clip


def create_image_background(image_path: str, resolution: tuple, duration: float) -> ImageClip:
    """B-roll 이미지를 배경으로 사용"""
    width, height = resolution

    try:
        # 이미지 로드 및 리사이즈
        img = Image.open(image_path)
        img = img.convert('RGB')

        # 화면에 맞게 크롭/리사이즈
        img_ratio = img.width / img.height
        target_ratio = width / height

        if img_ratio > target_ratio:
            # 이미지가 더 넓음 - 높이 기준으로 리사이즈
            new_height = height
            new_width = int(height * img_ratio)
        else:
            # 이미지가 더 높음 - 너비 기준으로 리사이즈
            new_width = width
            new_height = int(width / img_ratio)

        img = img.resize((new_width, new_height), Image.LANCZOS)

        # 중앙 크롭
        left = (new_width - width) // 2
        top = (new_height - height) // 2
        img = img.crop((left, top, left + width, top + height))

        # 약간 블러 처리 (텍스트 가독성)
        img = img.filter(ImageFilter.GaussianBlur(radius=2))

        # numpy 배열로 변환
        img_array = np.array(img)

        return ImageClip(img_array).set_duration(duration)

    except Exception as e:
        print(f"이미지 로드 오류: {e}")
        # 기본 배경 반환
        return ColorClip(size=resolution, color=(26, 26, 46), duration=duration)


def create_progress_bar(
    width: int,
    height: int,
    progress: float,
    accent_color: tuple,
    duration: float
) -> CompositeVideoClip:
    """진행 바 생성"""

    # 배경 바
    bg_bar = ColorClip(
        size=(width, height),
        color=(50, 50, 50)
    ).set_duration(duration)

    # 진행 바
    progress_width = int(width * min(progress, 1.0))
    if progress_width > 0:
        progress_bar = ColorClip(
            size=(progress_width, height),
            color=accent_color
        ).set_duration(duration).set_position((0, 0))

        return CompositeVideoClip([bg_bar, progress_bar], size=(width, height))

    return bg_bar


def parse_script_sections(script: str) -> list:
    """스크립트를 섹션별로 파싱"""
    sections = []

    # [섹션 제목] 패턴으로 분리
    pattern = r'\[([^\]]+)\]'
    parts = re.split(pattern, script)

    if len(parts) <= 1:
        # 섹션 마커가 없으면 문단으로 분리
        paragraphs = [p.strip() for p in script.split('\n\n') if p.strip()]
        for para in paragraphs[:15]:  # 최대 15개 섹션
            sections.append({
                "title": "",
                "content": para[:400]
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
                    "content": part[:400]
                })
                current_title = ""

    return sections


def wrap_text(text: str, max_chars: int = 45, max_lines: int = 4) -> str:
    """텍스트를 적절한 길이로 줄바꿈"""
    text = ' '.join(text.split())
    lines = textwrap.wrap(text, width=max_chars)

    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][:max_chars-3] + "..."

    return '\n'.join(lines)


def hex_to_rgb(hex_color: str) -> tuple:
    """HEX 색상을 RGB 튜플로 변환"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def get_accent_color(bg_color: tuple) -> tuple:
    """배경색에 맞는 강조색 생성"""
    # 배경이 어두우면 밝은 강조색
    brightness = sum(bg_color) / 3
    if brightness < 128:
        return (66, 133, 244)  # 구글 블루
    else:
        return (219, 68, 55)   # 구글 레드


def format_time(seconds: float) -> str:
    """초를 MM:SS 형식으로 변환"""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"
