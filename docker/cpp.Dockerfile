FROM gcc:13-bookworm

RUN apt-get update && apt-get install -y \
    nlohmann-json3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash runner

USER runner

WORKDIR /app

CMD ["sleep", "3600"]
