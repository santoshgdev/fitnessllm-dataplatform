# Use a small, compatible Python runtime
FROM python:3.12-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

CMD ["functions-framework", \
     "--target", "main.api_router", \
     "--signature-type", "http", \
     "--port", "8080"]
