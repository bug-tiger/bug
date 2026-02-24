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

        # API 키 검증
        print(f"[설정 확인]")
        print(f"  - ANTHROPIC_API_KEY: {'설정됨' if self.anthropic_key else '없음'}")
        print(f"  - LEONARDO_API_KEY: {'설정됨' if self.leonardo_key else '없음'}")
        print(f"  - ELEVENLABS_API_KEY: {'설정됨' if self.elevenlabs_key else '없음'}")
        print(f"  - ELEVENLABS_VOICE_ID: {self.elevenlabs_voice_id or '없음'}")

        if not self.anthropic_key:
            raise ValueError("ANTHROPIC_API_KEY가 .env 파일에 설정되지 않았습니다.")

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
            for i, (sentence, prompt_dict) in enumerate(zip(sentences, prompts), 1):
                f.write(f"--- {i:03d} ---\n")
                f.write(f"원문: {sentence}\n")
                f.write(f"miniature : {prompt_dict.get('prompt_miniature', '')}\n")
                f.write(f"infographic: {prompt_dict.get('prompt_infographic', '')}\n")
                f.write(f"napkin     : {prompt_dict.get('prompt_napkin', '')}\n\n")
        report("프롬프트 생성 완료", 30)

        # 5. 이미지 생성
        image_paths = []
        success_count = 0

        if self.leonardo_key:
            report("이미지 생성 시작...", 35)
            try:
                image_paths = await self._generate_images(
                    sentences, prompts, output_dir,
                    lambda msg: report(msg, 35)
                )
                success_count = sum(1 for p in image_paths if p is not None)
                report(f"이미지 생성 완료: {success_count}/{total_sentences}", 75)
            except Exception as e:
                print(f"[오류] 이미지 생성 실패: {e}")
                import traceback
                print(traceback.format_exc())
                report(f"이미지 생성 실패: {str(e)[:100]}", 75)
        else:
            report("LEONARDO_API_KEY 없음 - 이미지 생성 건너뜀", 75)
            print("[경고] LEONARDO_API_KEY가 설정되지 않아 이미지 생성을 건너뜁니다.")

        # 6. TTS 오디오 생성
        audio_path = None

        if self.elevenlabs_key:
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
                print(f"[오류] 오디오 생성 실패: {e}")
                import traceback
                print(traceback.format_exc())
                report(f"오디오 생성 실패: {str(e)[:100]}", 95)
                audio_path = None
        else:
            report("ELEVENLABS_API_KEY 없음 - 오디오 생성 건너뜀", 95)
            print("[경고] ELEVENLABS_API_KEY가 설정되지 않아 오디오 생성을 건너뜁니다.")

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

    async def _generate_image_prompts(self, sentences: List[str]) -> List[dict]:
        """
        문장 리스트를 3종 스타일 영문 이미지 프롬프트로 변환

        Returns:
            각 문장별 {"prompt_miniature", "prompt_infographic", "prompt_napkin"} dict 리스트
        """
        prompts = []

        for i, sentence in enumerate(sentences):
            print(f"  프롬프트 생성 중: {i+1}/{len(sentences)}")

            try:
                prompt_dict = await self._generate_all_style_prompts(sentence)
                prompts.append(prompt_dict)
            except Exception as e:
                print(f"  [오류] 프롬프트 생성 실패: {e}")
                prompts.append({
                    "prompt_miniature": "tiny doctors in white coats examining a GIANT MEDICAL MODEL",
                    "prompt_infographic": "three-step medical procedure diagram with labeled anatomy",
                    "prompt_napkin": "simple sketch of medical concept with arrows and labels"
                })

        return prompts

    async def _generate_all_style_prompts(self, korean_sentence: str) -> dict:
        """
        한글 문장을 3종 스타일 영문 프롬프트 JSON으로 변환 (단일 API 호출)
        """
        message = await self.anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            messages=[
                {
                    "role": "user",
                    "content": f"""당신은 이미지 프롬프트 생성 전문가입니다.
아래 한글 문장을 3가지 스타일의 영어 이미지 프롬프트로 변환하세요.
입력이 이상하더라도 반드시 JSON만 출력하고 설명은 생략하세요.

[스타일 규칙]
1. prompt_miniature (K-MINIATURE DIORAMA):
   - 사람: "tiny figurines", 의료진: "tiny doctors in white coats"
   - 의학 주제/신체: "GIANT oversized prop"

2. prompt_infographic (MEDICAL INFOGRAPHIC):
   - Step 1 → Step 2 → Step 3 진행 과정 다이어그램
   - 영문 라벨과 숫자만 사용

3. prompt_napkin (NAPKIN SKETCH):
   - 손그림 스케치 스타일로 개념 설명
   - 화살표, 동그라미, 간단한 영문 텍스트

[출력 형식 - JSON만 출력]
{{"prompt_miniature": "...", "prompt_infographic": "...", "prompt_napkin": "..."}}

[입력 문장]
{korean_sentence}"""
                }
            ]
        )

        import json
        import re
        raw = message.content[0].text.strip()

        # JSON 파싱 시도
        try:
            # 코드블록 제거
            raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
            result = json.loads(raw)
            # 한글 폴백 검사
            fallback_keys = ['입력', '문장', '해주세요', '변환']
            for key in ["prompt_miniature", "prompt_infographic", "prompt_napkin"]:
                if key not in result or any(w in result.get(key, "") for w in fallback_keys):
                    result[key] = {
                        "prompt_miniature": "tiny doctors examining a GIANT anatomical model",
                        "prompt_infographic": "three-step medical procedure diagram with labels",
                        "prompt_napkin": "simple sketch of medical concept with arrows"
                    }[key]
            return result
        except Exception:
            return {
                "prompt_miniature": "tiny doctors in white coats examining medical equipment",
                "prompt_infographic": "three-step medical procedure diagram with labeled anatomy",
                "prompt_napkin": "simple sketch of medical concept with arrows and labels"
            }

    async def _generate_images(
        self,
        sentences: List[str],
        prompts: List[dict],
        output_dir: str,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> List[Optional[str]]:
        """
        이미지 생성 및 저장 (문장당 3개: 미니어처 + 인포그래픽 + 나프킨)

        Returns:
            저장된 이미지 경로 리스트 (실패시 None)
        """
        generator = LeonardoImageGenerator(api_key=self.leonardo_key)

        paths = []
        total = len(prompts)

        for i, prompt_dict in enumerate(prompts):
            print(f"  문장 {i+1}/{total} 이미지 생성 중...")

            if progress_callback:
                progress_callback(f"문장 {i+1}/{total} 이미지 생성 중...")

            for style, suffix in [
                ("mini",   "_mini.png"),
                ("info",   "_info.png"),
                ("napkin", "_napkin.png"),
            ]:
                key_map = {"mini": "prompt_miniature", "info": "prompt_infographic", "napkin": "prompt_napkin"}
                prompt_text = prompt_dict.get(key_map[style], "")
                output_path = os.path.join(output_dir, f"{i+1:03d}{suffix}")
                try:
                    path = await generator.generate_and_save(
                        prompt=prompt_text,
                        output_path=output_path,
                        width=1344,
                        height=768,
                        apply_style=True,
                        style=style
                    )
                    paths.append(path)
                    print(f"    [완료] {i+1:03d}{suffix}")
                except Exception as e:
                    print(f"    [오류] {suffix} 이미지 생성 실패: {e}")
                    paths.append(None)

                # API 레이트 리밋 방지
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
