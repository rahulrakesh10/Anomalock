from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field


class LoginEventIn(BaseModel):
    user_id: str
    login_timestamp: dt.datetime
    ip_address: str
    country: str | None = None
    region: str | None = None
    city: str | None = None
    asn: int | None = None
    browser: str | None = None
    os: str | None = None
    device_type: str | None = None
    login_successful: bool = True


class ScoreOut(BaseModel):
    risk_score: float = Field(..., description="0-100; percentile rank of anomalousness vs. training history")
    risk_level: str = Field(..., description="low | medium | high")
    step_up_required: bool
    flagged_reasons: list[str]
    features: dict[str, float]
