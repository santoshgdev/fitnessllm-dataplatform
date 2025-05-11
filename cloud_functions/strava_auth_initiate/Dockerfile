FROM python:3.12-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

CMD ["functions-framework", \
    "--target", "main.strava_auth_initiate", \
    "--signature-type", "http", \
    "--port", "8080"]
