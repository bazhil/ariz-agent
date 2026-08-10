# ARIZAgent

Открытый прототип: прогон технической / изобретательской задачи через **АРИЗ-85-В** в чате (**OpenWebUI**), оркестрация в **n8n**, LLM (например **GigaChat**), опционально поиск по патентам (**Qdrant** + небольшой FastAPI-сервис).

> **English:** [README.md](README.md) · **Быстрый старт:** [docs/QUICKSTART_ru.md](docs/QUICKSTART_ru.md) · **Патенты:** [docs/GOOGLE_PATENTS.md](docs/GOOGLE_PATENTS.md) · **Микросервисы:** [docs/SERVICES.md](docs/SERVICES.md)

Это **учебный и экспериментальный прототип**, не коммерческая экспертиза по ТРИЗ и не замена патентному поверенному.

Источник методики: [АРИЗ-85-В (Официальный Фонд Г.С. Альтшуллера)](https://altshuller.ru/triz/ariz85v.asp).

---

## Что умеет

1. Вы описываете задачу обычным языком в чате.
2. n8n выполняет многошаговый пайплайн **АРИЗ-85-В** (`workflows/ariz_85_v_3.json`).
3. Вы получаете структурированный отчёт (постановка, ИКР, идеи решений, проверки).
4. По желанию идеи сопоставляются с патентами, которые вы сами загрузили в Qdrant.

**ИИ не заменяет человека.** Задача и критическая оценка результата — за вами. Система лишь ведёт разбор по маршруту АРИЗ.

Писать код для базового запуска **не нужно** — достаточно Docker и копирования настроек по инструкции.

---

## Архитектура

```text
Пользователь → OpenWebUI (чат + Pipe)
                  → webhook n8n (шаги АРИЗ-85-В через LLM)
                       ↘ опционально: patent_service → Qdrant
```

| Сервис | Роль | URL по умолчанию |
|--------|------|------------------|
| OpenWebUI | Чат | http://localhost:3000 |
| n8n | Оркестратор workflow | http://localhost:5678 |
| PostgreSQL | БД для n8n | внутри сети Docker |
| Qdrant *(опционально)* | Векторная БД патентов | http://localhost:6333 |
| patent_service *(опционально)* | Загрузка CSV и поиск | http://localhost:8000 |
| Ollama *(опционально)* | Локальные модели для UI | http://localhost:11435 |

Ссылки на официальную документацию: [docs/SERVICES.md](docs/SERVICES.md).

---

## Требования

- Docker и **Docker Compose V2** (команда `docker compose` **с пробелом**)
- Свободно ~10+ ГБ на диске (первый запуск качает образы)
- Доступ к LLM для нод workflow (по умолчанию — **GigaChat**, community-нода в n8n)

---

## Быстрый старт (основной стек)

```bash
git clone https://github.com/<ваш-аккаунт>/ariz-agent.git
cd ariz-agent
cp .env.example .env
docker compose up -d
```

Откройте в браузере:

- чат: http://localhost:3000  
- n8n: http://localhost:5678  

Дальше **один раз**:

1. **n8n:** установить community-ноду **GigaChat** → Import файла `workflows/ariz_85_v_3.json` → указать credentials API → включить workflow (**Active**) → скопировать **Production Webhook URL**.
2. **OpenWebUI:** Admin → Functions → создать **Pipe** → вставить код из `openai_functions/ariz_85_v.py` → в Valves указать `N8N_WEBHOOK_URL` → включить функцию.
3. Новый чат → выбрать Pipe → описать техническую задачу → дождаться отчёта (может занять несколько минут).

Подробно, «для людей» без программирования: [docs/QUICKSTART_ru.md](docs/QUICKSTART_ru.md).

### Остановить

```bash
docker compose down
```

### Патенты (профиль `patents`)

```bash
docker compose --profile patents up -d
```

Как искать и скачивать CSV в Google Patents и загрузить в векторную БД: [docs/GOOGLE_PATENTS.md](docs/GOOGLE_PATENTS.md).

### Локальный Ollama (профиль `ollama`)

```bash
docker compose --profile ollama up -d
```

Опубликованный workflow АРИЗ ходит в **GigaChat через n8n**, не в Ollama. Ollama нужен только если хотите локальные модели в интерфейсе OpenWebUI.

---

## Структура репозитория

```text
docker-compose.yml           # ядро + опциональные profiles
.env.example
workflows/ariz_85_v_3.json   # рабочий workflow АРИЗ-85-В
openai_functions/ariz_85_v.py
prompts/                     # промпты шагов (удобно читать вне JSON)
patent_service/              # FastAPI + эмбеддинги → Qdrant (вайбкод-демо)
patents/example.csv
docs/
```

Блок `patent_service` — **вайбкод**: для демо и экспериментов подходит, это не промышленный patent search.

---

## Обратная связь / опросник

Опросник для Google Forms (шкалы в логике TAM, для продукта и пилотного исследования): [docs/questionnaire_ru.md](docs/questionnaire_ru.md).

---

## Ограничения и дисклеймер

- Методика АРИЗ — наследие Г.С. Альтшуллера / Официального Фонда; в репозитории — **программная обёртка и промпты** со ссылкой на первоисточник.
- Ответы модели могут быть ошибочными — проверяйте.
- Сопоставление с патентами иллюстративное.

## Лицензия

MIT — файл [LICENSE](LICENSE).
