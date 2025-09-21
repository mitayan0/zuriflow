"""
http_exec.py
------------
Implements HTTPExecutor for making HTTP requests as workflow tasks.
"""
from .base import BaseExecutor
import requests

class HTTPExecutor(BaseExecutor):
    def execute(self, params, context):
        method = params.get("method", "GET").upper()
        url = params["url"]
        resp = requests.request(method, url, json=params.get("body"))
        return {"status_code": resp.status_code, "body": resp.json()}
