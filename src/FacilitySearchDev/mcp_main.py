from aged_care_mcp.server import mcp

if __name__ == "__main__":
    # Local/network MCP endpoint.
    # Hosted Foundry agents cannot call localhost on your laptop;
    # this is for local testing first, then later Azure hosting.
    mcp.run(transport="streamable-http")