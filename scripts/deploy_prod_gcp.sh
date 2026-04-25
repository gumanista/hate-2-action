#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

DEFAULT_GCP_ACCOUNT="hate2action@gmail.com"
DEFAULT_REGION="europe-central2"
DEFAULT_SERVICE_NAME="hate2action-prod"
DEFAULT_SQL_INSTANCE="hate2action-prod-db"
DEFAULT_DB_NAME="hate2action"
DEFAULT_DB_USER="hate2action"
DEFAULT_ARTIFACT_REPO="hate2action"
DEFAULT_IMAGE_NAME="bot"
DEFAULT_RUNTIME_SA_NAME="hate2action-prod-runtime"
DEFAULT_DB_TIER="db-custom-1-3840"
DEFAULT_DB_VERSION="POSTGRES_18"
DEFAULT_DB_EDITION="ENTERPRISE"
DEFAULT_BOT_ENV="prod"
DEFAULT_WEBHOOK_PATH=""
DEFAULT_SECRET_PREFIX="hate2action-prod"
DEFAULT_FINAL_MIN_INSTANCES="0"
DEFAULT_DB_INIT_MODE="auto"

PROJECT_ID="${PROJECT_ID:-}"
REGION="${REGION:-$DEFAULT_REGION}"
SERVICE_NAME="${SERVICE_NAME:-$DEFAULT_SERVICE_NAME}"
SQL_INSTANCE="${SQL_INSTANCE:-$DEFAULT_SQL_INSTANCE}"
DB_NAME="${DB_NAME:-$DEFAULT_DB_NAME}"
DB_USER="${DB_USER:-$DEFAULT_DB_USER}"
ARTIFACT_REPO="${ARTIFACT_REPO:-$DEFAULT_ARTIFACT_REPO}"
IMAGE_NAME="${IMAGE_NAME:-$DEFAULT_IMAGE_NAME}"
RUNTIME_SA_NAME="${RUNTIME_SA_NAME:-$DEFAULT_RUNTIME_SA_NAME}"
DB_TIER="${DB_TIER:-$DEFAULT_DB_TIER}"
DB_VERSION="${DB_VERSION:-$DEFAULT_DB_VERSION}"
DB_EDITION="${DB_EDITION:-$DEFAULT_DB_EDITION}"
BOT_ENV="${BOT_ENV:-$DEFAULT_BOT_ENV}"
TELEGRAM_WEBHOOK_PATH="${TELEGRAM_WEBHOOK_PATH:-$DEFAULT_WEBHOOK_PATH}"
SECRET_PREFIX="${SECRET_PREFIX:-$DEFAULT_SECRET_PREFIX}"
FINAL_MIN_INSTANCES="${FINAL_MIN_INSTANCES:-$DEFAULT_FINAL_MIN_INSTANCES}"
DB_INIT_MODE="${DB_INIT_MODE:-$DEFAULT_DB_INIT_MODE}"
GCP_ACCOUNT="${GCP_ACCOUNT:-$DEFAULT_GCP_ACCOUNT}"
OPENAI_API_KEY="${OPENAI_API_KEY:-}"
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
DB_PASSWORD="${DB_PASSWORD:-}"
WEBHOOK_SECRET="${WEBHOOK_SECRET:-}"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/deploy_prod_gcp.sh [options]

Options:
  --project PROJECT_ID
  --region REGION
  --service-name NAME
  --sql-instance NAME
  --db-name NAME
  --db-user NAME
  --artifact-repo NAME
  --image-name NAME
  --runtime-sa-name NAME
  --db-tier TIER
  --db-version VERSION
  --db-edition EDITION
  --bot-env NAME              short slug used as BOT_ENV (e.g. prod, test)
  --webhook-path PATH         override webhook path (defaults to telegram/webhook/<bot-env>)
  --secret-prefix PREFIX
  --final-min-instances COUNT
  --db-init-mode auto|always|never
  --gcp-account EMAIL
  --help

The script can also read these values from environment variables:
  PROJECT_ID REGION SERVICE_NAME SQL_INSTANCE DB_NAME DB_USER ARTIFACT_REPO
  IMAGE_NAME RUNTIME_SA_NAME DB_TIER DB_VERSION DB_EDITION BOT_ENV
  TELEGRAM_WEBHOOK_PATH SECRET_PREFIX FINAL_MIN_INSTANCES DB_INIT_MODE
  GCP_ACCOUNT OPENAI_API_KEY TELEGRAM_BOT_TOKEN DB_PASSWORD WEBHOOK_SECRET

If OPENAI_API_KEY, TELEGRAM_BOT_TOKEN, DB_PASSWORD, or WEBHOOK_SECRET are not
set, existing Secret Manager values are reused. New values are only prompted or
generated when the corresponding secret does not exist yet.

DB_INIT_MODE controls the Cloud Run DB init job:
  auto   Run only when the database is newly created. This is the default.
  always Run on every deploy.
  never  Do not run.
EOF
}

log() {
  printf '\n[%s] %s\n' "$(date +'%Y-%m-%d %H:%M:%S')" "$*"
}

die() {
  printf '\nERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"
}

prompt_with_default() {
  local prompt="$1"
  local default_value="$2"
  local reply

  if [[ -n "$default_value" ]]; then
    read -r -p "$prompt [$default_value]: " reply
    printf '%s' "${reply:-$default_value}"
    return
  fi

  read -r -p "$prompt: " reply
  printf '%s' "$reply"
}

prompt_secret() {
  local prompt="$1"
  local reply

  read -r -s -p "$prompt: " reply
  printf '\n' >&2
  printf '%s' "$reply"
}

generate_secret() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 24
  else
    date +%s | sha256sum | awk '{print $1}'
  fi
}

telegram_post() {
  local method="$1"
  shift

  curl -fsS -X POST \
    "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/${method}" \
    "$@"
}

telegram_get() {
  local method="$1"
  shift

  curl -fsS \
    "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/${method}" \
    "$@"
}

telegram_response_ok() {
  printf '%s' "$1" | grep -Eq '"ok"[[:space:]]*:[[:space:]]*true'
}

json_string_value() {
  local key="$1"

  sed -nE "s/.*\"${key}\"[[:space:]]*:[[:space:]]*\"([^\"]*)\".*/\1/p" \
    | sed 's#\\/#/#g'
}

secret_exists() {
  local secret_name="$1"
  gcloud secrets describe "$secret_name" --project "$PROJECT_ID" >/dev/null 2>&1
}

read_secret_value() {
  local secret_name="$1"
  gcloud secrets versions access latest \
    --secret "$secret_name" \
    --project "$PROJECT_ID" \
    2>/dev/null || true
}

upsert_secret() {
  local secret_name="$1"
  local secret_value="$2"
  local tmp_file

  tmp_file="$(mktemp)"
  printf '%s' "$secret_value" >"$tmp_file"

  if secret_exists "$secret_name"; then
    gcloud secrets versions add "$secret_name" \
      --data-file="$tmp_file" \
      --project "$PROJECT_ID" \
      >/dev/null
    log "Added a new version for secret ${secret_name}"
  else
    gcloud secrets create "$secret_name" \
      --replication-policy=automatic \
      --data-file="$tmp_file" \
      --project "$PROJECT_ID" \
      >/dev/null
    log "Created secret ${secret_name}"
  fi

  rm -f "$tmp_file"
}

service_account_exists() {
  local sa_email="$1"
  gcloud iam service-accounts describe "$sa_email" --project "$PROJECT_ID" >/dev/null 2>&1
}

grant_project_role() {
  local member="$1"
  local role="$2"

  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="$member" \
    --role="$role" \
    --quiet \
    >/dev/null
}

sql_instance_exists() {
  gcloud sql instances describe "$SQL_INSTANCE" --project "$PROJECT_ID" >/dev/null 2>&1
}

sql_database_exists() {
  local db_name="$1"
  gcloud sql databases describe "$db_name" \
    --instance "$SQL_INSTANCE" \
    --project "$PROJECT_ID" \
    >/dev/null 2>&1
}

sql_user_exists() {
  local user_name="$1"
  gcloud sql users list \
    --instance "$SQL_INSTANCE" \
    --project "$PROJECT_ID" \
    --format='value(name)' \
    | grep -Fxq "$user_name"
}

artifact_repo_exists() {
  gcloud artifacts repositories describe "$ARTIFACT_REPO" \
    --location "$REGION" \
    --project "$PROJECT_ID" \
    >/dev/null 2>&1
}

run_service_exists() {
  gcloud run services describe "$SERVICE_NAME" \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    >/dev/null 2>&1
}

run_job_exists() {
  gcloud run jobs describe "$JOB_NAME" \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    >/dev/null 2>&1
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --project)
        PROJECT_ID="$2"
        shift 2
        ;;
      --region)
        REGION="$2"
        shift 2
        ;;
      --service-name)
        SERVICE_NAME="$2"
        shift 2
        ;;
      --sql-instance)
        SQL_INSTANCE="$2"
        shift 2
        ;;
      --db-name)
        DB_NAME="$2"
        shift 2
        ;;
      --db-user)
        DB_USER="$2"
        shift 2
        ;;
      --artifact-repo)
        ARTIFACT_REPO="$2"
        shift 2
        ;;
      --image-name)
        IMAGE_NAME="$2"
        shift 2
        ;;
      --runtime-sa-name)
        RUNTIME_SA_NAME="$2"
        shift 2
        ;;
      --db-tier)
        DB_TIER="$2"
        shift 2
        ;;
      --db-version)
        DB_VERSION="$2"
        shift 2
        ;;
      --db-edition)
        DB_EDITION="$2"
        shift 2
        ;;
      --bot-env)
        BOT_ENV="$2"
        shift 2
        ;;
      --webhook-path)
        TELEGRAM_WEBHOOK_PATH="$2"
        shift 2
        ;;
      --secret-prefix)
        SECRET_PREFIX="$2"
        shift 2
        ;;
      --final-min-instances)
        FINAL_MIN_INSTANCES="$2"
        shift 2
        ;;
      --db-init-mode)
        DB_INIT_MODE="$2"
        shift 2
        ;;
      --gcp-account)
        GCP_ACCOUNT="$2"
        shift 2
        ;;
      --help|-h)
        usage
        exit 0
        ;;
      *)
        die "Unknown option: $1"
        ;;
    esac
  done
}

parse_args "$@"

require_command gcloud
require_command curl

if [[ -z "$PROJECT_ID" ]]; then
  current_project="$(gcloud config get-value project 2>/dev/null | tr -d '\n')"
  if [[ "$current_project" == "(unset)" ]]; then
    current_project=""
  fi
  PROJECT_ID="$(prompt_with_default "GCP project id for production" "$current_project")"
fi

[[ -n "$PROJECT_ID" ]] || die "PROJECT_ID is required"

case "$DB_EDITION" in
  ENTERPRISE|enterprise)
    DB_EDITION="ENTERPRISE"
    ;;
  ENTERPRISE_PLUS|enterprise_plus)
    DB_EDITION="ENTERPRISE_PLUS"
    ;;
  *)
    die "DB_EDITION must be ENTERPRISE or ENTERPRISE_PLUS"
    ;;
esac

if [[ "$DB_EDITION" == "ENTERPRISE_PLUS" && "$DB_TIER" == db-custom-* ]]; then
  die "Cloud SQL ENTERPRISE_PLUS does not support db-custom tiers. Use a predefined tier like db-perf-optimized-N-2 or set DB_EDITION=ENTERPRISE."
fi

case "$DB_INIT_MODE" in
  auto|always|never)
    ;;
  *)
    die "DB_INIT_MODE must be auto, always, or never"
    ;;
esac

if ! [[ "$BOT_ENV" =~ ^[a-z][a-z0-9_-]{0,31}$ ]]; then
  die "BOT_ENV must be a short lowercase slug (got: '${BOT_ENV}')"
fi

# Default webhook path namespaced per-environment so test and prod cannot
# collide, even if both deployments share a service URL by mistake.
if [[ -z "$TELEGRAM_WEBHOOK_PATH" ]]; then
  TELEGRAM_WEBHOOK_PATH="telegram/webhook/${BOT_ENV}"
fi

RUNTIME_SA_EMAIL="${RUNTIME_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
JOB_NAME="${SERVICE_NAME}-db-init"
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/${IMAGE_NAME}:latest"
DB_PASSWORD_SECRET="${SECRET_PREFIX}-db-password"
OPENAI_SECRET="${SECRET_PREFIX}-openai-api-key"
TELEGRAM_SECRET="${SECRET_PREFIX}-telegram-bot-token"
WEBHOOK_SECRET_NAME="${SECRET_PREFIX}-telegram-webhook-secret"

active_account="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -n 1)"
if [[ -z "$active_account" ]]; then
  die "No active gcloud account. Run: gcloud auth login ${GCP_ACCOUNT}"
fi

if [[ -n "$GCP_ACCOUNT" && "$active_account" != "$GCP_ACCOUNT" ]]; then
  die "Active gcloud account is ${active_account}. Switch to ${GCP_ACCOUNT} before running this script."
fi

log "Using gcloud account: ${active_account}"
log "Using production project: ${PROJECT_ID}"

gcloud config set project "$PROJECT_ID" >/dev/null
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
[[ -n "$PROJECT_NUMBER" ]] || die "Could not resolve project number for ${PROJECT_ID}"

log "Enabling required Google Cloud APIs"
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  --project "$PROJECT_ID" \
  >/dev/null

if [[ -z "$DB_PASSWORD" ]]; then
  if secret_exists "$DB_PASSWORD_SECRET"; then
    DB_PASSWORD="$(read_secret_value "$DB_PASSWORD_SECRET")"
    log "Reusing existing Cloud SQL password secret ${DB_PASSWORD_SECRET}"
  else
    DB_PASSWORD="$(generate_secret)"
    log "Generated a random Cloud SQL password for ${DB_USER}"
  fi
fi
[[ -n "$DB_PASSWORD" ]] || die "DB_PASSWORD is required"

if [[ -z "$OPENAI_API_KEY" ]]; then
  if secret_exists "$OPENAI_SECRET"; then
    OPENAI_API_KEY="$(read_secret_value "$OPENAI_SECRET")"
    log "Reusing existing OpenAI API key secret ${OPENAI_SECRET}"
  else
    OPENAI_API_KEY="$(prompt_secret "OpenAI API key")"
  fi
fi
[[ -n "$OPENAI_API_KEY" ]] || die "OPENAI_API_KEY is required"

SHELL_TELEGRAM_BOT_TOKEN="$TELEGRAM_BOT_TOKEN"
if [[ -z "$TELEGRAM_BOT_TOKEN" ]]; then
  if secret_exists "$TELEGRAM_SECRET"; then
    TELEGRAM_BOT_TOKEN="$(read_secret_value "$TELEGRAM_SECRET")"
    log "Reusing existing Telegram bot token secret ${TELEGRAM_SECRET}"
  else
    TELEGRAM_BOT_TOKEN="$(prompt_secret "Telegram bot token for ${BOT_ENV} bot")"
  fi
elif secret_exists "$TELEGRAM_SECRET"; then
  EXISTING_SECRET_VALUE="$(read_secret_value "$TELEGRAM_SECRET")"
  if [[ -n "$EXISTING_SECRET_VALUE" && "$EXISTING_SECRET_VALUE" != "$SHELL_TELEGRAM_BOT_TOKEN" ]]; then
    die "TELEGRAM_BOT_TOKEN is set in your shell but differs from the value in Secret Manager (${TELEGRAM_SECRET}). This usually means a token from another environment leaked into your shell (e.g. a sourced .env.local). Refusing to deploy and overwrite the wrong bot's webhook. Unset TELEGRAM_BOT_TOKEN or pass the correct one explicitly."
  fi
fi
[[ -n "$TELEGRAM_BOT_TOKEN" ]] || die "TELEGRAM_BOT_TOKEN is required"

if [[ -z "$WEBHOOK_SECRET" ]]; then
  if secret_exists "$WEBHOOK_SECRET_NAME"; then
    WEBHOOK_SECRET="$(read_secret_value "$WEBHOOK_SECRET_NAME")"
    log "Reusing existing Telegram webhook secret ${WEBHOOK_SECRET_NAME}"
  else
    WEBHOOK_SECRET="$(generate_secret)"
    log "Generated a random Telegram webhook secret"
  fi
fi
[[ -n "$WEBHOOK_SECRET" ]] || die "WEBHOOK_SECRET is required"

log "Validating Telegram bot token"
telegram_response="$(telegram_get getMe)"
if ! telegram_response_ok "$telegram_response"; then
  printf '%s\n' "$telegram_response" >&2
  die "Telegram bot token validation failed"
fi

if ! service_account_exists "$RUNTIME_SA_EMAIL"; then
  log "Creating runtime service account ${RUNTIME_SA_EMAIL}"
  gcloud iam service-accounts create "$RUNTIME_SA_NAME" \
    --display-name="Hate2Action Production Runtime" \
    --project "$PROJECT_ID" \
    >/dev/null
else
  log "Runtime service account already exists: ${RUNTIME_SA_EMAIL}"
fi

for role in roles/cloudsql.client roles/secretmanager.secretAccessor; do
  grant_project_role "serviceAccount:${RUNTIME_SA_EMAIL}" "$role"
done

for build_sa in \
  "${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  "${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
do
  if service_account_exists "$build_sa"; then
    grant_project_role "serviceAccount:${build_sa}" roles/artifactregistry.writer
  fi
done

if ! artifact_repo_exists; then
  log "Creating Artifact Registry repository ${ARTIFACT_REPO}"
  gcloud artifacts repositories create "$ARTIFACT_REPO" \
    --repository-format=docker \
    --location "$REGION" \
    --description="Hate2Action production images" \
    --project "$PROJECT_ID" \
    >/dev/null
else
  log "Artifact Registry repository already exists: ${ARTIFACT_REPO}"
fi

if ! sql_instance_exists; then
  log "Creating Cloud SQL instance ${SQL_INSTANCE}"
  gcloud sql instances create "$SQL_INSTANCE" \
    --database-version="$DB_VERSION" \
    --tier="$DB_TIER" \
    --edition="$DB_EDITION" \
    --region="$REGION" \
    --storage-type=SSD \
    --storage-size=20 \
    --availability-type=zonal \
    --backup-start-time=03:00 \
    --project "$PROJECT_ID" \
    >/dev/null
else
  log "Cloud SQL instance already exists: ${SQL_INSTANCE}"
fi

DB_CREATED=false
if ! sql_database_exists "$DB_NAME"; then
  log "Creating database ${DB_NAME}"
  gcloud sql databases create "$DB_NAME" \
    --instance "$SQL_INSTANCE" \
    --project "$PROJECT_ID" \
    >/dev/null
  DB_CREATED=true
else
  log "Database already exists: ${DB_NAME}"
fi

if ! sql_user_exists "$DB_USER"; then
  log "Creating Cloud SQL user ${DB_USER}"
  gcloud sql users create "$DB_USER" \
    --instance "$SQL_INSTANCE" \
    --password "$DB_PASSWORD" \
    --project "$PROJECT_ID" \
    >/dev/null
else
  log "Updating password for Cloud SQL user ${DB_USER}"
  gcloud sql users set-password "$DB_USER" \
    --instance "$SQL_INSTANCE" \
    --password "$DB_PASSWORD" \
    --project "$PROJECT_ID" \
    >/dev/null
fi

INSTANCE_CONNECTION_NAME="$(gcloud sql instances describe "$SQL_INSTANCE" \
  --project "$PROJECT_ID" \
  --format='value(connectionName)')"

[[ -n "$INSTANCE_CONNECTION_NAME" ]] || die "Could not resolve Cloud SQL connection name"

upsert_secret "$DB_PASSWORD_SECRET" "$DB_PASSWORD"
upsert_secret "$OPENAI_SECRET" "$OPENAI_API_KEY"
upsert_secret "$TELEGRAM_SECRET" "$TELEGRAM_BOT_TOKEN"
upsert_secret "$WEBHOOK_SECRET_NAME" "$WEBHOOK_SECRET"

log "Building container image ${IMAGE_URI}"
gcloud builds submit "$ROOT_DIR" \
  --tag "$IMAGE_URI" \
  --project "$PROJECT_ID"

INITIAL_ENV_VARS="BOT_ENV=${BOT_ENV},DB_NAME=${DB_NAME},DB_USER=${DB_USER},INSTANCE_CONNECTION_NAME=${INSTANCE_CONNECTION_NAME},TELEGRAM_WEBHOOK_PATH=${TELEGRAM_WEBHOOK_PATH}"
SECRET_BINDINGS="DB_PASSWORD=${DB_PASSWORD_SECRET}:latest,OPENAI_API_KEY=${OPENAI_SECRET}:latest,TELEGRAM_BOT_TOKEN=${TELEGRAM_SECRET}:latest,TELEGRAM_WEBHOOK_SECRET=${WEBHOOK_SECRET_NAME}:latest"

SERVICE_URL=""
if run_service_exists; then
  log "Cloud Run service already exists; reusing its URL"
  SERVICE_URL="$(gcloud run services describe "$SERVICE_NAME" \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --format='value(status.url)')"
fi

if [[ -z "$SERVICE_URL" ]]; then
  log "Deploying Cloud Run service ${SERVICE_NAME} with a temporary HTTP server"
  gcloud run deploy "$SERVICE_NAME" \
    --image "$IMAGE_URI" \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --service-account "$RUNTIME_SA_EMAIL" \
    --allow-unauthenticated \
    --add-cloudsql-instances "$INSTANCE_CONNECTION_NAME" \
    --set-env-vars "$INITIAL_ENV_VARS" \
    --set-secrets "$SECRET_BINDINGS" \
    --min-instances 1 \
    --command python \
    --args -m,http.server,8080,--bind,0.0.0.0 \
    >/dev/null

  SERVICE_URL="$(gcloud run services describe "$SERVICE_NAME" \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --format='value(status.url)')"
fi

[[ -n "$SERVICE_URL" ]] || die "Could not resolve Cloud Run service URL"

RUN_DB_INIT=false
if [[ "$DB_INIT_MODE" == "always" || ( "$DB_INIT_MODE" == "auto" && "$DB_CREATED" == true ) ]]; then
  RUN_DB_INIT=true
fi

if [[ "$RUN_DB_INIT" == true ]]; then
  JOB_FLAGS=(
    --image "$IMAGE_URI"
    --region "$REGION"
    --project "$PROJECT_ID"
    --service-account "$RUNTIME_SA_EMAIL"
    --set-cloudsql-instances "$INSTANCE_CONNECTION_NAME"
    --set-env-vars "BOT_ENV=${BOT_ENV},DB_NAME=${DB_NAME},DB_USER=${DB_USER},INSTANCE_CONNECTION_NAME=${INSTANCE_CONNECTION_NAME}"
    --set-secrets "$SECRET_BINDINGS"
    --command python
    --args init_db.py,--embed
    --max-retries 1
    --tasks 1
    --parallelism 1
    --task-timeout 3600s
  )

  if run_job_exists; then
    log "Updating Cloud Run job ${JOB_NAME}"
    gcloud run jobs update "$JOB_NAME" "${JOB_FLAGS[@]}" >/dev/null
  else
    log "Creating Cloud Run job ${JOB_NAME}"
    gcloud run jobs create "$JOB_NAME" "${JOB_FLAGS[@]}" >/dev/null
  fi

  log "Running database initialization job ${JOB_NAME}"
  gcloud run jobs execute "$JOB_NAME" \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --wait
else
  if [[ "$DB_INIT_MODE" == "never" ]]; then
    log "Skipping database initialization job (never mode)"
  else
    log "Skipping database initialization job (auto mode; database already exists)"
  fi
fi

FINAL_ENV_VARS="APP_MODE=webhook,BOT_ENV=${BOT_ENV},WEBHOOK_URL=${SERVICE_URL},DB_NAME=${DB_NAME},DB_USER=${DB_USER},INSTANCE_CONNECTION_NAME=${INSTANCE_CONNECTION_NAME},TELEGRAM_WEBHOOK_PATH=${TELEGRAM_WEBHOOK_PATH}"

log "Pausing Telegram webhook delivery during final Cloud Run update"
telegram_response="$(telegram_post deleteWebhook \
  --data-urlencode "drop_pending_updates=false")"
if ! telegram_response_ok "$telegram_response"; then
  printf '%s\n' "$telegram_response" >&2
  die "Telegram webhook pause failed"
fi

log "Updating Cloud Run service ${SERVICE_NAME} to final webhook configuration"
gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE_URI" \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --service-account "$RUNTIME_SA_EMAIL" \
  --allow-unauthenticated \
  --add-cloudsql-instances "$INSTANCE_CONNECTION_NAME" \
  --set-env-vars "$FINAL_ENV_VARS" \
  --set-secrets "$SECRET_BINDINGS" \
  --min-instances "$FINAL_MIN_INSTANCES" \
  --command "" \
  --args "" \
  >/dev/null

WEBHOOK_URL="${SERVICE_URL%/}/${TELEGRAM_WEBHOOK_PATH#/}"

log "Registering Telegram webhook ${WEBHOOK_URL}"
telegram_response="$(telegram_post setWebhook \
  --data-urlencode "url=${WEBHOOK_URL}" \
  --data-urlencode "secret_token=${WEBHOOK_SECRET}" \
  --data-urlencode "drop_pending_updates=false")"

if ! telegram_response_ok "$telegram_response"; then
  printf '%s\n' "$telegram_response" >&2
  die "Telegram webhook registration failed"
fi

log "Verifying Telegram webhook registration"
telegram_response="$(telegram_get getWebhookInfo)"
if ! telegram_response_ok "$telegram_response"; then
  printf '%s\n' "$telegram_response" >&2
  die "Telegram webhook verification failed"
fi

registered_webhook_url="$(printf '%s' "$telegram_response" | json_string_value url)"
if [[ "$registered_webhook_url" != "$WEBHOOK_URL" ]]; then
  printf '%s\n' "$telegram_response" >&2
  die "Telegram webhook URL mismatch. Expected ${WEBHOOK_URL}, got ${registered_webhook_url:-<empty>}"
fi

log "Production deployment completed"
cat <<EOF

Bot environment: ${BOT_ENV}
Service URL: ${SERVICE_URL}
Webhook URL: ${WEBHOOK_URL}
Cloud SQL instance: ${SQL_INSTANCE}
Database: ${DB_NAME}
DB init mode: ${DB_INIT_MODE}
Cloud Run service: ${SERVICE_NAME}
Cloud Run job: ${JOB_NAME}

Re-run this script to roll out a new image or rotate the secrets.
EOF
