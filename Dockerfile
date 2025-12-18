FROM python:3.12-slim

# Environment
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Work directory
WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create static directory if not exists
RUN mkdir -p static

# Collect static
RUN python manage.py collectstatic --noinput || true

# Expose port
EXPOSE 8000

# Default command - runs both Django and Bot
CMD ["python", "start.py"]
