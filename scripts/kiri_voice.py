#!/usr/bin/env python3
"""
Генератор голосового ответа через Yandex SpeechKit.
Обёртка для Hermes-агента: генерирует аудио и возвращает MEDIA: путь.

Использование:
    python3 kiri_voice.py "Текст ответа"
    → выводит MEDIA:/path/to/file.ogg

Настройки по умолчанию:
    - Голос: alena (женский, нейтральный)
    - Эмоция: good (доброжелательная)
    - Формат: oggopus (для Telegram)
"""

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TTS_SCRIPT = SCRIPT_DIR / "tts.py"


from typing import Optional


def voice_reply(text: str, voice: str = "alena", emotion: str = "good",
                audio_dir: Optional[str] = None) -> Optional[str]:
    """
    Озвучить текст и вернуть MEDIA: путь для Telegram.
    Возвращает None если TTS недоступен.
    """
    cmd = [
        sys.executable, str(TTS_SCRIPT),
        text,
        "--voice", voice,
        "--emotion", emotion,
        "--speed", "1.0",
    ]

    if audio_dir:
        cmd.extend(["--audio-dir", audio_dir])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    if result.returncode != 0:
        print(f"⚠️ Yandex TTS error: {result.stderr[:200]}", file=sys.stderr)
        return None

    # Ищем MEDIA: в stdout (tts.py его печатает)
    for line in result.stdout.split("\n"):
        if line.startswith("MEDIA:"):
            return line.strip()

    # Fallback: ищем по "Сохранено:" и собираем путь
    for line in result.stdout.split("\n"):
        if "Сохранено:" in line:
            # Формат: "✅ Сохранено: /path/to/file.ogg (12.3 KB)"
            parts = line.split("Сохранено:")
            if len(parts) > 1:
                path = parts[1].strip().split(" ")[0]
                return f"MEDIA:{path}"

    return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 kiri_voice.py <текст>", file=sys.stderr)
        sys.exit(1)

    text = " ".join(sys.argv[1:])
    result = voice_reply(text)

    if result:
        print(result)
    else:
        print("❌ Не удалось сгенерировать голосовой ответ", file=sys.stderr)
        sys.exit(1)
