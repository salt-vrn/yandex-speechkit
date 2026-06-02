---
name: yandex-speechkit
description: "Yandex SpeechKit для Telegram-агентов: голосовые ответы (TTS) и распознавание голосовых сообщений (STT). Чистый скилл, никакой телефонии."
version: 2.1
triggers:
  - yandex
  - speechkit
  - голос
  - озвучить
  - озвучь
  - скажи голосом
  - распознай голосовое
  - голосовое сообщение
  - tts
  - stt
  - speech
  - voice
  - синтез речи
  - распознавание речи
---

# Yandex SpeechKit — голос для Telegram-агента

## Что это

Скилл для подключения Yandex SpeechKit к агенту Hermes. Позволяет:
- **Отвечать голосом** (TTS — текст → аудио)
- **Понимать голосовые сообщения** (STT — аудио → текст)
- Встраивать `MEDIA:.ogg` в ответы Telegram

## Быстрый старт

### 1. Получить API-ключ
1. Идти на https://aistudio.yandex.ru/
2. Зарегистрироваться (дают грант 4000₽)
3. Создать API-ключ в разделе «Профиль → API-ключи»
4. Скопировать ключ (секретный)

### 2. Установить зависимости
```bash
pip install requests
```

### 3. Установить скрипты
Скрипты лежат в `scripts/` рядом с этим SKILL.md:
- `tts.py` — текст → аудио (.ogg)
- `stt.py` — аудио → текст
- `kiri_voice.py` — обёртка для Hermes (выдаёт MEDIA: путь)

Скопировать в skills своего профиля:
```bash
cp -r yandex-speechkit/ ~/.hermes/profiles/ВАШ-ПРОФИЛЬ/skills/yandex-speechkit/
```

### 4. Сохранить ключ
```bash
echo '{"yandex_speechkit_api_key": "ваш-ключ"}' > ~/.hermes/profiles/ВАШ-ПРОФИЛЬ/skills/yandex-speechkit/credentials.json
```

Или добавить в уже существующий `credentials.json`:
```json
{
  "yandex_speechkit_api_key": "ваш-ключ"
}
```

### 5. Проверить TTS
```bash
cd ~/.hermes/profiles/ВАШ-ПРОФИЛЬ/skills/yandex-speechkit
python3 scripts/tts.py "Привет! Я готов к голосовому общению" --voice alena
```
→ Создаст `.ogg` файл в папке `audio/`
→ Выведет `MEDIA:/полный/путь/к/audio.ogg`

### 6. Проверить STT
```bash
python3 scripts/stt.py audio/tts_alena_Привет.*.ogg
```
→ Выведет распознанный текст

## Как агенту отвечать голосом

### ПРАВИЛО — ОДНО сообщение, не два

Агент **НЕ** использует `send_message` для отправки голосовых.
`MEDIA:` вставляется прямо в конец обычного ответа — gateway сам доставит.

`send_message` + обычный ответ = **ДУБЛИКАТЫ** (два сообщения в Telegram).

### Алгоритм

1. Написать текстовый ответ (как обычно)
2. Вызвать `python3 scripts/tts.py "текст ответа"` — получить путь к .ogg
3. Вставить `MEDIA:/полный/путь/к/audio.ogg` в конец ответа — **отдельной строкой, не внутри markdown**

**Пример:**
```
Ответ на вопрос...

MEDIA:/root/.hermes/profiles/профиль/skills/yandex-speechkit/audio/tts_alena_Ответ.ogg
```

### Когда отвечать голосом?

- Если пользователь прислал голосовое → отвечать голосом
- Если пользователь просит голосовой ответ
- По умолчанию — текст

## Как агент понимает голосовые

Hermes gateway **автоматически** транскрибирует входящие голосовые сообщения через встроенный Whisper. Транскрипция приходит в контексте агента.

**Не нужно** вручную искать аудиофайлы и прогонять через `stt.py` — это только для тестов.

## Скрипты

### tts.py — текст → аудио
```bash
python3 scripts/tts.py "Текст для озвучки" [--voice alena] [--emotion good] [--audio-dir /path]
```
- Создаёт `.ogg` файл в `audio/`
- Возвращает путь к файлу в stdout (строка `MEDIA:...`)
- Автоматически разбивает текст > 250 символов на части и склеивает

### stt.py — аудио → текст
```bash
python3 scripts/stt.py path/to/audio.ogg [--lang ru-RU] [--format oggopus] [--rate 48000]
```
- Принимает `.ogg`, `.wav`, `.mp3`, `.flac`, `.m4a`
- Автоматически разбивает длинные файлы (>25 сек / >900 KB) через ffmpeg
- Sample rate определяется автоматически через ffprobe
- Retry: 3 попытки с exponential backoff на 429/5xx
- Возвращает распознанный текст в stdout

### kiri_voice.py — обёртка для Hermes
```bash
python3 scripts/kiri_voice.py "Текст ответа" [--voice alena] [--emotion good]
```
- Генерирует аудио и возвращает готовый `MEDIA:...` путь
- Удобно для вставки в ответ агента

## Голоса

- `alena` — Женский, нейтральный ✅ (по умолчанию)
- `filipp` — Мужской, нейтральный
- `ermil` — Мужской, добрый
- `jane` — Женский, грустный
- `oksana` — Женский, новостной
- `omazh` — Женский, злой
- `zahar` — Мужской, нейтральный
- `marina` — Женский, шёпот (премиум)
- `masha` — Женский, детский (премиум)
- `tatyana` — Женский, для Brand Voice

Эмоции: `neutral`, `good`, `evil` (параметр `--emotion`)

## PITFALLS

### TTS API: НЕ JSON
Yandex TTS v1 **не принимает JSON**. Ошибка «unsupported content-type: application/json» = передают `json=payload`. Нужно: `requests.post(url, data=params)` — form-data. Скрипт уже делает правильно.

### MEDIA: отдельной строкой
`MEDIA:` должен быть на отдельной строке, не внутри markdown-форматирования. Иначе Telegram не распознает как файл.

### send_message = дубликаты
Если вставить `MEDIA:` в обычный ответ — gateway доставит одно сообщение. Если вызвать `send_message` отдельно — будут два сообщения. Всегда вставлять `MEDIA:` в ответ агента.

### Лимит символов TTS
Максимум **250 символов** за один запрос к TTS API. Скрипт `tts.py` автоматически разбивает длинные тексты на части и склеивает аудио. Но лучше держать ответы компактными — длинные голосовые неудобно слушать.

### credentials.json — поиск ключа
Скрипты ищут ключ в порядке приоритета:
1. `YANDEX_SPEECHKIT_API_KEY` (переменная окружения)
2. `credentials.json` рядом с SKILL.md (директория проекта)
3. `credentials.json` в workspace текущего Hermes-профиля (`$HERMES_HOME/credentials.json`)

### Python 3.8+
Скрипты используют `Optional[str]` из `typing` — совместимо с Python 3.8+.

### Зависимости
Нужен `requests`: `pip install requests`. Обычно уже стоит, но если нет — скрипт упадёт с `ModuleNotFoundError`.

## Цены (ориентировочно)

- TTS: ~0.5–1.5 ₽ за 1000 символов
- STT: ~0.5–1.0 ₽ за минуту аудио
- Грант 4000₽ для новых пользователей
- Pay-as-you-go, без минимального платежа

## Структура

```
yandex-speechkit/
├── SKILL.md           ← этот файл
├── credentials.json   ← API-ключ (создать вручную)
├── scripts/
│   ├── tts.py         ← текст → аудио (с автобreak > 250 символов)
│   ├── stt.py         ← аудио → текст
│   └── kiri_voice.py  ← обёртка MEDIA: для Hermes
├── references/
│   └── review-findings.md ← история ревью, найденные баги, почему так сделано
└── audio/             ← сгенерированные .ogg файлы
```
