from .db import SessionLocal, Task, WorkflowRun, TaskRun, TaskStatus
from .celery_worker import run_task
import networkx as nx  # for DAG resolution

def run_workflow(workflow_id, run_id):
    session = SessionLocal()
    tasks = session.query(Task).filter_by(workflow_id=workflow_id).all()

    # Build DAG
    G = nx.DiGraph()
    for t in tasks:
        G.add_node(t.id, task=t)
        for dep in t.depends_on or []:
            G.add_edge(dep, t.id)

    execution_context = {}

    for task_id in nx.topological_sort(G):
        task = session.query(Task).get(task_id)
        task_run = TaskRun(task_id=task.id, workflow_run_id=run_id, status=TaskStatus.RUNNING)
        session.add(task_run)
        session.commit()

        async_result = run_task.delay(task.executor, task.params, execution_context)
        result = async_result.get()  # TODO: make async
        task_run.status = TaskStatus.SUCCESS
        task_run.result = result
        execution_context[task.name] = result
        session.commit()

    session.close()
