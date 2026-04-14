# Time limits (seconds)
EXECUTION_TIMEOUT_SECONDS = 30

# Compilation timeouts (seconds)
COMPILATION_TIMEOUT_SECONDS = 120     # heavy compilers: Kotlin, Java, C#
TS_COMPILE_TIMEOUT_SECONDS = 30       # TypeScript (tsc is fast)

# Docker resource limits
DOCKER_MEMORY_LIMIT = "1024m"
DOCKER_MEMORY_SWAP = "1024m"
DOCKER_CPU_LIMIT = "2"
DOCKER_PIDS_LIMIT = "1536"
DOCKER_NOFILE_LIMIT = "65535"
TS_CPU_LIMIT = "2"                    # TypeScript only needs a fraction

# Output limits
MAX_STDOUT_BYTES = 1_000_000          # 1 MB
MAX_COMPILE_ERROR_BYTES = 1000        # cap compiler error messages

# Container behavior
CONTAINER_SLEEP_SECONDS = 60

# Concurrency
MAX_CONCURRENT_EXECUTIONS = 20    # per worker process; 4 workers → 80 total
QUEUE_TIMEOUT_SECONDS = 120       # max time a request can wait in queue before 503
