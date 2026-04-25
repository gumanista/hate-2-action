"""Bot configuration loading and validation.

Centralises every environment-variable read related to the Telegram transport
so two deployments (prod, test, local) cannot silently share state.

Why this exists: previously ``bot/main.py`` read ``TELEGRAM_BOT_TOKEN`` and
``TELEGRAM_WEBHOOK_PATH`` directly with no environment identifier and no
fingerprint logging. A leaked token in the shell or a default webhook path
collision was enough to make the prod and test bots fight each other (Telegram
returns ``409 Conflict`` when two consumers compete for the same token).
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

REQUIRED_ENV_VARS = ("TELEGRAM_BOT_TOKEN", "OPENAI_API_KEY")
_TOKEN_RE = re.compile(r"^\d{6,}:[A-Za-z0-9_-]{20,}$")
_BOT_ENV_RE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
_PEER_TOKEN_PREFIX = "TELEGRAM_BOT_TOKEN_"


class ConfigError(ValueError):
    """Raised when bot configuration is missing or invalid."""


@dataclass(frozen=True)
class BotConfig:
    bot_env: str
    token: str
    run_mode: str
    port: int
    webhook_url: str | None
    webhook_path: str | None
    webhook_secret: str | None

    @property
    def token_fingerprint(self) -> str:
        return token_fingerprint(self.token)

    @property
    def db_namespace(self) -> str:
        return self.bot_env


def token_fingerprint(token: str) -> str:
    """Return a safe-to-log fingerprint: first 6 + last 4 characters."""
    if not token:
        return "<empty>"
    if len(token) <= 10:
        return "<short>"
    return f"{token[:6]}...{token[-4:]}"


def _resolve_run_mode() -> str:
    configured = os.getenv("APP_MODE")
    if configured:
        return configured.strip().lower()
    if os.getenv("WEBHOOK_URL"):
        return "webhook"
    return "polling"


def _check_no_peer_token_collision(token: str) -> None:
    """Fail fast if any TELEGRAM_BOT_TOKEN_* env var equals the active token.

    Catches the common mistake of sourcing one env file (test) while deploying
    or running another (prod). Two processes on the same token = 409 Conflict.
    """
    for key, value in os.environ.items():
        if key == "TELEGRAM_BOT_TOKEN" or not key.startswith(_PEER_TOKEN_PREFIX):
            continue
        if value.strip() == token:
            raise ConfigError(
                f"{key} has the same value as TELEGRAM_BOT_TOKEN. "
                "Refusing to start: two bots on one token cause Telegram 409 conflicts."
            )


def load_bot_config() -> BotConfig:
    missing = [name for name in REQUIRED_ENV_VARS if not os.getenv(name)]
    if missing:
        raise ConfigError(
            "Missing required environment variables: " + ", ".join(sorted(missing))
        )

    bot_env = (os.getenv("BOT_ENV") or "local").strip().lower()
    if not _BOT_ENV_RE.match(bot_env):
        raise ConfigError(
            f"BOT_ENV={bot_env!r} is invalid. Use a short slug like prod, test, local."
        )

    token = os.environ["TELEGRAM_BOT_TOKEN"].strip()
    if not _TOKEN_RE.match(token):
        raise ConfigError(
            "TELEGRAM_BOT_TOKEN does not look like a Telegram bot token "
            "(expected '<digits>:<base64-ish>')."
        )
    _check_no_peer_token_collision(token)

    run_mode = _resolve_run_mode()
    if run_mode not in ("polling", "webhook"):
        raise ConfigError(
            f"APP_MODE={run_mode!r} is invalid. Use 'polling' or 'webhook'."
        )

    port = int(os.getenv("PORT", "8080"))
    webhook_url: str | None = None
    webhook_path: str | None = None
    webhook_secret: str | None = None

    if run_mode == "webhook":
        base_url = os.getenv("WEBHOOK_URL")
        if not base_url:
            raise ConfigError(
                "WEBHOOK_URL is required when APP_MODE=webhook."
            )
        configured_path = os.getenv("TELEGRAM_WEBHOOK_PATH")
        webhook_path = (configured_path or f"telegram/webhook/{bot_env}").strip("/")
        if not webhook_path:
            raise ConfigError("TELEGRAM_WEBHOOK_PATH must not be empty.")
        webhook_url = f"{base_url.rstrip('/')}/{webhook_path}"
        webhook_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET") or None

    return BotConfig(
        bot_env=bot_env,
        token=token,
        run_mode=run_mode,
        port=port,
        webhook_url=webhook_url,
        webhook_path=webhook_path,
        webhook_secret=webhook_secret,
    )


def log_startup(config: BotConfig) -> None:
    """Log the resolved bot identity. Never logs the full token."""
    logger.info(
        "bot_startup env=%s pid=%s mode=%s token=%s webhook_path=%s db_ns=%s",
        config.bot_env,
        os.getpid(),
        config.run_mode,
        config.token_fingerprint,
        config.webhook_path or "-",
        config.db_namespace,
    )
