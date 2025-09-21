from apscheduler.schedulers.background import BackgroundScheduler
from db import SessionLocal, Workflow, WorkflowRun
from orchestrator import run_workflow
from croniter import croniter
from datetime import datetime

def start_scheduler():
    scheduler = BackgroundScheduler()
    session = SessionLocal()
    workflows = session.query(Workflow).filter(Workflow.schedule != None).all()
    for wf in workflows:
        scheduler.add_job(
            lambda w=wf: run_workflow(w.id, WorkflowRun(workflow_id=w.id, status="RUNNING").id),
            "cron", **parse_cron(wf.schedule)
        )
    scheduler.start()

def parse_cron(cron_expr: str):
    fields = cron_expr.split()
    return dict(minute=fields[0], hour=fields[1], day=fields[2], month=fields[3], day_of_week=fields[4])
