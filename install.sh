#!/usr/bin/env bash
set -euo pipefail

echo "== voip-portal install =="

if [ ! -f .env ]; then
  cp .env.example .env
  echo "[!] .env created. Edit it then re-run install.sh"
  exit 1
fi

# Ensure fernet key is present
FERNET_KEY=$(grep -E '^FERNET_KEY=' .env | cut -d= -f2- || true)
if [ -z "${FERNET_KEY}" ] || [ "${FERNET_KEY}" = "PUT_FERNET_KEY_HERE" ]; then
  echo "[!] Please set FERNET_KEY in .env. Generate with:"
  echo "    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())""
  exit 1
fi

docker compose pull --quiet || true
docker compose build
docker compose up -d

echo "== Migrating and creating superuser (if configured) =="
docker compose exec -T web sh -lc "python manage.py migrate"
docker compose exec -T web sh -lc "python manage.py collectstatic --noinput"

# Bootstrap superuser if env vars are set
docker compose exec -T web sh -lc "python manage.py bootstrap_superuser || true"

echo "== Done =="
echo "Open: http(s)://<SERVER_NAME>/voip-admin/"
