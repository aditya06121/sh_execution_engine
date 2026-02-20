import os
import re

from execution.exceptions import RuntimeExecutionError

WINDOWS_DRIVE_PATH = re.compile(r"^[A-Za-z]:[\\/]")


def get_sandbox_roots() -> tuple[str, str]:
    container_sandbox_root = os.environ.get("CONTAINER_SANDBOX_ROOT", "/sandbox")
    host_sandbox_root = os.environ.get("HOST_SANDBOX_ROOT")

    if not host_sandbox_root:
        raise RuntimeExecutionError("HOST_SANDBOX_ROOT not set")

    host_sandbox_root = host_sandbox_root.strip()

    if not host_sandbox_root:
        raise RuntimeExecutionError("HOST_SANDBOX_ROOT is empty")

    if WINDOWS_DRIVE_PATH.match(host_sandbox_root):
        raise RuntimeExecutionError(
            "HOST_SANDBOX_ROOT must be a Docker-daemon-visible Linux path "
            "(for Windows Docker Desktop use /run/desktop/mnt/host/<drive>/...)"
        )

    host_sandbox_root = host_sandbox_root.replace("\\", "/").rstrip("/")

    return container_sandbox_root, host_sandbox_root


def build_host_temp_dir(host_sandbox_root: str, temp_dir: str) -> str:
    folder_name = os.path.basename(temp_dir)
    return f"{host_sandbox_root}/{folder_name}"
