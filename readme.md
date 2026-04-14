# DSA Execution Engine

Ephemeral code execution and judging API for DSA-style problems.  
The service accepts user code + test cases, runs the code inside language-specific Docker sandboxes, and returns a verdict (`accepted`, `wrong_answer`, `runtime_error`, or `compilation_error`).

## What This Project Does

- Exposes a single HTTP API endpoint: `POST /execute`
- Supports multiple languages:
  - `python`
  - `javascript`
  - `typescript`
  - `java`
  - `kotlin`
  - `csharp`
  - `cpp`
  - `c`
  - `go`
  - `rust`
- Runs each submission in an isolated Docker container with resource limits
- Compiles when needed, then executes against test cases one by one
- Returns the first failing verdict early, or `accepted` if all pass

## High-Level Architecture

```text
Client
  -> FastAPI (/execute)
    -> ExecutionPipeline
      -> ExecutorFactory
        -> Language Executor (python/js/java/... etc)
          -> Wrapper Generation (inject user code)
          -> Docker Sandbox (compile + run)
      -> Verdict Builder
    -> JSON Response
```

## Repository Layout

```text
api/
  main.py            # FastAPI app and /execute route
  schemas.py         # Request/response models and strict validation

execution/
  pipeline.py        # Main orchestration: compile, run tests, compare
  executor.py        # Language -> executor registry
  base.py            # BaseExecutor interface
  exceptions.py      # Compile/runtime exceptions
  sandbox_paths.py   # Host/container sandbox path mapping

languages/
  *.py               # Per-language executors
  *_wrapper.py       # Language wrapper templates

config/
  limits.py          # Time/memory/stdout limits

docker/
  *.Dockerfile       # Sandbox images per runtime

Dockerfile           # API server image
```

## Dataflow (End-to-End)

1. Client sends `POST /execute` with language, source code, function name, and test cases.
2. FastAPI validates the body via `ExecuteRequest` (strict schema, extra fields forbidden).
3. `ExecutionPipeline` asks `ExecutorFactory` for the language executor.
4. Executor `compile()` phase:
   - Resolves sandbox paths (`CONTAINER_SANDBOX_ROOT`, `HOST_SANDBOX_ROOT`)
   - Creates temp workspace inside sandbox mount
   - Injects user code into a wrapper template
   - Starts a sandbox container (`docker run -d ... sleep ...`)
   - Runs language compile step if needed
5. For each test case:
   - Pipeline calls `executor.run(test_input)`
   - Executor sends JSON payload to process stdin via `docker exec -i`
   - Wrapper deserializes input, invokes target function/method, serializes output JSON
   - Pipeline compares returned output with `expected_output` using strict inequality (`!=`)
6. Pipeline returns:
   - first failure (`wrong_answer`, `runtime_error`, `compilation_error`)
   - or `accepted` if all tests pass
7. `finally` block always calls `executor.cleanup()`:
   - force-removes running container
   - deletes temp files

## API Endpoint

### `POST /execute`

- URL: `/execute`
- Content-Type: `application/json`
- Response model: discriminated union on `verdict`

Status codes:

- `200`: execution processed and verdict returned
- `400`: unsupported language raised by executor factory
- `422`: request schema validation error

### Request Body

```json
{
  "language": "python",
  "source_code": "def twoSum(nums, target): ...",
  "function_name": "twoSum",
  "test_cases": [
    {
      "input": { "nums": [2, 7, 11, 15], "target": 9 },
      "expected_output": [0, 1]
    }
  ]
}
```

Validation rules:

- `language`: one of the supported literals listed above
- `source_code`: required, `1..5000` chars
- `function_name`: required, `1..100` chars
- `test_cases`: required, `1..20` items
- each test case:
  - `input`: object/dictionary
  - `expected_output`: any JSON value
- unknown fields are rejected (`extra="forbid"`)

### Response Shapes

#### Accepted

```json
{
  "verdict": "accepted",
  "actual_outputs": [[0, 1]]
}
```

#### Wrong Answer

```json
{
  "verdict": "wrong_answer",
  "failed_test_case_index": 0,
  "actual_output": [1, 2],
  "expected_output": [0, 1]
}
```

#### Runtime Error

```json
{
  "verdict": "runtime_error",
  "failed_test_case_index": 0,
  "error_message": "Execution timed out",
  "actual_outputs": []
}
```

#### Compilation Error

```json
{
  "verdict": "compilation_error",
  "error_message": "...compiler output...",
  "actual_outputs": []
}
```

#### Timeout (Schema Note)

`TimeoutResponse` exists in `api/schemas.py`, but current pipeline/executors surface timeouts as `runtime_error` messages (for example `"Execution timed out"`).

## Execution Limits and Isolation

From `config/limits.py`:

- Compile timeout: `30s` (default; TypeScript uses a dedicated `10s` compile timeout)
- Execution timeout per test case: `30s`
- Memory: `1g` limit and `1g` swap
- CPU: `2` cores (TS compile container currently uses `1`)
- PID limit: `256` (`512` in C# executor)
- Open files (`nofile`): `65535`
- Max stdout: `1,000,000` bytes
- Sandbox container lifetime command: `sleep 60`

Container hardening used by executors:

- `--network none`
- `--cap-drop ALL`
- `--security-opt no-new-privileges`

## Dependencies

### Python/App Dependencies

Pinned in `requirements.txt` (notable runtime packages):

- `fastapi`
- `pydantic`
- `uvicorn`
- `starlette`

### System Dependencies

- Docker Engine (host)
- Docker CLI available to the API process/container
- Docker socket mount: `/var/run/docker.sock:/var/run/docker.sock`
- Writable sandbox mount (default container path: `/sandbox`)

### Sandbox Images

- `python-sandbox:latest` from `docker/python.Dockerfile`
- `js-sandbox:latest` from `docker/js.Dockerfile` (used by JavaScript + TypeScript)
- `java-sandbox:latest` from `docker/java.Dockerfile` (used by Java + Kotlin)
- `cpp-sandbox:latest` from `docker/cpp.Dockerfile` (used by C++ + C executor)
- `go-sandbox:latest` from `docker/go.Dockerfile`
- `rust-sandbox:latest` from `docker/rust.Dockerfile`
- `csharp-sandbox:latest` from `docker/csharp.Dockerfile`

## Local Setup

### 1. Build Sandbox Images

```bash
docker build -t python-sandbox:latest -f docker/python.Dockerfile .
docker build -t js-sandbox:latest -f docker/js.Dockerfile .
docker build -t java-sandbox:latest -f docker/java.Dockerfile .
docker build -t cpp-sandbox:latest -f docker/cpp.Dockerfile .
docker build -t go-sandbox:latest -f docker/go.Dockerfile .
docker build -t rust-sandbox:latest -f docker/rust.Dockerfile .
docker build -t csharp-sandbox:latest -f docker/csharp.Dockerfile .
```

### 2. Run API in Docker (Recommended)

Build API image:

```bash
docker build -t judge-api:latest .
```

Run (Linux/macOS example):

```bash
docker run --rm -p 8000:8000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd)/sandbox:/sandbox \
  -e HOST_SANDBOX_ROOT=$(pwd)/sandbox \
  --name judge-api \
  judge-api:latest
```

Run (Windows Docker Desktop example, PowerShell):

```powershell
docker run --rm -p 8000:8000 `
  -v /var/run/docker.sock:/var/run/docker.sock `
  -v C:\judge-sandbox:/sandbox `
  -e HOST_SANDBOX_ROOT=/run/desktop/mnt/host/c/judge-sandbox `
  --name judge-api `
  judge-api:latest
```

### 3. Run API Directly on Host (Alternative)

```bash
pip install -r requirements.txt
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

You still need Docker Engine running because executors call `docker run/exec/rm`.

## Environment Variables

- `HOST_SANDBOX_ROOT` (required)
  - Must be a Docker-daemon-visible Linux path
  - On Windows Docker Desktop, use `/run/desktop/mnt/host/<drive>/...`
- `CONTAINER_SANDBOX_ROOT` (optional)
  - Default: `/sandbox`

If `HOST_SANDBOX_ROOT` is missing, empty, or a Windows drive path (`C:\...`), execution fails with a runtime error from `execution/sandbox_paths.py`.

## Wrapper Behavior Notes

- Most wrappers support LeetCode-style types:
  - `TreeNode`
  - `ListNode` (with optional cycle via `pos`)
  - graph `Node` / adjacency list
- Dynamic conversion is based on:
  - key prefixes (`root`, `head`, `adj`) in Python/JS/TS
  - reflection/type inspection in Java/Kotlin/C#
  - signature parsing in Go/C++/C/Rust
- Function dispatch:
  - Python/JS/TS can call top-level function or `Solution` class method
  - Java/Kotlin/C# expect `Solution` class method by name
  - Go/C++/C/Rust parse and bind to `function_name` at compile/wrapper generation time

## Operational Notes

- Output comparison is strict (`output != expected_output`).
- C executor currently compiles generated code with `g++` and uses a C++ JSON wrapper (`solution.cpp`).
- `MAX_CONCURRENT_EXECUTIONS` exists in config but is not yet enforced in pipeline logic.

## Sample cURL

```bash
curl -X POST http://localhost:8000/execute \
  -H "Content-Type: application/json" \
  -d '{
    "language": "python",
    "source_code": "def twoSum(nums, target):\n    seen = {}\n    for i, n in enumerate(nums):\n        d = target - n\n        if d in seen:\n            return [seen[d], i]\n        seen[n] = i",
    "function_name": "twoSum",
    "test_cases": [
      {"input": {"nums": [2,7,11,15], "target": 9}, "expected_output": [0,1]},
      {"input": {"nums": [3,2,4], "target": 6}, "expected_output": [1,2]}
    ]
  }'
```

## Deploy Pipeline

`.github/workflows/deploy.yml`:

- Builds and pushes `gisul/execution-engine-py:latest` on `main`
- Deploys on a self-hosted runner
- Runs container with Docker socket + sandbox mount + `HOST_SANDBOX_ROOT`
