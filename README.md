# Foodgram — «Продуктовый помощник»

Проект для публикации рецептов, подписки на авторов и создания списка покупок.

## Запуск проекта

### 1. Настройка переменных окружения

Перед запуском необходимо настроить переменные окружения:

1. Перейдите в папку `backend/`
2. Выберите подходящий шаблон:
   - Для разработки: `.env.dev.example` → `.env.dev`
   - Для продакшена: `.env.prod.example` → `.env.prod`
3. Замените тестовые значения на актуальные (при необходимости)

> **Важно!** Всегда проверяйте `.env.*.example` при обновлении проекта — могут появиться новые переменные.

### 2. Запуск в среде разработки (Develop)

```bash
cd infra/  # Перейдите в папку с docker-конфигурацией
sudo docker-compose build # Сборка образов
docker-compose up -d  # # Запуск контейнеров в фоновом режиме
```

После запуска автоматически выполнятся:

- Применение миграций
- Сборка статических файлов
- Создание суперпользователя (данные берутся из `.env.dev`)

Сервер запускается в режиме разработки Django.

### 3. Запуск в продакшн-среде (Production)

```bash
cd infra/
docker-compose -f docker-compose.prod.yml up -d
```

Особенности production-режима:

- Автоматические миграции
- Сборка статических файлов
- Нет автоматического создания суперпользователя (создавайте вручную через createsuperuser)
- Оптимизированные настройки Django для production

## Использование проекта

### Управление базой данных

- Разработка: используется SQLite3 (файловая БД)
  - Рекомендуемый инструмент: DB Browser for SQLite
- Продакшен: PostgreSQL (настроена в docker-compose.prod.yml)

### Администрирование

- Доступ к админке: `/admin/`
- Для production: создайте суперпользователя командой:

```bash
docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

## Обновление проекта

При получении обновлений:

1. Проверьте изменения в `.env.*.example` файлах и `docker-compose*.yml` файлах
2. Если были изменения, выполните:

```bash
# Для develop-среды:
docker-compose down --remove-orphans
sudo docker-compose build
docker-compose up -d

# Для production:
docker-compose -f docker-compose.prod.yml down --remove-orphans
docker-compose -f docker-compose.prod.yml up -d
```

## Документация API

После запуска проекта документация доступна по адресу:

- http://localhost/api/docs/ — Swagger UI
