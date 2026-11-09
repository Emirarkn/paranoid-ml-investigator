"""Best-effort network block for the experiment worker process.

Patches the socket layer so project code executed through the adapter cannot open
network connections. This is a guard, not an OS sandbox: native extensions or
subprocesses spawned by project code can bypass it (documented in docs/PERMISSIONS.md).
"""
from __future__ import annotations

import socket


class NetworkBlocked(RuntimeError):
    pass


def install() -> None:
    def _blocked(*_a, **_k):
        raise NetworkBlocked("Network access is blocked inside pmi experiments (config/policy.yaml).")

    socket.socket.connect = _blocked          # type: ignore[assignment]
    socket.socket.connect_ex = _blocked       # type: ignore[assignment]
    socket.create_connection = _blocked       # type: ignore[assignment]
    socket.getaddrinfo = _blocked             # type: ignore[assignment]
