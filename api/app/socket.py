"""Socket.IO server mounted alongside the FastAPI app. Every scored login
event is broadcast to connected dashboard clients as a `login_scored`
message, so the live feed updates in real time without polling.

Single-instance assumption: this AsyncServer keeps its connected-client
registry in memory, local to one process. Fly.io defaults new apps to 2
machines for HA — if a /score request lands on a different machine than a
given browser's WebSocket, that browser never sees the broadcast (the
emit happens on a process that has no idea the client exists). This app
is pinned to a single machine (`fly scale count 1`) for that reason.
Scaling back out would need a shared client_manager (e.g.
socketio.AsyncRedisManager) to fan out emits across processes.
"""

from __future__ import annotations

import socketio

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")


async def broadcast_login_scored(payload: dict) -> None:
    await sio.emit("login_scored", payload)
