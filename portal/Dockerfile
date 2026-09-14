# Reproducible image for the web service and the worker (same image, different command).
# The research repository is copied in so the worker can import the exact validators engine
# and create pinned checkouts with `git archive`.
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --uid 10001 portal

WORKDIR /srv/library

COPY portal/requirements.txt portal/requirements.txt
RUN python -m pip install --require-hashes -r portal/requirements.txt

# Research repository (engine + registry) and the portal.
COPY . .
RUN git config --system safe.directory /srv/library \
 && chown -R portal:portal /srv/library

USER portal
ENV DJANGO_SETTINGS_MODULE=config.settings.prod \
    PORTAL_REGISTRY_REPO_PATH=/srv/library \
    PYTHONPATH=/srv/library:/srv/library/portal

RUN DJANGO_SETTINGS_MODULE=config.settings.dev DJANGO_SECRET_KEY=build-only python portal/manage.py collectstatic --noinput >/dev/null

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz').status in (200,503) else 1)"

# Default: web. The worker overrides the command (see compose.yaml). Migrations run as a separate one-shot service.
CMD ["gunicorn", "--chdir", "portal", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
