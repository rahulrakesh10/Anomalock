"""Socket.IO server mounted alongside the FastAPI app. Every scored login
event is broadcast to connected dashboard clients as a `login_scored`
message, so the live feed updates in real time without polling."""

from __future__ import annotations

import socketio

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")


async def broadcast_login_scored(payload: dict) -> None:
    await sio.emit("login_scored", payload)
