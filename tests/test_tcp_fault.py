import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "tcp_fault_server" / "server.py"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _start(mode: str, port: int):
    proc = subprocess.Popen(
        [sys.executable, str(SERVER), "--host", "127.0.0.1", "--port", str(port), "--mode", mode],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return proc
        except OSError:
            time.sleep(0.1)
    proc.terminate()
    raise RuntimeError("tcp fault server did not start")


def _stop(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def test_tcp_close():
    port = _free_port()
    proc = _start("close", port)
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2) as sock:
            sock.settimeout(2)
            try:
                data = sock.recv(10)
            except (ConnectionResetError, OSError):
                data = b""
        assert data == b""
    finally:
        _stop(proc)


def test_tcp_reset():
    port = _free_port()
    proc = _start("reset", port)
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2) as sock:
            sock.settimeout(2)
            with pytest.raises((ConnectionResetError, ConnectionAbortedError, OSError)):
                time.sleep(0.2)
                sock.sendall(b"hello")
                sock.recv(10)
    finally:
        _stop(proc)


def test_tcp_hang():
    port = _free_port()
    proc = _start("hang", port)
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2) as sock:
            sock.settimeout(1)
            sock.sendall(b"hello")
            with pytest.raises(socket.timeout):
                sock.recv(10)
    finally:
        _stop(proc)
