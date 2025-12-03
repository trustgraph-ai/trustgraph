
import requests
from typing import Optional, Dict


class Metrics:
    """Synchronous metrics client"""

    def __init__(self, url: str, timeout: int, token: Optional[str]) -> None:
        self.url: str = url
        self.timeout: int = timeout
        self.token: Optional[str] = token

    def get(self) -> str:
        """Get Prometheus metrics as text"""
        url: str = f"{self.url}/api/metrics"

        headers: Dict[str, str] = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        resp = requests.get(url, timeout=self.timeout, headers=headers)

        if resp.status_code != 200:
            raise Exception(f"Status code {resp.status_code}")

        return resp.text
