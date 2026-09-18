import socket
from collections.abc import Callable

import pytest


@pytest.fixture
def free_port() -> Callable[[], int]:
    """Factory for an available localhost TCP port, callable multiple times per test."""

    def _free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]

    return _free_port
