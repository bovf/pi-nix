import asyncio
import json
import os
import subprocess
import sys

import jsonschema
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

DDGR = os.environ.get("PI_SEARCH_DDGR", "ddgr")

WEB_SEARCH = types.Tool(
    name="web_search",
    description=("DuckDuckGo web search. Returns up to N results with "
                 "title, URL, and snippet."),
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer", "default": 10,
                            "minimum": 1, "maximum": 30},
        },
        "required": ["query"],
    },
)


async def list_tools(ctx, params):
    return types.ListToolsResult(tools=[WEB_SEARCH])


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


async def handle_call_tool(ctx, params):
    # MCP1's decorator supplied validation/error normalization; MCP2 callbacks own it.
    arguments = params.arguments or {}
    try:
        if params.name == WEB_SEARCH.name:
            jsonschema.validate(instance=arguments, schema=WEB_SEARCH.input_schema)
        return types.CallToolResult(content=await call_tool(params.name, arguments))
    except jsonschema.ValidationError as error:
        message = f"Input validation error: {error.message}"
    except Exception as error:
        message = str(error)
    return types.CallToolResult(content=[types.TextContent(type="text", text=message)], is_error=True)


server = Server("pi-search", version="0.1.0", on_list_tools=list_tools, on_call_tool=handle_call_tool)


async def main():
    async with stdio_server() as (rs, ws):
        await server.run(rs, ws, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
