import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Set, Optional, Any
from fastapi import WebSocket
from ..database import SessionLocal
from ..models.settings import SyncEventJournal

logger = logging.getLogger(__name__)


class WebSocketConnectionManager:
    """
    Manages active authenticated WebSocket connections partitioned strictly by user_id.
    Ensures events are only dispatched to authorized client sessions for that user.
    """

    def __init__(self):
        # user_id -> Set[WebSocket]
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        self.lock = asyncio.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    def get_loop(self) -> Optional[asyncio.AbstractEventLoop]:
        if self._loop and self._loop.is_running():
            return self._loop
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            return None

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        async with self.lock:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()
            self.active_connections[user_id].add(websocket)
        logger.info(f"WebSocket connected: user_id={user_id}, total_connections={len(self.active_connections.get(user_id, set()))}")

    async def disconnect(self, user_id: int, websocket: WebSocket):
        async with self.lock:
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
        logger.info(f"WebSocket disconnected: user_id={user_id}")

    async def broadcast_to_user(
        self,
        user_id: int,
        event: str,
        data: Any,
        version: Optional[int] = None,
        entity_id: Optional[str] = None,
    ):
        """
        Send an authoritative event strictly to active sessions owned by user_id.
        Also persists the event into SyncEventJournal for offline/reconnect recovery.
        """
        now_str = datetime.utcnow().isoformat() + "Z"
        message = {
            "event": event,
            "user_id": user_id,
            "timestamp": now_str,
            "version": version or 1,
            "entity_id": str(entity_id) if entity_id is not None else None,
            "data": data,
        }
        json_payload = json.dumps(message, default=str)

        # Record into durable sync journal
        try:
            from ..dependencies import get_db
            # Lazy import app
            from ..main import app
            db_override = app.dependency_overrides.get(get_db)
            if db_override:
                gen = db_override()
                db = next(gen)
            else:
                db = SessionLocal()
                gen = None

            try:
                journal_entry = SyncEventJournal(
                    user_id=user_id,
                    event_type=event,
                    entity_id=str(entity_id) if entity_id is not None else None,
                    version=version or 1,
                    payload=json_payload,
                    created_at=datetime.utcnow(),
                )
                db.add(journal_entry)
                db.commit()
            finally:
                if gen:
                    try:
                        next(gen)
                    except StopIteration:
                        pass
                else:
                    db.close()
        except Exception as e:
            logger.error(f"Failed to record event to SyncEventJournal: {e}")

        targets = list(self.active_connections.get(user_id, set()))
        if not targets:
            logger.debug(f"No active WebSocket connections for user_id={user_id} (event: {event})")
            return

        dead_connections = []
        for ws in targets:
            try:
                await ws.send_text(json_payload)
            except Exception as exc:
                logger.warning(f"Error sending WebSocket message to user_id={user_id}: {exc}")
                dead_connections.append(ws)

        if dead_connections:
            async with self.lock:
                for ws in dead_connections:
                    if user_id in self.active_connections:
                        self.active_connections[user_id].discard(ws)

    def publish_event(
        self,
        user_id: int,
        event: str,
        data: Any,
        version: Optional[int] = None,
        entity_id: Optional[str] = None,
    ):
        """
        Thread-safe/sync-safe event publisher. Can be called from synchronous background threads
        or asynchronous request handlers.
        """
        coro = self.broadcast_to_user(user_id, event, data, version, entity_id)
        loop = self.get_loop()
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, loop)
        else:
            try:
                asyncio.run(coro)
            except Exception as e:
                logger.error(f"Could not execute broadcast_to_user via asyncio.run: {e}")


ws_manager = WebSocketConnectionManager()
