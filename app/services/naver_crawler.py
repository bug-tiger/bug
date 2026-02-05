import re
from typing import Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


class NaverBlogCrawler:
    """네이버 블로그 크롤러 - 제목과 본문 텍스트 추출"""

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # 제거할 불필요한 요소들
    REMOVE_SELECTORS = [
        ".se-oglink",           # 링크 카드
        ".se-sticker",          # 스티커
        ".se-section-oglink",   # OG 링크 섹션
        ".se-module-oglink",    # OG 링크 모듈
        ".se-quotation",        # 인용구 (선택적)
        "script", "style",      # 스크립트/스타일
        ".se-component-share",  # 공유 버튼
        ".se-section-sticker",  # 스티커 섹션
    ]

    @classmethod
    def extract(cls, url: str) -> Tuple[str, str]:
        """
        네이버 블로그 URL에서 제목과 본문 추출

        Args:
            url: 네이버 블로그 URL

        Returns:
            Tuple[str, str]: (제목, 본문 텍스트)

        Raises:
            ValueError: 유효하지 않은 URL이거나 추출 실패 시
        """
        if "blog.naver.com" not in url:
            raise ValueError("네이버 블로그 URL이 아닙니다.")

        # 1차 접근: 메인 페이지에서 iframe src 추출
        real_content_url = cls._get_iframe_url(url)

        # 2차 접근: 실제 본문 페이지 크롤링
        response = requests.get(real_content_url, headers=cls.HEADERS, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        title = cls._extract_title(soup)
        content = cls._extract_content(soup)

        return title, content

    @classmethod
    def _get_iframe_url(cls, url: str) -> str:
        """iframe 내부의 실제 본문 URL 추출"""
        response = requests.get(url, headers=cls.HEADERS, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # mainFrame iframe 찾기
        iframe = soup.find("iframe", {"id": "mainFrame"})
        if iframe and iframe.get("src"):
            return urljoin(url, iframe["src"])

        # 모바일 URL이거나 새로운 에디터인 경우 직접 접근
        return url

    @classmethod
    def _extract_title(cls, soup: BeautifulSoup) -> str:
        """제목 추출"""
        # 새로운 스마트에디터 (SE3)
        title_elem = soup.select_one(".se-title-text")
        if title_elem:
            return title_elem.get_text(strip=True)

        # 구 에디터
        title_elem = soup.select_one(".pcol1, .htitle, .se_title")
        if title_elem:
            return title_elem.get_text(strip=True)

        # 일반적인 제목 태그
        title_elem = soup.find("title")
        if title_elem:
            return title_elem.get_text(strip=True).replace(" : 네이버 블로그", "")

        return "제목 없음"

    @classmethod
    def _extract_content(cls, soup: BeautifulSoup) -> str:
        """본문 텍스트 추출 (불필요한 요소 제거)"""
        # 불필요한 요소 제거
        for selector in cls.REMOVE_SELECTORS:
            for elem in soup.select(selector):
                elem.decompose()

        # 새로운 스마트에디터 (SE3) 본문
        content_area = soup.select_one(".se-main-container")
        if content_area:
            return cls._clean_text(content_area)

        # 구 에디터 본문
        content_area = soup.select_one("#postViewArea, .post-view, #post-view")
        if content_area:
            return cls._clean_text(content_area)

        # 전체 body에서 추출 시도
        body = soup.find("body")
        if body:
            return cls._clean_text(body)

        return ""

    @classmethod
    def _clean_text(cls, element: BeautifulSoup) -> str:
        """텍스트 정리 - 불필요한 공백 제거 및 정규화"""
        # 모든 텍스트 추출
        text = element.get_text(separator="\n", strip=True)

        # 여러 개의 연속된 줄바꿈을 2개로 정규화
        text = re.sub(r"\n{3,}", "\n\n", text)

        # 여러 개의 연속된 공백을 하나로
        text = re.sub(r"[ \t]+", " ", text)

        # 앞뒤 공백 제거
        text = text.strip()

        return text


async def crawl_naver_blog(url: str) -> Tuple[str, str]:
    """
    네이버 블로그 URL에서 제목과 본문 추출 (비동기 래퍼)

    Args:
        url: 네이버 블로그 URL

    Returns:
        Tuple[str, str]: (제목, 본문 텍스트)
    """
    return NaverBlogCrawler.extract(url)
