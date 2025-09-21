class BaseExecutor:
    def execute(self, params: dict, context: dict) -> dict:
        """
        params: task-specific parameters
        context: includes previous task results
        Returns: dict with result data
        """
        raise NotImplementedError
