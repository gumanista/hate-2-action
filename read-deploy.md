# Deployment Guide

This project currently has one deployment script:

```bash
scripts/deploy_prod_gcp.sh
```

Despite the name, the script is configurable. You can use it for production or
test deployments by passing different GCP project, Cloud Run, Cloud SQL, service
account, and secret-prefix values.

## When To Use The Script

Use this script when you want the full Cloud Run + Cloud SQL deployment flow:

- First-time setup of an environment.
- Redeploy after code changes.
- Redeploy after dependency changes in `requirements.txt` or `Dockerfile`.
- Update Cloud Run environment variables or Secret Manager bindings.
- Run the database initialization / embedding job.
- Register and verify the Telegram webhook for the deployed Cloud Run service.

The script does more than upload code. It builds the container image, ensures
GCP resources exist, runs the DB init job, deploys Cloud Run, registers the
Telegram webhook, and verifies that Telegram points to the final webhook URL.

## What Happens To The Database

The script always checks and prepares Cloud SQL, but it does not delete or
recreate the database when it already exists.

On every run, the script:

- Creates the Cloud SQL instance only if it does not already exist.
- Creates the database only if it does not already exist.
- Reuses the existing DB password from Secret Manager unless you explicitly pass
  a new `DB_PASSWORD`.

By default, the DB init job runs only when the database is newly created. The
default mode is:

```bash
--db-init-mode auto
```

In `auto` mode:

- First deploy with a new database: runs the Cloud Run DB init job.
- Later code-only redeploys with the same existing database: skips the DB init
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

## Production Deploy

Production uses the script defaults. This is the ready-to-copy production
deployment command:

```bash
gcloud config set account hate2action@gmail.com

PROJECT_ID=hate-2-action-492518 \
./scripts/deploy_prod_gcp.sh \
  --gcp-account hate2action@gmail.com \
  --project hate-2-action-492518 \
  --db-init-mode auto
```

The script reuses existing production Secret Manager values unless you
explicitly provide new values through environment variables.

Use this command after the test deployment works and you want to roll the same
local code state to the real Telegram bot.

## Test Redeploy

For test, switch to the test Google account and override the production
defaults.

```bash
gcloud config set account dashashevchuk2015@gmail.com

PROJECT_ID=YOUR_TEST_PROJECT_ID \
./scripts/deploy_prod_gcp.sh \
  --gcp-account dashashevchuk2015@gmail.com \
  --project YOUR_TEST_PROJECT_ID \
  --service-name hate2action-test \
  --sql-instance hate2action-test-db \
  --runtime-sa-name hate2action-test-runtime \
  --secret-prefix hate2action-test \
  --db-init-mode auto
```

Replace `YOUR_TEST_PROJECT_ID` with the actual test GCP project ID.

If the test secrets already exist in Secret Manager, the script reuses them. If
they do not exist yet, the script asks for `OPENAI_API_KEY` and
`TELEGRAM_BOT_TOKEN`, then generates DB and webhook secrets.

## Recommended Flow After Code Changes

Run tests locally:

```bash
python -m pytest tests/ -v
```

Redeploy test:

```bash
gcloud config set account dashashevchuk2015@gmail.com

PROJECT_ID=YOUR_TEST_PROJECT_ID \
./scripts/deploy_prod_gcp.sh \
  --gcp-account dashashevchuk2015@gmail.com \
  --project YOUR_TEST_PROJECT_ID \
  --service-name hate2action-test \
  --sql-instance hate2action-test-db \
  --runtime-sa-name hate2action-test-runtime \
  --secret-prefix hate2action-test \
  --db-init-mode auto
```

Then message the test Telegram bot. If test works, deploy production.

## Important Git Note

`scripts/` is currently ignored in `.gitignore`, so `scripts/deploy_prod_gcp.sh`
is not tracked by Git unless it is explicitly unignored or force-added.

Deployment scripts are usually worth tracking because they define how production
and test environments are recreated.
