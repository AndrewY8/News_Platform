# Use official Python 3.11 slim image
FROM python:3.11-slim

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy requirements and install
COPY requirements-dev.txt /app/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements-dev.txt

# Copy app code
COPY . /app/


CMD ["python", "run.py"]
