# Use official Python 3.11 slim image
FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY backend/requirements-dev.txt /app/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements-dev.txt

COPY backend /app/backend
COPY news_agent /app/news_agent

ENV PYTHONPATH=/app

# Copy app code
COPY . /app/

CMD ["python", "backend/run.py"]
