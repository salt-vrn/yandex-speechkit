#!/usr/bin/env python3
"""
Yandex SpeechKit STT — распознавание речи (аудио → текст)

Использование:
    python3 stt.py audio.ogg
    python3 stt.py audio.ogg --lang ru-RU

Требуется API-ключ:
    YANDEX_SPEECHKIT_API_KEY или credentials.json
"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

# STT API (синхронное распознавание, до ~30 сек / 1 MB)
STT_URL = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"


def get_api_key() -> str:
    """Получить API-ключ из разных источников."""
    key = os.environ.get("YANDEX_SPEECHKIT_API_KEY")
    if key:
        return key

    # credentials.json в папке проекта
    cred_file = PROJECT_DIR / "credentials.json"
    if not cred_file.exists():
        # credentials.json в workspace текущего Hermes-профиля
        hermes_home = os.environ.get("HERMES_HOME")
        if hermes_home:
            cred_file = Path(hermes_home) / "credentials.json"
        else:
            profiles_dir = Path.home() / ".hermes" / "profiles"
            if profiles_dir.exists():
                for profile_dir in profiles_dir.iterdir():
                    candidate = profile_dir / "workspace" / "credentials.json"
                    if candidate.exists():
                        cred_file = candidate
                        break

    if cred_file.exists():
        try:
            with open(cred_file) as f:
                creds = json.load(f)
            key = creds.get("yandex_speechkit_api_key") or creds.get("yandex_api_key")
            if key:
                return key
        except (json.JSONDecodeError, IOError):
            pass

    print("❌ API-ключ не найден. Укажите YANDEX_SPEECHKIT_API_KEY или добавьте в credentials.json")
    print("   Получить ключ: https://aistudio.yandex.ru/ → Профиль → API-ключи")
    sys.exit(1)


def recognize(file_path: str, lang: str = "ru-RU", sample_rate: int = None,
              audio_format: str = None) -> str:
    """
    Распознать речь из аудиофайла (синхронно, до ~1 MB / 30 сек).

    Возвращает распознанный текст.
    """
    api_key = get_api_key()
    file_path = Path(file_path)

    if not file_path.exists():
        print(f"❌ Файл не найден: {file_path}")
        sys.exit(1)

    # Определить формат по расширению
    ext = file_path.suffix.lower()
    fmt_map = {
        ".ogg": "oggopus",
        ".opus": "oggopus",
        ".wav": "lpcm",
        ".mp3": "mp3",
        ".flac": "flac",
        ".m4a": "m4a",
    }
    if audio_format is None:
        audio_format = fmt_map.get(ext, "oggopus")

    if sample_rate is None:
        rate_map = {".ogg": 48000, ".opus": 48000, ".mp3": 44100, ".wav": 16000}
        sample_rate = rate_map.get(ext, 48000)

    size_mb = file_path.stat().st_size / (1024 * 1024)
    print(f"🎤 Распознаю: {file_path.name} ({size_mb:.1f} MB)")
    print(f"   Формат: {audio_format}, частота: {sample_rate} Hz, язык: {lang}")

    if size_mb > 1.0:
        print("⚠️ Файл > 1 MB — синхронный API может не справиться.")
        print("   Попробуйте разбить файл или использовать ffmpeg для сжатия.")

    with open(file_path, "rb") as f:
        audio_data = f.read()

    headers = {
        "Authorization": f"Api-Key {api_key}",
    }

    params = {
        "lang": lang,
        "format": audio_format,
        "sampleRateHertz": sample_rate,
    }

    resp = requests.post(
        STT_URL,
        headers=headers,
        params=params,
        data=audio_data,
        timeout=60,
    )

    if resp.status_code != 200:
        print(f"❌ Ошибка API: {resp.status_code}")
        print(f"   {resp.text[:500]}")
        sys.exit(1)

    result = resp.json()
    text = result.get("result", "")

    if text:
        print(f"✅ Распознано: «{text}»")
    else:
        print("⚠️ Текст не распознан (тишина или шум?)")
        print(f"   Ответ API: {json.dumps(result, ensure_ascii=False, indent=2)}")

    return text


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Yandex SpeechKit STT")
    parser.add_argument("file", help="Аудиофайл для распознавания")
    parser.add_argument("--lang", default="ru-RU", help="Язык (по умолчанию: ru-RU)")
    parser.add_argument("--format", help="Формат аудио (oggopus, lpcm, mp3)")
    parser.add_argument("--rate", type=int, help="Частота дискретизации (Hz)")

    args = parser.parse_args()

    recognize(
        file_path=args.file,
        lang=args.lang,
        sample_rate=args.rate,
        audio_format=args.format,
    )
