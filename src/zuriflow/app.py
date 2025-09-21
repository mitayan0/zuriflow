"""
app.py
--------
Main FastAPI application entrypoint. Defines API endpoints for workflows and tasks CRUD, and workflow execution trigger.
Initializes the database and exposes the REST API for workflow engine operations.
"""
from fastapi import FastAPI, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from zuriflow.orchestrator import run_workflow
from zuriflow.db import (
    SessionLocal,
    init_db,
    Workflow, WorkflowCreate, WorkflowUpdate, WorkflowOut, WorkflowRun,
    Task, TaskCreate, TaskUpdate, TaskOut, TaskRun
)
from zuriflow.schedulers import register_scheduled_workflows
from zuriflow.celery_worker import run_task
from zuriflow.utils.dag_validation import validate_dag, DAGValidationError

# Initialize DB
init_db()

app = FastAPI(title="Workflow Engine API")


# -------------------------------
# Dependency: get DB session
# -------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------------
# Workflows CRUD
# -------------------------------
@app.post("/workflows/", response_model=WorkflowOut)
def create_workflow(workflow: WorkflowCreate, db: Session = Depends(get_db)):
    # Validate DAG if present
    if workflow.dag:
        try:
            validate_dag(workflow.dag)
        except DAGValidationError as e:
            raise HTTPException(status_code=400, detail=f"Invalid DAG: {e}")
    db_workflow = Workflow(
        name=workflow.name,
        schedule=workflow.schedule,
        status=workflow.status,
        dag=workflow.dag
    )
    db.add(db_workflow)
    db.commit()
    db.refresh(db_workflow)
    return db_workflow


@app.get("/workflows/", response_model=List[WorkflowOut])
def list_workflows(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    workflows = db.query(Workflow).offset(skip).limit(limit).all()
    return workflows


@app.get("/workflows/{workflow_id}", response_model=WorkflowOut)
def get_workflow(workflow_id: int, db: Session = Depends(get_db)):
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@app.put("/workflows/{workflow_id}", response_model=WorkflowOut)
def update_workflow(workflow_id: int, workflow_update: WorkflowUpdate, db: Session = Depends(get_db)):
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    update_data = workflow_update.dict(exclude_unset=True)
    # Validate DAG if present
    if "dag" in update_data and update_data["dag"]:
        try:
            validate_dag(update_data["dag"])
        except DAGValidationError as e:
            raise HTTPException(status_code=400, detail=f"Invalid DAG: {e}")
    for field, value in update_data.items():
        setattr(workflow, field, value)
    db.commit()
    db.refresh(workflow)
    return workflow


@app.delete("/workflows/{workflow_id}")
def delete_workflow(workflow_id: int, db: Session = Depends(get_db)):
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    db.delete(workflow)
    db.commit()
    return {"detail": "Workflow deleted"}



# Tasks CRUD

@app.post("/tasks/", response_model=TaskOut)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    workflow = db.query(Workflow).filter(Workflow.id == task.workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    db_task = Task(
        workflow_id=task.workflow_id,
        name=task.name,
        executor=task.executor,
        params=task.params,
        retries=task.retries,
        depends_on=task.depends_on
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


@app.get("/tasks/", response_model=List[TaskOut])
def list_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    tasks = db.query(Task).offset(skip).limit(limit).all()
    return tasks


@app.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.put("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: int, task_update: TaskUpdate, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    for field, value in task_update.dict(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return {"detail": "Task deleted"}


@app.post("/workflows/{workflow_id}/run")
def trigger_workflow(workflow_id: int):
    session = SessionLocal()
    wf_run = WorkflowRun(workflow_id=workflow_id, status="RUNNING")
    session.add(wf_run)
    session.commit()
    run_workflow(workflow_id, wf_run.id)
    return {"workflow_run_id": wf_run.id}


# -------------------------------
# Schedule a workflow (set/update cron)
# -------------------------------
@app.post("/workflows/{workflow_id}/schedule")
def schedule_workflow(workflow_id: int, cron: str = Body(..., embed=True), db: Session = Depends(get_db)):
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    workflow.schedule = cron
    db.commit()
    # Re-register schedules (for dev, or instruct user to restart beat in prod)
    register_scheduled_workflows()
    return {"workflow_id": workflow_id, "schedule": cron}


# -------------------------------
# Schedule a single task (as a one-task workflow)
# -------------------------------
@app.post("/tasks/{task_id}/schedule")
def schedule_task(task_id: int, cron: str = Body(..., embed=True), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    # Create or update a workflow for this single task
    workflow = db.query(Workflow).filter(Workflow.id == task.workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Parent workflow not found")
    workflow.schedule = cron
    db.commit()
    register_scheduled_workflows()
    return {"task_id": task_id, "workflow_id": workflow.id, "schedule": cron}


# -------------------------------
# Trigger a single task immediately
# -------------------------------
@app.post("/tasks/{task_id}/run")
def trigger_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    # Create a TaskRun and run via Celery
    task_run = TaskRun(task_id=task_id, workflow_run_id=None, status="RUNNING")
    db.add(task_run)
    db.commit()
    # Use Celery to run the task
    async_result = run_task.apply_async(args=[task.executor, task.params, {}, task_run.id])
    return {"task_run_id": task_run.id, "celery_id": async_result.id}


# -------------------------------
# Monitoring: Workflow/task runs
# -------------------------------
from fastapi.responses import JSONResponse

@app.get("/workflow_runs/")
def list_workflow_runs(db: Session = Depends(get_db)):
    runs = db.query(WorkflowRun).all()
    return [
        {"id": r.id, "workflow_id": r.workflow_id, "status": r.status, "started_at": r.started_at, "finished_at": r.finished_at}
        for r in runs
    ]

@app.get("/workflow_runs/{run_id}")
def get_workflow_run(run_id: int, db: Session = Depends(get_db)):
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="WorkflowRun not found")
    return {"id": run.id, "workflow_id": run.workflow_id, "status": run.status, "started_at": run.started_at, "finished_at": run.finished_at}

@app.get("/task_runs/")
def list_task_runs(db: Session = Depends(get_db)):
    runs = db.query(TaskRun).all()
    return [
        {"id": r.id, "task_id": r.task_id, "workflow_run_id": r.workflow_run_id, "status": r.status, "result": r.result, "started_at": r.started_at, "finished_at": r.finished_at}
        for r in runs
    ]

@app.get("/task_runs/{run_id}")
def get_task_run(run_id: int, db: Session = Depends(get_db)):
    run = db.query(TaskRun).filter(TaskRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="TaskRun not found")
    return {"id": run.id, "task_id": run.task_id, "workflow_run_id": run.workflow_run_id, "status": run.status, "result": run.result, "started_at": run.started_at, "finished_at": run.finished_at}
