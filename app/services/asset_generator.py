"""
Asset Kit 생성 파이프라인

블로그 글 -> 문장 분리 -> 이미지 생성 -> 오디오 생성 -> 폴더 정리

Vrew, 캡컷(CapCut) 등 편집 툴에서 바로 불러올 수 있는
고품질 영상 소스 패키지를 생성합니다.
"""

import os
import asyncio
from datetime import datetime
from typing import List, Optional, Callable

import anthropic

from app.services.text_processor import split_into_sentences, clean_text_for_tts
from app.services.image_generator import LeonardoImageGenerator
from app.services.tts_service import generate_audio_chunked
from app.core.config import settings


class AssetKitGenerator:
    """
    Asset Kit 생성기

    블로그 글을 입력받아 Vrew/CapCut에서 편집 가능한 소스 패키지 생성
    """

    def __init__(
        self,
        anthropic_api_key: Optional[str] = None,
        leonardo_api_key: Optional[str] = None,
        elevenlabs_api_key: Optional[str] = None,
        elevenlabs_voice_id: Optional[str] = None
    ):
        self.anthropic_key = anthropic_api_key or settings.ANTHROPIC_API_KEY
        self.leonardo_key = leonardo_api_key or settings.LEONARDO_API_KEY
        self.elevenlabs_key = elevenlabs_api_key or settings.ELEVENLABS_API_KEY
        self.elevenlabs_voice_id = elevenlabs_voice_id or settings.ELEVENLABS_VOICE_ID

        # Anthropic 클라이언트 (문장 -> 영문 프롬프트 변환용)
        self.anthropic_client = anthropic.AsyncAnthropic(api_key=self.anthropic_key)

    async def generate_asset_kit(
        self,
        text: str,
        project_name: str = "project",
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> dict:
        """
        Asset Kit 생성 메인 파이프라인

        Args:
            text: 블로그 글 텍스트
            project_name: 프로젝트 이름 (폴더명에 사용)
            progress_callback: 진행 상황 콜백 (message, percentage)

        Returns:
            생성 결과 딕셔너리
        """
        def report(msg: str, pct: int):
            print(f"[{pct}%] {msg}")
            if progress_callback:
                progress_callback(msg, pct)

        # 1. 출력 디렉토리 생성
        date_str = datetime.now().strftime("%Y%m%d")
        safe_name = "".join(c for c in project_name if c.isalnum() or c in (' ', '_', '-')).strip()
        safe_name = safe_name.replace(' ', '_')[:30]
        output_dir = os.path.join("output", f"{date_str}_{safe_name}")
        os.makedirs(output_dir, exist_ok=True)

        report(f"출력 폴더: {output_dir}", 5)

        # 2. 텍스트 정리 및 문장 분리
        report("텍스트 분석 중...", 10)
        clean_text = clean_text_for_tts(text)
        sentences = split_into_sentences(clean_text)
        total_sentences = len(sentences)
        report(f"총 {total_sentences}개 문장 감지됨", 15)

        # 3. 전체 스크립트 저장
        script_path = os.path.join(output_dir, "000_full_script.txt")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(clean_text)
            f.write("\n\n--- 문장 분리 ---\n\n")
            for i, sentence in enumerate(sentences, 1):
                f.write(f"{i:03d}. {sentence}\n\n")
        report("스크립트 저장 완료", 20)

        # 4. 문장별 영문 이미지 프롬프트 생성
        report("이미지 프롬프트 생성 중...", 25)
        prompts = await self._generate_image_prompts(sentences)

        # 프롬프트 저장
        prompts_path = os.path.join(output_dir, "000_prompts.txt")
        with open(prompts_path, "w", encoding="utf-8") as f:
            for i, (sentence, prompt) in enumerate(zip(sentences, prompts), 1):
                f.write(f"--- {i:03d} ---\n")
                f.write(f"원문: {sentence}\n")
                f.write(f"프롬프트: {prompt}\n\n")
        report("프롬프트 생성 완료", 30)

        # 5. 이미지 생성
        report("이미지 생성 시작...", 35)
        image_paths = await self._generate_images(
            sentences, prompts, output_dir,
            lambda msg: report(msg, 35 + int(40 * (prompts.index(msg.split()[-1]) if msg.split() else 0) / max(len(prompts), 1)))
        )

        success_count = sum(1 for p in image_paths if p is not None)
        report(f"이미지 생성 완료: {success_count}/{total_sentences}", 75)

        # 6. TTS 오디오 생성
        report("오디오 생성 중...", 80)
        audio_path = os.path.join(output_dir, "000_full_audio.mp3")

        try:
            await generate_audio_chunked(
                text=clean_text,
                output_path=audio_path,
                voice=self.elevenlabs_voice_id or "Lily",
                api_key=self.elevenlabs_key
            )
            report("오디오 생성 완료", 95)
        except Exception as e:
            report(f"오디오 생성 실패: {e}", 95)
            audio_path = None

        # 7. 결과 요약
        report("Asset Kit 생성 완료!", 100)

        return {
            "success": True,
            "output_dir": output_dir,
            "total_sentences": total_sentences,
            "images_generated": success_count,
            "audio_path": audio_path,
            "script_path": script_path,
            "files": {
                "script": script_path,
                "prompts": prompts_path,
                "audio": audio_path,
                "images": [p for p in image_paths if p is not None]
            }
        }

    async def _generate_image_prompts(self, sentences: List[str]) -> List[str]:
        """
        문장 리스트를 영문 이미지 프롬프트로 변환

        Args:
            sentences: 한글 문장 리스트

        Returns:
            영문 프롬프트 리스트
        """
        prompts = []

        for i, sentence in enumerate(sentences):
            print(f"  프롬프트 생성 중: {i+1}/{len(sentences)}")

            try:
                prompt = await self._translate_to_image_prompt(sentence)
                prompts.append(prompt)
            except Exception as e:
                print(f"  [오류] 프롬프트 생성 실패: {e}")
                # 기본 프롬프트 사용
                prompts.append("A professional medical scene in a modern hospital setting")

        return prompts

    async def _translate_to_image_prompt(self, korean_sentence: str) -> str:
        """
        한글 문장을 영문 이미지 프롬프트로 변환 (Anthropic Claude 사용)
        """
        message = await self.anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[
                {
                    "role": "user",
                    "content": f"""다음 한글 문장의 핵심 내용을 영어 이미지 프롬프트로 변환해주세요.
의학/건강 콘텐츠에 적합한 시각적 묘사로 작성해주세요.
카메라 앵글, 조명, 분위기를 포함하면 좋습니다.
프롬프트만 출력하세요 (설명 없이).

문장: {korean_sentence}

영어 이미지 프롬프트:"""
                }
            ]
        )

        return message.content[0].text.strip()

    async def _generate_images(
        self,
        sentences: List[str],
        prompts: List[str],
        output_dir: str,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> List[Optional[str]]:
        """
        이미지 생성 및 저장

        Returns:
            저장된 이미지 경로 리스트 (실패시 None)
        """
        generator = LeonardoImageGenerator(api_key=self.leonardo_key)

        paths = []
        total = len(prompts)

        for i, prompt in enumerate(prompts):
            output_path = os.path.join(output_dir, f"{i+1:03d}_image.png")
            print(f"  문장 {i+1}/{total} 이미지 생성 중...")

            if progress_callback:
                progress_callback(f"문장 {i+1}/{total} 이미지 생성 중...")

            try:
                path = await generator.generate_and_save(
                    prompt=prompt,
                    output_path=output_path,
                    width=1344,
                    height=768,
                    apply_style=True
                )
                paths.append(path)
                print(f"  [완료] {i+1:03d}_image.png")

            except Exception as e:
                print(f"  [오류] 문장 {i+1} 이미지 생성 실패: {e}")
                paths.append(None)

            # API 레이트 리밋 방지
            if i < total - 1:
                await asyncio.sleep(2)

        return paths


# ============================================================
# 편의 함수
# ============================================================

async def generate_asset_kit(
    text: str,
    project_name: str = "project",
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> dict:
    """
    Asset Kit 생성 (편의 함수)

    Args:
        text: 블로그 글 텍스트
        project_name: 프로젝트 이름
        progress_callback: 진행 상황 콜백

    Returns:
        생성 결과 딕셔너리
    """
    generator = AssetKitGenerator()
    return await generator.generate_asset_kit(text, project_name, progress_callback)
