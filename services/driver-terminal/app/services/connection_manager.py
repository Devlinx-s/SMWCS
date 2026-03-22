from fastapi import WebSocket
from typing import Dict
import json
import structlog

log = structlog.get_logger()


class TerminalConnectionManager:
    """Maps truck_id → active WebSocket connection."""

    def __init__(self):
        self._connections: Dict[str, WebSocket] = {}

    async def connect(self, truck_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._connections[truck_id] = ws
        log.info('terminal.connected',
                 truck_id=truck_id,
                 total=len(self._connections))

    def disconnect(self, truck_id: str) -> None:
        self._connections.pop(truck_id, None)
        log.info('terminal.disconnected',
                 truck_id=truck_id,
                 remaining=len(self._connections))

    async def send(self, truck_id: str, message: dict) -> bool:
        ws = self._connections.get(truck_id)
        if not ws:
            return False
        try:
            await ws.send_text(json.dumps(message, default=str))
            return True
        except Exception as e:
            log.error('terminal.send.failed',
                      truck_id=truck_id, error=str(e))
            self.disconnect(truck_id)
            return False

    async def broadcast(self, message: dict) -> None:
        for truck_id in list(self._connections.keys()):
            await self.send(truck_id, message)

    @property
    def connected_trucks(self) -> list[str]:
        return list(self._connections.keys())

    @property
    def count(self) -> int:
        return len(self._connections)


manager = TerminalConnectionManager()
