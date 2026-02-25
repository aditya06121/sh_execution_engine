FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    nlohmann-json3-dev \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1001 runner
WORKDIR /app