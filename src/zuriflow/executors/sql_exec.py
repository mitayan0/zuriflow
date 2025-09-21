from .base import BaseExecutor
from sqlalchemy import text
from zuriflow.db import engine

class SQLExecutor(BaseExecutor):
    def execute(self, params, context):
        query = params.get("query")
        with engine.connect() as conn:
            result = conn.execute(text(query))
            return {"rows": [dict(r) for r in result]}
