# Time limits (seconds)
EXECUTION_TIMEOUT_SECONDS = 10

# Compilation timeouts (seconds)
COMPILATION_TIMEOUT_SECONDS = 30      # was 120 — heavy compilers still have room
TS_COMPILE_TIMEOUT_SECONDS = 15       # was 30

# Docker resource limits
# Reduced: allows 4× more containers on the same host
DOCKER_MEMORY_LIMIT = "256m"          # was 1024m
DOCKER_MEMORY_SWAP = "256m"           # was 1024m  (no swap, keeps pressure visible)
DOCKER_CPU_LIMIT = "0.5"              # was 2
DOCKER_PIDS_LIMIT = "64"              # was 1536  (typical solutions need <20)
DOCKER_NOFILE_LIMIT = "1024"          # was 65535

TS_CPU_LIMIT = "0.5"                  # was 2

# Output limits
MAX_STDOUT_BYTES = 1_000_000          # 1 MB
MAX_COMPILE_ERROR_BYTES = 1000

# Container behavior
CONTAINER_SLEEP_SECONDS = 60

# Worker concurrency — slots per worker process
# Run multiple worker.py processes to scale out horizontally.
WORKER_CONCURRENCY = 10
