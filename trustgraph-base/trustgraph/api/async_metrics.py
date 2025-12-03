
import aiohttp
from typing import Optional


class AsyncMetrics:
    """Asynchronous metrics client"""

    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = url
        self.timeout = timeout
        self.token = token

    async def get(self) -> str:
        """Get Prometheus metrics as text"""
        url = f"{self.url}/api/metrics"

        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        timeout = aiohttp.ClientTimeout(total=self.timeout)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    raise Exception(f"Status code {resp.status}")

                return await resp.text()
