import asyncio
import os
from typing import List, Optional

import aiohttp
from openai import AsyncOpenAI

from app.schemas.script import Scene


class ImageGenerator:
    """OpenAI DALL-E 3 이미지 생성기"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
        self.client = AsyncOpenAI(api_key=self.api_key)

    async def generate_image(
        self,
        prompt: str,
        size: str = "1792x1024",  # 16:9 비율 (유튜브 최적화)
        quality: str = "hd",
        style: str = "vivid"
    ) -> str:
        """
        DALL-E 3로 단일 이미지 생성

        Args:
            prompt: 영문 이미지 프롬프트
            size: 이미지 크기 (1024x1024, 1792x1024, 1024x1792)
            quality: 품질 (standard, hd)
            style: 스타일 (vivid, natural)

        Returns:
            str: 생성된 이미지 URL
        """
        response = await self.client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            quality=quality,
            style=style,
            n=1
        )

        return response.data[0].url

    async def generate_images_for_scenes(
        self,
        scenes: List[Scene],
        output_dir: str = "output/images",
        size: str = "1792x1024"
    ) -> List[str]:
        """
        장면 리스트에 대해 병렬로 이미지 생성

        Args:
            scenes: Scene 객체 리스트
            output_dir: 이미지 저장 디렉토리
            size: 이미지 크기

        Returns:
            List[str]: 저장된 이미지 파일 경로 리스트
        """
        os.makedirs(output_dir, exist_ok=True)

        # 병렬 생성을 위한 태스크 생성
        tasks = [
            self._generate_and_save(
                scene.image_prompt_english,
                os.path.join(output_dir, f"scene_{i:02d}_{scene.section_title}.png"),
                size
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
        size: str = "1792x1024"
    ) -> str:
        """이미지 생성 후 파일로 저장"""
        # 이미지 URL 생성
        image_url = await self.generate_image(prompt, size)

        # 이미지 다운로드 및 저장
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                if response.status != 200:
                    raise Exception(f"이미지 다운로드 실패: {response.status}")

                image_data = await response.read()
                with open(output_path, "wb") as f:
                    f.write(image_data)

        return output_path


async def generate_scene_images(
    scenes: List[Scene],
    api_key: Optional[str] = None,
    output_dir: str = "output/images"
) -> List[str]:
    """
    장면 리스트에 대한 이미지 일괄 생성 (편의 함수)

    Args:
        scenes: Scene 객체 리스트
        api_key: OpenAI API 키 (없으면 환경변수에서 가져옴)
        output_dir: 이미지 저장 디렉토리

    Returns:
        List[str]: 생성된 이미지 파일 경로 리스트
    """
    generator = ImageGenerator(api_key)
    return await generator.generate_images_for_scenes(scenes, output_dir)


async def generate_single_image(
    prompt: str,
    api_key: Optional[str] = None,
    size: str = "1792x1024"
) -> str:
    """
    단일 이미지 URL 생성 (편의 함수)

    Returns:
        str: 생성된 이미지 URL
    """
    generator = ImageGenerator(api_key)
    return await generator.generate_image(prompt, size)
