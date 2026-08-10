# Google Patents → CSV → Qdrant (patent_service)

Инструкция: как найти патенты на [Google Patents](https://patents.google.com/), скачать выгрузку и загрузить её в векторную БД прототипа.

Блок патентов **опционален**. Основной АРИЗ-чат работает без него.  
Поиск в Qdrant — **демо**, не юридическая проверка патентной чистоты.

---

## 1. Поднять сервисы патентов

Из корня репозитория:

```bash
docker compose --profile patents up -d
```

Проверка в браузере:

- Qdrant UI: http://localhost:6333/dashboard  
- patent_service health: http://localhost:8000/health  
- Swagger: http://localhost:8000/docs  

Ожидаемый health (примерно): `{"status":"ok","qdrant":"connected",...}`.

Первый запрос к сервису может быть долгим: скачивается модель эмбеддингов `all-MiniLM-L6-v2`.

---

## 2. Поиск на Google Patents

1. Откройте https://patents.google.com/
2. Введите запрос на **английском** (для техники обычно лучше покрытие), например:
   - `low vibration suspension`
   - `hermetic enclosure cooling without fan`
   - `self-healing polymer coating`
3. При необходимости уточните фильтры слева:
   - **Patent office** (USPTO, EPO, …)
   - **Status** (Grant и т.д.)
   - даты, язык, тип документа
4. Просмотрите выдачу: заголовок, абстракт, рисунки — отберите релевантную тему.

Официальная справка Google: [About Google Patents](https://support.google.com/faqs/answer/6390996) (раздел помощи Google; интерфейс Patents периодически меняется).

---

## 3. Скачать CSV

В интерфейсе Google Patents для текущей поисковой выдачи доступна выгрузка:

1. Выполните поиск, дождитесь списка результатов.
2. Найдите действие экспорта / download (часто иконка или меню в верхней части результатов; формулировка в UI может быть вроде **Download** / выгрузка результатов поиска в CSV).
3. Сохраните файл `.csv` на компьютер.

Типичные колонки выгрузки (имена могут слегка отличаться):

- `id`, `title`, `assignee`, `inventor/author`
- даты: priority / filing / publication / grant
- `result link`, иногда ссылка на рисунок
- в начале файла иногда есть строка `search URL:,https://patents.google.com/...`

Именно такой формат ожидает `patent_service` (см. пример `patents/example.csv`).

**Если кнопки CSV нет** (аккаунт, регион, изменение UI):

- откройте несколько патентов вручную и соберите упрощённый CSV с колонками как в `example.csv`;  
- или используйте уже скачанный `patents/example.csv` только чтобы проверить загрузку.

Лимиты и полнота выгрузки зависят от Google — больших «дампов всего мира» этот прототип не предполагает.

---

## 4. Загрузить CSV в векторную БД

### Способ A — через Swagger (удобно без терминала)

1. Откройте http://localhost:8000/docs
2. Найдите `POST /load_csv`
3. **Try it out** → выберите файл CSV → **Execute**
4. В ответе будет `task_id` и путь статуса, например `/load_status/<task_id>`
5. Вызовите `GET /load_status/{task_id}` несколько раз, пока `status` не станет `completed`

### Способ B — через curl

```bash
curl -X POST "http://localhost:8000/load_csv" \
  -F "file=@patents/example.csv"
```

Пример ответа:

```json
{
  "message": "CSV load started",
  "task_id": "...",
  "status_endpoint": "/load_status/..."
}
```

Проверка:

```bash
curl "http://localhost:8000/load_status/<task_id>"
curl "http://localhost:8000/health"
```

### Что происходит внутри

1. CSV парсится.
2. Тексты патентов (заголовок / доступные поля, при необходимости доп. загрузка описания) режутся на фрагменты.
3. Считаются эмбеддинги (Sentence-Transformers).
4. Векторы пишутся в коллекцию Qdrant `patents`.

Большой CSV (тысячи строк) займёт заметное время и память.

---

## 5. Проверить поиск

```bash
curl "http://localhost:8000/search?q=vibration%20damping&limit=5"
```

Или в Swagger: `GET /search`.

В workflow АРИЗ после генерации идей вызывается `POST /search_by_output` с JSON вида:

```json
{
  "breakthrough": ["idea one", "idea two"],
  "good": ["..."],
  "trivial": ["..."]
}
```

URL внутри Docker-сети: `http://patent_service:8000/search_by_output` (уже прописан в `ariz_85_v_3.json`).

Если профиль `patents` не запущен, соответствующие ноды workflow завершатся ошибкой сети — либо поднимите профиль, либо отключите/обойдите патентные ноды в n8n для учебных прогонов без БД.

---

## 6. Практические советы

| Совет | Зачем |
|-------|--------|
| Копите **тематические** выгрузки под свою задачу, а не «всё подряд» | Выше качество ближайших соседей |
| Начинайте с малого CSV (десятки–сотни строк) | Быстрее проверить пайплайн |
| Переформулируйте запросы на английском | Лучше покрытие Google Patents |
| Не полагайтесь на top-k как на «новизну» | Нужна ручная проверка специалистом |
| Повторная загрузка | Может добавить дубликаты — для демо допустимо; для чистоты пересоздайте коллекцию (через UI Qdrant или API) |

---

## 7. Остановить только патентный контур

```bash
docker compose --profile patents stop qdrant patent_service
```

или полный останов проекта:

```bash
docker compose --profile patents down
```

Данные Qdrant хранятся в Docker volume `qdrant_data` и переживают `stop`; `down -v` удалит тома — используйте осторожно.
