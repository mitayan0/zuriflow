"""
dag_validation.py
----------------
Validation utilities for workflow DAG schemas and task parameters.
"""
from typing import Dict, Any, List

REQUIRED_TASK_FIELDS = {"task_id", "type", "params"}
REQUIRED_DAG_FIELDS = {"tasks", "dependencies"}

class DAGValidationError(Exception):
    pass

def validate_task(task: Dict[str, Any]) -> None:
    missing = REQUIRED_TASK_FIELDS - set(task.keys())
    if missing:
        raise DAGValidationError(f"Task missing required fields: {missing}")
    # Add more per-type validation here if needed

def validate_dag(dag: Dict[str, Any]) -> None:
    missing = REQUIRED_DAG_FIELDS - set(dag.keys())
    if missing:
        raise DAGValidationError(f"DAG missing required fields: {missing}")
    if not isinstance(dag["tasks"], list):
        raise DAGValidationError("DAG 'tasks' must be a list")
    if not isinstance(dag["dependencies"], list):
        raise DAGValidationError("DAG 'dependencies' must be a list")
    task_ids = set()
    for task in dag["tasks"]:
        validate_task(task)
        if task["task_id"] in task_ids:
            raise DAGValidationError(f"Duplicate task_id: {task['task_id']}")
        task_ids.add(task["task_id"])
    for dep in dag["dependencies"]:
        if not ("upstream" in dep and "downstream" in dep):
            raise DAGValidationError(f"Dependency missing 'upstream' or 'downstream': {dep}")
        if dep["upstream"] not in task_ids or dep["downstream"] not in task_ids:
            raise DAGValidationError(f"Dependency references unknown task_id: {dep}")
