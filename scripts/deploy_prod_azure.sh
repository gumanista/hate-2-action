#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Azure deployment configuration can live in .env.azure (gitignored by .env.*).
# Values already set in your shell take precedence over this file.
ENV_FILE="${ENV_FILE:-${ROOT_DIR}/.env.azure}"
if [[ -f "$ENV_FILE" ]]; then
  printf 'Loading deploy configuration from %s\n' "$ENV_FILE"
  set -a
  # shellcheck disable=SC1090
  source <(grep -E '^(export )?[A-Za-z_][A-Za-z0-9_]*=' "$ENV_FILE" | while IFS= read -r line; do
    var_name="${line#export }"
    var_name="${var_name%%=*}"
    if [[ -z "${!var_name:-}" ]]; then
      printf '%s\n' "$line"
    fi
  done)
  set +a
fi

DEFAULT_LOCATION="westeurope"
DEFAULT_RESOURCE_GROUP="hate2action-prod-rg"
DEFAULT_CONTAINERAPP_ENV="hate2action-prod-env"
DEFAULT_SERVICE_NAME="hate2action-prod"
DEFAULT_JOB_NAME=""
DEFAULT_ACR_NAME="hate2actionprodacr"
DEFAULT_IMAGE_NAME="hate2action-bot"
DEFAULT_IMAGE_BUILD_MODE="auto"
DEFAULT_POSTGRES_SERVER="hate2action-prod-db"
DEFAULT_POSTGRES_VERSION="16"
DEFAULT_POSTGRES_SKU="Standard_B1ms"
DEFAULT_POSTGRES_TIER="Burstable"
DEFAULT_POSTGRES_STORAGE_GB="32"
DEFAULT_POSTGRES_PUBLIC_ACCESS="0.0.0.0"
DEFAULT_DB_NAME="hate2action"
DEFAULT_DB_USER="hate2actionadmin"
DEFAULT_BOT_ENV="prod"
DEFAULT_WEBHOOK_PATH=""
DEFAULT_MIN_REPLICAS="1"
DEFAULT_MAX_REPLICAS="1"
DEFAULT_DB_INIT_MODE="auto"

SUBSCRIPTION_ID="${SUBSCRIPTION_ID:-}"
LOCATION="${LOCATION:-$DEFAULT_LOCATION}"
RESOURCE_GROUP="${RESOURCE_GROUP:-$DEFAULT_RESOURCE_GROUP}"
CONTAINERAPP_ENV="${CONTAINERAPP_ENV:-$DEFAULT_CONTAINERAPP_ENV}"
SERVICE_NAME="${SERVICE_NAME:-$DEFAULT_SERVICE_NAME}"
JOB_NAME="${JOB_NAME:-$DEFAULT_JOB_NAME}"
ACR_NAME="${ACR_NAME:-$DEFAULT_ACR_NAME}"
IMAGE_NAME="${IMAGE_NAME:-$DEFAULT_IMAGE_NAME}"
IMAGE_BUILD_MODE="${IMAGE_BUILD_MODE:-$DEFAULT_IMAGE_BUILD_MODE}"
POSTGRES_SERVER="${POSTGRES_SERVER:-$DEFAULT_POSTGRES_SERVER}"
POSTGRES_VERSION="${POSTGRES_VERSION:-$DEFAULT_POSTGRES_VERSION}"
POSTGRES_SKU="${POSTGRES_SKU:-$DEFAULT_POSTGRES_SKU}"
POSTGRES_TIER="${POSTGRES_TIER:-$DEFAULT_POSTGRES_TIER}"
POSTGRES_STORAGE_GB="${POSTGRES_STORAGE_GB:-$DEFAULT_POSTGRES_STORAGE_GB}"
POSTGRES_PUBLIC_ACCESS="${POSTGRES_PUBLIC_ACCESS:-$DEFAULT_POSTGRES_PUBLIC_ACCESS}"
DB_NAME="${DB_NAME:-$DEFAULT_DB_NAME}"
DB_USER="${DB_USER:-$DEFAULT_DB_USER}"
BOT_ENV="${BOT_ENV:-$DEFAULT_BOT_ENV}"
TELEGRAM_WEBHOOK_PATH="${TELEGRAM_WEBHOOK_PATH:-$DEFAULT_WEBHOOK_PATH}"
MIN_REPLICAS="${MIN_REPLICAS:-$DEFAULT_MIN_REPLICAS}"
MAX_REPLICAS="${MAX_REPLICAS:-$DEFAULT_MAX_REPLICAS}"
DB_INIT_MODE="${DB_INIT_MODE:-$DEFAULT_DB_INIT_MODE}"
OPENAI_API_KEY="${OPENAI_API_KEY:-}"
GEMINI_API_KEY="${GEMINI_API_KEY:-}"
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
DB_PASSWORD="${DB_PASSWORD:-}"
WEBHOOK_SECRET="${WEBHOOK_SECRET:-}"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/deploy_prod_azure.sh [options]

Options:
  --subscription SUBSCRIPTION_ID
  --location LOCATION
  --resource-group NAME
  --containerapp-env NAME
  --service-name NAME
  --job-name NAME
  --acr-name NAME
  --image-name NAME
  --image-build-mode auto|acr|local|existing
  --postgres-server NAME
  --postgres-version VERSION
  --postgres-sku SKU
  --postgres-tier TIER
  --postgres-storage-gb GB
  --postgres-public-access VALUE
  --db-name NAME
  --db-user NAME
  --bot-env NAME
  --webhook-path PATH
  --min-replicas COUNT
  --max-replicas COUNT
  --db-init-mode auto|always|never
  --help

The script can also read these values from environment variables:
  SUBSCRIPTION_ID LOCATION RESOURCE_GROUP CONTAINERAPP_ENV SERVICE_NAME JOB_NAME
  ACR_NAME IMAGE_NAME IMAGE_BUILD_MODE POSTGRES_SERVER POSTGRES_VERSION POSTGRES_SKU POSTGRES_TIER
  POSTGRES_STORAGE_GB POSTGRES_PUBLIC_ACCESS DB_NAME DB_USER BOT_ENV
  TELEGRAM_WEBHOOK_PATH MIN_REPLICAS MAX_REPLICAS DB_INIT_MODE
  OPENAI_API_KEY GEMINI_API_KEY TELEGRAM_BOT_TOKEN DB_PASSWORD WEBHOOK_SECRET

Secrets/config may be placed in .env.azure. Values already exported in the
shell take precedence over the file.

DB_INIT_MODE controls the Azure Container Apps DB init job:
  auto   Run when the database was just created, or when the init job has
         never completed successfully. This is the default.
  always Run on every deploy.
  never  Do not run.

IMAGE_BUILD_MODE controls how the container image is built:
  auto   Try ACR Tasks, then fall back to a local Docker build and push.
  acr    Build remotely with ACR Tasks.
  local  Build and push with the local Docker daemon.
  existing  Reuse the current IMAGE_NAME:latest image already in ACR.
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

resource_group_exists() {
  az group show --name "$RESOURCE_GROUP" >/dev/null 2>&1
}

register_provider() {
  local namespace="$1"
  local state

  state="$(az provider show \
    --namespace "$namespace" \
    --query registrationState \
    --output tsv \
    2>/dev/null || true)"

  if [[ "$state" == "Registered" ]]; then
    log "Azure provider already registered: ${namespace}"
    return
  fi

  log "Registering Azure provider ${namespace}"
  az provider register --namespace "$namespace" >/dev/null

  for _ in $(seq 1 30); do
    state="$(az provider show \
      --namespace "$namespace" \
      --query registrationState \
      --output tsv \
      2>/dev/null || true)"
    if [[ "$state" == "Registered" ]]; then
      return
    fi
    sleep 10
  done

  die "Azure provider ${namespace} did not finish registration in time"
}

acr_exists() {
  az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1
}

containerapp_env_exists() {
  az containerapp env show \
    --name "$CONTAINERAPP_ENV" \
    --resource-group "$RESOURCE_GROUP" \
    >/dev/null 2>&1
}

containerapp_exists() {
  az containerapp show \
    --name "$SERVICE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    >/dev/null 2>&1
}

containerapp_job_exists() {
  az containerapp job show \
    --name "$JOB_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    >/dev/null 2>&1
}

postgres_server_exists() {
  az postgres flexible-server show \
    --name "$POSTGRES_SERVER" \
    --resource-group "$RESOURCE_GROUP" \
    >/dev/null 2>&1
}

postgres_database_exists() {
  az postgres flexible-server db show \
    --server-name "$POSTGRES_SERVER" \
    --resource-group "$RESOURCE_GROUP" \
    --name "$DB_NAME" \
    >/dev/null 2>&1
}

postgres_firewall_rule_exists() {
  az postgres flexible-server firewall-rule show \
    --name AllowAzureServices \
    --resource-group "$RESOURCE_GROUP" \
    --server-name "$POSTGRES_SERVER" \
    >/dev/null 2>&1
}

db_init_has_succeeded() {
  local count

  count="$(az containerapp job execution list \
    --name "$JOB_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "[?properties.status=='Succeeded'] | length(@)" \
    --output tsv \
    2>/dev/null || true)"

  [[ "${count:-0}" =~ ^[1-9][0-9]*$ ]]
}

wait_for_job_execution() {
  local execution_name="$1"
  local attempt
  local status

  for ((attempt = 1; attempt <= 360; attempt++)); do
    status="$(az containerapp job execution show \
      --name "$JOB_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --job-execution-name "$execution_name" \
      --query properties.status \
      --output tsv \
      2>/dev/null || true)"

    case "$status" in
      Succeeded)
        log "Database initialization succeeded: ${execution_name}"
        return
        ;;
      Failed|Stopped|Degraded)
        die "Database initialization ${status,,}: ${execution_name}"
        ;;
    esac

    if ((attempt == 1 || attempt % 6 == 0)); then
      log "Database initialization status: ${status:-Pending} (${execution_name})"
    fi
    sleep 10
  done

  die "Timed out waiting for database initialization: ${execution_name}"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --subscription)
        SUBSCRIPTION_ID="$2"
        shift 2
        ;;
      --location)
        LOCATION="$2"
        shift 2
        ;;
      --resource-group)
        RESOURCE_GROUP="$2"
        shift 2
        ;;
      --containerapp-env)
        CONTAINERAPP_ENV="$2"
        shift 2
        ;;
      --service-name)
        SERVICE_NAME="$2"
        shift 2
        ;;
      --job-name)
        JOB_NAME="$2"
        shift 2
        ;;
      --acr-name)
        ACR_NAME="$2"
        shift 2
        ;;
      --image-name)
        IMAGE_NAME="$2"
        shift 2
        ;;
      --image-build-mode)
        IMAGE_BUILD_MODE="$2"
        shift 2
        ;;
      --postgres-server)
        POSTGRES_SERVER="$2"
        shift 2
        ;;
      --postgres-version)
        POSTGRES_VERSION="$2"
        shift 2
        ;;
      --postgres-sku)
        POSTGRES_SKU="$2"
        shift 2
        ;;
      --postgres-tier)
        POSTGRES_TIER="$2"
        shift 2
        ;;
      --postgres-storage-gb)
        POSTGRES_STORAGE_GB="$2"
        shift 2
        ;;
      --postgres-public-access)
        POSTGRES_PUBLIC_ACCESS="$2"
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
      --bot-env)
        BOT_ENV="$2"
        shift 2
        ;;
      --webhook-path)
        TELEGRAM_WEBHOOK_PATH="$2"
        shift 2
        ;;
      --min-replicas)
        MIN_REPLICAS="$2"
        shift 2
        ;;
      --max-replicas)
        MAX_REPLICAS="$2"
        shift 2
        ;;
      --db-init-mode)
        DB_INIT_MODE="$2"
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

require_command az
require_command curl

if ! az containerapp --help >/dev/null 2>&1; then
  die "Azure CLI Container Apps commands are unavailable. Run: az extension add --name containerapp --upgrade"
fi

if [[ -z "$SUBSCRIPTION_ID" ]]; then
  current_subscription="$(az account show --query id --output tsv 2>/dev/null || true)"
  SUBSCRIPTION_ID="$(prompt_with_default "Azure subscription id" "$current_subscription")"
fi

[[ -n "$SUBSCRIPTION_ID" ]] || die "SUBSCRIPTION_ID is required"

case "$DB_INIT_MODE" in
  auto|always|never)
    ;;
  *)
    die "DB_INIT_MODE must be auto, always, or never"
    ;;
esac

case "$IMAGE_BUILD_MODE" in
  auto|acr|local|existing)
    ;;
  *)
    die "IMAGE_BUILD_MODE must be auto, acr, local, or existing"
    ;;
esac

if ! [[ "$BOT_ENV" =~ ^[a-z][a-z0-9_-]{0,31}$ ]]; then
  die "BOT_ENV must be a short lowercase slug (got: '${BOT_ENV}')"
fi

if ! [[ "$ACR_NAME" =~ ^[A-Za-z0-9]{5,50}$ ]]; then
  die "ACR_NAME must be 5-50 alphanumeric characters with no hyphens (got: '${ACR_NAME}')"
fi

if [[ -z "$TELEGRAM_WEBHOOK_PATH" ]]; then
  TELEGRAM_WEBHOOK_PATH="telegram/webhook/${BOT_ENV}"
fi

if [[ -z "$JOB_NAME" ]]; then
  JOB_NAME="${SERVICE_NAME}-db-init"
fi

az account set --subscription "$SUBSCRIPTION_ID" >/dev/null

log "Using Azure subscription: ${SUBSCRIPTION_ID}"

for provider in \
  Microsoft.App \
  Microsoft.ContainerRegistry \
  Microsoft.OperationalInsights \
  Microsoft.DBforPostgreSQL
do
  register_provider "$provider"
done

if [[ -z "$OPENAI_API_KEY" ]]; then
  OPENAI_API_KEY="$(prompt_secret "OpenAI API key")"
fi
[[ -n "$OPENAI_API_KEY" ]] || die "OPENAI_API_KEY is required"

if [[ -z "$TELEGRAM_BOT_TOKEN" ]]; then
  TELEGRAM_BOT_TOKEN="$(prompt_secret "Telegram bot token for ${BOT_ENV} bot")"
fi
[[ -n "$TELEGRAM_BOT_TOKEN" ]] || die "TELEGRAM_BOT_TOKEN is required"

if [[ -z "$WEBHOOK_SECRET" ]]; then
  WEBHOOK_SECRET="$(generate_secret)"
  log "Generated a random Telegram webhook secret"
fi
[[ -n "$WEBHOOK_SECRET" ]] || die "WEBHOOK_SECRET is required"

log "Validating Telegram bot token"
telegram_response="$(telegram_get getMe)"
if ! telegram_response_ok "$telegram_response"; then
  printf '%s\n' "$telegram_response" >&2
  die "Telegram bot token validation failed"
fi

if resource_group_exists; then
  log "Resource group already exists: ${RESOURCE_GROUP}"
else
  log "Creating resource group ${RESOURCE_GROUP}"
  az group create \
    --name "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    >/dev/null
fi

if acr_exists; then
  log "Azure Container Registry already exists: ${ACR_NAME}"
else
  log "Creating Azure Container Registry ${ACR_NAME}"
  az acr create \
    --name "$ACR_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --sku Basic \
    --admin-enabled true \
    >/dev/null
fi

log "Ensuring ACR admin credentials are enabled"
az acr update \
  --name "$ACR_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --admin-enabled true \
  >/dev/null

ACR_LOGIN_SERVER="$(az acr show \
  --name "$ACR_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query loginServer \
  --output tsv)"
ACR_PASSWORD="$(az acr credential show \
  --name "$ACR_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query 'passwords[0].value' \
  --output tsv)"
ACR_USERNAME="$(az acr credential show \
  --name "$ACR_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query username \
  --output tsv)"
IMAGE_URI="${ACR_LOGIN_SERVER}/${IMAGE_NAME}:latest"

build_image_locally() {
  if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
    die "Local Docker is unavailable. In Docker Desktop, enable Settings > Resources > WSL Integration for this distro, restart the terminal, and verify with: docker version"
  fi

  log "Logging in to ${ACR_LOGIN_SERVER} with local Docker"
  printf '%s' "$ACR_PASSWORD" | docker login \
    "$ACR_LOGIN_SERVER" \
    --username "$ACR_USERNAME" \
    --password-stdin \
    >/dev/null

  log "Building container image locally: ${IMAGE_URI}"
  docker build --tag "$IMAGE_URI" "$ROOT_DIR"

  log "Pushing container image to Azure Container Registry"
  docker push "$IMAGE_URI"
}

case "$IMAGE_BUILD_MODE" in
  acr)
    log "Building container image with ACR Tasks: ${IMAGE_URI}"
    az acr build \
      --registry "$ACR_NAME" \
      --image "${IMAGE_NAME}:latest" \
      "$ROOT_DIR"
    ;;
  local)
    build_image_locally
    ;;
  auto)
    log "Building container image with ACR Tasks: ${IMAGE_URI}"
    if ! az acr build \
      --registry "$ACR_NAME" \
      --image "${IMAGE_NAME}:latest" \
      "$ROOT_DIR"
    then
      log "ACR Tasks build was unavailable; falling back to local Docker"
      build_image_locally
    fi
    ;;
  existing)
    log "Reusing existing container image: ${IMAGE_URI}"
    ;;
esac

DB_CREATED=false
if postgres_server_exists; then
  log "PostgreSQL Flexible Server already exists: ${POSTGRES_SERVER}"
  if [[ -z "$DB_PASSWORD" ]]; then
    DB_PASSWORD="$(prompt_secret "Existing PostgreSQL admin password for ${DB_USER}")"
  fi
else
  if [[ -z "$DB_PASSWORD" ]]; then
    DB_PASSWORD="$(prompt_secret "New PostgreSQL admin password for ${DB_USER}")"
  fi
  [[ -n "$DB_PASSWORD" ]] || die "DB_PASSWORD is required"
  log "Creating PostgreSQL Flexible Server ${POSTGRES_SERVER}"
  az postgres flexible-server create \
    --name "$POSTGRES_SERVER" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --admin-user "$DB_USER" \
    --admin-password "$DB_PASSWORD" \
    --version "$POSTGRES_VERSION" \
    --sku-name "$POSTGRES_SKU" \
    --tier "$POSTGRES_TIER" \
    --storage-size "$POSTGRES_STORAGE_GB" \
    --public-access "$POSTGRES_PUBLIC_ACCESS" \
    --yes \
    >/dev/null
  DB_CREATED=true
fi
[[ -n "$DB_PASSWORD" ]] || die "DB_PASSWORD is required"

current_extensions="$(az postgres flexible-server parameter show \
  --resource-group "$RESOURCE_GROUP" \
  --server-name "$POSTGRES_SERVER" \
  --name azure.extensions \
  --query value \
  --output tsv \
  2>/dev/null || true)"
if [[ ",${current_extensions}," == *",vector,"* ]]; then
  log "pgvector is already allowlisted on ${POSTGRES_SERVER}"
else
  if [[ -n "$current_extensions" ]]; then
    next_extensions="${current_extensions},vector"
  else
    next_extensions="vector"
  fi
  log "Allowlisting pgvector extension on ${POSTGRES_SERVER}"
  az postgres flexible-server parameter set \
    --resource-group "$RESOURCE_GROUP" \
    --server-name "$POSTGRES_SERVER" \
    --name azure.extensions \
    --value "$next_extensions" \
    >/dev/null
fi

if postgres_database_exists; then
  log "Database already exists: ${DB_NAME}"
else
  log "Creating database ${DB_NAME}"
  az postgres flexible-server db create \
    --server-name "$POSTGRES_SERVER" \
    --resource-group "$RESOURCE_GROUP" \
    --name "$DB_NAME" \
    >/dev/null
  DB_CREATED=true
fi

log "Allowing Azure services to reach PostgreSQL"
if postgres_firewall_rule_exists; then
  az postgres flexible-server firewall-rule update \
    --name AllowAzureServices \
    --resource-group "$RESOURCE_GROUP" \
    --server-name "$POSTGRES_SERVER" \
    --start-ip-address 0.0.0.0 \
    --end-ip-address 0.0.0.0 \
    >/dev/null
else
  az postgres flexible-server firewall-rule create \
    --name AllowAzureServices \
    --resource-group "$RESOURCE_GROUP" \
    --server-name "$POSTGRES_SERVER" \
    --start-ip-address 0.0.0.0 \
    --end-ip-address 0.0.0.0 \
    >/dev/null
fi

POSTGRES_HOST="$(az postgres flexible-server show \
  --name "$POSTGRES_SERVER" \
  --resource-group "$RESOURCE_GROUP" \
  --query fullyQualifiedDomainName \
  --output tsv)"
DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@${POSTGRES_HOST}:5432/${DB_NAME}?sslmode=require"

if containerapp_env_exists; then
  log "Container Apps environment already exists: ${CONTAINERAPP_ENV}"
else
  log "Creating Container Apps environment ${CONTAINERAPP_ENV}"
  az containerapp env create \
    --name "$CONTAINERAPP_ENV" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    >/dev/null
fi

COMMON_SECRETS=(
  "database-url=${DATABASE_URL}"
  "openai-api-key=${OPENAI_API_KEY}"
  "telegram-bot-token=${TELEGRAM_BOT_TOKEN}"
  "telegram-webhook-secret=${WEBHOOK_SECRET}"
)
if [[ -n "$GEMINI_API_KEY" ]]; then
  COMMON_SECRETS+=("gemini-api-key=${GEMINI_API_KEY}")
fi

INITIAL_ENV_VARS=(
  "BOT_ENV=${BOT_ENV}"
  "DATABASE_URL=secretref:database-url"
  "OPENAI_API_KEY=secretref:openai-api-key"
  "TELEGRAM_BOT_TOKEN=secretref:telegram-bot-token"
  "TELEGRAM_WEBHOOK_SECRET=secretref:telegram-webhook-secret"
  "TELEGRAM_WEBHOOK_PATH=${TELEGRAM_WEBHOOK_PATH}"
)
if [[ -n "$GEMINI_API_KEY" ]]; then
  INITIAL_ENV_VARS+=("GEMINI_API_KEY=secretref:gemini-api-key")
fi

SERVICE_URL=""
if containerapp_exists; then
  log "Container App already exists; reusing its URL"
  az containerapp secret set \
    --name "$SERVICE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --secrets "${COMMON_SECRETS[@]}" \
    >/dev/null
  az containerapp registry set \
    --name "$SERVICE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --server "$ACR_LOGIN_SERVER" \
    --username "$ACR_USERNAME" \
    --password "$ACR_PASSWORD" \
    >/dev/null
  SERVICE_FQDN="$(az containerapp show \
    --name "$SERVICE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query properties.configuration.ingress.fqdn \
    --output tsv)"
  SERVICE_URL="https://${SERVICE_FQDN}"
else
  log "Creating Container App ${SERVICE_NAME} with a temporary HTTP server"
  az containerapp create \
    --name "$SERVICE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --environment "$CONTAINERAPP_ENV" \
    --image "$IMAGE_URI" \
    --target-port 8080 \
    --ingress external \
    --registry-server "$ACR_LOGIN_SERVER" \
    --registry-username "$ACR_NAME" \
    --registry-password "$ACR_PASSWORD" \
    --min-replicas 1 \
    --max-replicas 1 \
    --secrets "${COMMON_SECRETS[@]}" \
    --env-vars "${INITIAL_ENV_VARS[@]}" \
    --command python \
    --args "/usr/local/lib/python3.11/http/server.py" "8080" \
    >/dev/null

  SERVICE_FQDN="$(az containerapp show \
    --name "$SERVICE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query properties.configuration.ingress.fqdn \
    --output tsv)"
  SERVICE_URL="https://${SERVICE_FQDN}"
fi

[[ -n "$SERVICE_URL" && "$SERVICE_URL" != "https://" ]] || die "Could not resolve Container App URL"

RUN_DB_INIT=false
if [[ "$DB_INIT_MODE" == "always" ]]; then
  RUN_DB_INIT=true
elif [[ "$DB_INIT_MODE" == "auto" ]]; then
  if [[ "$DB_CREATED" == true ]]; then
    RUN_DB_INIT=true
  elif ! containerapp_job_exists || ! db_init_has_succeeded; then
    log "Database exists but the DB init job has never succeeded; running DB init"
    RUN_DB_INIT=true
  fi
fi

JOB_ENV_VARS=(
  "BOT_ENV=${BOT_ENV}"
  "DATABASE_URL=secretref:database-url"
  "OPENAI_API_KEY=secretref:openai-api-key"
)
if [[ -n "$GEMINI_API_KEY" ]]; then
  JOB_ENV_VARS+=("GEMINI_API_KEY=secretref:gemini-api-key")
fi

if [[ "$RUN_DB_INIT" == true ]]; then
  if containerapp_job_exists; then
    log "Updating Container Apps job ${JOB_NAME}"
    az containerapp job secret set \
      --name "$JOB_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --secrets "${COMMON_SECRETS[@]}" \
      >/dev/null
    az containerapp job registry set \
      --name "$JOB_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --server "$ACR_LOGIN_SERVER" \
      --username "$ACR_USERNAME" \
      --password "$ACR_PASSWORD" \
      >/dev/null
    az containerapp job update \
      --name "$JOB_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --image "$IMAGE_URI" \
      --set-env-vars "${JOB_ENV_VARS[@]}" \
      --command python \
      --args init_db.py \
      >/dev/null
  else
    log "Creating Container Apps job ${JOB_NAME}"
    az containerapp job create \
      --name "$JOB_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --environment "$CONTAINERAPP_ENV" \
      --trigger-type Manual \
      --replica-timeout 3600 \
      --replica-retry-limit 1 \
      --replica-completion-count 1 \
      --parallelism 1 \
      --image "$IMAGE_URI" \
      --registry-server "$ACR_LOGIN_SERVER" \
      --registry-username "$ACR_NAME" \
      --registry-password "$ACR_PASSWORD" \
      --secrets "${COMMON_SECRETS[@]}" \
      --env-vars "${JOB_ENV_VARS[@]}" \
      --command python \
      --args init_db.py \
      >/dev/null
  fi

  log "Running database initialization job ${JOB_NAME}"
  require_command python3
  DB_INIT_TEMPLATE_FILE="$(mktemp "${TMPDIR:-/tmp}/hate2action-db-init.XXXXXX.json")"
  az containerapp job show \
    --name "$JOB_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query properties.template \
    --output json \
    >"$DB_INIT_TEMPLATE_FILE"
  python3 - "$DB_INIT_TEMPLATE_FILE" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
template = json.loads(path.read_text())
container = template["containers"][0]
container["command"] = ["python"]
container["args"] = ["init_db.py", "--embed", "--keep-runtime"]
path.write_text(json.dumps(template))
PY
  DB_INIT_EXECUTION_NAME="$(az containerapp job start \
    --name "$JOB_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --yaml "$DB_INIT_TEMPLATE_FILE" \
    --query name \
    --output tsv)"
  rm -f -- "$DB_INIT_TEMPLATE_FILE"
  [[ -n "$DB_INIT_EXECUTION_NAME" ]] || die "Azure did not return a database initialization execution name"
  wait_for_job_execution "$DB_INIT_EXECUTION_NAME"
else
  if [[ "$DB_INIT_MODE" == "never" ]]; then
    log "Skipping database initialization job (never mode)"
  else
    log "Skipping database initialization job (auto mode; database exists and init job has succeeded before)"
  fi
fi

FINAL_ENV_VARS=(
  "APP_MODE=webhook"
  "BOT_ENV=${BOT_ENV}"
  "WEBHOOK_URL=${SERVICE_URL}"
  "DATABASE_URL=secretref:database-url"
  "OPENAI_API_KEY=secretref:openai-api-key"
  "TELEGRAM_BOT_TOKEN=secretref:telegram-bot-token"
  "TELEGRAM_WEBHOOK_SECRET=secretref:telegram-webhook-secret"
  "TELEGRAM_WEBHOOK_PATH=${TELEGRAM_WEBHOOK_PATH}"
)
if [[ -n "$GEMINI_API_KEY" ]]; then
  FINAL_ENV_VARS+=("GEMINI_API_KEY=secretref:gemini-api-key")
fi

log "Pausing Telegram webhook delivery during final Container App update"
telegram_response="$(telegram_post deleteWebhook \
  --data-urlencode "drop_pending_updates=false")"
if ! telegram_response_ok "$telegram_response"; then
  printf '%s\n' "$telegram_response" >&2
  die "Telegram webhook pause failed"
fi

log "Updating Container App ${SERVICE_NAME} to final webhook configuration"
# The az CLI's --command/--args flags choke on dash-prefixed values like "-m"
# (they get silently dropped or rejected depending on quoting), so the real
# entrypoint is applied via a --yaml full-resource patch instead. "update
# --yaml" (unlike "job start --yaml") requires the *entire* container app
# resource, not just properties.template, so we round-trip the full "show".
FINAL_UPDATE_TEMPLATE_FILE="$(mktemp "${TMPDIR:-/tmp}/hate2action-final-update.XXXXXX.json")"
az containerapp show \
  --name "$SERVICE_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --output json \
  >"$FINAL_UPDATE_TEMPLATE_FILE"
python3 - "$FINAL_UPDATE_TEMPLATE_FILE" "$IMAGE_URI" "$MIN_REPLICAS" "$MAX_REPLICAS" "${FINAL_ENV_VARS[@]}" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
image_uri, min_replicas, max_replicas = sys.argv[2:5]
env_pairs = sys.argv[5:]

resource = json.loads(path.read_text())
template = resource["properties"]["template"]
container = template["containers"][0]
container["image"] = image_uri
container["command"] = ["python"]
container["args"] = ["-m", "bot.main"]

env_list = []
for pair in env_pairs:
    name, _, value = pair.partition("=")
    entry = {"name": name}
    if value.startswith("secretref:"):
        entry["secretRef"] = value[len("secretref:"):]
    else:
        entry["value"] = value
    env_list.append(entry)
container["env"] = env_list

template.setdefault("scale", {})["minReplicas"] = int(min_replicas)
template["scale"]["maxReplicas"] = int(max_replicas)

path.write_text(json.dumps(resource))
PY
az containerapp update \
  --name "$SERVICE_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --yaml "$FINAL_UPDATE_TEMPLATE_FILE" \
  >/dev/null
rm -f -- "$FINAL_UPDATE_TEMPLATE_FILE"

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

log "Azure production deployment completed"
cat <<EOF

Bot environment: ${BOT_ENV}
Service URL: ${SERVICE_URL}
Webhook URL: ${WEBHOOK_URL}
Resource group: ${RESOURCE_GROUP}
Container App: ${SERVICE_NAME}
Container Apps job: ${JOB_NAME}
PostgreSQL server: ${POSTGRES_SERVER}
Database: ${DB_NAME}
DB init mode: ${DB_INIT_MODE}
Image: ${IMAGE_URI}

Re-run this script to roll out a new image or rotate secrets.
EOF
