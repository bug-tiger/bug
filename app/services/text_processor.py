"""
텍스트 처리 서비스 - 문장 단위 분리
"""
import re
from typing import List


def split_into_sentences(text: str) -> List[str]:
    """
    텍스트를 문장 단위로 분리
    한국어와 영어 모두 지원

    Args:
        text: 입력 텍스트

    Returns:
        문장 리스트
    """
    # 텍스트 정리
    text = text.strip()
    text = re.sub(r'\n+', ' ', text)  # 줄바꿈을 공백으로
    text = re.sub(r'\s+', ' ', text)  # 연속 공백 제거

    # 한국어/영어 문장 종결 패턴
    # 마침표, 물음표, 느낌표 뒤에 공백이 오면 문장 끝으로 인식
    # 단, 숫자.숫자 패턴(소수점)은 제외
    sentence_endings = r'(?<![0-9])([.!?])(?=\s|$)'

    # 문장 분리
    sentences = []
    current_pos = 0

    for match in re.finditer(sentence_endings, text):
        end_pos = match.end()
        sentence = text[current_pos:end_pos].strip()
        if sentence and len(sentence) > 5:  # 너무 짧은 문장 제외
            sentences.append(sentence)
        current_pos = end_pos

    # 마지막 남은 텍스트 처리
    remaining = text[current_pos:].strip()
    if remaining and len(remaining) > 5:
        sentences.append(remaining)

    # 문장이 없으면 전체 텍스트를 하나의 문장으로
    if not sentences:
        sentences = [text]

    return sentences


def extract_keywords_for_image(sentence: str) -> str:
    """
    문장에서 이미지 생성용 핵심 키워드 추출

    Args:
        sentence: 입력 문장 (한국어)

    Returns:
        영어 이미지 프롬프트용 키워드
    """
    # 불필요한 조사/어미 제거 (간단한 버전)
    # 실제로는 Anthropic API를 사용하여 더 정확한 번역/요약 수행
    return sentence


def clean_text_for_tts(text: str) -> str:
    """
    TTS용 텍스트 정리

    Args:
        text: 입력 텍스트

    Returns:
        정리된 텍스트
    """
    # URL 제거
    text = re.sub(r'https?://\S+', '', text)

    # 특수문자 정리
    text = re.sub(r'[#*_~`]', '', text)

    # 연속 공백/줄바꿈 정리
    text = re.sub(r'\s+', ' ', text)

    return text.strip()
