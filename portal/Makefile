# Researcher portal — documented commands. Run from the repository root with `make -C portal <target>`.
PY ?= python
VENV ?= .venv
export DJANGO_SETTINGS_MODULE ?= config.settings.dev

.PHONY: venv lock install migrate run worker test check-config reindex up down engine-tests

venv:                 ## create a Python 3.12 virtualenv for the portal
	python3.12 -m venv $(VENV) && $(VENV)/bin/pip install --require-hashes -r requirements.txt -r requirements-dev.txt

lock:                 ## regenerate hashed dependency locks from requirements*.in
	pip-compile --quiet --strip-extras --generate-hashes -o requirements.txt requirements.in
	pip-compile --quiet --strip-extras --generate-hashes -c requirements.txt -o requirements-dev.txt requirements-dev.in

migrate:              ## apply database migrations (run separately from service startup)
	$(PY) manage.py migrate --noinput

run:                  ## development web server
	$(PY) manage.py runserver 0.0.0.0:8000

worker:               ## background worker with the reconciliation beat
	celery -A config worker --beat --loglevel=INFO --concurrency=2

test:                 ## portal test suite (isolated scratch repo + git-backed GitHub double)
	$(PY) -m pytest tests -q -p no:warnings

engine-tests:         ## repository engine tests (validators/)
	cd .. && $(PY) -m validators.validate && $(PY) -m pytest -q

check-config:         ## validate deployment inputs for the active settings module
	$(PY) manage.py check_config

reindex:              ## rebuild the public projection from the committed registry
	$(PY) manage.py reindex_registry

up:                   ## one-command local stack: web, worker, PostgreSQL, Redis, MinIO, Mailpit
	docker compose -f compose.yaml up --build

down:
	docker compose -f compose.yaml down
