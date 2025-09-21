"""
schedulers.py
-------------
Celery beat/RedBeat-ready workflow scheduling logic.
On startup, registers all workflows with a schedule as periodic Celery tasks.
This enables distributed, production-grade scheduling (filesystem or Redis-backed).
"""

from .db import SessionLocal, Workflow
from .celery_worker import app

def register_scheduled_workflows():
    """
    Registers all workflows with a cron schedule as periodic Celery beat tasks.
    If using RedBeat, these will be stored in Redis for distributed scheduling.
    Call this on app startup (e.g., from app.py or celery_worker.py main).
    """
    session = SessionLocal()
    workflows = session.query(Workflow).filter(Workflow.schedule != None).all()
    for wf in workflows:
        # Use workflow_id as unique name for periodic task
        task_name = f"run_workflow_{wf.id}"
        schedule = wf.schedule
        # Celery beat/RedBeat expects crontab schedule as5 fields
        minute, hour, day_of_month, month_of_year, day_of_week = schedule.split()
        app.conf.beat_schedule = app.conf.get('beat_schedule', {})
        app.conf.beat_schedule[task_name] = {
            'task': 'zuriflow.schedulers.run_scheduled_workflow',
            'schedule': {
                'type': 'crontab',
                'minute': minute,
                'hour': hour,
                'day_of_month': day_of_month,
                'month_of_year': month_of_year,
                'day_of_week': day_of_week
            },
            'args': (wf.id,)
        }
    session.close()

# This is the Celery task that will be triggered by beat/RedBeat

@app.task(name="zuriflow.schedulers.run_scheduled_workflow")
def run_scheduled_workflow(workflow_id):
    """
    Celery beat/RedBeat entrypoint for scheduled workflow runs.
    Creates a WorkflowRun and triggers the orchestrator.
    """
    from .db import SessionLocal, WorkflowRun
    # Import here to break circular import
    from .orchestrator import run_workflow
    session = SessionLocal()
    wf_run = WorkflowRun(workflow_id=workflow_id, status="RUNNING")
    session.add(wf_run)
    session.commit()
    run_workflow(workflow_id, wf_run.id)
    session.close()

# To use: call register_scheduled_workflows() on startup (e.g., in celery_worker.py or app.py)
# For RedBeat: set CELERY_BEAT_SCHEDULER = 'redbeat.RedBeatScheduler' in config/env


