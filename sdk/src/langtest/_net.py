import socket
import time


def port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex((host, port)) == 0


def wait_for_port(port: int, host: str = "127.0.0.1", timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if port_in_use(port, host):
            return
        time.sleep(0.05)
    raise RuntimeError(f"LangTest server did not come up on port {port} within {timeout}s.")
