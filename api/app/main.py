from __future__ import annotations

from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from api.app.db import Base, engine, get_db
from api.app.models import LoginEvent
from api.app.schemas import LoginEventIn, ScoreOut
from api.app.scoring import get_scorer

app = FastAPI(title="Anomalock", description="ML-based login risk scoring API")


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    get_scorer()  # fail fast at startup if the model artifact is missing/broken


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/score", response_model=ScoreOut)
def score_login(event: LoginEventIn, db: Session = Depends(get_db)) -> ScoreOut:
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

    return ScoreOut(
        risk_score=score_info["risk_score"],
        risk_level=score_info["risk_level"],
        step_up_required=score_info["step_up_required"],
        flagged_reasons=score_info["flagged_reasons"],
        features={k: float(v) for k, v in features.items()},
    )
