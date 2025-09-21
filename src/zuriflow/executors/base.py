"""
base.py
-------
Defines the BaseExecutor interface for all task executors.
All custom executors should inherit from this class and implement the execute method.
"""
class BaseExecutor:
    def execute(self, params: dict, context: dict) -> dict:
        """
        params: task-specific parameters
        context: includes previous task results
        Returns: dict with result data
        """
        raise NotImplementedError
