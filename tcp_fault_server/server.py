import argparse
import logging
import random
import socket
import struct
import sys
import threading
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s tcp_fault %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("tcp_fault")

MODES = ("accept", "close", "hang", "reset", "random-close")


def _reset(conn: socket.socket) -> None:
    try:
        conn.setsockopt(
            socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0)
        )
    except OSError:
        pass
    try:
        conn.close()
    except OSError:
        pass


def _handle(conn: socket.socket, addr, mode: str) -> None:
    logger.info("accepted connection from %s:%s mode=%s", addr[0], addr[1], mode)
    try:
        if mode == "close":
            conn.close()
        elif mode == "reset":
            _reset(conn)
        elif mode == "hang":
            while True:
                time.sleep(3600)
        elif mode == "random-close":
            if random.random() < 0.5:
                logger.info("random-close: closing immediately")
                conn.close()
            else:
                logger.info("random-close: hanging")
                while True:
                    time.sleep(3600)
        else:
            conn.settimeout(365 * 24 * 3600)
            try:
                conn.recv(4096)
            except socket.timeout:
                pass
    except OSError as error:
        logger.info("connection %s:%s ended: %s", addr[0], addr[1], error)
    finally:
        if mode not in ("reset",):
            try:
                conn.close()
            except OSError:
                pass


def serve(host: str, port: int, mode: str) -> None:
    if mode not in MODES:
        raise SystemExit(f"mode must be one of {MODES}")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(100)
    logger.info("TCP Fault Server listening on %s:%s mode=%s", host, port, mode)
    try:
        while True:
            try:
                conn, addr = server.accept()
            except OSError as error:
                logger.error("accept failed: %s", error)
                continue
            thread = threading.Thread(
                target=_handle, args=(conn, addr, mode), daemon=True
            )
            thread.start()
    except KeyboardInterrupt:
        logger.info("shutting down")
    finally:
        server.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="TCP 5450 Fault Server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5450)
    parser.add_argument("--mode", default="close", choices=MODES)
    args = parser.parse_args()
    serve(args.host, args.port, args.mode)


if __name__ == "__main__":
    sys.exit(main())
