FROM python:3.9-slim

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements-web.txt .
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements-web.txt

COPY . .

EXPOSE 8080

CMD ["python", "web_app.py"]
