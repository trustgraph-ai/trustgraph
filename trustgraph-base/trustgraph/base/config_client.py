
from . request_response_spec import RequestResponse, RequestResponseSpec
from .. schema import ConfigRequest, ConfigResponse, ConfigKey, ConfigValue

CONFIG_TIMEOUT = 10


class ConfigClient(RequestResponse):

    async def _request(self, timeout=CONFIG_TIMEOUT, **kwargs):
        resp = await self.request(
            ConfigRequest(**kwargs),
            timeout=timeout,
        )
        if resp.error:
            raise RuntimeError(
                f"{resp.error.type}: {resp.error.message}"
            )
        return resp

    async def get(self, type, key, timeout=CONFIG_TIMEOUT):
        """Get a single config value. Returns the value string or None."""
        resp = await self._request(
            operation="get",
            keys=[ConfigKey(type=type, key=key)],
            timeout=timeout,
        )
        if resp.values and len(resp.values) > 0:
            return resp.values[0].value
        return None

    async def put(self, type, key, value, timeout=CONFIG_TIMEOUT):
        """Put a single config value."""
        await self._request(
            operation="put",
            values=[ConfigValue(type=type, key=key, value=value)],
            timeout=timeout,
        )

    async def put_many(self, values, timeout=CONFIG_TIMEOUT):
        """Put multiple config values in a single request.
        values is a list of (type, key, value) tuples."""
        await self._request(
            operation="put",
            values=[
                ConfigValue(type=t, key=k, value=v)
                for t, k, v in values
            ],
            timeout=timeout,
        )

    async def delete(self, type, key, timeout=CONFIG_TIMEOUT):
        """Delete a single config key."""
        await self._request(
            operation="delete",
            keys=[ConfigKey(type=type, key=key)],
            timeout=timeout,
        )

    async def delete_many(self, keys, timeout=CONFIG_TIMEOUT):
        """Delete multiple config keys in a single request.
        keys is a list of (type, key) tuples."""
        await self._request(
            operation="delete",
            keys=[
                ConfigKey(type=t, key=k)
                for t, k in keys
            ],
            timeout=timeout,
        )

    async def keys(self, type, timeout=CONFIG_TIMEOUT):
        """List all keys for a config type."""
        resp = await self._request(
            operation="list",
            type=type,
            timeout=timeout,
        )
        return resp.directory


class ConfigClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name,
    ):
        super(ConfigClientSpec, self).__init__(
            request_name=request_name,
            request_schema=ConfigRequest,
            response_name=response_name,
            response_schema=ConfigResponse,
            impl=ConfigClient,
        )
