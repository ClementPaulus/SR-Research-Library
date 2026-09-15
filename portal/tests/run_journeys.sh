#!/usr/bin/env bash
# Run the browser journeys against a fresh dev server on an isolated clone of this repository.
# Usage: portal/tests/run_journeys.sh [OUT_DIR]   (default docs/portal-evidence/journeys)
# Requires: /tmp/portal-venv (make -C portal venv) with playwright + chromium installed.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY="${PORTAL_PYTHON:-/tmp/portal-venv/bin/python}"
OUT="${1:-$ROOT/docs/portal-evidence/journeys}"
PORT="${PORT:-8123}"
CLONE=/tmp/journeys-repo
MAIL=/tmp/journeys-mail
OUTAGE=/tmp/journeys-github-outage

pkill -f "runserver" || true; sleep 1
rm -rf "$CLONE" "$MAIL" "$OUT" "$OUTAGE" "$ROOT/portal/portal-dev.sqlite3" "$ROOT/portal/private-media"
mkdir -p "$MAIL"
git clone -q "$ROOT" "$CLONE"
git -C "$CLONE" checkout -q -B main
git -C "$CLONE" remote remove origin

export DJANGO_SETTINGS_MODULE=config.settings.dev CELERY_TASK_ALWAYS_EAGER=true
export PORTAL_GITHUB_ADAPTER=registry_bridge.fake_github.FakeGitHubClient GITHUB_REPO_OWNER=local GITHUB_REPO_NAME=local
export PORTAL_FAKE_GITHUB_OUTAGE_FILE="$OUTAGE"
export EMAIL_BACKEND=django.core.mail.backends.filebased.EmailBackend EMAIL_FILE_PATH="$MAIL"
export PORTAL_REGISTRY_REPO_PATH="$CLONE" PORTAL_PUBLIC_BASE_URL="http://127.0.0.1:$PORT" PORTAL_ALLOWED_HOSTS=127.0.0.1,localhost

cd "$ROOT/portal"
"$PY" manage.py migrate --noinput -v0
"$PY" manage.py reindex_registry | tail -1
"$PY" manage.py runserver --noreload "127.0.0.1:$PORT" >/tmp/journeys-server.log 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null || true' EXIT
sleep 4
cd "$ROOT"
"$PY" portal/tests/browser_journeys.py "http://127.0.0.1:$PORT" "$MAIL" "$OUT" \
  --outage-file "$OUTAGE" --reconcile-cmd "cd $ROOT/portal && $PY manage.py reconcile --due"
echo "--- merged main in isolated clone ---"
git -C "$CLONE" --no-pager log --oneline -8 main | cut -c1-110
(cd "$CLONE" && git reset -q --hard main && python -m validators.validate | tail -1 && python -m pytest -q -p no:cacheprovider tests/test_census_2026_09.py tests/test_baseline_preservation.py 2>&1 | tail -1)
