
# zuriflow

## About

Zuri Flow is a distributed, API-first workflow orchestration engine that supports parallel and dependent task execution across multiple languages, making it ideal for teams needing scalable automation pipelines without being locked into a single runtime or environment.

## commands

celery -A src.zuriflow.celery_worker.app worker --loglevel=INFO

uvicorn src.zuriflow.app:app --reload --host 0.0.0.0 --port 8000

uvicorn zuriflow.app:app --reload --app-dir src
