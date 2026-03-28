"""Spoke Mail Relay — HTTP-to-SMTP bridge for automated notifications."""

import logging
import os
from email.message import EmailMessage
from pathlib import Path

import aiosmtplib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr

logger = logging.getLogger("mail_relay")

app = FastAPI(
    title="Spoke Mail Relay",
    description="HTTP-to-SMTP mail relay for automated service notifications",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
)

# ---------------------------------------------------------------------------
# Configuration (loaded once at startup)
# ---------------------------------------------------------------------------

SMTP_HOST: str = ""
SMTP_PORT: int = 587
SMTP_USERNAME: str = ""
SMTP_PASSWORD: str = ""
MAIL_FROM_EMAIL: str = ""
MAIL_FROM_NAME: str = ""
ALLOWED_RECIPIENTS: set[str] = set()


@app.on_event("startup")
async def _load_config() -> None:
    global SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD
    global MAIL_FROM_EMAIL, MAIL_FROM_NAME, ALLOWED_RECIPIENTS

    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
    MAIL_FROM_EMAIL = os.environ.get("MAIL_FROM_EMAIL", "")
    MAIL_FROM_NAME = os.environ.get("MAIL_FROM_NAME", "Spoke Mail Relay")

    password_file = os.environ.get("SMTP_PASSWORD_FILE", "")
    if password_file:
        password_path = Path(password_file)
        if not password_path.is_file():
            raise RuntimeError(f"SMTP_PASSWORD_FILE not found: {password_file}")
        SMTP_PASSWORD = password_path.read_text().strip()
    else:
        raise RuntimeError("SMTP_PASSWORD_FILE is required")

    recipients_raw = os.environ.get("MAIL_RELAY_ALLOWED_RECIPIENTS", "")
    if not recipients_raw:
        raise RuntimeError("MAIL_RELAY_ALLOWED_RECIPIENTS is required")
    ALLOWED_RECIPIENTS = {r.strip().lower() for r in recipients_raw.split(",") if r.strip()}

    if not SMTP_HOST:
        raise RuntimeError("SMTP_HOST is required")
    if not SMTP_USERNAME:
        raise RuntimeError("SMTP_USERNAME is required")
    if not MAIL_FROM_EMAIL:
        raise RuntimeError("MAIL_FROM_EMAIL is required")

    logger.info(
        "Mail relay configured: smtp=%s:%d, from=%s, allowed_recipients=%d",
        SMTP_HOST,
        SMTP_PORT,
        MAIL_FROM_EMAIL,
        len(ALLOWED_RECIPIENTS),
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
    recipient = req.to.lower()
    if recipient not in ALLOWED_RECIPIENTS:
        raise HTTPException(
            status_code=403,
            detail=f"Recipient not in allowlist: {req.to}",
        )

    msg = EmailMessage()
    msg["From"] = f"{MAIL_FROM_NAME} <{MAIL_FROM_EMAIL}>"
    msg["To"] = req.to
    msg["Subject"] = req.subject
    msg.set_content(req.body_text)

    if req.body_html:
        msg.add_alternative(req.body_html, subtype="html")

    try:
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USERNAME,
            password=SMTP_PASSWORD,
            use_tls=False,
            start_tls=False,
        )
    except aiosmtplib.SMTPException as exc:
        logger.error("SMTP send failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"SMTP error: {exc}") from exc

    logger.info("Email sent to %s: %s", req.to, req.subject)
    return SendResponse(status="sent", detail=f"Delivered to {req.to}")
