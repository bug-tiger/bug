"""
비디오 어셈블리 엔진 - MoviePy 기반 영상 생성

이미지, 오디오, 자막을 합쳐서 최종 MP4 영상을 생성합니다.
"""

import os
from dataclasses import dataclass
from typing import List, Optional, Callable

from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    concatenate_videoclips,
    CompositeVideoClip,
    vfx
)
import numpy as np


@dataclass
class SceneAsset:
    """장면 자산 데이터"""
    image_path: str
    audio_path: str
    subtitle_text: Optional[str] = None
    section_title: Optional[str] = None


class VideoAssembler:
    """
    비디오 조립기 - 이미지와 오디오를 합쳐 영상 생성

    사용 예시:
    ```python
    assembler = VideoAssembler()
    assembler.add_scene(SceneAsset(
        image_path="output/images/scene_00.png",
        audio_path="output/audio/scene_00.mp3",
        subtitle_text="안녕하세요, 여러분!"
    ))
    assembler.render("output/final_video.mp4")
    ```
    """

    # 기본 설정
    DEFAULT_WIDTH = 1920
    DEFAULT_HEIGHT = 1080
    DEFAULT_FPS = 24

    def __init__(
        self,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        fps: int = DEFAULT_FPS
    ):
        self.width = width
        self.height = height
        self.fps = fps
        self.scenes: List[SceneAsset] = []

    def add_scene(self, scene: SceneAsset):
        """장면 추가"""
        self.scenes.append(scene)

    def add_scenes(self, scenes: List[SceneAsset]):
        """여러 장면 일괄 추가"""
        self.scenes.extend(scenes)

    def render(
        self,
        output_path: str,
        apply_zoom_effect: bool = True,
        zoom_ratio: float = 0.04,
        codec: str = "libx264",
        audio_codec: str = "aac",
        threads: int = 4,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> str:
        """
        모든 장면을 합쳐서 최종 영상 렌더링

        Args:
            output_path: 출력 파일 경로 (예: output/video.mp4)
            apply_zoom_effect: 줌인 효과 적용 여부
            zoom_ratio: 줌인 비율 (기본 4%, 클수록 더 많이 줌)
            codec: 비디오 코덱 (기본 H.264)
            audio_codec: 오디오 코덱 (기본 AAC)
            threads: 렌더링 스레드 수
            progress_callback: 진행률 콜백 함수 (0.0 ~ 1.0)

        Returns:
            str: 생성된 영상 파일 경로
        """
        if not self.scenes:
            raise ValueError("렌더링할 장면이 없습니다. add_scene()으로 장면을 추가해주세요.")

        # 출력 디렉토리 생성
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        # 각 장면을 비디오 클립으로 변환
        clips = []
        total_scenes = len(self.scenes)

        for i, scene in enumerate(self.scenes):
            clip = self._create_scene_clip(scene, apply_zoom_effect, zoom_ratio)
            clips.append(clip)

            # 진행률 콜백
            if progress_callback:
                progress_callback((i + 1) / total_scenes * 0.5)  # 클립 생성 50%

        # 모든 클립 연결
        final_clip = concatenate_videoclips(clips, method="compose")

        # 영상 렌더링
        final_clip.write_videofile(
            output_path,
            fps=self.fps,
            codec=codec,
            audio_codec=audio_codec,
            threads=threads,
            preset="medium",
            logger=None  # 로깅 비활성화 (콘솔 출력 줄이기)
        )

        # 리소스 해제
        final_clip.close()
        for clip in clips:
            clip.close()

        if progress_callback:
            progress_callback(1.0)

        return output_path

    def _create_scene_clip(
        self,
        scene: SceneAsset,
        apply_zoom_effect: bool = True,
        zoom_ratio: float = 0.04
    ) -> CompositeVideoClip:
        """
        단일 장면을 비디오 클립으로 변환

        1. 이미지 로드 및 크기 조정
        2. 오디오 로드 및 길이 매핑
        3. 줌인 효과 적용 (선택)
        """
        # 오디오 로드 (길이 결정)
        audio = AudioFileClip(scene.audio_path)
        duration = audio.duration

        # 이미지 로드 및 크기 조정 (해상도 맞추기)
        image_clip = (
            ImageClip(scene.image_path)
            .set_duration(duration)
            .resize(height=self.height)  # 높이 기준으로 리사이즈
        )

        # 이미지가 영상 너비보다 작으면 중앙 정렬, 크면 크롭
        if image_clip.w < self.width:
            # 이미지가 작으면 배경과 함께 중앙 배치
            image_clip = image_clip.set_position("center")
        else:
            # 이미지가 크면 중앙 크롭
            x_center = (image_clip.w - self.width) // 2
            image_clip = image_clip.crop(x1=x_center, x2=x_center + self.width)

        # 줌인 효과 적용
        if apply_zoom_effect:
            image_clip = self._apply_zoom_effect(image_clip, zoom_ratio)

        # 오디오 설정
        image_clip = image_clip.set_audio(audio)

        # CompositeVideoClip으로 최종 크기 고정
        final_clip = CompositeVideoClip(
            [image_clip.set_position("center")],
            size=(self.width, self.height)
        ).set_duration(duration)

        return final_clip

    def _apply_zoom_effect(
        self,
        clip: ImageClip,
        zoom_ratio: float = 0.04
    ) -> ImageClip:
        """
        천천히 줌인하는 효과 적용 (Ken Burns 효과)

        시작: 100% -> 끝: 100% + zoom_ratio (예: 104%)
        """
        def zoom_func(get_frame, t):
            """시간에 따라 점진적으로 줌인"""
            progress = t / clip.duration
            # 1.0에서 시작해서 1.0 + zoom_ratio까지 증가
            scale = 1.0 + (zoom_ratio * progress)

            frame = get_frame(t)
            h, w = frame.shape[:2]

            # 새로운 크기 계산
            new_h = int(h * scale)
            new_w = int(w * scale)

            # 리사이즈
            from PIL import Image
            img = Image.fromarray(frame)
            img = img.resize((new_w, new_h), Image.LANCZOS)

            # 중앙 크롭 (원래 크기로)
            left = (new_w - w) // 2
            top = (new_h - h) // 2
            img = img.crop((left, top, left + w, top + h))

            return np.array(img)

        return clip.fl(zoom_func)


def assemble_video_from_scenes(
    scenes: List[SceneAsset],
    output_path: str,
    width: int = 1920,
    height: int = 1080,
    fps: int = 24,
    apply_zoom: bool = True
) -> str:
    """
    편의 함수: 장면 리스트로 영상 생성

    Args:
        scenes: SceneAsset 리스트
        output_path: 출력 파일 경로
        width: 영상 너비 (기본 1920)
        height: 영상 높이 (기본 1080)
        fps: 프레임 레이트 (기본 24)
        apply_zoom: 줌 효과 적용 여부

    Returns:
        str: 생성된 영상 파일 경로
    """
    assembler = VideoAssembler(width=width, height=height, fps=fps)
    assembler.add_scenes(scenes)
    return assembler.render(output_path, apply_zoom_effect=apply_zoom)
