# ==============================================================================
# SPOKE MAIL RELAY - DOCKERFILE
# ==============================================================================
# Description: HTTP-to-SMTP mail relay service
# Base: python:3.13-slim (multi-stage build)
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
COPY src/ ./src/

RUN chown -R ${USERNAME}:${GROUPNAME} /app
USER ${USERNAME}:${GROUPNAME}

EXPOSE 8000

CMD ["uvicorn", "mail_relay.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
