from __future__ import annotations

import datetime as dt

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Index, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from api.app.db import Base


class LoginEvent(Base):
    __tablename__ = "login_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    user_id: Mapped[str] = mapped_column(String, index=True)
    login_timestamp: Mapped[dt.datetime] = mapped_column(DateTime, index=True)

    ip_address: Mapped[str] = mapped_column(String, index=True)
    country: Mapped[str | None] = mapped_column(String, nullable=True)
    region: Mapped[str | None] = mapped_column(String, nullable=True)
    city: Mapped[str | None] = mapped_column(String, nullable=True)
    asn: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    browser: Mapped[str | None] = mapped_column(String, nullable=True)
    os: Mapped[str | None] = mapped_column(String, nullable=True)
    device_type: Mapped[str | None] = mapped_column(String, nullable=True)

    login_successful: Mapped[bool] = mapped_column(Boolean)

    # Populated at scoring time
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    flagged_reasons: Mapped[list | None] = mapped_column(JSON, nullable=True)
    step_up_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_login_events_user_ts", "user_id", "login_timestamp"),
        # Supports the per-IP failed-attempt window query used at scoring time.
        Index("ix_login_events_ip_ts_success", "ip_address", "login_timestamp", "login_successful"),
    )
