# spoke-mail-relay

Spoke module for an HTTP-to-SMTP mail relay — a lightweight [FastAPI](https://fastapi.tiangolo.com/) service that lets automated agents send email through any SMTP provider.

## Services

| Service    | Description           | Port | Network |
|------------|-----------------------|------|---------|
| mail-relay | HTTP-to-SMTP bridge   | 8000 | troxy   |

## Prerequisites

- Spoke hub deployed with `troxy` network
- Traefik available as a hub service (with `chain-agent-api` middleware for BasicAuth)
- An SMTP provider accessible from the Docker network (e.g., [spoke-protonmail](https://github.com/captainzonks/spoke-protonmail))
- `smtp_password` secret created

## Quick Start

```bash
# Copy and configure environment
cp .env.example .env
# Edit .env with your SMTP provider details and allowed recipients

# Create secrets
mkdir -p ${SECRETS_DIR}/proton/
echo "your-smtp-password" > ${SECRETS_DIR}/proton/proton_bridge_password

# Build and deploy
docker compose build
docker compose up -d
```

## API

All endpoints are behind Traefik BasicAuth (`chain-agent-api` middleware).

### `POST /send`

Send an email to an allowlisted recipient.

```json
{
  "to": "admin@example.com",
  "subject": "Alert from Rome",
  "body_text": "Plain text content",
  "body_html": "<p>Optional HTML content</p>"
}
```

**Responses:**
- `200` — Email delivered
- `403` — Recipient not in allowlist
- `502` — SMTP error (upstream provider issue)

### `GET /health`

Returns `{"status": "ok"}` when the service is running.

## Module Environment Variables

| Variable                        | Default                | Description                              |
|---------------------------------|------------------------|------------------------------------------|
| `MAIL_RELAY_IMAGE`              | `spoke/mail-relay:1.0.0` | Docker image (custom build)           |
| `MAIL_RELAY_IP`                 | `192.168.35.112`       | Static IP on troxy network               |
| `SMTP_HOST`                     | `smtp-bridge`          | SMTP server hostname                     |
| `SMTP_PORT`                     | `587`                  | SMTP server port                         |
| `SMTP_USERNAME`                 | `user@example.com`     | SMTP authentication username             |
| `MAIL_FROM_EMAIL`               | `noreply@example.com`  | Sender email address                     |
| `MAIL_FROM_NAME`                | `Spoke Mail Relay`     | Sender display name                      |
| `MAIL_RELAY_ALLOWED_RECIPIENTS` | `admin@example.com`    | Comma-separated recipient allowlist      |
| `PORT`                          | `8000`                 | Application listen port                  |

## Secrets

| Secret Name      | Required | Description                    |
|------------------|----------|--------------------------------|
| `smtp_password`  | Yes      | SMTP authentication password   |

## Security

- **Recipient allowlist**: Only addresses in `MAIL_RELAY_ALLOWED_RECIPIENTS` can receive email (open relay prevention)
- **BasicAuth**: Traefik `chain-agent-api` middleware gates all HTTP access
- **Docker secrets**: SMTP password loaded from `/run/secrets/`, never in environment variables
- **Non-root**: Runs as UID 1000 / GID 968 with all capabilities dropped
- **Resource limits**: 128MB memory, 0.25 CPU

## Architecture

```
Automated Agent (Claude, cron, etc.)
    |
    | HTTPS POST /send (BasicAuth)
    v
[Traefik] → chain-agent-api middleware
    |
    | HTTP :8000
    v
[mail-relay container]
    |
    | SMTP :587
    v
[SMTP Provider (e.g., protonmail-bridge)]
    |
    | ProtonMail API / external SMTP
    v
[Recipient inbox]
```

## References

- [FastAPI](https://fastapi.tiangolo.com/)
- [aiosmtplib](https://aiosmtplib.readthedocs.io/)
- [Spoke](https://github.com/captainzonks/spoke)
