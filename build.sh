#!/usr/bin/env bash
# Exit immediately if a command fails
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files (CSS, JS, images)
python manage.py collectstatic --noinput

# Apply database migrations
python manage.py migrate