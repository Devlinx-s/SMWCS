from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.broadcaster import broadcaster
import structlog

log    = structlog.get_logger()
router = APIRouter()


@router.websocket('/ws/dashboard')
async def dashboard_ws(ws: WebSocket):
    await broadcaster.connect(ws)
    try:
        while True:
            # Keep connection alive — client can send pings
            data = await ws.receive_text()
            if data == 'ping':
                await ws.send_text('pong')
    except WebSocketDisconnect:
        broadcaster.disconnect(ws)
    except Exception as e:
        log.error('ws.error', error=str(e))
        broadcaster.disconnect(ws)
