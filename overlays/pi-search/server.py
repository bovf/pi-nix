import asyncio
import json
import os
import subprocess
import sys

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
import mcp.types as types

DDGR = os.environ.get("PI_SEARCH_DDGR", "ddgr")

server = Server("pi-search")


@server.list_tools()
async def list_tools():
    return [types.Tool(
        name="web_search",
        description=("DuckDuckGo web search. Returns up to N results with "
                     "title, URL, and snippet."),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer", "default": 10,
                                "minimum": 1, "maximum": 30},
            },
            "required": ["query"],
        },
    )]


@server.call_tool()
async def call_tool(name, arguments):
    if name != "web_search":
        return [types.TextContent(type="text", text=f"unknown tool {name}")]
    q = (arguments.get("query") or "").strip()
    n = int(arguments.get("max_results", 10))
    if not q:
        return [types.TextContent(type="text", text="empty query")]
    try:
        out = subprocess.run(
            [DDGR, "--json", "-n", str(n), "--noua", q],
            capture_output=True, text=True, timeout=15, check=False,
        )
    except subprocess.TimeoutExpired:
        return [types.TextContent(type="text", text="search timed out")]
    if out.returncode != 0:
        return [types.TextContent(
            type="text",
            text=f"ddgr error ({out.returncode}): {out.stderr.strip()}",
        )]
    try:
        items = json.loads(out.stdout or "[]")
    except json.JSONDecodeError:
        return [types.TextContent(type="text", text=out.stdout)]
    if not items:
        return [types.TextContent(type="text", text="no results")]
    lines = []
    for i, it in enumerate(items[:n]):
        title = it.get("title", "(no title)")
        url = it.get("url", "")
        abstract = (it.get("abstract") or "").strip()
        lines.append(f"{i+1}. {title}\n   {url}\n   {abstract}")
    return [types.TextContent(type="text", text="\n\n".join(lines))]


async def main():
    async with stdio_server() as (rs, ws):
        await server.run(
            rs, ws,
            InitializationOptions(
                server_name="pi-search",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
