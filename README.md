# Visions15 API

FastAPI-сервис для создания проектов в Label Studio и загрузки датасетов из архивов.

Сервис работает рядом с Label Studio через `docker-compose`: API принимает запросы, проверяет внутренний `X-API-Key`, валидирует структуру архива и создает проект в Label Studio через ее API.

## Возможности

- Проверка доступа по заголовку `X-API-Key`.
- Создание проекта Label Studio по списку классов.
- Загрузка архива датасета.
- Поиск и проверка `metadata.json` внутри архива.
- Проверка структуры директорий классов и количества изображений.
- Безопасная распаковка ZIP/TAR с защитой от path traversal и ссылок в TAR.

## Стек

- Python 3.13
- FastAPI
- Uvicorn
- httpx
- Pydantic Settings
- Docker Compose
- Label Studio

## Структура проекта

```text
app/
  api/                  FastAPI роутеры и зависимости
  clients/              HTTP-клиент для Label Studio
  core/                 настройки и security dependencies
  schemas/              Pydantic-схемы запросов и ответов
  services/             бизнес-логика
  cli/                  CLI для управления API-ключами
docker-compose.yml      запуск API и Label Studio
Dockerfile              образ API-сервиса
.env.example            пример переменных окружения
```

## Переменные окружения

Создайте `.env` на основе `.env.example`:

```env
APP_NAME=Visions15-API
APP_VERSION=0.1.0

API_KEYS_FILE=/app/storage/secrets/api_keys.json

LABEL_STUDIO_URL=http://label-studio:8080
LABEL_STUDIO_API_KEY=<label-studio-legacy-token>

UPLOAD_DIR=/label-studio/files/uploads
EXTRACTED_DIR=/label-studio/files/extracted
```

### `LABEL_STUDIO_API_KEY`

Нужен Legacy Token пользователя Label Studio. Его можно получить в UI Label Studio:

1. Откройте `http://localhost:8080`.
2. Войдите или создайте первого пользователя.
3. Откройте меню пользователя.
4. Перейдите в `Account & Settings`.
5. Откройте `Legacy Token`.
6. Скопируйте токен в `LABEL_STUDIO_API_KEY`.

Код отправляет токен как:

```http
Authorization: Token <LABEL_STUDIO_API_KEY>
```

Не коммитьте реальный `.env` и токены.

## Запуск

```bash
docker compose up --build
```

После запуска:

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- Label Studio: `http://localhost:8080`

Проверка health endpoint:

```bash
curl http://localhost:8000/api/v1/health
```

Ответ:

```json
{
  "status": "ok"
}
```

## API-ключи сервиса

Все рабочие API endpoint'ы, кроме healthcheck, требуют заголовок:

```http
X-API-Key: <api-key>
```

Сами ключи хранятся в JSON-файле из переменной `API_KEYS_FILE`. В Docker Compose этот файл находится в volume:

```text
./storage:/app/storage
```

### Создать API-ключ внутри контейнера

После запуска контейнеров:

```bash
docker compose exec automation-api python -m app.cli.api_keys create --name local-admin
```

Команда выведет ключ один раз:

```text
API key created.

Name: local-admin
Key:  lsa_...

Save this key now. It will not be shown again.
```

Сохраните значение `lsa_...` и используйте его в заголовке `X-API-Key`.

## API Usage

Базовый URL локально:

```text
http://localhost:8000/api/v1
```

В примерах ниже:

```bash
API_URL=http://localhost:8000/api/v1
API_KEY=lsa_your_api_key
```

На Windows PowerShell используйте `$env:API_URL` и `$env:API_KEY` либо подставляйте значения прямо в команды.

## `GET /health`

Проверяет, что API запущен.

### Request

```bash
curl "$API_URL/health"
```

### Response `200`

```json
{
  "status": "ok"
}
```

Авторизация для health endpoint не нужна.

## `POST /projects`

Создает проект в Label Studio с object detection label config.

### Request

```bash
curl -X POST "$API_URL/projects" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "project_name": "Demo dataset",
    "classes": ["cat", "dog", "car"]
  }'
```

### Request body

```json
{
  "project_name": "Demo dataset",
  "classes": ["cat", "dog", "car"]
}
```

Поля:

- `project_name` - имя проекта в Label Studio, непустая строка до 255 символов.
- `classes` - непустой список названий классов.

Пробелы по краям `project_name` и элементов `classes` удаляются.

### Response `200`

```json
{
  "status": "success",
  "project_id": 12,
  "project_name": "Demo dataset",
  "classes": ["cat", "dog", "car"]
}
```

### Возможные ошибки

- `401` - отсутствует или неверный `X-API-Key`.
- `422` - неверное тело запроса.
- `502` - Label Studio отклонил создание проекта или недоступен.

## `POST /uploads/archive`

Загружает архив датасета, распаковывает его, читает `metadata.json`, проверяет структуру классов и создает проект в Label Studio.

### Request

```bash
curl -X POST "$API_URL/uploads/archive" \
  -H "X-API-Key: $API_KEY" \
  -F "archive=@dataset.zip"
```

Поле multipart form-data должно называться `archive`.

Поддерживаемые форматы:

- `.zip`
- `.tar`
- `.tar.gz`

Фактически формат определяется содержимым файла, а не только расширением.

### Response `200`

```json
{
  "status": "success",
  "project_id": 12,
  "project_name": "Demo dataset",
  "saved_archive_path": "/label-studio/files/uploads/...",
  "extracted_dir": "/label-studio/files/extracted/...",
  "classes": ["cat", "dog"]
}
```

Поля:

- `project_id` - ID созданного проекта в Label Studio.
- `project_name` - имя созданного проекта.
- `saved_archive_path` - путь сохраненного архива внутри контейнера.
- `extracted_dir` - путь распакованного датасета внутри контейнера.
- `classes` - список классов из `metadata.json`.

### Возможные ошибки

- `400` - архив не поддерживается, `metadata.json` отсутствует или структура датасета не совпадает с metadata.
- `401` - отсутствует или неверный `X-API-Key`.
- `422` - файл не передан в multipart form-data.
- `502` - Label Studio отклонил создание проекта или недоступен.

При ошибке загрузки сервис удаляет сохраненный архив и распакованную директорию.

## Формат архива датасета

`metadata.json` должен находиться:

- либо в корне архива;
- либо в единственной директории первого уровня.

Пример структуры:

```text
dataset/
  metadata.json
  cat/
    images/
      cat_001.jpg
      cat_002.png
  dog/
    images/
      dog_001.jpeg
```

Разрешенные расширения изображений:

- `.jpg`
- `.jpeg`
- `.png`

Расширения сравниваются без учета регистра.

## Формат `metadata.json`

Пример:

```json
{
  "schema_version": "1.0",
  "dataset_update": {
    "name": "Demo dataset"
  },
  "classes": {
    "cat": {
      "article": "cat article",
      "directory": "cat",
      "images_count": 2
    },
    "dog": {
      "article": "dog article",
      "directory": "dog",
      "images_count": 1
    }
  }
}
```

Поля:

- `schema_version` - сейчас поддерживается только `"1.0"`.
- `dataset_update.name` - имя проекта, который будет создан в Label Studio.
- `classes` - объект, где ключи являются названиями классов.
- `classes.<class>.article` - обязательная непустая строка.
- `classes.<class>.directory` - относительный путь к директории класса внутри датасета.
- `classes.<class>.images_count` - ожидаемое количество изображений в `<directory>/images`.

Требования к `directory`:

- только относительный путь;
- без пустых сегментов;
- без `.` и `..`;
- путь должен оставаться внутри датасета.

## Пример полного сценария

1. Запустить сервисы:

```bash
docker compose up --build
```

2. Открыть Label Studio и получить Legacy Token.

3. Записать токен в `.env`:

```env
LABEL_STUDIO_API_KEY=<label-studio-legacy-token>
```

4. Перезапустить API-контейнер:

```bash
docker compose restart automation-api
```

5. Создать API-ключ сервиса:

```bash
docker compose exec automation-api python -m app.cli.api_keys create --name local-admin
```

6. Проверить API:

```bash
curl -X POST "http://localhost:8000/api/v1/projects" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: lsa_your_api_key" \
  -d '{
    "project_name": "Smoke test",
    "classes": ["cat", "dog"]
  }'
```

7. Загрузить архив:

```bash
curl -X POST "http://localhost:8000/api/v1/uploads/archive" \
  -H "X-API-Key: lsa_your_api_key" \
  -F "archive=@dataset.zip"
```

## Локальный запуск без Docker

Для локального запуска нужен Python и зависимости из `requirements.txt`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

На Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Для локального запуска без Docker убедитесь, что в `.env` корректно указаны:

- `LABEL_STUDIO_URL`
- `LABEL_STUDIO_API_KEY`
- `API_KEYS_FILE`
- `UPLOAD_DIR`
- `EXTRACTED_DIR`

## Проверки разработки

Быстрая проверка импорта приложения:

```bash
python -c "from app.main import app; print(app.title)"
```

Проверка зависимостей:

```bash
python -m pip check
```

Проверка синтаксиса:

```bash
python -m compileall app
```
