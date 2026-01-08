
import aiohttp
from typing import Optional, Dict


class AsyncMetrics:
    """Asynchronous metrics client"""

    def __init__(self, url: str, timeout: int, token: Optional[str]) -> None:
        self.url: str = url
        self.timeout: int = timeout
        self.token: Optional[str] = token

    async def get(self) -> str:
        """Get Prometheus metrics as text"""
        url: str = f"{self.url}/api/metrics"

        headers: Dict[str, str] = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        timeout = aiohttp.ClientTimeout(total=self.timeout)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    raise Exception(f"Status code {resp.status}")

                return await resp.text()

    async def aclose(self) -> None:
        """Close connections"""
        pass
