# Инструкция по настройке (Linux)

Пошаговый запуск прототипа ARIZ-Agent: Docker → n8n (GigaChat) → OpenWebUI (Pipe) → загрузка патентов.

См. также: [README.ru.md](../README.ru.md) · [быстрый старт без скриншотов](QUICKSTART_ru.md) · [патенты подробно](GOOGLE_PATENTS.md) · [English](SETUP_LINUX.en.md) · [Windows](SETUP_WINDOWS_ru.md) · [macOS](SETUP_MACOS_ru.md) · [все ОС](SETUP.md)

---

## Подготовка

1. Клонировать репозиторий:

```bash
git clone https://github.com/bazhil/ariz-agent.git
```

2. Перейти в каталог проекта:

```bash
cd ariz-agent
```

3. Создать файл переменных окружения:

```bash
cp .env.example .env
```

В `.env` при необходимости поменяйте пароли и порты. Ключ GigaChat обычно вводят позже в интерфейсе n8n, не в `.env`.

Значение `GIGACHAT_TIMEOUT=300` задаёт таймаут **одного** запроса к API GigaChat (секунды). Полный прогон АРИЗ занимает несколько минут и состоит из десятков таких запросов.

4. Запустить контейнеры:

```bash
docker compose up -d
```

`docker compose up` без `-d` тоже работает: логи идут в терминал. Для повседневной работы удобнее `-d`. Первый запуск качает образы и собирает `patent_service`.

5. Когда сервисы поднялись, откройте в браузере:

| URL | Назначение |
|-----|------------|
| http://localhost:5678/setup | n8n — учётная запись владельца (первый вход) |
| http://localhost:3000/ | OpenWebUI — чат |
| http://localhost:8000/docs | patent-service — Swagger, загрузка CSV |

Проверка адаптера патентов: http://localhost:8000/health

---

## Настройка n8n

### Учётная запись владельца

Откройте http://localhost:5678/setup. Заполните email, имя, фамилию и пароль (не менее 8 символов, цифра и заглавная буква). Нажмите **Next**.

![Создание владельца n8n](images/setup/01-n8n-owner-setup.png)

### Community-нода GigaChat

**Settings → Community nodes → Install a community node**. В поле npm-пакета укажите:

```text
n8n-nodes-gigachat
```

Подтвердите риск установки кода из публичного источника и дождитесь **Installing**. После установки обновите страницу.

![Установка n8n-nodes-gigachat](images/setup/02-n8n-community-nodes.png)

### Ключ GigaChat в credentials

**Credentials → Add credential**, в поиске введите `GigaChat`, нажмите **Continue**.

![Поиск credential GigaChat](images/setup/03-n8n-add-credential.png)

Вставьте **Authorization key** из кабинета GigaChat. **Scope** для личного кабинета обычно `GIGACHAT_API_PERS` (для бизнеса — соответствующий scope из документации Сбера). URL авторизации и API по умолчанию не меняйте, если не знаете, зачем:

- Base Auth URL: `https://ngw.devices.sberbank.ru:9443`
- Base Backend URL: `https://gigachat.devices.sberbank.ru/api/v1`

![Поля credential GigaChat](images/setup/04-n8n-gigachat-fields.png)

Сохраните. Должно появиться **Connection tested successfully**.

![Успешная проверка GigaChat](images/setup/05-n8n-gigachat-tested.png)

Если тест падает, проверьте ключ, scope и исходящий HTTPS из контейнера `ariz-n8n` к хостам Сбера.

### Импорт workflow

**Import from File** → `n8n_workflows/ariz_85_v.json`. На холсте — цепочка шагов АРИЗ-85-В и вызов patent-service в конце.

![Workflow АРИЗ-85-В](images/setup/06-n8n-workflow.png)

У каждой ноды GigaChat выберите сохранённые credentials. Красные замечания (нет credentials, не выбрана модель) устраните и сохраните workflow. Включите тумблер **Active**.

### Webhook URL

Откройте первую ноду **Webhook**. Для постоянной работы чата нужен **Production URL** вида:

`http://localhost:5678/webhook/<uuid>`

В скрине ниже выбран **Test URL** (`…/webhook-test/…`). Он удобен при отладке, но тогда в n8n нужно каждый раз нажимать **Listen for test event**. Для OpenWebUI уберите `-test`: путь должен быть `/webhook/…`, workflow — **Active**.

![Нода Webhook](images/setup/07-n8n-webhook.png)

OpenWebUI работает **внутри Docker-сети**. В Valves Pipe укажите хост `n8n`, а не `localhost`:

```text
http://n8n:5678/webhook/aa3eb1a4-66a4-4f63-9354-065d103e0a0f
```

UUID возьмите из своей ноды Webhook (он совпадает с полем **Path**, если вы не меняли импорт).

---

## Настройка OpenWebUI

1. Откройте http://localhost:3000 и создайте администратора (первый запуск).
2. В настройках интерфейса **отключите** автогенерацию заголовка чата, продолжения диалога и тегов. Иначе модель будет тратить ответы на служебный текст, и качество разбора АРИЗ упадёт.
3. **Admin Panel → Functions** (в части версий — Workspace → Functions). Создайте функцию типа **Pipe**.
4. Вставьте содержимое файла `openwebui_functions/ariz_85_v.py`.
5. В **Valves**:
   - **N8N_WEBHOOK_URL** — Production URL с хостом `n8n` (см. выше), без `webhook-test`.
   - **TIMEOUT** — увеличьте, например до `600` (секунды на весь прогон webhook). Значение по умолчанию в коде — 120, этого мало для полного АРИЗ.
6. Включите функцию (**Enabled**).
7. Новый чат → выберите эту функцию → опишите техническую задачу и ждите ответ (минуты).

---

## Загрузка патентов

Поиск по патентам опционален: чат АРИЗ работает и с пустой коллекцией. Чтобы шаги сопоставления находили документы:

1. На [Google Patents](https://patents.google.com/) (часто нужен VPN) выполните поиск по интересующей теме и скачайте **Download (CSV)**.

![Выгрузка CSV с Google Patents](images/setup/08-google-patents-csv.png)

2. Откройте http://localhost:8000/docs, метод **POST /load_csv**, выберите CSV, **Execute**. При первой загрузке сервис может долго тянуть модель эмбеддингов.

![Загрузка CSV в patent-service](images/setup/09-patent-load-csv.png)

3. Ответ `202` содержит `task_id` и `status_endpoint`:

```json
{
  "message": "CSV load started",
  "task_id": "5f224275-6734-4074-bde8-b179b42aed2a",
  "status_endpoint": "/load_status/5f224275-6734-4074-bde8-b179b42aed2a"
}
```

![Ответ load_csv](images/setup/10-patent-load-accepted.png)

4. Проверьте прогресс: **GET /load_status/{task_id}**. Когда `"status": "completed"`, можно пользоваться поиском из workflow.

![Статус загрузки](images/setup/11-patent-load-status.png)

Подробности запросов и полей CSV: [GOOGLE_PATENTS.md](GOOGLE_PATENTS.md).

---

## Работа

Откройте чат в OpenWebUI с включённой функцией ARIZ и сформулируйте задачу (конфликт, ограничения, что нельзя менять).

Если в ответе Axios `timeout of 30000ms exceeded` — это лимит ноды GigaChat, не OpenWebUI. В compose уже задано `GIGACHAT_TIMEOUT=300`; пересоздайте n8n (`docker compose up -d n8n --force-recreate`) и увеличьте TIMEOUT в Valves Pipe.

---

## Команды

```bash
docker compose up -d
docker compose ps
docker compose logs n8n --tail 50
docker compose down
```
