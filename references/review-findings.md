# Review Findings — yandex-speechkit v1→v2→v3

## Что было не так в оригинале (до исправления)

### Critical
1. **tts.py не печатал `MEDIA:`** — kiri_voice.py искал `MEDIA:` в stdout, но tts.py его не выводил. Обёртка никогда не находила файл. Исправлено: добавлена строка `MEDIA:{path}` в вывод tts.py.

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

## v3 — major corrections (по официальной документации)

### Critical corrections from official Yandex Cloud docs

14. **Текстовый лимит TTS: 5000 символов, НЕ 250** — Предыдущие версии основывались на неверной информации. Официальная документация Yandex Cloud и SDK (`tikhonp/yandex-speechkit-lib-python`) указывают лимит **5000 символов** на запрос. Исправлено: `MAX_CHARS = 5000` в tts.py и SKILL.md.

15. **Голос по умолчанию: oksana, НЕ alena** — Официальная документация: голос по умолчанию — `oksana`. Предыдущие версии использовали `alena`. Исправлено в tts.py, kiri_voice.py, SKILL.md.

16. **Формат по умолчанию: oggopus, НЕ mp3** — API принимает только `oggopus` и `lpcm`. Формат `mp3` не поддерживается (был в списке форматов, но не в API). Исправлено: убран `mp3` из FORMATS, формат по умолчанию `oggopus`.

17. **Авторизация: Api-Key header напрямую** — Для AI Studio ключей не нужен IAM-токен. Достаточно `Authorization: Api-Key <ключ>`. Предыдущая документация была неполной. Добавлено описание двух методов авторизации в SKILL.md.

18. **SSML поддержка** — API поддерживает параметр `ssml` как альтернативу `text`. Документировано в SKILL.md.

19. **Эмоция убрана из параметров по умолчанию** — API принимает `emotion`, но это не основной параметр. Убран из kiri_voice.py для упрощения.

20. **Environment variable: YANDEX_API_KEY** — Стандартное имя переменной окружения. Добавлено как первичный источник ключа (в дополнение к YANDEX_SPEECHKIT_API_KEY).

## Что тестировалось

### v1-v2
- ✅ TTS (короткий текст, alena, emotion=good)
- ✅ STT (обратное распознавание сгенерированного .ogg)
- ✅ kiri_voice.py (обёртка → MEDIA:)
- ✅ Автобreak (319 символов → 2 части → склейка → 204.8 KB)
- ✅ MEDIA: доставка в Telegram (голосовое сообщение дошло)

### v3 (tested)
- ✅ TTS с голосом oksana (новый default)
- ✅ STT с auto-chunking (ffprobe + ffmpeg)
- ✅ kiri_voice.py (обёртка → MEDIA:)
- ✅ Синтаксис Python: все файлы проходят `ast.parse()`
- ✅ MEDIA: доставка в Telegram (голосовое сообщение дошло)
- ⏳ TTS с текстом >5000 символов (новый лимит)

### v3.1 (bug fix)
21. **Кириллица в имени файла ломает MEDIA: доставку** — `\w` в Python regex матчит Unicode, включая кириллицу. Файл `tts_oksana_Привет_мир.ogg` не доставляется в Telegram. Исправлено на `[^a-zA-Z0-9_-]` + fallback на timestamp.
- Нашёл: Vector (агент на Hermes, SaaS сервер)

## Источники информации (v3)

- `tikhonp/yandex-speechkit-lib-python` — официальный Python SDK
- `yandex-cloud-examples` — примеры использования API
- https://yandex.cloud/ru/docs/speechkit/tts/
- https://yandex.cloud/ru/docs/speechkit/stt/

## Ключ API
- Сохранён в `credentials.json` рядом с SKILL.md
- Источник: Леонид, 28.05.2026
- Документация: https://aistudio.yandex.ru/docs/en/ai-studio/quickstart/

## v3.4 — Hermes STT integration

21. **stt.py как command STT provider** — `stt.py` подключён как внешняя команда в `config.yaml` (`stt.providers.yandex.type: command`). Все `print()` диагностики → `file=sys.stderr`, stdout = только транскрипт.

22. **Лог-файл** — stt.py пишет invocation log в `/tmp/yandex-stt.log` для подтверждения что Yandex STT вызывается.

23. **Duplicate content** — строки 275-279 в SKILL.md были мусорным дубликатом с артефактом "ча". Исправлено.

24. **ffmpeg warning** — `split_audio()` теперь предупреждает если ffmpeg не установлен.

25. **Troubleshooting** — заменён "добавь лог вручную" на "лог уже встроен с v3.4".

## v3.5 — OpenClaw integration

26. **OpenClaw STT config** — добавлена секция "Настройка STT в OpenClaw" с JSON-конфигом `tools.media.audio` и CLI-провайдером. Плейсхолдер `{{MediaPath}}` подтверждён документацией OpenClaw.

27. **TOOLS.md template** — обновлён шаблон с полными инструкциями (credentials, message-отправка, зависимости, автотранскрипция).

28. **ffmpeg dependency** — добавлен в зависимости и Quick Start, и в шаблон TOOLS.md.

29. **PITFALLS** — добавлены: "ffmpeg обязателен для STT" и "OpenClaw: MEDIA: в stdout не используется".

30. **Установка на OpenClaw** — шаги 5-7: настройка tools.media.audio, restart gateway, проверка лога.

## v3.6 — voice delivery fix

31. **[[audio_as_voice]] tag** — tts.py и kiri_voice.py теперь выводят `[[audio_as_voice]]` перед `MEDIA:`. Без этого тега Hermes gateway отправляет .ogg как документ, а не как голосовое сообщение. Нашёл агент на Hermes (проверено в gateway/platforms/base.py:2609).

32. **Whisper BCP-47 pitfall** — faster_whisper принимает ISO 639-1 (`ru`), не BCP-47 (`ru-RU`). Добавлен pitfall.

33. **SKILL.md** — обновлён алгоритм "Как агенту отвечать голосом" с `[[audio_as_voice]]` тегом.

**Отвергнуто:**
- Пункт 5: "{{MediaPath}} — двойные скобки = литерал в Hermes". Агент путает Hermes и OpenClaw. Документация OpenClaw явно использует `{{MediaPath}}` как плейсхолдер.
