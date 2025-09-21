from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from zuriflow.orchestrator import run_workflow

from zuriflow.db import (
    SessionLocal,
    init_db,
    Workflow, WorkflowCreate, WorkflowUpdate, WorkflowOut, WorkflowRun,
    Task, TaskCreate, TaskUpdate, TaskOut
)

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
    db_workflow = Workflow(name=workflow.name, schedule=workflow.schedule, status=workflow.status)
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
    for field, value in workflow_update.dict(exclude_unset=True).items():
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
