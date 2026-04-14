# Time limits (seconds)
EXECUTION_TIMEOUT_SECONDS = 10

# Compilation timeouts (seconds)
COMPILATION_TIMEOUT_SECONDS = 120      
TS_COMPILE_TIMEOUT_SECONDS = 30       

# Docker resource limits
DOCKER_MEMORY_LIMIT = "1024m"         
DOCKER_MEMORY_SWAP = "1024m"
DOCKER_CPU_LIMIT = "2"                
DOCKER_PIDS_LIMIT = "1536"
DOCKER_NOFILE_LIMIT = "65535"

TS_CPU_LIMIT = "2"

# Output limits
MAX_STDOUT_BYTES = 1_000_000          # 1 MB
MAX_COMPILE_ERROR_BYTES = 1000

# Container behavior
CONTAINER_SLEEP_SECONDS = 60

# Worker concurrency — slots per worker process
# Run multiple worker.py processes to scale out horizontally.
WORKER_CONCURRENCY = 10

# Fallback concurrency used when Redis is unavailable.
# Requests are executed synchronously under this semaphore instead of queued.
FALLBACK_MAX_CONCURRENT = 20
