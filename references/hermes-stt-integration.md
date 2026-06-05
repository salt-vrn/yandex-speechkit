# Hermes STT Integration — Command Provider

## Как это работает

Hermes gateway автоматически транскрибирует входящие голосовые сообщения.
Провайдер STT настраивается в `config.yaml` секции `stt:`.

### Command-type provider

Hermes поддерживает `type: command` — кастомные shell-команды как бэкенд STT.
При входящем голосовом:

1. Gateway скачивает аудиофайл (`.ogg`)
2. Рендерит command template с плейсхолдерами
3. Запускает команду через `subprocess` (shell=True)
4. Читает stdout — это и есть транскрипт
5. Передаёт текст агенту как содержимое голосового сообщения

### Плейсхолдеры

| Плейсхолдер    | Значение                                    |
|----------------|---------------------------------------------|
| `{input_path}` | Абсолютный путь к аудиофайлу                |
| `{output_path}`| Путь для записи результата (мы не используем — пишем в stdout) |
| `{output_dir}` | Родительская директория output_path         |
| `{language}`   | Код языка из config (default `en`)          |
| `{model}`      | Модель (пусто если не задана)               |
| `{format}`     | Формат вывода (txt/json/srt/vtt)            |

### Важно: stdout = только транскрипт

Hermes читает stdout как текст транскрипции. Если в stdout попадёт
диагностика (эмодзи, логи) — агент получит мусор вместо текста.

**Правило:** все `print()` с диагностикой → `file=sys.stderr`.
В stdout — только распознанный текст.

### Конфиг config.yaml

```yaml
stt:
  enabled: true
  provider: yandex
  providers:
    yandex:
      type: command
      command: python3 /root/.hermes/skills/yandex-speechkit/scripts/stt.py {input_path} --lang {language}
      language: ru-RU
      format: txt
      timeout: 120
```

### Лог-файл

stt.py пишет лог в `/tmp/yandex-stt.log` при каждом вызове.
Проверить что Yandex используется:
```bash
cat /tmp/yandex-stt.log
```
Если файл пуст — gateway использует другой провайдер.

### Возврат на Whisper

```bash
hermes config set stt.provider local
hermes gateway restart
```

### Pitfall: обновляйте ВСЕ файлы

При обновлении скилла из репозитория копируйте **все** файлы, не только SKILL.md. Если скрипты (`stt.py`, `tts.py`) устареют — command provider может отдавать Hermes'у эмодзи-строки вместо чистого текста. Проверяй: `python3 stt.py file.ogg 2>/dev/null` → должен быть только текст.
