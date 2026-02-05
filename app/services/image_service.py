import aiohttp
import asyncio
import os
import re
from typing import List, Optional


PEXELS_API_URL = "https://api.pexels.com/v1"


async def search_images(
    query: str,
    api_key: str = None,
    per_page: int = 5,
    orientation: str = "landscape"
) -> List[dict]:
    """
    Pexels API로 이미지 검색

    Args:
        query: 검색어
        api_key: Pexels API 키
        per_page: 결과 개수
        orientation: 방향 (landscape, portrait, square)

    Returns:
        이미지 정보 리스트
    """
    api_key = api_key or os.getenv("PEXELS_API_KEY")
    if not api_key:
        return []

    url = f"{PEXELS_API_URL}/search"
    headers = {"Authorization": api_key}
    params = {
        "query": query,
        "per_page": per_page,
        "orientation": orientation
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status != 200:
                    return []

                data = await response.json()
                return data.get("photos", [])
    except Exception as e:
        print(f"Pexels API 오류: {e}")
        return []


async def download_image(url: str, output_path: str) -> Optional[str]:
    """이미지 다운로드"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return None

                content = await response.read()
                with open(output_path, 'wb') as f:
                    f.write(content)

                return output_path
    except Exception as e:
        print(f"이미지 다운로드 오류: {e}")
        return None


async def get_images_for_script(
    script: str,
    title: str,
    api_key: str = None,
    output_dir: str = "output",
    images_per_section: int = 2
) -> List[str]:
    """
    스크립트 내용을 분석하여 관련 이미지 다운로드

    Args:
        script: 영상 스크립트
        title: 영상 제목
        api_key: Pexels API 키
        output_dir: 이미지 저장 디렉토리
        images_per_section: 섹션당 이미지 수

    Returns:
        다운로드된 이미지 경로 리스트
    """
    api_key = api_key or os.getenv("PEXELS_API_KEY")
    if not api_key:
        return []

    # 스크립트에서 키워드 추출
    keywords = extract_keywords(script, title)

    downloaded_images = []

    for i, keyword in enumerate(keywords[:10]):  # 최대 10개 키워드
        images = await search_images(keyword, api_key, per_page=images_per_section)

        for j, image in enumerate(images):
            image_url = image.get("src", {}).get("large2x") or image.get("src", {}).get("large")
            if image_url:
                output_path = os.path.join(output_dir, f"broll_{i}_{j}.jpg")
                downloaded = await download_image(image_url, output_path)
                if downloaded:
                    downloaded_images.append({
                        "path": downloaded,
                        "keyword": keyword,
                        "photographer": image.get("photographer", "Unknown"),
                        "url": image.get("url", "")
                    })

        # API 레이트 리밋 방지
        await asyncio.sleep(0.2)

    return downloaded_images


def extract_keywords(script: str, title: str) -> List[str]:
    """스크립트에서 이미지 검색용 키워드 추출"""
    keywords = []

    # 제목에서 키워드 추출
    title_words = re.findall(r'[가-힣a-zA-Z]+', title)
    keywords.extend([w for w in title_words if len(w) > 1])

    # 섹션 제목에서 키워드 추출
    section_titles = re.findall(r'\[(.*?)\]', script)
    for section in section_titles:
        words = re.findall(r'[가-힣a-zA-Z]+', section)
        keywords.extend([w for w in words if len(w) > 1])

    # 일반적인 유튜브 영상 관련 키워드 추가
    generic_keywords = [
        "technology", "business", "creative", "workspace",
        "teamwork", "success", "innovation", "digital"
    ]

    # 중복 제거 및 제한
    seen = set()
    unique_keywords = []
    for kw in keywords + generic_keywords:
        if kw.lower() not in seen:
            seen.add(kw.lower())
            unique_keywords.append(kw)

    return unique_keywords[:15]


async def search_videos(
    query: str,
    api_key: str = None,
    per_page: int = 3
) -> List[dict]:
    """
    Pexels API로 비디오 검색 (B-roll 용)

    Args:
        query: 검색어
        api_key: Pexels API 키
        per_page: 결과 개수

    Returns:
        비디오 정보 리스트
    """
    api_key = api_key or os.getenv("PEXELS_API_KEY")
    if not api_key:
        return []

    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": api_key}
    params = {
        "query": query,
        "per_page": per_page,
        "orientation": "landscape"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status != 200:
                    return []

                data = await response.json()
                return data.get("videos", [])
    except Exception as e:
        print(f"Pexels Video API 오류: {e}")
        return []
