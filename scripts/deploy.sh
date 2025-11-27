#!/bin/bash
set -e  

# === SSH Configuration ===
mkdir -p ~/.ssh
echo "${EC2_SSH_PRIVATE_KEY}" > ~/.ssh/deploy_key
chmod 600 ~/.ssh/deploy_key
ssh-keyscan -H "${EC2_HOST}" >> ~/.ssh/known_hosts


# === Remote Deployment ===
ssh -i ~/.ssh/deploy_key -o StrictHostKeyChecking=no "${EC2_USER}@${EC2_HOST}" << EOF
set -e

# Variables
APP_DIR="erp_konecta"
REPO_URL="${REPO_URL}"
BRANCH="${BRANCH:-main}"

echo "Deploying service: ${SERVICE_NAME}"
echo "Repo: ${REPO_URL}"
echo "Branch: ${BRANCH}"

#Setup / Update Code

if [ ! -d "\$APP_DIR/.git" ]; then
  echo "Cloning repository..."
  git clone -b \$BRANCH \$REPO_URL \$APP_DIR
  cd \$APP_DIR
else
  echo "Pulling latest changes..."
  cd \$APP_DIR
  git fetch origin \$BRANCH
  git reset --hard origin/\$BRANCH
fi

echo cat docker-compose.yml

# Create/Update environment file for the service
if [ -n "${SERVICE_ENV_FILE}" ]; then
  echo "Creating environment file for ${SERVICE_NAME}..."
  echo "${SERVICE_ENV_FILE}" > ${SERVICE_NAME}/.env
  echo "Environment file created at ${SERVICE_NAME}/.env"
else
  echo "Warning: No environment file provided for ${SERVICE_NAME}"
fi

# Docker login
echo "${DOCKERHUB_TOKEN}" | docker login --username "${DOCKERHUB_USERNAME}" --password-stdin


# Pull new images first
docker compose pull

# Recreate only the containers whose image or config changed (ignore recreating dependant services)
docker compose up -d --no-deps --build ${SERVICE_NAME}

# Optionally clean up old images
docker image prune -af

EOF