
import requests
from typing import Optional


class Metrics:
    """Synchronous metrics client"""

    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = url
        self.timeout = timeout
        self.token = token

    def get(self) -> str:
        """Get Prometheus metrics as text"""
        url = f"{self.url}/api/metrics"

        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        resp = requests.get(url, timeout=self.timeout, headers=headers)

        if resp.status_code != 200:
            raise Exception(f"Status code {resp.status_code}")

        return resp.text
