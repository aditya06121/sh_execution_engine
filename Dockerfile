FROM python:3.11-slim

WORKDIR /app

# Install ONLY docker CLI (not full engine)
RUN apt-get update && \
    apt-get install -y docker-cli && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy only requirements first (better layer caching)
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Then copy source code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
