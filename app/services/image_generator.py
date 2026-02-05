"""
Leonardo AI 이미지 생성 모듈

환경변수 설정:
- LEONARDO_API_KEY: Leonardo AI API 키
  https://app.leonardo.ai/api-access 에서 발급

- LEONARDO_MODEL_ID: 사용할 모델 ID (선택사항)
  추천 모델:
  - "6bef9f1b-29cb-40c7-b9df-32b51c1f67d3" (Leonardo Creative)
  - "e316348f-7773-490e-adcd-46757c738eb7" (Leonardo Diffusion XL)
  - "1e60896f-3c26-4296-8ecc-53e2afecc132" (Leonardo Lightning XL - 빠른 생성)
"""

import asyncio
import os
import time
from typing import List, Optional

import aiohttp

from app.schemas.script import Scene


class LeonardoImageGenerator:
    """Leonardo AI 이미지 생성기 (비동기)"""

    BASE_URL = "https://cloud.leonardo.ai/api/rest/v1"

    # 추천 기본 모델: Leonardo Lightning XL (빠른 생성, 고품질)
    DEFAULT_MODEL_ID = "1e60896f-3c26-4296-8ecc-53e2afecc132"

    def __init__(self, api_key: Optional[str] = None, model_id: Optional[str] = None):
        self.api_key = api_key or os.getenv("LEONARDO_API_KEY")
        if not self.api_key:
            raise ValueError("LEONARDO_API_KEY가 설정되지 않았습니다.")

        self.model_id = model_id or os.getenv("LEONARDO_MODEL_ID") or self.DEFAULT_MODEL_ID
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def generate_image(
        self,
        prompt: str,
        width: int = 1344,  # 16:9 비율 (유튜브 최적화)
        height: int = 768,
        num_images: int = 1,
        prompt_magic: bool = True,
        guidance_scale: float = 7.0
    ) -> str:
        """
        Leonardo AI로 단일 이미지 생성

        Args:
            prompt: 영문 이미지 프롬프트
            width: 이미지 너비 (기본 1344, 16:9 비율)
            height: 이미지 높이 (기본 768)
            num_images: 생성할 이미지 수 (기본 1)
            prompt_magic: 프롬프트 자동 향상 (기본 True)
            guidance_scale: 프롬프트 충실도 (기본 7.0)

        Returns:
            str: 생성된 이미지 URL
        """
        # 1. 이미지 생성 요청
        generation_id = await self._request_generation(
            prompt=prompt,
            width=width,
            height=height,
            num_images=num_images,
            prompt_magic=prompt_magic,
            guidance_scale=guidance_scale
        )

        # 2. 생성 완료까지 폴링
        image_url = await self._poll_generation_result(generation_id)

        return image_url

    async def _request_generation(
        self,
        prompt: str,
        width: int,
        height: int,
        num_images: int,
        prompt_magic: bool,
        guidance_scale: float
    ) -> str:
        """이미지 생성 요청 후 generation_id 반환"""
        url = f"{self.BASE_URL}/generations"

        payload = {
            "prompt": prompt,
            "modelId": self.model_id,
            "width": width,
            "height": height,
            "num_images": num_images,
            "promptMagic": prompt_magic,
            "guidance_scale": guidance_scale,
            "presetStyle": "CINEMATIC",  # 영상에 적합한 시네마틱 스타일
            "public": False
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=self.headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Leonardo AI 생성 요청 실패: {response.status} - {error_text}")

                data = await response.json()
                return data["sdGenerationJob"]["generationId"]

    async def _poll_generation_result(
        self,
        generation_id: str,
        max_attempts: int = 60,
        poll_interval: float = 2.0
    ) -> str:
        """생성 완료까지 폴링하고 이미지 URL 반환"""
        url = f"{self.BASE_URL}/generations/{generation_id}"

        async with aiohttp.ClientSession() as session:
            for _ in range(max_attempts):
                async with session.get(url, headers=self.headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Leonardo AI 조회 실패: {response.status} - {error_text}")

                    data = await response.json()
                    generation = data.get("generations_by_pk")

                    if generation:
                        status = generation.get("status")

                        if status == "COMPLETE":
                            images = generation.get("generated_images", [])
                            if images:
                                return images[0]["url"]
                            raise Exception("이미지가 생성되지 않았습니다.")

                        elif status == "FAILED":
                            raise Exception("Leonardo AI 이미지 생성 실패")

                await asyncio.sleep(poll_interval)

        raise TimeoutError(f"이미지 생성 시간 초과 (generation_id: {generation_id})")

    async def generate_images_for_scenes(
        self,
        scenes: List[Scene],
        output_dir: str = "output/images",
        width: int = 1344,
        height: int = 768
    ) -> List[str]:
        """
        장면 리스트에 대해 병렬로 이미지 생성

        Args:
            scenes: Scene 객체 리스트
            output_dir: 이미지 저장 디렉토리
            width: 이미지 너비
            height: 이미지 높이

        Returns:
            List[str]: 저장된 이미지 파일 경로 리스트
        """
        os.makedirs(output_dir, exist_ok=True)

        # 병렬 생성을 위한 태스크 생성
        tasks = [
            self._generate_and_save(
                scene.image_prompt_english,
                os.path.join(output_dir, f"scene_{i:02d}_{scene.section_title}.png"),
                width,
                height
            )
            for i, scene in enumerate(scenes)
        ]

        # 동시 실행 (API 레이트 리밋 고려하여 세마포어 사용)
        semaphore = asyncio.Semaphore(3)  # 동시 3개까지

        async def limited_task(task):
            async with semaphore:
                return await task

        results = await asyncio.gather(
            *[limited_task(task) for task in tasks],
            return_exceptions=True
        )

        # 에러 처리
        paths = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Scene {i} 이미지 생성 실패: {result}")
                paths.append(None)
            else:
                paths.append(result)

        return paths

    async def _generate_and_save(
        self,
        prompt: str,
        output_path: str,
        width: int = 1344,
        height: int = 768
    ) -> str:
        """이미지 생성 후 파일로 저장"""
        # 이미지 URL 생성
        image_url = await self.generate_image(prompt, width, height)

        # 이미지 다운로드 및 저장
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                if response.status != 200:
                    raise Exception(f"이미지 다운로드 실패: {response.status}")

                image_data = await response.read()
                with open(output_path, "wb") as f:
                    f.write(image_data)

        return output_path


# 편의 함수들

async def generate_scene_images(
    scenes: List[Scene],
    api_key: Optional[str] = None,
    model_id: Optional[str] = None,
    output_dir: str = "output/images"
) -> List[str]:
    """
    장면 리스트에 대한 이미지 일괄 생성

    Args:
        scenes: Scene 객체 리스트
        api_key: Leonardo API 키 (없으면 환경변수에서 가져옴)
        model_id: 사용할 모델 ID (없으면 환경변수 또는 기본값 사용)
        output_dir: 이미지 저장 디렉토리

    Returns:
        List[str]: 생성된 이미지 파일 경로 리스트
    """
    generator = LeonardoImageGenerator(api_key, model_id)
    return await generator.generate_images_for_scenes(scenes, output_dir)


async def generate_single_image(
    prompt: str,
    api_key: Optional[str] = None,
    model_id: Optional[str] = None,
    width: int = 1344,
    height: int = 768
) -> str:
    """
    단일 이미지 URL 생성

    Returns:
        str: 생성된 이미지 URL
    """
    generator = LeonardoImageGenerator(api_key, model_id)
    return await generator.generate_image(prompt, width, height)
