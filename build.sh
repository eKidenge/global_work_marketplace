#!/usr/bin/env bash
# exit on error
set -o errexit

echo "==> Installing Python dependencies"
pip install --upgrade pip
pip install -r requirements/base.txt

echo "==> Collecting static files"
python manage.py collectstatic --no-input

echo "==> Applying database migrations"
python manage.py migrate

echo "==> Ensuring super admin exists"
python manage.py setup_super_admin --noinput || echo "Super admin setup skipped or already exists"

echo "==> Build complete"
