# novelcast/api/ws/notifications.py
import asyncio
from contextlib import asynccontextmanager
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        # job_id → payload dict, persists across page navigations
        self._active_jobs: dict[str, dict] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Replay all in-progress jobs to the new connection immediately
        for payload in self._active_jobs.values():
            try:
                await websocket.send_json(payload)
            except Exception:
                pass

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, event_type: str, payload: dict | None = None):
        message = {"type": event_type, "payload": payload}
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead.append(connection)
        for d in dead:
            self.disconnect(d)

    async def _job_start(self, job_id: str, event_type: str, payload: dict):
        """Register a job as active and broadcast it."""
        message = {"type": event_type, "payload": {"job_id": job_id, **payload}}
        self._active_jobs[job_id] = message
        await self.broadcast(event_type, {"job_id": job_id, **payload})

    async def _job_update(self, job_id: str, event_type: str, payload: dict):
        """Update a job's stored state and broadcast."""
        message = {"type": event_type, "payload": {"job_id": job_id, **payload}}
        if job_id in self._active_jobs:
            self._active_jobs[job_id] = message
        await self.broadcast(event_type, {"job_id": job_id, **payload})

    async def _job_finish(self, job_id: str, event_type: str, payload: dict, linger_seconds: int = 5):
        """Broadcast completion, then remove job after a short linger so late-reconnects still see it."""
        await self.broadcast(event_type, {"job_id": job_id, **payload})
        await asyncio.sleep(linger_seconds)
        self._active_jobs.pop(job_id, None)

    @asynccontextmanager
    async def job(self, job_id: str, label: str):
        """
        Async context manager for a tracked job. Usage:

            async with manager.job("sync-123", "Syncing chapters") as j:
                await j.update("Fetching remote...", progress=10)
                ...
                await j.update("Writing to DB...", progress=80)
            # success broadcast + cleanup happen automatically
        """
        await self._job_start(job_id, "job:start", {"label": label, "status": "running"})
        handle = _JobHandle(self, job_id)
        try:
            yield handle
            asyncio.ensure_future(
                self._job_finish(job_id, "job:done", {"label": label, "status": "done"})
            )
        except Exception as exc:
            asyncio.ensure_future(
                self._job_finish(
                    job_id, "job:error",
                    {"label": label, "status": "error", "error": str(exc)},
                    linger_seconds=15,  # errors linger longer so users can see them
                )
            )
            raise


class _JobHandle:
    """Returned by `manager.job()` — call `.update()` to push progress."""
    def __init__(self, manager: "ConnectionManager", job_id: str):
        self._manager = manager
        self._job_id = job_id

    async def update(self, message: str, progress: int | None = None):
        payload: dict = {"status": "running", "message": message}
        if progress is not None:
            payload["progress"] = progress
        await self._manager._job_update(self._job_id, "job:progress", payload)


manager = ConnectionManager()


@router.websocket("/ws/notifications")
async def notifications_ws(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)