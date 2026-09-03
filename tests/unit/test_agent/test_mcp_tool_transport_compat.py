"""MCP transport contract tests for the outbound tool service."""

import pytest
from pydantic import BaseModel

from trustgraph.agent.mcp_tool import service as mcp_tool_service

try:
    from mcp.server import MCPServer
except ImportError:
    from mcp.server.fastmcp import FastMCP

    MCPServer = None


class EchoResult(BaseModel):
    echo: str


class HeaderCapture:
    """ASGI wrapper that records the HTTP headers seen by the MCP server."""

    def __init__(self, app):
        self.app = app
        self.requests = []

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            self.requests.append({
                name.decode("latin-1").lower(): value.decode("latin-1")
                for name, value in scope["headers"]
            })
        await self.app(scope, receive, send)


def create_test_server():
    """Create the native server for the installed MCP major version."""
    if MCPServer is not None:
        server = MCPServer("test-mcp-server")

        def app_factory():
            return server.streamable_http_app(
                json_response=True,
                stateless_http=True,
                host="testserver",
            )
    else:
        server = FastMCP(
            "test-mcp-server",
            json_response=True,
            stateless_http=True,
            host="testserver",
        )
        app_factory = server.streamable_http_app

    return server, app_factory


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("auth_token", "expected_authorization"),
    [
        ("test-token", "Bearer test-token"),
        ("", None),
        (None, None),
    ],
)
async def test_invoke_tool_uses_supported_streamable_http_contract(
        monkeypatch,
        auth_token,
        expected_authorization,
):
    """Exercise the real MCP transport and session over an in-process server."""
    server, app_factory = create_test_server()

    @server.tool()
    def echo(value: str) -> EchoResult:
        return EchoResult(echo=value)

    app = app_factory()
    captured_app = HeaderCapture(app)

    http_module = (
        mcp_tool_service.create_mcp_http_client.__globals__.get("httpx2")
        or mcp_tool_service.create_mcp_http_client.__globals__["httpx"]
    )
    real_async_client = http_module.AsyncClient
    client_options = []

    def create_in_process_client(*args, **kwargs):
        client_options.append(kwargs.copy())
        kwargs["transport"] = http_module.ASGITransport(app=captured_app)
        kwargs["base_url"] = "http://testserver"
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(
        http_module,
        "AsyncClient",
        create_in_process_client,
    )

    tool_config = {
        "url": "http://testserver/mcp",
        "remote-name": "echo",
    }
    if auth_token is not None:
        tool_config["auth-token"] = auth_token

    service = object.__new__(mcp_tool_service.Service)
    service.mcp_services = {
        "test-workspace": {"local-echo": tool_config},
    }

    async with app.router.lifespan_context(app):
        result = await service.invoke_tool(
            "test-workspace",
            "local-echo",
            {"value": "hello"},
        )

    assert result == {"echo": "hello"} or (
        isinstance(result, str) and "hello" in result
    )
    assert len(client_options) == 1
    assert client_options[0]["follow_redirects"] is True
    assert isinstance(client_options[0]["timeout"], http_module.Timeout)
    assert captured_app.requests

    for headers in captured_app.requests:
        assert headers.get("authorization") == expected_authorization
