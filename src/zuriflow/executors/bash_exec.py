"""
bash_exec.py
------------
Implements BashExecutor for running shell commands as workflow tasks.
"""
from .base import BaseExecutor

import subprocess
import os

class BashExecutor(BaseExecutor):
    def execute(self, params, context):
        cmd = params.get("cmd")
        # If cmd is a script path, resolve to absolute if not already
        if cmd and (cmd.endswith('.sh') or cmd.endswith('.bat')):
            if not os.path.isabs(cmd):
                cmd_path = os.path.abspath(os.path.join(os.getcwd(), cmd))
            else:
                cmd_path = cmd
            if not os.path.isfile(cmd_path):
                raise FileNotFoundError(f"Script not found: {cmd_path}")
            cmd = cmd_path
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return {
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode
        }
