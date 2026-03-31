"""Spoke Mail Relay — HTTP-to-SMTP bridge for automated notifications."""

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path

import aiosmtplib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr

logger = logging.getLogger("mail_relay")


# ---------------------------------------------------------------------------
# Configuration (loaded once at startup)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Config:
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    mail_from_email: str
    mail_from_name: str
    allowed_recipients: frozenset[str]


def _load_config() -> Config:
    password_file = os.environ.get("SMTP_PASSWORD_FILE", "")
    if not password_file:
        raise RuntimeError("SMTP_PASSWORD_FILE is required")
    password_path = Path(password_file)
    if not password_path.is_file():
        raise RuntimeError(f"SMTP_PASSWORD_FILE not found: {password_file}")

    smtp_host = os.environ.get("SMTP_HOST", "")
    smtp_username = os.environ.get("SMTP_USERNAME", "")
    mail_from_email = os.environ.get("MAIL_FROM_EMAIL", "")

    if not smtp_host:
        raise RuntimeError("SMTP_HOST is required")
    if not smtp_username:
        raise RuntimeError("SMTP_USERNAME is required")
    if not mail_from_email:
        raise RuntimeError("MAIL_FROM_EMAIL is required")

    recipients_raw = os.environ.get("MAIL_RELAY_ALLOWED_RECIPIENTS", "")
    if not recipients_raw:
        raise RuntimeError("MAIL_RELAY_ALLOWED_RECIPIENTS is required")
    allowed = frozenset(r.strip().lower() for r in recipients_raw.split(",") if r.strip())

    return Config(
        smtp_host=smtp_host,
        smtp_port=int(os.environ.get("SMTP_PORT", "587")),
        smtp_username=smtp_username,
        smtp_password=password_path.read_text().strip(),
        mail_from_email=mail_from_email,
        mail_from_name=os.environ.get("MAIL_FROM_NAME", "Spoke Mail Relay"),
        allowed_recipients=allowed,
    )


_config: Config | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    global _config
    _config = _load_config()
    logger.info(
        "Mail relay configured: smtp=%s:%d, from=%s, allowed_recipients=%d",
        _config.smtp_host,
        _config.smtp_port,
        _config.mail_from_email,
        len(_config.allowed_recipients),
    )
    yield


app = FastAPI(
    title="Spoke Mail Relay",
    description="HTTP-to-SMTP mail relay for automated service notifications",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class SendRequest(BaseModel):
    to: EmailStr
    subject: str
    body_text: str
    body_html: str | None = None


class SendResponse(BaseModel):
    status: str
    detail: str


class HealthResponse(BaseModel):
    status: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/send", response_model=SendResponse)
async def send_email(req: SendRequest) -> SendResponse:
    if _config is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    recipient = req.to.lower()
    if recipient not in _config.allowed_recipients:
        raise HTTPException(
            status_code=403,
            detail=f"Recipient not in allowlist: {req.to}",
        )

    msg = EmailMessage()
    msg["From"] = f"{_config.mail_from_name} <{_config.mail_from_email}>"
    msg["To"] = req.to
    msg["Subject"] = req.subject
    msg.set_content(req.body_text)

    if req.body_html:
        msg.add_alternative(req.body_html, subtype="html")

    try:
        await aiosmtplib.send(
            msg,
            hostname=_config.smtp_host,
            port=_config.smtp_port,
            username=_config.smtp_username,
            password=_config.smtp_password,
            use_tls=False,
            start_tls=False,
        )
    except aiosmtplib.SMTPException as exc:
        logger.error("SMTP send failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"SMTP error: {exc}") from exc

    logger.info("Email sent to %s: %s", req.to, req.subject)
    return SendResponse(status="sent", detail=f"Delivered to {req.to}")
