from .base import BaseExecutor
import runpy

class PythonExecutor(BaseExecutor):
    def execute(self, params, context):
        script = params.get("script")
        if not script:
            raise ValueError("Missing script path")
        result = runpy.run_path(script)
        return {"output": result}
