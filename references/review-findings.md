# Review Findings — yandex-speechkit v1→v2

## Что было не так в оригинале (до исправления)

### Critical
1. **tts.py не печатал `MEDIA:`** — kiri_voice.py искал `MEDIA:` в stdout, но tts.py его не выводил. Обёртка永远 не находила файл. Исправлено: добавлена строка `MEDIA:{path}` в вывод tts.py.

2. **Hardcoded `kiri` профиль** — tts.py и stt.py искали credentials.json по пути `~/.hermes/profiles/kiri/workspace/credentials.json`. Не работало для других профилей. Исправлено: используется `$HERMES_HOME` или обход `~/.hermes/profiles/*/workspace/`.

3. **250 символов — молча падал** — SKILL.md описывал лимит 250 символов, но tts.py не разбивал текст. Длинные тексты получали ошибку API. Исправлено: `_split_text()` с разбивкой по предложениям/словам и склейкой аудио.

### Medium
4. **STT_ASYNC_URL мёртвый код** — объявлен, но не использовался. Убран.

5. **Таблица в SKILL.md** — Telegram не поддерживает markdown-таблицы. Переделано в bullet list.

6. **Нет `pip install requests`** — зависимости не указаны. Добавлено в быстрый старт.

### Minor
7. **`str | None`** — Python 3.10+ аннотация. Исправлено на `Optional[str]` (Python 3.8+).

8. **`--audio-dir`** — audio/ создавался рядом со скриптом, не было возможности переопределить. Добавлен параметр.

## v2 — fixes (по замечаниям ревью)

9. **Голос по умолчанию** — kiri_voice.py использовал `filipp`, SKILL.md и tts.py — `alena`. Выровнено на `alena` везде.

10. **Sample rate для .m4a/.flac** — hardcoded fallback 48000. Исправлено: ffprobe определяет sample rate из метаданных любого формата.

11. **Retry** — API вызовы без retry, падение на 429/5xx. Добавлен retry: 3 попытки, exponential backoff (2s → 4s), для tts.py и stt.py.

12. **Triggers** — SKILL.md не имел triggers в frontmatter, агент не знал когда загружать скилл. Добавлено 15 триггеров.

13. **STT chunking** — лимит API ~30 сек / 1 MB, голосовые в Telegram до 1-2 минут. Добавлена автоматическая разбивка через ffmpeg (25 сек / 900 KB), склейка результатов.

## Ключ API
- Сохранён в `credentials.json` рядом с SKILL.md
- Источник: Леонид, 28.05.2026
- Документация: https://aistudio.yandex.ru/docs/en/ai-studio/quickstart/

## Что тестировалось
- ✅ TTS (короткий текст, alena, emotion=good)
- ✅ STT (обратное распознавание сгенерированного .ogg)
- ✅ kiri_voice.py (обёртка → MEDIA:)
- ✅ Автобreak (319 символов → 2 части → склейка → 204.8 KB)
- ✅ MEDIA: доставка в Telegram (голосовое сообщение дошло)
