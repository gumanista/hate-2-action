#!/bin/bash

set -e

# Required environment variables:
# CI_PROJECT_NAME
# CI_COMMIT_SHA
# REGISTRY_IMAGE
# DEPLOYMENT_BASE
# ENVIRONMENT_SLUG
# DOMAIN_NAME
# POSTGRES_USER
# POSTGRES_PASSWORD
# POSTGRES_DB
# API_KEY
# TELEGRAM_BOT_TOKEN

DEPLOY_DIR="${DEPLOYMENT_BASE}/${ENVIRONMENT_SLUG}"
mkdir -p ${DEPLOY_DIR}

# Create .env file
cat << EOF > "${DEPLOY_DIR}/.env"
POSTGRES_USER=${POSTGRES_USER}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=${POSTGRES_DB}
POSTGRES_HOST=db
POSTGRES_PORT=5432
API_KEY=${API_KEY}
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
EOF

# Create docker-compose.prod.yml
cat << EOF > "${DEPLOY_DIR}/docker-compose.prod.yml"
version: '3.8'
services:
  db:
    image: pgvector/pgvector:pg15
    env_file: .env
    volumes:
      - ./.data/postgres:/var/lib/postgresql/data
    networks:
      - default
  api:
    image: ${REGISTRY_IMAGE}:${CI_COMMIT_SHA}
    env_file: .env
    networks:
      - default
      - traefik-public
    labels:
      - "traefik.enable=true"
      - "traefik.docker.network=traefik-public"
      - "traefik.http.routers.${CI_PROJECT_NAME}-${ENVIRONMENT_SLUG}.rule=Host(\`${DOMAIN_NAME}\`)"
      - "traefik.http.routers.${CI_PROJECT_NAME}-${ENVIRONMENT_SLUG}.entrypoints=websecure"
      - "traefik.http.routers.${CI_PROJECT_NAME}-${ENVIRONMENT_SLUG}.tls.certresolver=myresolver"
      - "traefik.http.services.${CI_PROJECT_NAME}-${ENVIRONMENT_SLUG}.loadbalancer.server.port=8000"
    depends_on:
      - db
  bot:
    image: ${REGISTRY_IMAGE}:${CI_COMMIT_SHA}
    command: python -m server.telegram.bot
    env_file: .env
    networks:
      - default
    depends_on:
      - api

networks:
  traefik-public:
    external: true
EOF

echo "Starting deployment in ${DEPLOY_DIR}"
cd ${DEPLOY_DIR} && docker-compose -f docker-compose.prod.yml up -d --pull always
echo "Deployment successful"