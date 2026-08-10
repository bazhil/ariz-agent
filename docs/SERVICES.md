# Микросервисы и компоненты стека

Кратко: зачем каждый сервис в прототипе и куда смотреть официальную документацию.

Используйте **Docker Compose V2**: команда `docker compose` (с пробелом), не устаревший `docker-compose`.

---

## Схема

```text
┌─────────────┐     Pipe / webhook      ┌─────────┐      LLM API
│  OpenWebUI  │ ───────────────────────►│   n8n   │ ─────────────► GigaChat (и др.)
└─────────────┘                         └────┬────┘
                                             │ HTTP (опционально)
                                             ▼
                                      ┌──────────────┐     ┌────────┐
                                      │patent_service│────►│ Qdrant │
                                      └──────────────┘     └────────┘
┌──────────┐   БД n8n
│ Postgres │◄── n8n
└──────────┘
┌──────────┐   опционально для локальных моделей в UI
│  Ollama  │
└──────────┘
```

---

## OpenWebUI

**Роль в проекте:** человеческий интерфейс чата. Сюда пользователь пишет задачу. Через **Pipe** (`openai_functions/ariz_85_v.py`) сообщение уходит в webhook n8n, ответ показывается в чате.

| | |
|--|--|
| Сайт | https://openwebui.com/ |
| Документация | https://docs.openwebui.com/ |
| Репозиторий | https://github.com/open-webui/open-webui |
| Образ в compose | `ghcr.io/open-webui/open-webui:v0.8.3` |
| Порт | http://localhost:3000 |

Полезные разделы docs: Functions / Tools, authentication, connecting backends.

---

## n8n

**Роль в проекте:** оркестратор шагов АРИЗ-85-В. Импортируется workflow `workflows/ariz_85_v_3.json` (webhook → цепочка LLM-нод → опциональный поиск патентов → summary → ответ в webhook).

| | |
|--|--|
| Сайт | https://n8n.io/ |
| Документация | https://docs.n8n.io/ |
| Репозиторий | https://github.com/n8n-io/n8n |
| Образ в compose | `n8nio/n8n:1.114.3` |
| Порт | http://localhost:5678 |
| Hosted workflows / self-hosting | https://docs.n8n.io/hosting/ |
| Webhooks | https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/ |
| Community nodes | https://docs.n8n.io/integrations/community-nodes/installation/ |

Для GigaChat обычно ставят community-пакет нод (имя пакета уточняйте в README/npm на момент установки), затем создаёте credentials в UI n8n.

---

## PostgreSQL

**Роль в проекте:** рекомендуемая БД для хранения данных n8n (workflow, executions, пользователи).

| | |
|--|--|
| Документация | https://www.postgresql.org/docs/ |
| Образ | `postgres:13-alpine` |
| Порт наружу | не проброшен (только внутри Docker-сети) |

---

## Qdrant

**Роль в проекте:** векторная база для семантического поиска по загруженным фрагментам патентных описаний (профиль `patents`).

| | |
|--|--|
| Сайт | https://qdrant.tech/ |
| Документация | https://qdrant.tech/documentation/ |
| Quick start | https://qdrant.tech/documentation/quickstart/ |
| Репозиторий | https://github.com/qdrant/qdrant |
| Образ | `qdrant/qdrant:latest` |
| HTTP API / UI | http://localhost:6333/dashboard |

---

## patent_service (этот репозиторий)

**Роль в проекте:** тонкий FastAPI-слой над Qdrant: загрузка CSV из Google Patents, эмбеддинги (`sentence-transformers`), поиск. Код — **демо / вайбкод**: для экспериментов достаточно, для промышленного prior art — нет.

| Endpoint | Назначение |
|----------|------------|
| `GET /health` | Статус и число точек в коллекции |
| `POST /load_csv` | Загрузка CSV (multipart), фоновая задача |
| `GET /load_status/{task_id}` | Прогресс загрузки |
| `GET /search?q=...` | Поиск по текстовому запросу |
| `POST /search_by_output` | Поиск по JSON с полями breakthrough / good / trivial (как из workflow) |
| `POST /embed` | Получить вектор(а) текста |

Локально: http://localhost:8000 · интерактивная схема после запуска: http://localhost:8000/docs (Swagger UI FastAPI).

Зависимости и идеи стека:

- FastAPI: https://fastapi.tiangolo.com/
- Sentence-Transformers: https://www.sbert.net/
- Модель по умолчанию: `sentence-transformers/all-MiniLM-L6-v2` (384 dim)

---

## Ollama (опционально)

**Роль в проекте:** локальный рантайм LLM для OpenWebUI. **Не используется** опубликованным workflow АРИЗ (там GigaChat через n8n). Профиль Compose: `ollama`.

| | |
|--|--|
| Сайт | https://ollama.com/ |
| Документация | https://github.com/ollama/ollama/tree/main/docs |
| Репозиторий | https://github.com/ollama/ollama |
| Порт в этом compose | http://localhost:11435 → внутри контейнера 11434 |

---

## Docker / Compose

| | |
|--|--|
| Docker Docs | https://docs.docker.com/ |
| Compose V2 | https://docs.docker.com/compose/ |
| Profiles | https://docs.docker.com/compose/how-tos/profiles/ |

Примеры команд проекта:

```bash
docker compose up -d
docker compose --profile patents up -d
docker compose --profile ollama up -d
docker compose --profile patents --profile ollama up -d
docker compose ps
docker compose down
```

---

## LLM: GigaChat

В workflow v3 шаги АРИЗ вызываются через ноды GigaChat в n8n. Документация API и кабинета — на стороне провайдера (Сбер / GigaChat). Community-нода n8n устанавливается из UI n8n (Settings → Community nodes).

При проблемах с TLS в корпоративной сети может понадобиться свой CA — в этот публичный прототип сертификаты намеренно не включены; при необходимости смонтируйте их в сервис `n8n` по [документации n8n](https://docs.n8n.io/).

---

## Методика АРИЗ (не сервис, но опора пайплайна)

| | |
|--|--|
| АРИЗ-85-В | https://altshuller.ru/triz/ariz85v.asp |
| Официальный Фонд Г.С. Альтшуллера | https://www.altshuller.ru/ |
