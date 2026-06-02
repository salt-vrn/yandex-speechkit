#!/usr/bin/env python3
"""
Yandex SpeechKit STT — распознавание речи (аудио → текст)

Использование:
    python3 stt.py audio.ogg
    python3 stt.py audio.ogg --lang ru-RU
    python3 stt.py audio.ogg --format oggopus --rate 48000

Требуется API-ключ:
    YANDEX_API_KEY или credentials.json

API Reference (официальная документация):
    URL: https://stt.api.cloud.yandex.net/speech/v1/stt:recognize
    Method: POST с raw audio body, параметры в query string
    Лимиты: 1 MB, 30 секунд, 1 канал
    Формат по умолчанию: oggopus
    Язык по умолчанию: ru-RU

Для длинного аудио (>30 сек):
    Скрипт автоматически разбивает на чанки через ffmpeg.
"""

import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import List, Optional, Tuple

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

# STT API (синхронное распознавание, до ~30 сек / 1 MB)
STT_URL = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"

# Лимиты для chunking
MAX_CHUNK_DURATION_SEC = 25
MAX_CHUNK_SIZE_BYTES = 900_000


def get_audio_info(file_path: str) -> Tuple[float, int]:
    """Получить длительность (сек) и sample rate через ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet",
             "-show_entries", "format=duration",
             "-show_entries", "stream=sample_rate",
             "-of", "json", file_path],
            capture_output=True, text=True, timeout=30,
        )
        info = json.loads(result.stdout)
        duration = float(info.get("format", {}).get("duration", 0))
        sample_rate = 48000
        for s in info.get("streams", []):
            if "sample_rate" in s:
                sample_rate = int(s["sample_rate"])
                break
        return duration, sample_rate
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        return 0, 48000


def split_audio(file_path: str, chunk_duration: int = MAX_CHUNK_DURATION_SEC) -> List[str]:
    """Разбить аудио на чанки через ffmpeg. Возвращает список путей."""
    tmpdir = tempfile.mkdtemp(prefix="stt_chunks_")
    ext = Path(file_path).suffix or ".ogg"
    pattern = os.path.join(tmpdir, f"chunk_%03d{ext}")

    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", file_path,
             "-f", "segment", "-segment_time", str(chunk_duration),
             "-c:a", "libopus", "-b:a", "64k", pattern],
            capture_output=True, timeout=300, check=True,
        )
    except FileNotFoundError:
        print("⚠️ ffmpeg не установлен — длинное аудио не будет разбито на чанки. Установите: apt install ffmpeg", file=sys.stderr)
        return [file_path]
    except subprocess.CalledProcessError:
        return [file_path]

    chunks = sorted(Path(tmpdir).glob(f"chunk_*{ext}"))
    return [str(c) for c in chunks] if chunks else [file_path]


def get_api_key() -> str:
    """Получить API-ключ из разных источников."""
    key = os.environ.get("YANDEX_API_KEY") or os.environ.get("YANDEX_SPEECHKIT_API_KEY")
    if key:
        return key

    # credentials.json в папке проекта
    cred_file = PROJECT_DIR / "credentials.json"
    if not cred_file.exists():
        # credentials.json в workspace (Hermes или OpenClaw)
        hermes_home = os.environ.get("HERMES_HOME")
        if hermes_home:
            cred_file = Path(hermes_home) / "credentials.json"
        else:
            home = Path.home()
            # Hermes: ~/.hermes/profiles/*/workspace/credentials.json
            profiles_dir = home / ".hermes" / "profiles"
            if profiles_dir.exists():
                for profile_dir in profiles_dir.iterdir():
                    candidate = profile_dir / "workspace" / "credentials.json"
                    if candidate.exists():
                        cred_file = candidate
                        break
            # OpenClaw: ~/.openclaw/workspace/credentials.json
            if not cred_file.exists():
                openclaw_cred = home / ".openclaw" / "workspace" / "credentials.json"
                if openclaw_cred.exists():
                    cred_file = openclaw_cred

    if cred_file.exists():
        try:
            with open(cred_file) as f:
                creds = json.load(f)
            key = creds.get("yandex_speechkit_api_key") or creds.get("yandex_api_key")
            if key:
                return key
        except (json.JSONDecodeError, IOError):
            pass

    print("❌ API-ключ не найден. Укажите YANDEX_API_KEY или добавьте в credentials.json", file=sys.stderr)
    print("   Получить ключ: https://aistudio.yandex.ru/ → Профиль → API-ключи", file=sys.stderr)
    sys.exit(1)


def recognize(file_path: str, lang: str = "ru-RU", sample_rate: Optional[int] = None,
              audio_format: Optional[str] = None, topic: Optional[str] = None) -> str:
    """
    Распознать речь из аудиофайла.
    Автоматически разбивает длинные файлы через ffmpeg.

    Возвращает распознанный текст.
    """
    api_key = get_api_key()
    file_path = Path(file_path)

    if not file_path.exists():
        print(f"❌ Файл не найден: {file_path}", file=sys.stderr)
        sys.exit(1)

    # Определить формат по расширению
    ext = file_path.suffix.lower()
    fmt_map = {
        ".ogg": "oggopus", ".opus": "oggopus",
        ".wav": "lpcm", ".mp3": "lpcm",
        ".flac": "lpcm", ".m4a": "lpcm",
    }
    if audio_format is None:
        audio_format = fmt_map.get(ext, "oggopus")

    # ffprobe для определения длительности и sample rate
    duration, detected_rate = get_audio_info(str(file_path))
    if sample_rate is None:
        sample_rate = detected_rate

    size_mb = file_path.stat().st_size / (1024 * 1024)
    print(f"🎤 Распознаю: {file_path.name} ({size_mb:.1f} MB, {duration:.1f}s)", file=sys.stderr)
    print(f"   Формат: {audio_format}, частота: {sample_rate} Hz, язык: {lang}", file=sys.stderr)

    # Разбивка если нужно
    needs_split = (size_mb > MAX_CHUNK_SIZE_BYTES / (1024 * 1024)) or \
                  (duration > MAX_CHUNK_DURATION_SEC)
    if needs_split:
        n_chunks = max(2, math.ceil(duration / MAX_CHUNK_DURATION_SEC))
        print(f"📎 Длинное аудио → разбиваю на ~{n_chunks} чанков", file=sys.stderr)
        chunks = split_audio(str(file_path))
    else:
        chunks = [str(file_path)]

    texts = []
    for i, chunk in enumerate(chunks, 1):
        if len(chunks) > 1:
            print(f"  Чанк {i}/{len(chunks)}...", file=sys.stderr)

        with open(chunk, "rb") as f:
            audio_data = f.read()

        # Auth: Api-Key header (для AI Studio ключей — напрямую)
        headers = {"Authorization": f"Api-Key {api_key}"}
        params = {
            "lang": lang,
            "format": audio_format,
            "sampleRateHertz": sample_rate,
        }
        if topic:
            params["topic"] = topic

        last_err = None
        for attempt in range(3):
            resp = requests.post(STT_URL, headers=headers, params=params,
                                 data=audio_data, timeout=60)
            if resp.status_code == 200:
                result = resp.json()
                text = result.get("result", "")
                if text:
                    texts.append(text)
                break
            last_err = f"HTTP {resp.status_code}: {resp.text[:300]}"
            if resp.status_code == 429 or resp.status_code >= 500:
                if attempt < 2:
                    delay = 2 * (2 ** attempt)
                    print(f"⚠️ Retry {attempt + 1}/3 after {delay}s: {last_err}", file=sys.stderr)
                    time.sleep(delay)
                    continue
            print(f"❌ Ошибка API: {last_err}", file=sys.stderr)
            break
        else:
            print(f"❌ Ошибка API после 3 попыток: {last_err}", file=sys.stderr)

    # Cleanup temp chunks
    if len(chunks) > 1 and chunks[0] != str(file_path):
        import shutil
        shutil.rmtree(os.path.dirname(chunks[0]), ignore_errors=True)

    full_text = " ".join(texts)
    if full_text:
        print(f"✅ Распознано: «{full_text}»", file=sys.stderr)
    else:
        print("⚠️ Текст не распознан", file=sys.stderr)

    return full_text


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Yandex SpeechKit STT")
    parser.add_argument("file", help="Аудиофайл для распознавания")
    parser.add_argument("--lang", default="ru-RU",
                        help="Язык (по умолчанию: ru-RU)")
    parser.add_argument("--format", choices=["oggopus", "lpcm"],
                        help="Формат аудио (oggopus, lpcm)")
    parser.add_argument("--rate", type=int,
                        help="Частота дискретизации (Hz)")
    parser.add_argument("--topic", default=None,
                        help="Тема (general, dates, names, geo, etc.)")

    args = parser.parse_args()

    import datetime
    with open("/tmp/yandex-stt.log", "a") as _f:
        _f.write(f"{datetime.datetime.now().isoformat()} STT called: {args.file} lang={args.lang}\n")

    result = recognize(
        file_path=args.file,
        lang=args.lang,
        sample_rate=args.rate,
        audio_format=args.format,
        topic=args.topic,
    )
    # Print transcript to stdout (diagnostics go to stderr)
    if result:
        print(result)
        with open("/tmp/yandex-stt.log", "a") as _f:
            _f.write(f"{datetime.datetime.now().isoformat()} STT result: {result[:100]}\n")
