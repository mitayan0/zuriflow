from celery import Celery
from .config import BROKER_URL, RESULT_BACKEND
from .executors.python_exec import PythonExecutor
from .executors.bash_exec import BashExecutor
from .executors.http_exec import HTTPExecutor
from .executors.sql_exec import SQLExecutor

app = Celery("worker", broker=BROKER_URL, backend=RESULT_BACKEND)

EXECUTORS = {
    "python": PythonExecutor(),
    "bash": BashExecutor(),
    "http": HTTPExecutor(),
    "sql": SQLExecutor(),
}

@app.task(bind=True)
def run_task(self, executor_name, params, context):
    executor = EXECUTORS[executor_name]
    return executor.execute(params, context)
