from __future__ import annotations

import socketio
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from api.app.db import Base, engine, get_db
from api.app.models import LoginEvent
from api.app.schemas import LoginEventIn, ScoreOut
from api.app.scoring import get_scorer
from api.app.socket import broadcast_login_scored, sio

fastapi_app = FastAPI(title="Anomalock", description="ML-based login risk scoring API")

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@fastapi_app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    get_scorer()  # fail fast at startup if the model artifact is missing/broken


@fastapi_app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@fastapi_app.post("/score", response_model=ScoreOut)
async def score_login(event: LoginEventIn, db: Session = Depends(get_db)) -> ScoreOut:
    scorer = get_scorer()
    features, score_info = scorer.score(db, event)

    row = LoginEvent(
        user_id=event.user_id,
        login_timestamp=event.login_timestamp,
        ip_address=event.ip_address,
        country=event.country,
        region=event.region,
        city=event.city,
        asn=event.asn,
        browser=event.browser,
        os=event.os,
        device_type=event.device_type,
        login_successful=event.login_successful,
        risk_score=score_info["risk_score"],
        flagged_reasons=score_info["flagged_reasons"],
        step_up_required=score_info["step_up_required"],
    )
    db.add(row)
    db.commit()

    result = ScoreOut(
        risk_score=score_info["risk_score"],
        risk_level=score_info["risk_level"],
        step_up_required=score_info["step_up_required"],
        flagged_reasons=score_info["flagged_reasons"],
        features={k: float(v) for k, v in features.items()},
    )

    await broadcast_login_scored(
        {
            "user_id": event.user_id,
            "login_timestamp": event.login_timestamp.isoformat(),
            "ip_address": event.ip_address,
            "country": event.country,
            "city": event.city,
            "device_type": event.device_type,
            "login_successful": event.login_successful,
            **result.model_dump(),
        }
    )

    return result


# Combined ASGI app: Socket.IO wraps FastAPI so both share one port/process.
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)
