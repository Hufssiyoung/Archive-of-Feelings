import os
import re
import hashlib
from gtts import gTTS

TTS_CACHE_DIR = "tts_cache"


def _clean_text(text: str) -> str:
    """마크다운 문법을 제거하여 TTS에 적합한 순수 텍스트로 변환."""
    # 볼드/이탤릭 제거
    text = re.sub(r'\*{1,3}(.+?)\*{1,3}', r'\1', text)
    # 헤더 기호 제거
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # 인라인 코드 제거
    text = re.sub(r'`+(.+?)`+', r'\1', text)
    # 링크 제거 → 텍스트만 유지
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    # 수평선 제거
    text = re.sub(r'^[-*_]{3,}$', '', text, flags=re.MULTILINE)
    # 앞뒤 공백 정리
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def generate_tts(text: str, username: str) -> str:
    """
    텍스트를 한국어 TTS로 변환하여 tts_cache에 저장하고 파일 경로를 반환.
    동일한 텍스트+사용자 조합은 캐시된 파일을 재사용.
    """
    os.makedirs(TTS_CACHE_DIR, exist_ok=True)

    clean = _clean_text(text)
    key = hashlib.md5(f"{username}:{clean}".encode()).hexdigest()
    filepath = os.path.join(TTS_CACHE_DIR, f"{username}_{key}.mp3")

    if not os.path.exists(filepath):
        tts = gTTS(text=clean, lang="ko")
        tts.save(filepath)

    return filepath


def clear_user_cache(username: str) -> None:
    """로그아웃 시 해당 사용자의 TTS 캐시 파일을 모두 삭제."""
    if not os.path.isdir(TTS_CACHE_DIR):
        return
    prefix = f"{username}_"
    for filename in os.listdir(TTS_CACHE_DIR):
        if filename.startswith(prefix) and filename.endswith(".mp3"):
            try:
                os.remove(os.path.join(TTS_CACHE_DIR, filename))
            except OSError:
                pass
