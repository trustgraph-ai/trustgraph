
from .. schema import ConfigRequest, ConfigResponse, ConfigKey, ConfigValue
from . request_response_client import RequestResponseClient

CONFIG_TIMEOUT = 10


class AsyncConfigClient:

    def __init__(self, client):
        self._client = client

    @classmethod
    async def create(cls, backend, request_topic, response_topic,
                     subscription=None):
        client = await RequestResponseClient.create(
            backend=backend,
            request_topic=request_topic,
            response_topic=response_topic,
            request_schema=ConfigRequest,
            response_schema=ConfigResponse,
            subscription=subscription,
        )
        return cls(client)

    async def start(self):
        pass

    async def stop(self):
        await self._client.close()

    async def close(self):
        await self._client.close()

    async def request(self, message, timeout=CONFIG_TIMEOUT):
        return await self._client.request(message, timeout=timeout)

    async def _request(self, timeout=CONFIG_TIMEOUT, **kwargs):
        resp = await self._client.request(
            ConfigRequest(**kwargs),
            timeout=timeout,
        )
        if resp.error:
            raise RuntimeError(
                f"{resp.error.type}: {resp.error.message}"
            )
        return resp

    async def get(self, workspace, type, key, timeout=CONFIG_TIMEOUT):
        resp = await self._request(
            operation="get",
            workspace=workspace,
            keys=[ConfigKey(type=type, key=key)],
            timeout=timeout,
        )
        if resp.values and len(resp.values) > 0:
            return resp.values[0].value
        return None

    async def put(self, workspace, type, key, value, timeout=CONFIG_TIMEOUT):
        await self._request(
            operation="put",
            workspace=workspace,
            values=[ConfigValue(type=type, key=key, value=value)],
            timeout=timeout,
        )

    async def put_many(self, workspace, values, timeout=CONFIG_TIMEOUT):
        await self._request(
            operation="put",
            workspace=workspace,
            values=[
                ConfigValue(type=t, key=k, value=v)
                for t, k, v in values
            ],
            timeout=timeout,
        )

    async def delete(self, workspace, type, key, timeout=CONFIG_TIMEOUT):
        await self._request(
            operation="delete",
            workspace=workspace,
            keys=[ConfigKey(type=type, key=key)],
            timeout=timeout,
        )

    async def delete_many(self, workspace, keys, timeout=CONFIG_TIMEOUT):
        await self._request(
            operation="delete",
            workspace=workspace,
            keys=[
                ConfigKey(type=t, key=k)
                for t, k in keys
            ],
            timeout=timeout,
        )

    async def keys(self, workspace, type, timeout=CONFIG_TIMEOUT):
        resp = await self._request(
            operation="list",
            workspace=workspace,
            type=type,
            timeout=timeout,
        )
        return resp.directory

    async def get_all(self, workspace, timeout=CONFIG_TIMEOUT):
        resp = await self._request(
            operation="config",
            workspace=workspace,
            timeout=timeout,
        )
        return resp.config

    async def workspaces_for_type(self, type, timeout=CONFIG_TIMEOUT):
        resp = await self._request(
            operation="getvalues-all-ws",
            type=type,
            timeout=timeout,
        )
        return {v.workspace for v in resp.values if v.workspace}
