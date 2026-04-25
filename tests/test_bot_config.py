"""Tests for bot.config and the create_bot factory.

These tests guard the behaviour that keeps prod and test bots independent:
- required env vars fail fast
- token format is validated
- BOT_ENV is validated and used as the db namespace
- identical tokens across peer env vars are rejected (would cause TG 409)
- webhook path defaults to telegram/webhook/<bot_env> and is overrideable
- create_bot(config) yields independent Application instances for different configs
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Match tests/test_pipelines.py: stub heavy side-effecty deps before importing
# bot.main so the test doesn't need a DB or OpenAI key.
mock_queries = MagicMock()
mock_llm = MagicMock()
sys.modules.setdefault("db.queries", mock_queries)
sys.modules.setdefault("db", MagicMock(queries=mock_queries))
sys.modules.setdefault("utils.llm", mock_llm)
sys.modules.setdefault("utils", MagicMock(llm=mock_llm))

from bot.config import (  # noqa: E402
    BotConfig,
    ConfigError,
    load_bot_config,
    token_fingerprint,
)


VALID_TOKEN_A = "1234567:AAEQ57qaJUuU-Zg4rk0kvzbGzIDwl35vQ1M"
VALID_TOKEN_B = "7654321:ZZEQ57qaJUuU-Zg4rk0kvzbGzIDwl35vQ1Z"


class _EnvPatch:
    """Context manager that replaces os.environ for the duration of the test."""

    def __init__(self, env: dict):
        self._env = env
        self._patcher = None

    def __enter__(self):
        self._patcher = patch.dict(os.environ, self._env, clear=True)
        self._patcher.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self._patcher.stop()


class TestTokenFingerprint(unittest.TestCase):
    def test_format_is_prefix_and_suffix(self):
        fp = token_fingerprint(VALID_TOKEN_A)
        self.assertTrue(fp.startswith(VALID_TOKEN_A[:6]))
        self.assertTrue(fp.endswith(VALID_TOKEN_A[-4:]))
        self.assertIn("...", fp)

    def test_full_token_never_appears(self):
        fp = token_fingerprint(VALID_TOKEN_A)
        self.assertNotIn(VALID_TOKEN_A, fp)
        self.assertNotIn(VALID_TOKEN_A[6:-4], fp)

    def test_empty_and_short_tokens_are_safe(self):
        self.assertEqual(token_fingerprint(""), "<empty>")
        self.assertEqual(token_fingerprint("abc"), "<short>")


class TestLoadBotConfig(unittest.TestCase):
    def _base_env(self, **overrides) -> dict:
        env = {
            "TELEGRAM_BOT_TOKEN": VALID_TOKEN_A,
            "OPENAI_API_KEY": "sk-test",
            "BOT_ENV": "test",
            "APP_MODE": "polling",
        }
        env.update(overrides)
        return env

    def test_missing_required_env_vars_raise(self):
        with _EnvPatch({}):
            with self.assertRaises(ConfigError) as ctx:
                load_bot_config()
            self.assertIn("TELEGRAM_BOT_TOKEN", str(ctx.exception))
            self.assertIn("OPENAI_API_KEY", str(ctx.exception))

    def test_invalid_token_format_is_rejected(self):
        with _EnvPatch(self._base_env(TELEGRAM_BOT_TOKEN="not-a-token")):
            with self.assertRaises(ConfigError):
                load_bot_config()

    def test_invalid_bot_env_is_rejected(self):
        with _EnvPatch(self._base_env(BOT_ENV="Prod With Spaces")):
            with self.assertRaises(ConfigError):
                load_bot_config()

    def test_bot_env_defaults_to_local(self):
        env = self._base_env()
        env.pop("BOT_ENV")
        with _EnvPatch(env):
            config = load_bot_config()
        self.assertEqual(config.bot_env, "local")
        self.assertEqual(config.db_namespace, "local")

    def test_peer_token_collision_is_rejected(self):
        env = self._base_env(TELEGRAM_BOT_TOKEN_TEST=VALID_TOKEN_A)
        with _EnvPatch(env):
            with self.assertRaises(ConfigError) as ctx:
                load_bot_config()
        self.assertIn("TELEGRAM_BOT_TOKEN_TEST", str(ctx.exception))

    def test_peer_token_with_different_value_is_accepted(self):
        env = self._base_env(TELEGRAM_BOT_TOKEN_TEST=VALID_TOKEN_B)
        with _EnvPatch(env):
            config = load_bot_config()
        self.assertEqual(config.token, VALID_TOKEN_A)

    def test_polling_mode_has_no_webhook_fields(self):
        with _EnvPatch(self._base_env(APP_MODE="polling")):
            config = load_bot_config()
        self.assertEqual(config.run_mode, "polling")
        self.assertIsNone(config.webhook_url)
        self.assertIsNone(config.webhook_path)

    def test_webhook_mode_requires_webhook_url(self):
        with _EnvPatch(self._base_env(APP_MODE="webhook")):
            with self.assertRaises(ConfigError):
                load_bot_config()

    def test_webhook_path_defaults_to_env_namespaced(self):
        env = self._base_env(
            APP_MODE="webhook",
            WEBHOOK_URL="https://example.run.app",
            BOT_ENV="prod",
        )
        with _EnvPatch(env):
            config = load_bot_config()
        self.assertEqual(config.webhook_path, "telegram/webhook/prod")
        self.assertEqual(
            config.webhook_url, "https://example.run.app/telegram/webhook/prod"
        )

    def test_webhook_path_can_be_overridden(self):
        env = self._base_env(
            APP_MODE="webhook",
            WEBHOOK_URL="https://example.run.app",
            TELEGRAM_WEBHOOK_PATH="custom/path",
        )
        with _EnvPatch(env):
            config = load_bot_config()
        self.assertEqual(config.webhook_path, "custom/path")

    def test_prod_and_test_configs_are_independent(self):
        prod_env = self._base_env(
            BOT_ENV="prod",
            TELEGRAM_BOT_TOKEN=VALID_TOKEN_A,
            APP_MODE="webhook",
            WEBHOOK_URL="https://prod.run.app",
        )
        test_env = self._base_env(
            BOT_ENV="test",
            TELEGRAM_BOT_TOKEN=VALID_TOKEN_B,
            APP_MODE="webhook",
            WEBHOOK_URL="https://test.run.app",
        )

        with _EnvPatch(prod_env):
            prod = load_bot_config()
        with _EnvPatch(test_env):
            test = load_bot_config()

        self.assertNotEqual(prod.token, test.token)
        self.assertNotEqual(prod.webhook_path, test.webhook_path)
        self.assertNotEqual(prod.webhook_url, test.webhook_url)
        self.assertNotEqual(prod.db_namespace, test.db_namespace)
        self.assertNotEqual(prod.token_fingerprint, test.token_fingerprint)


class TestCreateBotFactory(unittest.TestCase):
    """Two configs must yield two independent Application instances."""

    def _make_config(self, token: str, bot_env: str) -> BotConfig:
        return BotConfig(
            bot_env=bot_env,
            token=token,
            run_mode="polling",
            port=8080,
            webhook_url=None,
            webhook_path=None,
            webhook_secret=None,
        )

    def test_two_bots_get_distinct_applications(self):
        from bot.main import create_bot

        prod = create_bot(self._make_config(VALID_TOKEN_A, "prod"))
        test = create_bot(self._make_config(VALID_TOKEN_B, "test"))

        self.assertIsNot(prod, test)
        self.assertIsNot(prod.bot, test.bot)
        self.assertEqual(prod.bot.token, VALID_TOKEN_A)
        self.assertEqual(test.bot.token, VALID_TOKEN_B)


if __name__ == "__main__":
    unittest.main(verbosity=2)
