# Инструкция по настройке (macOS)

Пошаговый запуск ARIZ-Agent на macOS: Docker Desktop → n8n (GigaChat) → OpenWebUI (Pipe) → загрузка патентов.

См. также: [все ОС](SETUP.md) · [README.ru.md](../README.ru.md) · [патенты](GOOGLE_PATENTS.md) · [English](SETUP_MACOS.en.md)

---

## Требования

- macOS на Apple silicon или Intel
- [Docker Desktop for Mac](https://docs.docker.com/desktop/setup/install/mac-install/) (установщик под чип Apple или Intel)
- ~10+ ГБ свободно
- Git (`xcode-select --install`) или ZIP с GitHub
- ключ GigaChat API (вводится позже в n8n)

Запустите **Docker Desktop** и дождитесь работы движка (кит в строке меню). Разрешите доступ к файлам и сети, если система спросит.

В **Терминале**:

```bash
docker compose version
```

Нужен Compose **V2**: `docker compose` с пробелом.

---

## Подготовка

```bash
git clone https://github.com/bazhil/ariz-agent.git
cd ariz-agent
cp .env.example .env
```

Без Git: **Code → Download ZIP** на GitHub → распаковать → `cd` в `ariz-agent` → `cp .env.example .env`.

`.env` правьте в TextEdit при смене портов и паролей. Ключ GigaChat обычно вводят в n8n.

`GIGACHAT_TIMEOUT=300` — таймаут **одного** запроса к GigaChat. Полный АРИЗ — минуты и десятки запросов.

Из папки проекта:

```bash
docker compose up -d
```

Без `-d` логи в терминале. Первый запуск качает образы и собирает `patent_service`.

Если порт занят (3000, 5678, 6333, 8000) — закройте программу или смените порты в `.env`.

Когда сервисы поднялись:

| URL | Назначение |
|-----|------------|
| http://localhost:5678/setup | n8n — владелец |
| http://localhost:3000/ | OpenWebUI |
| http://localhost:8000/docs | patent-service |

Проверка: http://localhost:8000/health

---

## Настройка n8n

### Учётная запись владельца

http://localhost:5678/setup — email, имя, пароль (от 8 символов, цифра и заглавная буква). **Next**.

![Создание владельца n8n](images/setup/01-n8n-owner-setup.png)

### Community-нода GigaChat

**Settings → Community nodes → Install a community node**, пакет `n8n-nodes-gigachat`. Дождитесь **Installing**.

![Установка n8n-nodes-gigachat](images/setup/02-n8n-community-nodes.png)

### Ключ GigaChat

**Credentials → Add credential**, поиск `GigaChat`.

![Поиск credential GigaChat](images/setup/03-n8n-add-credential.png)

**Authorization key**, scope обычно `GIGACHAT_API_PERS`. URL по умолчанию не трогайте:

- Base Auth URL: `https://ngw.devices.sberbank.ru:9443`
- Base Backend URL: `https://gigachat.devices.sberbank.ru/api/v1`

![Поля credential GigaChat](images/setup/04-n8n-gigachat-fields.png)

Сохраните — **Connection tested successfully**.

![Успешная проверка GigaChat](images/setup/05-n8n-gigachat-tested.png)

При ошибке: ключ, scope, HTTPS из контейнера `ariz-n8n` (VPN/прокси на Mac).

### Импорт workflow

**Import from File** → `n8n_workflows/ariz_85_v.json`.

![Workflow АРИЗ-85-В](images/setup/06-n8n-workflow.png)

Выберите credentials на нодах GigaChat, сохраните, включите **Active**.

### Webhook URL

**Production URL**: `http://localhost:5678/webhook/<uuid>`. На скрине **Test URL** (`webhook-test`) — только для отладки. Для чата уберите `-test`.

![Нода Webhook](images/setup/07-n8n-webhook.png)

В Valves OpenWebUI хост `n8n`, не `localhost`:

```text
http://n8n:5678/webhook/aa3eb1a4-66a4-4f63-9354-065d103e0a0f
```

---

## Настройка OpenWebUI

1. http://localhost:3000 — администратор.
2. Отключите автозаголовок чата, продолжения и теги.
3. **Admin Panel → Functions** → **Pipe**, вставьте `openwebui_functions/ariz_85_v.py`.
4. **N8N_WEBHOOK_URL** с хостом `n8n`; **TIMEOUT** например `600`.
5. Включите функцию, новый чат, опишите задачу.

---

## Загрузка патентов

1. [Google Patents](https://patents.google.com/) (часто VPN) → **Download (CSV)**.

![Выгрузка CSV с Google Patents](images/setup/08-google-patents-csv.png)

2. http://localhost:8000/docs → **POST /load_csv**.

![Загрузка CSV в patent-service](images/setup/09-patent-load-csv.png)

3. `202` и `task_id`:

```json
{
  "message": "CSV load started",
  "task_id": "5f224275-6734-4074-bde8-b179b42aed2a",
  "status_endpoint": "/load_status/5f224275-6734-4074-bde8-b179b42aed2a"
}
```

![Ответ load_csv](images/setup/10-patent-load-accepted.png)

4. **GET /load_status/{task_id}** до `"completed"`.

![Статус загрузки](images/setup/11-patent-load-status.png)

Подробнее: [GOOGLE_PATENTS.md](GOOGLE_PATENTS.md).

---

## Работа

Чат с функцией ARIZ. При Axios timeout 30 с — `docker compose up -d n8n --force-recreate` и больший TIMEOUT в Valves.

---

## Команды

```bash
docker compose up -d
docker compose ps
docker compose logs n8n --tail 50
docker compose down
```
