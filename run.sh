#!/usr/bin/env bash
# run.sh - start the API server
# Preload the app so APScheduler runs in the master process
# Increase timeout to prevent worker startup timeouts
exec gunicorn wsgi:app \
  --bind 0.0.0.0:5000 \
  --workers 1 \
  --threads 4 \
  --timeout 120 \
  --preload \
  "$@"
