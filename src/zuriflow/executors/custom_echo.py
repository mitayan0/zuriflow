"""
custom_echo.py
-------------
A sample custom executor for demonstration. Echoes the input params.
"""
from .base import BaseExecutor

def register(register_executor):
    register_executor("echo", EchoExecutor)

class EchoExecutor(BaseExecutor):
    def execute(self, params, context):
        return {"echo": params}
