"""
db.py
-----
Defines SQLAlchemy ORM models for Workflow, Task, WorkflowRun, TaskRun.
Defines Pydantic schemas for API validation.
Handles database setup and initialization.
"""
from sqlalchemy import create_engine, Column, Integer, String, JSON, ForeignKey, Enum, DateTime, Text, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from pydantic import BaseModel
from typing import List, Optional
import enum
from .config import settings

Base = declarative_base()


# Enum

class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


# Models

class Workflow(Base):
    __tablename__ = "workflows"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    schedule = Column(String, nullable=True)  # cron expression
    status = Column(String, default="ACTIVE")
    dag = Column(JSON, nullable=True)  # Store workflow DAG as JSON (industry-grade, extensible)
    tasks = relationship("Task", back_populates="workflow")

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"))
    name = Column(String)
    executor = Column(String)  # python/bash/http/sql
    params = Column(JSON)
    retries = Column(Integer, default=0)
    depends_on = Column(JSON, default=list)
    workflow = relationship("Workflow", back_populates="tasks")

class WorkflowRun(Base):
    __tablename__ = "workflow_runs"
    id = Column(Integer, primary_key=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"))
    status = Column(String, default="PENDING")
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True))

class TaskRun(Base):
    __tablename__ = "task_runs"
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    workflow_run_id = Column(Integer, ForeignKey("workflow_runs.id"))
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    result = Column(JSON, nullable=True)
    log = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True))


# Pydantic Schemas

class WorkflowBase(BaseModel):
    name: str
    schedule: Optional[str] = None
    status: Optional[str] = "PENDING"
    dag: Optional[dict] = None  # See orchestrator.py for supported fields

class WorkflowCreate(WorkflowBase):
    pass

class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    schedule: Optional[str] = None
    status: Optional[str] = None
    dag: Optional[dict] = None

class WorkflowOut(WorkflowBase):
    id: int
    dag: Optional[dict] = None
    class Config:
        from_attributes = True

class TaskBase(BaseModel):
    name: str
    executor: str
    params: Optional[dict] = {}
    retries: Optional[int] = 0
    depends_on: Optional[List[int]] = []

class TaskCreate(TaskBase):
    workflow_id: int

class TaskUpdate(BaseModel):
    name: Optional[str] = None
    executor: Optional[str] = None
    params: Optional[dict] = None
    retries: Optional[int] = None
    depends_on: Optional[List[int]] = None

class TaskOut(TaskBase):
    id: int
    workflow_id: int
    class Config:
        from_attributes = True


# Database setup

engine = create_engine(settings.DB_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
