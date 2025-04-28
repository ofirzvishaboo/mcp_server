from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP(
    name="Test Server",
    host="0.0.0.0",
    port=8050,
)

@mcp.tool()
async def compare_prices(product_name: str) -> str:
    """Compare prices of a tech product across different websites."""
    return f"Testing price comparison for: {product_name}"

# Run the server
if __name__ == "__main__":
    print("Running test server with SSE transport")
    mcp.run(transport="sse")