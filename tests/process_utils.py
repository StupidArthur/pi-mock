import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def wait_for_health(base_url: str, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            response = httpx.get(base_url + "/health", timeout=1.0)
            if response.status_code == 200:
                return
        except httpx.HTTPError as error:
            last_error = error
        time.sleep(0.2)
    raise RuntimeError(f"server did not become healthy: {last_error}")


def start_server(args, base_url: str, env=None):
    import os

    full_env = {
        key: value for key, value in os.environ.items() if not key.startswith("PI_")
    }
    if env:
        full_env.update(env)
    process = subprocess.Popen(
        [sys.executable, "-m", "app.main", *args],
        cwd=str(ROOT),
        env=full_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        wait_for_health(base_url)
    except RuntimeError:
        process.terminate()
        raise
    return process


def stop_server(process) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
