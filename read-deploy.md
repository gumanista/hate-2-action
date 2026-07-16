# Deployment Guide

This project has one deployment script:

```bash
scripts/deploy_prod_gcp.sh
```

Despite the name, the script is configurable. You can use it for production or
test deployments by passing different GCP project, Cloud Run, Cloud SQL, service
account, and secret-prefix values.

## Current Production Environment

- Google account: `hate2actionbot@gmail.com`
- GCP project: `h2a-bot-v2` (region `europe-central2`)
- Telegram bot: [@Hate_2_Action_bot](https://t.me/Hate_2_Action_bot)
- Cloud Run service: `hate2action-prod`, Cloud SQL instance: `hate2action-prod-db`

The previous account/projects (`hate2action@gmail.com`, `hate-2-action-*`) were
deleted and no longer exist.

## Configuration Files (Not Committed)

Secrets never live in the script or in git. They live in two gitignored files:

- `.env.prod` — deploy configuration and secrets for production:
  `GCP_ACCOUNT`, `PROJECT_ID`, `TELEGRAM_BOT_TOKEN` (prod bot),
  `OPENAI_API_KEY`, `GEMINI_API_KEY`. The deploy script loads this file
  automatically at startup. Variables already set in your shell take precedence
  over the file; use `ENV_FILE=/path/to/file` to point the script at a
  different file.
- `.env.local` — local development: test bot token and API keys. Used by
  `docker-compose` (`env_file`) and can be `source`d when running the bot
  directly on the host.

`DB_PASSWORD` and `WEBHOOK_SECRET` are intentionally not set in `.env.prod`:
the script generates them on first deploy and stores/reuses them in Secret
Manager (`hate2action-prod-db-password`, `hate2action-prod-telegram-webhook-secret`).

Do not `export TELEGRAM_BOT_TOKEN` (or other secrets) in `~/.bashrc`. Because
shell values override `.env.prod`, a stale token exported globally can deploy
the wrong bot. The script has a mismatch safeguard, but it only works once the
secret already exists in Secret Manager — it cannot catch this on a first
deploy to a fresh project.

## Production Deploy

With `.env.prod` in place, the production deploy is:

```bash
gcloud auth login hate2actionbot@gmail.com   # once per machine
./scripts/deploy_prod_gcp.sh
```

No flags are needed: project, account, and secrets come from `.env.prod`, and
everything else uses the script defaults. The script refuses to run if the
active gcloud account does not match `GCP_ACCOUNT`.

For a brand-new GCP project, before the first run:

- Link a billing account to the project in the Cloud Console (Cloud SQL and
  Cloud Run creation fail without it).
- Expect the first deploy to take a while: Cloud SQL instance creation alone is
  ~10 minutes, plus the Cloud Build and the embedding job (which consumes
  OpenAI API credits).

On every run the script: builds the image with Cloud Build, ensures GCP
resources exist, upserts secrets, deploys Cloud Run, runs the DB init job when
needed, registers the Telegram webhook, and verifies that Telegram points to
the final webhook URL. Re-run it to roll out code changes or rotate secrets.

## What Happens To The Database

The script always checks and prepares Cloud SQL, but it does not delete or
recreate the database when it already exists.

On every run, the script:

- Creates the Cloud SQL instance only if it does not already exist.
- Creates the database only if it does not already exist.
- Reuses the existing DB password from Secret Manager unless you explicitly pass
  a new `DB_PASSWORD`.

By default (`--db-init-mode auto`), the DB init job runs when the database is
newly created **or** when the init job has never completed successfully:

- First deploy with a new database: runs the Cloud Run DB init job.
- Deploy after an earlier run was interrupted between creating and
  initializing the database: detects the missing successful init execution and
  runs the DB init job.
- Later code-only redeploys with an initialized database: skips the DB init
  job.

The DB init job runs this command inside Cloud Run:

```bash
python init_db.py --embed
```

When the DB init job does run, it is generally safe for an existing database:

- Existing tables are kept because `db/schema.sql` uses `CREATE TABLE IF NOT EXISTS`.
- Existing seed rows are kept because `db/seed.sql` uses `ON CONFLICT ... DO NOTHING`.
- Existing user/chat/message data is not wiped.
- Existing organizations/projects/problems/solutions are not duplicated.

However, it still regenerates embeddings and recomputes similarity links, so it
can take extra time and use OpenAI API calls.

Use these modes when needed:

```bash
# Default: run DB init only when the database was just created
--db-init-mode auto

# Force DB init again after schema, seed, organization, project, or embedding changes
--db-init-mode always

# Never run DB init for this deploy
--db-init-mode never
```

## Test Deploy

A second bot token exists for testing. To deploy a separate test environment
(same or different project), override the production defaults so the two
deployments cannot collide:

```bash
TELEGRAM_BOT_TOKEN=<test bot token> \
./scripts/deploy_prod_gcp.sh \
  --bot-env test \
  --service-name hate2action-test \
  --sql-instance hate2action-test-db \
  --runtime-sa-name hate2action-test-runtime \
  --secret-prefix hate2action-test
```

Passing `TELEGRAM_BOT_TOKEN` in the command overrides the prod token from
`.env.prod` for this run only. `--bot-env test` also namespaces the webhook
path (`telegram/webhook/test`) so test and prod never receive each other's
updates. Once the test secrets exist in Secret Manager, later test redeploys
can omit the token.

## Recommended Flow After Code Changes

Run tests locally:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/ -v
```

(`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` avoids a clash with globally installed ROS
pytest plugins on this machine.)

Deploy test, message the test Telegram bot, and if it works:

```bash
./scripts/deploy_prod_gcp.sh
```

## Rotating Secrets

To rotate any secret (bot token, OpenAI key), update the value in `.env.prod`
and re-run the script — it adds a new Secret Manager version and re-registers
the webhook. If a token was ever exposed (pasted somewhere public), revoke it
via @BotFather first, then rotate.
