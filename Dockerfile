ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY . .
RUN mkdir -p data

EXPOSE 8585

# Using gunicorn with eventlet for SSE support
# Change dir to src so it can find app:app and relative templates/static
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "-b", "0.0.0.0:8585", "--chdir", "src", "app:app"]
