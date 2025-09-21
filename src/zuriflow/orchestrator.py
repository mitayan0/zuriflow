"""
orchestrator.py
--------------
Core workflow engine logic. Parses workflow DAG from JSON, builds execution graph,
and orchestrates distributed execution using Celery primitives.

Supports advanced features: branching, conditions, loops, error handling, timeouts, and extensibility.
"""

import typing as _typing
import networkx as nx
from celery import group, chain
from .db import SessionLocal, Workflow, WorkflowRun, TaskRun, TaskStatus


def run_workflow(workflow_id: int, run_id: _typing.Optional[int] = None):
    """
    Orchestrates a workflow DAG execution using Celery primitives.
    Handles advanced features: branching, conditions, loops, error handling, timeouts, and extensibility.
    """
    # Import here to break circular import
    from .celery_worker import run_task

    session = SessionLocal()

    # Fetch workflow
    workflow = session.query(Workflow).get(workflow_id)
    if not workflow:
        session.close()
        raise ValueError(f"Workflow {workflow_id} not found")

    dag = workflow.dag or {}
    tasks = {node["task_id"]: node for node in dag.get("tasks", [])}
    dependencies = dag.get("dependencies", [])

    # Create or update WorkflowRun
    if not run_id:
        wf_run = WorkflowRun(workflow_id=workflow_id, status="RUNNING")
        session.add(wf_run)
        session.commit()
        run_id = wf_run.id
    else:
        wf_run = session.query(WorkflowRun).get(run_id)
        wf_run.status = "RUNNING"
        session.commit()

    # Build DAG using networkx
    G = nx.DiGraph()
    for node_id, node in tasks.items():
        G.add_node(node_id, **node)
    for dep in dependencies:
        G.add_edge(dep["upstream"], dep["downstream"])

    # Map node_id to Celery signature, and create TaskRun records
    celery_sigs = {}
    for node_id, node in tasks.items():
        params = node.get("params", {})
        executor = node.get("type", "python")
        retries = node.get("retries", 0)
        retry_delay = node.get("retry_delay")
        timeout = node.get("timeout")
        trigger_rule = node.get("trigger_rule", "all_success")
        condition = node.get("condition")
        branches = node.get("branches")
        loop = node.get("loop")

        # Create TaskRun record
        task_run = TaskRun(task_id=node_id, workflow_run_id=run_id, status=TaskStatus.PENDING)
        session.add(task_run)
        session.commit()

        # Pass all extensible fields to executor via params
        exec_params = {
            **params,
            "trigger_rule": trigger_rule,
            "condition": condition,
            "branches": branches,
            "loop": loop,
            "timeout": timeout,
        }

        sig = run_task.s(executor, exec_params, {}, task_run.id).set(retries=retries)
        if retry_delay:
            sig = sig.set(countdown=retry_delay)
        celery_sigs[node_id] = sig

    # Advanced graph builder
    def build_celery_graph(node_id: str):
        node = tasks[node_id]
        children = list(G.successors(node_id))

        # Handle branching
        if node.get("branches"):
            branch_map = node["branches"]
            branch_chains = {
                branch_val: group([build_celery_graph(child) for child in branch_nodes])
                for branch_val, branch_nodes in branch_map.items()
            }
            # Currently schedules all branches — dynamic execution can be added later
            return chain(celery_sigs[node_id], group(branch_chains.values()))

        # Handle loops (foreach)
        if node.get("loop") and node["loop"].get("foreach"):
            items = node["loop"]["foreach"]
            loop_group = group(
                [
                    celery_sigs[node_id].clone(
                        args=(
                            tasks[node_id]["type"],
                            {**tasks[node_id]["params"], "loop_item": item},
                            {},
                            None,
                        )
                    )
                    for item in items
                ]
            )
            if children:
                child_sigs = [build_celery_graph(child) for child in children]
                return chain(loop_group, child_sigs[0] if len(child_sigs) == 1 else group(child_sigs))
            return loop_group

        # Handle conditions
        if node.get("condition"):
            # Executor evaluates condition, may skip task
            # Here we just schedule it always
            pass

        # If leaf node
        if not children:
            return celery_sigs[node_id]

        # Otherwise, chain this task with its children
        child_sigs = [build_celery_graph(child) for child in children]
        return chain(celery_sigs[node_id], child_sigs[0] if len(child_sigs) == 1 else group(child_sigs))

    # Find root nodes (no incoming edges)
    roots = [n for n in G.nodes if G.in_degree(n) == 0]
    if not roots:
        session.close()
        raise ValueError("No root node found in workflow DAG")

    # Build workflow signature
    workflow_sig = (
        build_celery_graph(roots[0]) if len(roots) == 1 else group([build_celery_graph(r) for r in roots])
    )

    # Launch workflow
    try:
        async_result = workflow_sig.apply_async()
        async_result.get()  # optionally wait for completion
        wf_run.status = "SUCCESS"
    except Exception:
        wf_run.status = "FAILED"
        session.commit()
        session.close()
        raise
    else:
        session.commit()
        session.close()
