#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install library
pip install -r requirements.txt

# Kumpulkan file static
python manage.py collectstatic --no-input

# Jalankan migrasi database
python manage.py migrate

python manage.py createsuperuser --noinput || true