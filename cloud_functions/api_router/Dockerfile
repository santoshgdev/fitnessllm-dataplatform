# Use a small, compatible Python runtime
FROM python:3.12-slim

# Set workdir
WORKDIR /app

# Install git for GitHub dependencies
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all files
COPY . .

# Expose the Functions Framework port
EXPOSE 8080

# Launch the HTTP function
CMD ["functions-framework", \
     "--target", "main.api_router", \
     "--signature-type", "http", \
     "--port", "8080"]
