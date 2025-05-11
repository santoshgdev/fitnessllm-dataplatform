FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

CMD ["functions-framework",
     "--target", "main.strava_auth_initiate",
     "--signature-type", "http",
     "--host", "0.0.0.0",
     "--port", "8080"]
