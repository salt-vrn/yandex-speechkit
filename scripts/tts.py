#!/usr/bin/env python3
"""
Yandex SpeechKit TTS — синтез речи (текст → аудио)

Использование:
    python3 tts.py "Привет, это тестовый синтез речи"
    python3 tts.py "Привет" --voice oksana --format oggopus
    python3 tts.py "Привет" --output /path/to/audio.ogg

Требуется API-ключ Yandex Cloud / AI Studio.
Источники ключа (по приоритету):
    1. Переменная окружения YANDEX_API_KEY
    2. Файл credentials.json в директории проекта (рядом с SKILL.md)
    3. Файл credentials.json в workspace текущего Hermes-профиля

API Reference (официальная документация):
    URL: https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize
    Method: POST с form-data (НЕ JSON!)
    Лимит: 5000 символов за запрос
    Голос по умолчанию: oksana
    Формат по умолчанию: oggopus
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import List, Optional

import requests

# --- Конфигурация ---
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent


def _resolve_audio_dir() -> Path:
    """Определить директорию для аудио. Приоритет:
    1. HERMES_HOME/audio_cache/ (Hermes agents — gateway пропускает только эти пути)
    2. ~/.hermes/audio_cache/ (Hermes, если HERMES_HOME не задан)
    3. ~/.openclaw/media/audio/ (OpenClaw)
    4. PROJECT_DIR/audio/ (fallback)
    """
    hermes_home = os.environ.get("HERMES_HOME")
    if hermes_home:
        return Path(hermes_home) / "audio_cache"

    home = Path.home()
    hermes_cache = home / ".hermes" / "audio_cache"
    if hermes_cache.parent.exists():
        return hermes_cache

    openclaw_audio = home / ".openclaw" / "media" / "audio"
    if openclaw_audio.parent.exists():
        return openclaw_audio

    return PROJECT_DIR / "audio"


DEFAULT_AUDIO_DIR = _resolve_audio_dir()

TTS_URL = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"

# Максимум символов за один запрос к Yandex TTS (из официальной документации)
MAX_CHARS = 5000

# Доступные голоса: https://yandex.cloud/ru/docs/speechkit/tts/voices
VOICES = [
    "oksana",    # женский (по умолчанию)
    "alena",     # женский
    "filipp",    # мужской
    "ermil",     # мужской
    "jane",      # женский
    "omazh",     # женский
    "zahar",     # мужской
    "marina",    # премиум
    "masha",     # премиум
    "tatyana",   # премиум
]

FORMATS = ["oggopus", "lpcm"]


def get_api_key() -> str:
    """Получить API-ключ из разных источников."""
    # 1. Переменная окружения
    key = os.environ.get("YANDEX_API_KEY") or os.environ.get("YANDEX_SPEECHKIT_API_KEY")
    if key:
        return key

    # 2. credentials.json в папке проекта (рядом с SKILL.md)
    cred_file = PROJECT_DIR / "credentials.json"
    if not cred_file.exists():
        # credentials.json в workspace (Hermes или OpenClaw)
        hermes_home = os.environ.get("HERMES_HOME")
        candidates = []
        if hermes_home:
            candidates.append(Path(hermes_home) / "credentials.json")
        home = Path.home()
        # Hermes default: ~/.hermes/credentials.json
        candidates.append(home / ".hermes" / "credentials.json")
        # Hermes profiles: ~/.hermes/profiles/*/workspace/credentials.json
        profiles_dir = home / ".hermes" / "profiles"
        if profiles_dir.exists():
            for profile_dir in profiles_dir.iterdir():
                candidates.append(profile_dir / "workspace" / "credentials.json")
        # OpenClaw: ~/.openclaw/workspace/credentials.json
        candidates.append(home / ".openclaw" / "workspace" / "credentials.json")
        for candidate in candidates:
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

    print("❌ API-ключ не найден. Укажите YANDEX_API_KEY или добавьте в credentials.json")
    print("   Получить ключ: https://aistudio.yandex.ru/ → Профиль → API-ключи")
    sys.exit(1)


def _split_text(text: str, max_len: int = MAX_CHARS) -> List[str]:
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


def synthesize(text: str, voice: str = "oksana",
               speed: float = 1.0, audio_format: str = "oggopus",
               lang: str = "ru-RU", output: Optional[str] = None,
               audio_dir: Optional[Path] = None) -> Path:
    """
    Синтезировать речь из текста.
    Если текст длиннее 5000 символов — разбивает на части и склеивает.

    Возвращает путь к аудиофайлу.
    """
    api_key = get_api_key()

    audio_dir = audio_dir or DEFAULT_AUDIO_DIR
    audio_dir.mkdir(parents=True, exist_ok=True)

    # Auth: Api-Key header (для AI Studio ключей — напрямую, без IAM-токена)
    headers = {
        "Authorization": f"Api-Key {api_key}",
    }

    # Определяем расширение
    ext_map = {"oggopus": "ogg", "lpcm": "pcm"}
    ext = ext_map.get(audio_format, "ogg")

    # Разбиваем длинный текст на части
    parts = _split_text(text)
    is_multi = len(parts) > 1

    if is_multi:
        print(f"📝 Текст {len(text)} символов — разбит на {len(parts)} частей (лимит {MAX_CHARS})")

    if output:
        out_path = Path(output)
    else:
        # Only ASCII in filenames — Cyrillic breaks MEDIA: delivery in Telegram
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '', text[:30]).strip().rstrip('_')
        if not safe_name:
            safe_name = f"tts_{int(time.time())}"
        out_path = audio_dir / f"tts_{voice}_{safe_name}.{ext}"

    out_path.parent.mkdir(parents=True, exist_ok=True)

    all_audio = bytearray()

    for i, part in enumerate(parts, 1):
        if is_multi:
            print(f"🎙️ Часть {i}/{len(parts)}: «{part[:60]}{'...' if len(part) > 60 else ''}»")
        else:
            print(f"🎙️ Синтезирую: «{part[:80]}{'...' if len(part) > 80 else ''}»")

        print(f"   Голос: {voice}, скорость: {speed}x, формат: {audio_format}")

        # POST form-data (НЕ JSON!)
        params = {
            "text": part,
            "voice": voice,
            "speed": str(speed),
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
                    delay = 2 * (2 ** attempt)
                    print(f"⚠️ Retry {attempt + 1}/3 after {delay}s: {last_err}")
                    time.sleep(delay)
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

    # ВАЖНО: [[audio_as_voice]] + MEDIA: для Hermes — gateway доставит как голосовое
    print(f"[[audio_as_voice]]\nMEDIA:{out_path}")

    return out_path


def list_voices():
    """Вывести список доступных голосов."""
    print("Доступные голоса:")
    for v in VOICES:
        default = " (по умолчанию)" if v == "oksana" else ""
        print(f"  • {v}{default}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Yandex SpeechKit TTS")
    parser.add_argument("text", nargs="?", help="Текст для озвучки (до 5000 символов)")
    parser.add_argument("--voice", default="oksana", choices=VOICES,
                        help="Голос (по умолчанию: oksana)")
    parser.add_argument("--speed", type=float, default=1.0,
                        help="Скорость речи (0.1–3.0)")
    parser.add_argument("--format", default="oggopus", choices=FORMATS,
                        help="Формат аудио (по умолчанию: oggopus)")
    parser.add_argument("--lang", default="ru-RU",
                        help="Язык (по умолчанию: ru-RU)")
    parser.add_argument("--output", "-o", help="Путь для сохранения")
    parser.add_argument("--audio-dir",
                        help="Директория для аудио (по умолчанию: audio/ рядом со скриптом)")
    parser.add_argument("--list-voices", action="store_true",
                        help="Показать список голосов")

    args = parser.parse_args()

    if args.list_voices:
        list_voices()
    elif args.text:
        output_path = synthesize(
            text=args.text,
            voice=args.voice,
            speed=args.speed,
            audio_format=args.format,
            lang=args.lang,
            output=args.output,
            audio_dir=Path(args.audio_dir) if args.audio_dir else None,
        )
        print(f"\n▶️ Воспроизвести: ffplay -autoexit -nodisp {output_path}")
    else:
        parser.print_help()
