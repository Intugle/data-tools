import contextlib

from logging import getLogger

import uvicorn

from starlette.applications import Starlette
from starlette.routing import Mount

from intugle.core.settings import settings

# from intugle.mcp.adapter.router import adapter_mcp
from intugle.mcp.semantic_layer.router import semantic_layer_mcp

log = getLogger(__name__)

# Mount the semantic layer MCP server
# semantic_layer_mcp.settings.mount_path = "/semantic_layer"


# Create a combined lifespan to manage both session managers
@contextlib.asynccontextmanager
async def lifespan(app: Starlette):
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(semantic_layer_mcp.session_manager.run())
        yield


# Create Starlette app with multiple mounted servers
app = Starlette(
    routes=[
        # Using settings-based configuration
        Mount("/semantic_layer", app=semantic_layer_mcp.streamable_http_app()),
        # Mount("/adapter", app=adapter_mcp.streamable_http_app()),
    ],
    lifespan=lifespan
)


def main():
    log.info(f"[*] MCP server started at {settings.MCP_SERVER_HOST}:{settings.MCP_SERVER_PORT}")
    uvicorn.run(
        app,
        host=settings.MCP_SERVER_HOST,
        port=settings.MCP_SERVER_PORT,
        log_level=settings.MCP_SERVER_LOG_LEVEL,
        # reload=True,
    )


if __name__ == "__main__":
    main()
