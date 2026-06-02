#!/usr/bin/env python3
"""
Генератор голосового ответа через Yandex SpeechKit.
Обёртка для Hermes-агента: генерирует аудио и возвращает MEDIA: путь.

Использование:
    python3 kiri_voice.py "Текст ответа"
    → выводит MEDIA:/path/to/file.ogg

Настройки по умолчанию:
    - Голос: oksana (женский, по умолчанию API)
    - Формат: oggopus (для Telegram)
    - Скорость: 1.0
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).resolve().parent
TTS_SCRIPT = SCRIPT_DIR / "tts.py"


def voice_reply(text: str, voice: str = "oksana",
                speed: float = 1.0, audio_dir: Optional[str] = None) -> Optional[str]:
    """
    Озвучить текст и вернуть MEDIA: путь для Telegram.
    Возвращает None если TTS недоступен.
    """
    cmd = [
        sys.executable, str(TTS_SCRIPT),
        text,
        "--voice", voice,
        "--speed", str(speed),
    ]

    if audio_dir:
        cmd.extend(["--audio-dir", audio_dir])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode != 0:
        print(f"⚠️ Yandex TTS error: {result.stderr[:200]}", file=sys.stderr)
        return None

    # Ищем [[audio_as_voice]] и MEDIA: в stdout (tts.py их печатает)
    has_voice_tag = False
    for line in result.stdout.split("\n"):
        if "[[audio_as_voice]]" in line:
            has_voice_tag = True
        if line.startswith("MEDIA:"):
            path = line.strip()
            return f"[[audio_as_voice]]\n{path}" if has_voice_tag else path

    # Fallback: ищем по "Сохранено:" и собираем путь
    for line in result.stdout.split("\n"):
        if "Сохранено:" in line:
            # Формат: "✅ Сохранено: /path/to/file.ogg (12.3 KB)"
            parts = line.split("Сохранено:")
            if len(parts) > 1:
                path = parts[1].strip().split(" ")[0]
                return f"[[audio_as_voice]]\nMEDIA:{path}"

    return None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Yandex SpeechKit voice reply (Hermes wrapper)")
    parser.add_argument("text", nargs="?", help="Текст для озвучки")
    parser.add_argument("--voice", default="oksana",
                        help="Голос (по умолчанию: oksana)")
    parser.add_argument("--speed", type=float, default=1.0,
                        help="Скорость речи (0.1–3.0)")
    parser.add_argument("--audio-dir",
                        help="Директория для аудио")

    args = parser.parse_args()

    if not args.text:
        parser.print_help()
        sys.exit(1)

    result = voice_reply(
        text=args.text,
        voice=args.voice,
        speed=args.speed,
        audio_dir=args.audio_dir,
    )

    if result:
        print(result)
    else:
        print("❌ Не удалось сгенерировать голосовой ответ", file=sys.stderr)
        sys.exit(1)
