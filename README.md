# zuriflow

## About

Zuri Flow is a distributed, API-first workflow orchestration engine that supports parallel and dependent task execution across multiple languages, making it ideal for teams needing scalable automation pipelines without being locked into a single runtime or environment.

## How to Run

1. Install dependencies:

   ```sh

   pip install -r requirements.txt

   ```

2. Set up your `.env` file (see example in repo).
3. Start the FastAPI server:

   ```sh
   uvicorn src.zuriflow.app:app --reload --host 0.0.0.0 --port 8000
   # or (if using app-dir)
   uvicorn zuriflow.app:app --reload --app-dir src

   ```

4. Start the Celery worker:

   ```sh
   celery -A src.zuriflow.celery_worker worker --loglevel=INFO

   ```

   ```sh
   celery -A src.zuriflow.celery_worker worker --loglevel=INFO --pool=solo

   ```

5. (Optional) Start the scheduler:

   ```sh
   celery -A src.zuriflow.celery_worker beat --loglevel=INFO
   # or for RedBeat (production)
   celery -A zuriflow.celery_worker beat --loglevel=info
   ```

You can now use the API to create workflows, tasks, and trigger or schedule runs.

## Features

- Distributed, API-first workflow orchestration
- DAG-based workflow definition (JSON schema)
- Parallel and dependent task execution
- Pluggable executors: Python, Bash, HTTP, SQL, and custom
- Dynamic executor registration (just drop a file in `executors/`)
- Advanced features: branching, conditions, loops, error handling, timeouts
- Scheduling with Celery beat/RedBeat (cron, periodic)
- Circuit breaker and exponential backoff for robust task retries
- Audit and replay: all task input/output persisted
- Monitoring endpoints for workflow/task runs

## API Quick Reference

- `POST /workflows/` — Create workflow (with DAG)
- `PUT /workflows/{id}` — Update workflow
- `POST /workflows/{id}/run` — Trigger workflow
- `POST /workflows/{id}/schedule` — Schedule workflow (cron)
- `POST /tasks/` — Create task
- `POST /tasks/{id}/run` — Trigger single task
- `POST /tasks/{id}/schedule` — Schedule single task
- Monitoring: `/workflow_runs/`, `/task_runs/`

## Project Structure

- `src/zuriflow/app.py` — FastAPI app and API endpoints
- `src/zuriflow/db.py` — SQLAlchemy models and DB setup
- `src/zuriflow/orchestrator.py` — DAG parsing and orchestration logic
- `src/zuriflow/celery_worker.py` — Celery worker, executor registry, task logic
- `src/zuriflow/schedulers.py` — Scheduling integration (Celery beat/RedBeat)
- `src/zuriflow/executors/` — Built-in and custom executors (Python, Bash, HTTP, SQL, etc.)
- `src/zuriflow/utils/` — Utilities (DAG validation, etc.)
- `examples/` — Example DAGs, API payloads, and scripts
- `scripts/` — Scripts for Python/Bash task execution
