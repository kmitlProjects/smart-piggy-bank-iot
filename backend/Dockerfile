FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random

WORKDIR /app

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend /app

# Explicitly remove any .pyc files and __pycache__ directories
RUN find /app -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
RUN find /app -name "*.pyc" -delete 2>/dev/null || true

EXPOSE 5001

# Use Gunicorn WSGI app entrypoint
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "1", "--timeout", "300", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
