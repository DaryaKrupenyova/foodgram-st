#!/bin/bash

# Проверяем окружение
if [ "$FOODGRAM_ENV" = "PROD" ]; then
    echo "Starting in PRODUCTION mode..."

    echo "Applying migrations..."
    python manage.py migrate
    echo "Migrations applied"

    echo "Collecting static files..."
    python manage.py collectstatic --noinput
    echo "Static files collected"

    echo "If you need to create a superuser, please do it manually."

    echo "Starting Gunicorn..."
    gunicorn foodgram_api.wsgi:application --bind 0.0.0.0:8000 
else
    echo "Starting in DEVELOPMENT mode..."
    echo

    echo "Applying migrations..."
    python manage.py migrate
    echo "Migrations applied"
    echo

    echo "Collecting static files..."
    python manage.py collectstatic --noinput
    echo "Static files collected"
    echo

    echo "Creating superuser..."
    DJANGO_SUPERUSER_PASSWORD=$DJANGO_SUPERUSER_PASSWORD python manage.py createsuperuser --username=admin --email=$DJANGO_SUPERUSER_EMAIL --first_name=admin --last_name=admin --noinput
    echo "Superuser created. Login: $DJANGO_SUPERUSER_EMAIL, Password: $DJANGO_SUPERUSER_PASSWORD"
    echo

    echo "Starting development server..."
    python manage.py runserver 0.0.0.0:8000
fi
