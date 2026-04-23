# ==============================================================================
# MAIL-RELAY MODULE - MAIL-RELAY DOCKERFILE
# ==============================================================================
# Description: HTTP-to-SMTP mail relay service (FastAPI + uvicorn)
# Author: Matt Barham
# Created: 2026-03-28
# Modified: 2026-04-22
# Version: 1.0.1
# Host: Your Server
# ==============================================================================
# Type: Dockerfile
# Base Image: python:3.13-slim (multi-stage build)
# Documentation: https://fastapi.tiangolo.com/
# Component: module: mail-relay / service: mail-relay
# ==============================================================================

FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml .
RUN uv pip compile pyproject.toml --quiet > requirements.txt && \
    uv pip install --system --no-cache --compile-bytecode -r requirements.txt

FROM python:3.13-slim

ARG USER_ID=1000
ARG GROUP_ID=968
ARG USERNAME=appuser
ARG GROUPNAME=appgroup

RUN groupadd -g ${GROUP_ID} ${GROUPNAME} && \
    useradd -u ${USER_ID} -g ${GROUPNAME} -s /bin/false -M ${USERNAME}

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn
COPY src/ ./

RUN chown -R ${USERNAME}:${GROUPNAME} /app
USER ${USERNAME}:${GROUPNAME}

EXPOSE 8000

CMD ["uvicorn", "mail_relay.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
