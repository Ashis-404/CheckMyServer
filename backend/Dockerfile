FROM python:3.9-slim

WORKDIR /app

# Install k6 for performance testing
RUN apt-get update && apt-get install -y wget && \
    wget -qO- https://github.com/grafana/k6/releases/download/v0.47.0/k6-v0.47.0-linux-amd64.tar.gz | tar -xz && \
    mv k6-v0.47.0-linux-amd64/k6 /usr/local/bin/ && \
    rm -rf k6-v0.47.0-linux-amd64 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy the startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

ENV PYTHONPATH=/app/backend

# Start both services
CMD ["/app/start.sh"]

