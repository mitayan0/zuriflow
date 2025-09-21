"""
celery_worker.py
---------------
Defines Celery app and the main task execution function. Dynamically dispatches to the correct executor (Python, Bash, HTTP, SQL).
Handles task run state, retries, timeouts, and error handling. Integrates with the database for task run tracking.
"""

import importlib
import os
import time
import signal
from celery import Celery
from celery.utils.time import get_exponential_backoff_interval
from celery.signals import worker_init, beat_init
from .config import BROKER_URL, RESULT_BACKEND

app = Celery("worker", broker=BROKER_URL, backend=RESULT_BACKEND)


# --- Plugin/dynamic executor registry ---
EXECUTOR_REGISTRY = {}


def register_executor(name, executor_cls):
    EXECUTOR_REGISTRY[name] = executor_cls


# Register built-in executors
def _register_builtin_executors():
    from .executors.python_exec import PythonExecutor
    from .executors.bash_exec import BashExecutor
    from .executors.http_exec import HTTPExecutor
    from .executors.sql_exec import SQLExecutor

    register_executor("python", PythonExecutor)
    register_executor("bash", BashExecutor)
    register_executor("http", HTTPExecutor)
    register_executor("sql", SQLExecutor)


_register_builtin_executors()


# Load all executors in executors/ as plugins (if they have register())
def load_executor_plugins():
    exec_dir = os.path.join(os.path.dirname(__file__), "executors")
    for fname in os.listdir(exec_dir):
        if fname.endswith(".py") and not fname.startswith("__"):
            modname = f"zuriflow.executors.{fname[:-3]}"
            mod = importlib.import_module(modname)
            if hasattr(mod, "register"):
                mod.register(register_executor)


load_executor_plugins()


def get_executor(executor_name):
    if executor_name in EXECUTOR_REGISTRY:
        return EXECUTOR_REGISTRY[executor_name]()
    raise ValueError(f"Unknown executor: {executor_name}")


# Circuit breaker state (in-memory, for demo; use Redis for distributed)
CIRCUIT_BREAKER = {}
CIRCUIT_BREAKER_THRESHOLD = 5  # fail N times before open
CIRCUIT_BREAKER_RESET = 300    # seconds to reset breaker


@app.task(bind=True, autoretry_for=(), retry_backoff=False)
def run_task(self, executor_name, params, context, task_run_id=None):
    from .db import SessionLocal, TaskRun, TaskStatus

    session = SessionLocal()
    task_run = None

    if task_run_id:
        task_run = session.query(TaskRun).get(task_run_id)
        if task_run:
            task_run.status = TaskStatus.RUNNING
            # Persist input params for audit
            task_run.log = f"INPUT: {params}"
            session.commit()

    # Circuit breaker check
    cb_key = f"{executor_name}"
    now = time.time()
    cb = CIRCUIT_BREAKER.get(cb_key, {"failures": 0, "opened": 0})
    if cb["failures"] >= CIRCUIT_BREAKER_THRESHOLD and now - cb["opened"] < CIRCUIT_BREAKER_RESET:
        if task_run:
            task_run.status = TaskStatus.FAILED
            task_run.result = {"error": "Circuit breaker open for executor"}
            session.commit()
        raise Exception("Circuit breaker open for executor")

    try:
        executor = get_executor(executor_name)

        # Handle timeout if specified
        class TimeoutException(Exception):
            pass

        def handler(signum, frame):
            raise TimeoutException()

        timeout = params.get("timeout")
        if timeout:
            signal.signal(signal.SIGALRM, handler)
            signal.alarm(timeout)

        try:
            # Handle condition: skip if not met
            condition = params.get("condition")
            if condition:
                if not eval(condition, {}, context):  # ⚠️ basic eval (replace with safe eval in prod)
                    if task_run:
                        task_run.status = TaskStatus.SKIPPED
                        task_run.result = {"skipped": True, "reason": "Condition not met"}
                        session.commit()
                    return {"skipped": True, "reason": "Condition not met"}

            # Handle loop_item for foreach
            loop_item = params.get("loop_item")
            if loop_item is not None:
                params["loop_item"] = loop_item

            result = executor.execute(params, context)

            # Persist output for audit
            if task_run:
                task_run.log = (task_run.log or "") + f"\nOUTPUT: {result}"
                session.commit()

            # Handle branching
            branch = params.get("branches")
            if branch and isinstance(result, dict) and "branch" in result:
                result["branch_taken"] = result["branch"]

            if task_run:
                task_run.status = TaskStatus.SUCCESS
                task_run.result = result
                session.commit()

            return result

        finally:
            if timeout:
                signal.alarm(0)

    except Exception as e:
        # Circuit breaker update
        cb = CIRCUIT_BREAKER.get(cb_key, {"failures": 0, "opened": 0})
        cb["failures"] += 1
        if cb["failures"] >= CIRCUIT_BREAKER_THRESHOLD:
            cb["opened"] = time.time()
        CIRCUIT_BREAKER[cb_key] = cb

        # Exponential backoff retry
        retries = params.get("retries", 3)
        attempt = getattr(self, "request", None) and getattr(self.request, "retries", 0) or 0
        if attempt < retries:
            delay = get_exponential_backoff_interval(attempt, 1, 60, 2)
            time.sleep(delay)
            raise self.retry(exc=e, countdown=delay)

        if task_run:
            task_run.status = TaskStatus.FAILED
            task_run.result = {"error": str(e)}
            session.commit()

        raise

    finally:
        session.close()


# --- Signals ---

@worker_init.connect
def worker_ready(sender=None, **kwargs):
    """Run any worker-specific initialization here if needed."""
    print("Worker initialized.")


@beat_init.connect
def register_schedules(sender=None, **kwargs):
    """Register scheduled workflows only when Beat starts."""
    from .schedulers import register_scheduled_workflows
    print("Registering scheduled workflows in Celery Beat...")
    register_scheduled_workflows()
