"""Test simple MCP server with inline tool registration"""
from mcp.server.fastmcp import FastMCP, Context

server = FastMCP(name="test")

@server.tool()
def simple_test_tool(ctx: Context, message: str) -> str:
    """Simple test tool that echoes message with user info."""
    return f"User {ctx.client_id} says: {message}"

@server.tool()
def another_test() -> str:
    """Another simple test."""
    return "Hello from test tool!"

if __name__ == "__main__":
    # List registered tools
    print(f"Registered tools: {[name for name in dir(server) if not name.startswith('_')]}")
    server.run()
