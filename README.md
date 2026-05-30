# Yandex SpeechKit для AI-агентов

Голос для вашего AI-агента: **TTS** (текст → аудио) и **STT** (аудио → текст) через Yandex SpeechKit.

Работает с Hermes и OpenClaw. Интеграция с Telegram через маркер `MEDIA:`.

## Возможности

- 🗣️ **TTS** — текст → голосовое сообщение (.ogg)
- 👂 **STT** — распознавание голосовых сообщений
- 🔊 10 голосов + 3 эмоции (neutral, good, evil)
- ✂️ Автобрейк текста > 250 символов (API-лимит)
- 🔑 Ключ из env, credentials.json или workspace

## Быстрый старт

### 1. Получить API-ключ

1. Зайти на https://aistudio.yandex.ru/
2. Зарегистрироваться (дают грант **4000₽**)
3. Создать API-ключ: Профиль → API-ключи
4. Скопировать ключ

### 2. Установить зависимости

```bash
pip install requests
```

### 3. Скопировать скилл

```bash
cp -r yandex-speechkit/ ~/.hermes/profiles/ВАШ-ПРОФИЛЬ/skills/yandex-speechkit/
```

### 4. Сохранить ключ

```bash
cp credentials.example.json credentials.json
# Отредактировать credentials.json — вставить свой ключ
```

Или через переменную окружения:
```bash
export YANDEX_SPEECHKIT_API_KEY="ваш-ключ"
```

### 5. Проверить

```bash
# TTS
python3 scripts/tts.py "Привет! Я готов к голосовому общению" --voice alena

# STT
python3 scripts/stt.py audio/tts_alena_*.ogg
```

## Как агенту отвечать голосом

**Правило:** одно сообщение, не два. `MEDIA:` вставляется в конец обычного ответа:

```
Текстовый ответ на вопрос...

MEDIA:/полный/путь/к/audio.ogg
```

**Не использовать** `send_message` для голосовых — будут дубликаты.

## Голоса

| Голос | Пол | Характер |
|---|---|---|
| `alena` | Женский | Нейтральный ✅ (по умолчанию) |
| `filipp` | Мужской | Нейтральный |
| `ermil` | Мужской | Добрый |
| `jane` | Женский | Грустный |
| `oksana` | Женский | Новостной |
| `omazh` | Женский | Злой |
| `zahar` | Мужской | Нейтральный |
| `marina` | Женский | Шёпот (премиум) |
| `masha` | Женский | Детский (премиум) |
| `tatyana` | Женский | Brand Voice |

Эмоции: `neutral`, `good`, `evil` (параметр `--emotion`)

## Скрипты

```bash
# TTS: текст → аудио
python3 scripts/tts.py "Текст" [--voice alena] [--emotion good] [--audio-dir /path]

# STT: аудио → текст
python3 scripts/stt.py path/to/audio.ogg [--lang ru-RU]

# Обёртка для Hermes (выдаёт MEDIA: путь)
python3 scripts/kiri_voice.py "Текст ответа" [--voice alena]
```

## Структура

```
yandex-speechkit/
├── SKILL.md                  ← инструкция для агента
├── README.md                 ← этот файл
├── LICENSE
├── credentials.example.json  ← шаблон ключа
├── .gitignore
├── scripts/
│   ├── tts.py                ← текст → аудио
│   ├── stt.py                ← аудио → текст
│   └── kiri_voice.py         ← обёртка MEDIA: для Hermes
└── references/
    └── review-findings.md    ← история ревью, баги, почему так сделано
```

## Цены

- TTS: ~0.5–1.5 ₽ за 1000 символов
- STT: ~0.5–1.0 ₽ за минуту аудио
- Грант 4000₽ для новых пользователей
- Pay-as-you-go, без минимального платежа

## Ссылки

- Yandex AI Studio: https://aistudio.yandex.ru/
- SpeechKit API: https://cloud.yandex.ru/docs/speechkit/
- NeiroHost: https://neirohost.ru

## Лицензия

MIT
