---
name: yandex-speechkit
description: "Yandex SpeechKit для Telegram-агентов: голосовые ответы (TTS) и распознавание голосовых сообщений (STT). Чистый скилл, никакой телефонии."
version: 3.4
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
python3 scripts/tts.py "Привет! Я готов к голосовому общению"
```
→ Создаст `.ogg` файл в папке `audio/`
→ Выведет `MEDIA:/полный/путь/к/audio.ogg`

### 6. Проверить STT
```bash
python3 scripts/stt.py audio/tts_oksana_Привет.*.ogg
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

MEDIA:/root/.hermes/profiles/профиль/skills/yandex-speechkit/audio/tts_oksana_Ответ.ogg
```

### Когда отвечать голосом?

- Если пользователь прислал голосовое → отвечать голосом
- Если пользователь просит голосовой ответ
- По умолчанию — текст

### Для OpenClaw-агентов

OpenClaw **не использует** `MEDIA:` в stdout. Вместо этого:

1. Сгенерировать аудио: `python3 scripts/tts.py "текст"`
2. Получить путь к файлу из stdout (строка после `MEDIA:` или из `✅ Сохранено:`)
3. Отправить через message tool:

```
message(action="send", filePath="/path/to/audio.ogg", asVoice=true, buttons=[])
```

**MEDIA:** в stdout можно игнорировать — это для Hermes. OpenClaw берёт путь к файлу.

### Об OpenClaw и MEDIA:

Строка `MEDIA:` в выводе tts.py **безопасна** для OpenClaw — агент просто её игнорирует и берёт путь из строки `✅ Сохранено:`. Не нужно удалять `MEDIA:` из скриптов — она нужна Hermes-агентам.

## Как агент понимает голосовые

Hermes gateway **автоматически** транскрибирует входящие голосовые сообщения. Провайдер STT настраивается в `config.yaml`:

- **local** (по умолчанию) — faster-whisper. Плохо работает с русским языком.
- **yandex** (рекомендуется для русского) — command-type provider через `stt.py`. Настройка ниже.
- **groq/openai/mistral** — облачные Whisper API.

После настройки Yandex STT (см. секцию ниже) gateway вызывает `stt.py` как внешнюю команду для каждого входящего голосового. Транскрипция приходит в контексте агента автоматически.

**Не нужно** вручную искать аудиофайлы и прогонять через `stt.py` — это только для тестов.

## API Reference (из официальной документации)

### TTS API

- **URL**: `https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize`
- **Method**: POST с `application/x-www-form-urlencoded` (НЕ JSON!)
- **Лимит текста**: **5000 символов** за один запрос
- **Голос по умолчанию**: `oksana`
- **Формат по умолчанию**: `oggopus`
- **Языки**: `ru-RU` (default), `en-US`, `tr-TR`

**Голоса:**
- `oksana` — Женский (по умолчанию)
- `alena` — Женский
- `filipp` — Мужской
- `ermil` — Мужской
- `jane` — Женский
- `omazh` — Женский
- `zahar` — Мужской
- `marina` — Премиум
- `masha` — Премиум
- `tatyana` — Премиум

**Параметры:**
- `speed`: 0.1–3.0 (default 1.0)
- `sampleRateHertz`: 48000 (default), 16000, 8000
- `format`: `oggopus` (default) или `lpcm`
- `ssml`: SSML-разметка (альтернатива `text`)
- `lang`: язык

**SSML-фичи:**
- Ударение: `+` перед ударной гласной (напр. `contr+ol`)
- Пауза: `-` между словами

### STT API

- **URL**: `https://stt.api.cloud.yandex.net/speech/v1/stt:recognize`
- **Method**: POST с raw audio body, параметры в query string
- **Лимиты**: 1 MB, 30 секунд, 1 канал
- **Языки**: `ru-RU` (default), `en-US`, `tr-TR`
- **Формат**: `oggopus` (default) или `lpcm`
- **Доп. параметры**: `topic` (general default), `profanityFilter`, `sampleRateHertz`

**Для длинного аудио (>30 сек):**
Асинхронный API: `https://transcribe.api.cloud.yandex.net/speech/stt/v2/longRunningRecognize`
(Скрипт stt.py автоматически разбивает на чанки по 25 сек через ffmpeg.)

### Авторизация

**Метод 1: AI Studio API-ключ (рекомендуется)**
- Заголовок: `Api-Key: ваш-ключ`
- Не требует обмена токенов
- Получить: https://aistudio.yandex.ru/ → Профиль → API-ключи

**Метод 2: IAM-токен (для service account)**
- Получить JWT → обменять на IAM-токен → `Authorization: Bearer <token>`
- Endpoint: `https://iam.api.cloud.yandex.net/iam/v1/tokens`
- Токен живёт 12 часов

Скрипты используют **Метод 1** (Api-Key) — достаточно для AI Studio ключей.

## Скрипты

### tts.py — текст → аудио
```bash
python3 scripts/tts.py "Текст для озвучки" [--voice oksana] [--format oggopus] [--speed 1.0] [--audio-dir /path]
```
- Создаёт `.ogg` файл в `audio/`
- Возвращает путь к файлу в stdout (строка `MEDIA:...`)
- Автоматически разбивает текст > 5000 символов на части и склеивает
- Retry: 3 попытки с exponential backoff на 429/5xx

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
python3 scripts/kiri_voice.py "Текст ответа" [--voice oksana] [--format oggopus]
```
- Генерирует аудио и возвращает готовый `MEDIA:...` путь
- Удобно для вставки в ответ агента
- **Примечание:** имя `kiri_voice.py` — историческое (от агента "Кири"). Скрипт универсален и работает на любой платформе. OpenClaw-агенты могут использовать его для генерации аудио, а путь брать из строки `✅ Сохранено:`

## PITFALLS

### TTS API: НЕ JSON
Yandex TTS v1 **не принимает JSON**. Ошибка «unsupported content-type: application/json» = передают `json=payload`. Нужно: `requests.post(url, data=params)` — form-data. Скрипт уже делает правильно.

### MEDIA: отдельной строкой
`MEDIA:` должен быть на отдельной строке, не внутри markdown-форматирования. Иначе Telegram не распознает как файл.

### send_message = дубликаты
Если вставить `MEDIA:` в обычный ответ — gateway доставит одно сообщение. Если вызвать `send_message` отдельно — будут два сообщения. Всегда вставлять `MEDIA:` в ответ агента.

### Кириллица в имени файла ломает MEDIA: доставку
Python `\w` матчит Unicode-символы, включая кириллицу. Если текст на русском — имя файла `tts_oksana_Привет_мир.ogg` содержит не-ASCII символы, и Telegram gateway не может его обработать.
**Решение:** только ASCII в именах файлов: `[^a-zA-Z0-9_-]`. Скрипт `tts.py` уже исправлен — генерирует чистые имена.

### Лимит символов TTS: 5000
Максимум **5000 символов** за один запрос к TTS API. Скрипт `tts.py` автоматически разбивает длинные тексты на части и склеивает аудио. Но лучше держать ответы компактными — длинные голосовые неудобно слушать.

### Формат по умолчанию: oggopus
Telegram голосовые сообщения требуют `.ogg` (Opus). Используйте `--format oggopus` (по умолчанию).

### credentials.json — поиск ключа
Скрипты ищут ключ в порядке приоритета:
1. `YANDEX_API_KEY` (переменная окружения)
2. `credentials.json` рядом с SKILL.md (директория проекта)
3. `credentials.json` в workspace текущего Hermes-профиля (`$HERMES_HOME/credentials.json`)
4. `credentials.json` в workspace OpenClaw (`~/.openclaw/workspace/credentials.json`)

### Python 3.8+
Скрипты используют `Optional[str]` из `typing` — совместимо с Python 3.8+.

### Зависимости
Нужен `requests`: `pip install requests`. Обычно уже стоит, но если нет — скрипт упадёт с `ModuleNotFoundError`.

### FFmpeg для STT
Для распознавания длинных аудио (>25 сек) нужен `ffmpeg` и `ffprobe`. Установка: `apt install ffmpeg` или `brew install ffmpeg`.

### stdout command provider — только текст!
Когда `stt.py` используется как command-type STT provider в Hermes (`stt.providers.yandex.type: command`), **stdout = только распознанный текст**. Все диагностические сообщения (🎤, ✅, ⚠️) обязаны идти в `stderr` (`print(..., file=sys.stderr)`). Если в stdout попадёт мусор — Hermes передаст его агенту как транскрипцию, и ответ будет испорчен. Скрипт `stt.py` уже исправлен (v3.3), но если модифицируешь — проверяй `2>/dev/null` при тесте.

### credentials.json — два имени ключа
Скрипты проверяют оба имени: `yandex_speechkit_api_key` и `yandex_api_key`. В документации AI Studio ключ называется `YANDEX_API_KEY`, но в инструкциях установки скилла используется `yandex_speechkit_api_key`. Оба работают. Приоритет: env var → credentials.json рядом со скриптом → Hermes home → OpenClaw home.

### Проверка через лог-файл
Hermes не пишет в логи какой STT провайдер обработал голосовое. Добавить в `stt.py` блок логирования в `/tmp/yandex-stt.log` — единственный способ убедиться что Yandex STT вызывается, а не Whisper.

## Цены (ориентировочно)ча
Скрипты проверяют оба имени: `yandex_speechkit_api_key` и `yandex_api_key`. В документации AI Studio ключ называется `YANDEX_API_KEY`, но в инструкциях установки скилла используется `yandex_speechkit_api_key`. Оба работают. Приоритет: env var → credentials.json рядом со скриптом → Hermes home → OpenClaw home.

### Проверка через лог-файл
Hermes не пишет в логи какой STT провайдер обработал голосовое. Добавить в `stt.py` блок логирования в `/tmp/yandex-stt.log` — единственный способ убедиться что Yandex STT вызывается, а не Whisper.

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
│   ├── tts.py         ← текст → аудио (автобreak >5000 символов)
│   ├── stt.py         ← аудио → текст (автобreak >25 сек)
│   └── kiri_voice.py  ← обёртка MEDIA: для Hermes
├── references/
│   ├── review-findings.md ← история ревью, найденные баги, почему так сделано
│   └── hermes-stt-integration.md ← как Hermes вызывает command STT, плейсхолдеры, pitfalls
└── audio/             ← сгенерированные .ogg файлы
```

## Настройка STT через Yandex в Hermes

По умолчанию Hermes использует Whisper (local/Groq/OpenAI) для распознавания голосовых сообщений. Yandex SpeechKit лучше подходит для русского языка.

### Как это работает

Hermes поддерживает **command-type STT providers** — кастомные shell-команды как бэкенд для распознавания. Скрипт `stt.py` вызывается как внешняя команда, получает путь к аудиофайлу и печатает распознанный текст в stdout.

### Настройка

1. Убедиться что API-ключ есть в `~/.hermes/.env`:
```bash
echo "YANDEX_API_KEY=ваш-ключ" >> ~/.hermes/.env
```

2. Добавить Yandex как command STT provider:
```bash
hermes config set stt.providers.yandex.type command
hermes config set stt.providers.yandex.command 'python3 /root/.hermes/skills/yandex-speechkit/scripts/stt.py {input_path} --lang {language}'
hermes config set stt.providers.yandex.language ru-RU
hermes config set stt.providers.yandex.format txt
hermes config set stt.providers.yandex.timeout 120
```

3. Переключить STT на Yandex:
```bash
hermes config set stt.provider yandex
```

4. Перезапустить gateway:
```bash
hermes gateway restart
```

### Плейсхолдеры команды

| Плейсхолдер | Значение |
|-------------|----------|
| `{input_path}` | Путь к аудиофайлу |
| `{output_path}` | Путь для записи результата (не используется — stdout) |
| `{language}` | Код языка (из config, по умолчанию `ru-RU`) |
| `{model}` | Модель (не используется Yandex) |

### Проверка

```bash
# Должен вывести только текст (диагностика идёт в stderr)
python3 /root/.hermes/skills/yandex-speechkit/scripts/stt.py /path/to/audio.ogg --lang ru-RU 2>/dev/null
```

### Возврат на Whisper

```bash
hermes config set stt.provider local
hermes gateway restart
```

### Troubleshooting: какой провайдер используется?

Hermes не пишет в логи какой STT провайдер обработал голосовое. Чтобы проверить:

1. **Добавить логирование в stt.py** (в блок `if __name__ == "__main__"`):
```python
import datetime
with open("/tmp/yandex-stt.log", "a") as _f:
    _f.write(f"{datetime.datetime.now().isoformat()} STT called: {args.file} lang={args.lang}\n")
```

2. Отправить голосовое сообщение агенту.

3. Проверить лог:
```bash
cat /tmp/yandex-stt.log
```
Если файл пуст или не существует — Yandex STT **не вызывался** (gateway использует другой провайдер).

4. **Проверить stdout vs stderr** при ручном тесте:
```bash
python3 scripts/stt.py /path/to/audio.ogg 1>/tmp/out.txt 2>/tmp/err.txt
cat /tmp/out.txt  # ← только текст транскрипции
cat /tmp/err.txt  # ← диагностика (🎤, ✅)
```
Если в stdout есть эмодзи-строки — сломан redirect в stderr, Hermes получит мусор.

## Установка на OpenClaw

### Шаги

1. Скопировать скилл в `~/.openclaw/workspace/skills/yandex-speechkit/`
2. Создать `credentials.json` с API-ключом (рядом с SKILL.md или в `~/.openclaw/workspace/credentials.json`)
3. Установить зависимости: `pip install requests`
4. Обновить `TOOLS.md` (шаблон ниже)

### Шаблон TOOLS.md для OpenClaw

Добавить в `TOOLS.md` агента:

```markdown
## Yandex SpeechKit — голосовой модуль

### TTS (текст → голос)
Сгенерировать аудио:
```
python3 ~/.openclaw/workspace/skills/yandex-speechkit/scripts/tts.py "Текст для озвучки" --voice oksana
```
Путь к файлу будет в stdout (строка `✅ Сохранено:`).

Отправить голосовое:
```
message(action="send", filePath="/path/to/audio.ogg", asVoice=true, buttons=[])
```

### STT (голос → текст)
Распознать аудио:
```
python3 ~/.openclaw/workspace/skills/yandex-speechkit/scripts/stt.py /path/to/audio.ogg
```

### Голоса
- oksana (по умолчанию), alena, filipp, ermil, jane, omazh, zahar
- Формат: oggopus (по умолчанию, для Telegram)
- Лимит: 5000 символов за запрос
```
