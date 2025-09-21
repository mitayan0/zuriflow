"""
python_exec.py
--------------
Implements PythonExecutor for running Python scripts as workflow tasks.
"""
from .base import BaseExecutor

import runpy
import os

class PythonExecutor(BaseExecutor):
    def execute(self, params, context):
        script = params.get("script")
        if not script:
            raise ValueError("Missing script path")
        # Resolve to absolute path if not already
        if not os.path.isabs(script):
            script_path = os.path.abspath(os.path.join(os.getcwd(), script))
        else:
            script_path = script
        if not os.path.isfile(script_path):
            raise FileNotFoundError(f"Script not found: {script_path}")
        result = runpy.run_path(script_path)
        return {"output": result}
