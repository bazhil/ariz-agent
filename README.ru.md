# ARIZAgent

Открытый прототип: прогон технической / изобретательской задачи через **АРИЗ-85-В** в чате (**OpenWebUI**), оркестрация в **n8n**, LLM (например **GigaChat**), опционально поиск по патентам (**Qdrant** + небольшой FastAPI-сервис).

> **English:** [README.md](README.md) · **Настройка (Linux / Windows / macOS):** [docs/SETUP.md](docs/SETUP.md) · **Быстрый старт:** [docs/QUICKSTART_ru.md](docs/QUICKSTART_ru.md) · **Патенты:** [docs/GOOGLE_PATENTS.md](docs/GOOGLE_PATENTS.md) · **Микросервисы:** [docs/SERVICES.md](docs/SERVICES.md)

Это **учебный и экспериментальный прототип**, не коммерческая экспертиза по ТРИЗ и не замена патентному поверенному.

Источник методики: [АРИЗ-85-В (Официальный Фонд Г.С. Альтшуллера)](https://altshuller.ru/triz/ariz85v.asp).

---

## Что умеет

1. Вы описываете задачу обычным языком в чате.
2. n8n выполняет многошаговый пайплайн **АРИЗ-85-В** (`n8n_workflows/ariz_85_v.json`).
3. Вы получаете структурированный отчёт (постановка, ИКР, идеи решений, проверки).
4. По желанию идеи сопоставляются с патентами, которые вы сами загрузили в Qdrant.

**ИИ не заменяет человека.** Задача и критическая оценка результата — за вами. Система лишь ведёт разбор по маршруту АРИЗ.

Писать код для базового запуска **не нужно** — достаточно Docker и копирования настроек по инструкции.

---

## Архитектура

```text
Пользователь → OpenWebUI (чат + Pipe)
                  → webhook n8n (шаги АРИЗ-85-В через LLM)
                       ↘ patent_service → Qdrant
```

| Сервис | Роль | URL по умолчанию |
|--------|------|------------------|
| OpenWebUI | Чат | http://localhost:3000 |
| n8n | Оркестратор workflow | http://localhost:5678 |
| PostgreSQL | БД для n8n | внутри сети Docker |
| Qdrant | Векторная БД патентов | http://localhost:6333 |
| patent_service | Загрузка CSV и поиск по патентам | http://localhost:8000 |

Ссылки на официальную документацию: [docs/SERVICES.md](docs/SERVICES.md).

---

## Требования

- Docker и **Docker Compose V2** (команда `docker compose` **с пробелом**)
- Свободно ~10+ ГБ на диске (первый запуск качает образы)
- Доступ к LLM для нод workflow (по умолчанию — **GigaChat**, community-нода в n8n)

---

## Быстрый старт (основной стек)

```bash
git clone https://github.com/bazhil/ariz-agent.git
cd ariz-agent
cp .env.example .env
docker compose up -d
```

Откройте в браузере:

- чат: http://localhost:3000  
- n8n: http://localhost:5678  
- адаптер патентов: http://localhost:8000/health  
- Qdrant: http://localhost:6333/dashboard  

Дальше **один раз**:

1. **n8n:** установить community-ноду **GigaChat** → Import файла `n8n_workflows/ariz_85_v.json` → указать credentials API → включить workflow (**Active**) → скопировать **Production Webhook URL**.
2. **OpenWebUI:** Admin → Functions → создать **Pipe** → вставить код из `openwebui_functions/ariz_85_v.py` → в Valves указать `N8N_WEBHOOK_URL` → включить функцию.
3. Новый чат → выбрать Pipe → описать техническую задачу → дождаться отчёта (может занять несколько минут).

Пошагово со скриншотами: [docs/SETUP.md](docs/SETUP.md) (Linux, Windows, macOS). Краткая версия без скриншотов: [docs/QUICKSTART_ru.md](docs/QUICKSTART_ru.md).

### Остановить

```bash
docker compose down
```

### Патенты

Qdrant и `patent_service` входят в обычный `docker compose up -d` (первый запуск собирает образ адаптера). Как искать и скачивать CSV в Google Patents и загрузить в векторную БД: [docs/GOOGLE_PATENTS.md](docs/GOOGLE_PATENTS.md).

**Ollama не нужен.** OpenWebUI поднимается с `ENABLE_OLLAMA_API=false`; чат АРИЗ идёт по цепочке **Pipe → n8n → GigaChat**, без локальных моделей.

---

## Структура репозитория

```text
docker-compose.yml           # весь стек, включая патентный адаптер
.env.example
n8n_workflows/ariz_85_v.json # рабочий workflow АРИЗ-85-В
openwebui_functions/ariz_85_v.py
patent_service/              # FastAPI + эмбеддинги → Qdrant (вайбкод-демо)
patents/example.csv
docs/
```

Блок `patent_service` — **вайбкод**: для демо и экспериментов подходит, это не промышленный patent search.

---

## Ограничения и дисклеймер

- Методика АРИЗ — наследие Г.С. Альтшуллера / Официального Фонда; в репозитории — **программная обёртка и промпты** со ссылкой на первоисточник.
- Ответы модели могут быть ошибочными — проверяйте.
- Сопоставление с патентами иллюстративное.

## Лицензия

Лицензия в духе MIT с условием о благотворительности — файл [LICENSE](LICENSE) (текст на английском).

Проект публикуется как некоммерческий открытый прототип. Коммерческое использование не запрещено. Если вы извлекаете финансовую прибыль из этого ПО, вы обязуетесь перевести значимую часть средств в благотворительные фонды, оплачивающие лечение детям.
