from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field, field_validator


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

    @field_validator("login_timestamp")
    @classmethod
    def _to_naive_utc(cls, v: dt.datetime) -> dt.datetime:
        """Stored/compared as naive UTC throughout, matching the RBA
        dataset's own timestamps — a timezone-aware value from a client
        (e.g. the dashboard's `Date.toISOString()`) would otherwise crash
        when subtracted against the naive datetimes already in the DB."""
        if v.tzinfo is not None:
            v = v.astimezone(dt.timezone.utc).replace(tzinfo=None)
        return v


class ScoreOut(BaseModel):
    risk_score: float = Field(..., description="0-100; percentile rank of anomalousness vs. training history")
    risk_level: str = Field(..., description="low | medium | high")
    step_up_required: bool
    flagged_reasons: list[str]
    features: dict[str, float]
