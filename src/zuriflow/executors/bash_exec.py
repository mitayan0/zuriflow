from .base import BaseExecutor
import subprocess

class BashExecutor(BaseExecutor):
    def execute(self, params, context):
        cmd = params.get("cmd")
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return {
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode
        }
