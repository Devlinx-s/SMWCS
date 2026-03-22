from fastapi import WebSocket
from typing import Set
import json
import structlog

log = structlog.get_logger()


class DashboardBroadcaster:
    def __init__(self):
        self._clients: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.add(ws)
        log.info('dashboard.client.connected', total=len(self._clients))

    def disconnect(self, ws: WebSocket) -> None:
        self._clients.discard(ws)
        log.info('dashboard.client.disconnected', total=len(self._clients))

    async def broadcast(self, message: dict) -> None:
        if not self._clients:
            return
        dead     = set()
        payload  = json.dumps(message, default=str)
        for ws in list(self._clients):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)
        self._clients -= dead

    @property
    def client_count(self) -> int:
        return len(self._clients)


broadcaster = DashboardBroadcaster()
