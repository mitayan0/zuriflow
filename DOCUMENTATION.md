# Zuriflow Workflow Engine Documentation

**description:**
> A modern, extensible, and distributed workflow engine for Python, supporting DAG-based orchestration, scheduling, and pluggable task execution.

## Features

- FastAPI-powered REST API for workflow and task management
- DAG-based workflow definition (JSON schema)
- Distributed execution with Celery (supports parallelism, dependencies, retries)
- Pluggable executors: Python, Bash, HTTP, SQL, and custom executors
- Dynamic executor registration (just drop a file in `executors/`)
- Advanced workflow features: branching, conditions, loops, error handling, timeouts
- Scheduling with Celery beat/RedBeat (cron, periodic)
- Circuit breaker and exponential backoff for robust task retries
- Audit and replay: all task input/output persisted
- Monitoring endpoints for workflow/task runs
- Example DAGs and scripts for quick testing

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

## Quickstart

1. Install dependencies: `pip install -r requirements.txt`
2. Configure `.env` (DB, Redis, etc.)
3. Start API: `uvicorn src.zuriflow.app:app --reload`
4. Start Celery worker: `celery -A src.zuriflow.celery_worker worker --loglevel=info`
5. (Optional) Start scheduler: `celery -A src.zuriflow.celery_worker beat --loglevel=info`
6. Use API endpoints to create workflows, tasks, and trigger runs

## API Overview

- `POST /workflows/` — Create workflow (with DAG)
- `PUT /workflows/{id}` — Update workflow
- `POST /workflows/{id}/run` — Trigger workflow
- `POST /workflows/{id}/schedule` — Schedule workflow (cron)
- `POST /tasks/` — Create task
- `POST /tasks/{id}/run` — Trigger single task
- `POST /tasks/{id}/schedule` — Schedule single task
- Monitoring: `/workflow_runs/`, `/task_runs/`

## DAG Schema Example

See `examples/simple_dag.json` and `examples/full_dag.json` for reference.

## Adding Custom Executors

- Create a new file in `src/zuriflow/executors/` with a `register(register_executor)` function.
- Register your executor type and implement the `BaseExecutor` interface.
- No core code changes required.

## Advanced Topics

- Circuit breaker and exponential backoff are built-in for robust retries.
- All task input/output is logged for audit and replay.
- Plugin system supports custom triggers and result handlers (extendable).

## Testing

- Use the payloads in `examples/api_payloads.json` and scripts in `scripts/` for end-to-end tests.

---

## Scheduling Workflows with Celery Beat & RedBeat

This project supports distributed workflow scheduling using Celery beat (filesystem) or RedBeat (Redis-backed, production-grade).

**How it works:**

- All workflows with a `schedule` (cron string) are auto-registered as periodic Celery tasks on worker startup.
- The scheduler triggers workflow runs at the specified times, using the orchestrator for execution.

**RedBeat (recommended for production):**

- Install RedBeat: `pip install redbeat`
- Set the following in your environment/config:
  - `CELERY_BEAT_SCHEDULER=redbeat.RedBeatScheduler`
  - `REDIS_URL` (used for both broker and RedBeat storage)
- Start the beat process:
  - `celery -A zuriflow.celery_worker beat --loglevel=info`

**Celery beat (filesystem, for dev/small scale):**

- No extra dependencies needed.
- Start the beat process:
  - `celery -A zuriflow.celery_worker beat --loglevel=info`

**Notes:**

- All scheduling logic is in `src/zuriflow/schedulers.py`.
- On worker/beat startup, all scheduled workflows are registered.
- To add or update schedules, update the workflow's `schedule` field and restart the worker/beat.

See `src/zuriflow/schedulers.py` for details.

---
For more, see code comments and the `README.md` for usage tips.
