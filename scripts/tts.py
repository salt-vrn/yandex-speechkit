#!/usr/bin/env python3
"""
Yandex SpeechKit TTS — синтез речи (текст → аудио)

Использование:
    python3 tts.py "Привет, это тестовый синтез речи"
    python3 tts.py "Привет" --voice alena --emotion good --format oggopus
    python3 tts.py "Привет" --output /path/to/audio.ogg

Требуется API-ключ Yandex Cloud / AI Studio.
Источники ключа (по приоритету):
    1. Переменная окружения YANDEX_SPEECHKIT_API_KEY
    2. Файл credentials.json в директории проекта (рядом с SKILL.md)
    3. Файл credentials.json в workspace текущего Hermes-профиля
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

import requests

# --- Конфигурация ---
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

# audio/ по умолчанию рядом со скриптом, но можно переопределить через --audio-dir
DEFAULT_AUDIO_DIR = PROJECT_DIR / "audio"

TTS_URL = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"

# Максимум символов за один запрос к Yandex TTS
MAX_CHARS = 250

# Доступные голоса: https://yandex.cloud/ru/docs/speechkit/tts/voices
VOICES = [
    "alena",     # женский, нейтральный (по умолчанию)
    "filipp",    # мужской
    "ermil",     # мужской, добрый
    "jane",      # женский, грустный
    "oksana",    # женский, новостной
    "omazh",     # женский, злой
    "zahar",     # мужской, нейтральный
    "marina",    # женский, шёпот (премиум)
    "masha",     # женский, детский (премиум)
    "tatyana",   # женский, для Brand Voice
]

EMOTIONS = ["neutral", "good", "evil"]
FORMATS = ["oggopus", "lpcm", "mp3"]


def get_api_key() -> str:
    """Получить API-ключ из разных источников."""
    # 1. Переменная окружения
    key = os.environ.get("YANDEX_SPEECHKIT_API_KEY")
    if key:
        return key

    # 2. credentials.json в папке проекта (рядом с SKILL.md)
    cred_file = PROJECT_DIR / "credentials.json"
    if not cred_file.exists():
        # 3. credentials.json в workspace текущего Hermes-профиля
        hermes_home = os.environ.get("HERMES_HOME")
        if hermes_home:
            cred_file = Path(hermes_home) / "credentials.json"
        else:
            # Fallback: ищем в ~/.hermes/profiles/*/workspace/credentials.json
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


def _split_text(text: str, max_len: int = MAX_CHARS) -> list[str]:
    """Разбить текст на части не более max_len символов, по границам предложений/слов."""
    if len(text) <= max_len:
        return [text]

    parts = []
    while text:
        if len(text) <= max_len:
            parts.append(text)
            break

        # Ищем границу предложения (. ! ?) в пределах max_len
        chunk = text[:max_len]
        # Ищем последний знак конца предложения
        match = re.search(r'[.!?…]\s+', chunk[::-1])
        if match:
            # Позиция с конца
            split_pos = max_len - match.start()
        else:
            # Разбиваем по последнему пробелу
            last_space = chunk.rfind(' ')
            split_pos = last_space if last_space > 0 else max_len

        parts.append(text[:split_pos].strip())
        text = text[split_pos:].strip()

    return parts


def synthesize(text: str, voice: str = "alena", emotion: str = "neutral",
               speed: float = 1.0, audio_format: str = "oggopus",
               lang: str = "ru-RU", output: str = None,
               audio_dir: Path = None) -> Path:
    """
    Синтезировать речь из текста.
    Если текст длиннее 250 символов — разбивает на части и склеивает.

    Возвращает путь к аудиофайлу.
    """
    api_key = get_api_key()

    audio_dir = audio_dir or DEFAULT_AUDIO_DIR
    audio_dir.mkdir(parents=True, exist_ok=True)

    headers = {
        "Authorization": f"Api-Key {api_key}",
    }

    # Определяем расширение
    ext_map = {"oggopus": "ogg", "lpcm": "wav", "mp3": "mp3"}
    ext = ext_map.get(audio_format, "ogg")

    # Разбиваем длинный текст на части
    parts = _split_text(text)
    is_multi = len(parts) > 1

    if is_multi:
        print(f"📝 Текст {len(text)} символов — разбит на {len(parts)} частей (лимит {MAX_CHARS})")

    if output:
        out_path = Path(output)
    else:
        safe_name = re.sub(r'[^\w\s-]', '', text[:30]).strip().replace(" ", "_")
        if not safe_name:
            safe_name = "tts_output"
        out_path = audio_dir / f"tts_{voice}_{safe_name}.{ext}"

    out_path.parent.mkdir(parents=True, exist_ok=True)

    all_audio = bytearray()

    for i, part in enumerate(parts, 1):
        if is_multi:
            print(f"🎙️ Часть {i}/{len(parts)}: «{part[:60]}{'...' if len(part) > 60 else ''}»")
        else:
            print(f"🎙️ Синтезирую: «{part[:80]}{'...' if len(part) > 80 else ''}»")

        print(f"   Голос: {voice}, эмоция: {emotion}, скорость: {speed}x")

        params = {
            "text": part,
            "voice": voice,
            "emotion": emotion,
            "speed": speed,
            "format": audio_format,
            "lang": lang,
        }

        last_err = None
        for attempt in range(3):
            resp = requests.post(TTS_URL, headers=headers, data=params, timeout=30)

            if resp.status_code == 200:
                break
            last_err = f"HTTP {resp.status_code}: {resp.text[:300]}"
            if resp.status_code == 429 or resp.status_code >= 500:
                if attempt < 2:
                    time.sleep(2 * (2 ** attempt))
                    continue
            print(f"❌ Ошибка API: {last_err}")
            sys.exit(1)
        else:
            print(f"❌ Ошибка API после 3 попыток: {last_err}")
            sys.exit(1)

        all_audio.extend(resp.content)

    with open(out_path, "wb") as f:
        f.write(all_audio)

    size_kb = len(all_audio) / 1024
    print(f"✅ Сохранено: {out_path} ({size_kb:.1f} KB)")

    # ВАЖНО: MEDIA: путь для Hermes — чтобы kiri_voice.py и агент могли найти файл
    print(f"MEDIA:{out_path}")

    return out_path


def list_voices():
    """Вывести список доступных голосов."""
    print("Доступные голоса:")
    for v in VOICES:
        print(f"  • {v}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Yandex SpeechKit TTS")
    parser.add_argument("text", nargs="?", help="Текст для озвучки")
    parser.add_argument("--voice", default="alena", choices=VOICES, help="Голос (по умолчанию: alena)")
    parser.add_argument("--emotion", default="neutral", choices=EMOTIONS, help="Эмоция")
    parser.add_argument("--speed", type=float, default=1.0, help="Скорость речи (0.1–3.0)")
    parser.add_argument("--format", default="oggopus", choices=FORMATS, help="Формат аудио")
    parser.add_argument("--output", "-o", help="Путь для сохранения")
    parser.add_argument("--audio-dir", help="Директория для аудио (по умолчанию: audio/ рядом со скриптом)")
    parser.add_argument("--list-voices", action="store_true", help="Показать список голосов")

    args = parser.parse_args()

    if args.list_voices:
        list_voices()
    elif args.text:
        output_path = synthesize(
            text=args.text,
            voice=args.voice,
            emotion=args.emotion,
            speed=args.speed,
            audio_format=args.format,
            output=args.output,
            audio_dir=Path(args.audio_dir) if args.audio_dir else None,
        )
        print(f"\n▶️ Воспроизвести: ffplay -autoexit -nodisp {output_path}")
    else:
        parser.print_help()
