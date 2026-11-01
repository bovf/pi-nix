"""Local stdio MCP. Loading/listing never connects to a desktop or captures pixels."""
import importlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Literal

# One declared SDK, with its public v1/v2 high-level API; never install a fallback.
modern = importlib.util.find_spec('mcp.server.mcpserver') is not None
sdk = importlib.import_module('mcp.server.mcpserver' if modern else 'mcp.server.fastmcp')
MCPServer = sdk.MCPServer if modern else sdk.FastMCP
Image = sdk.Image

from backend import CaptureEngine

ROOT = Path(__file__).resolve().parent
engine = CaptureEngine(json.loads((ROOT / 'paths.json').read_text()))
mcp = MCPServer('badwater-screenshot', instructions='Capture only operator-authorized targets. Prefer isolated web/code. GUI discovery/capture, focus/clipboard changes and model image sharing are separate permissions. Captures return metadata only; read_capture emits pixels only with explicit sharing. No WM policy changes, cookies/CDP attachment, arbitrary commands or automatic publication.', log_level='WARNING')


@mcp.tool()
def screenshot_capabilities() -> dict:
    """Describe managed backends and privacy limits without querying GUI state."""
    return engine.capabilities()


@mcp.tool()
def screenshot_targets(backend: Literal['auto', 'niri', 'kde'] = 'auto', pid: int | None = None, include_titles: bool = False) -> dict:
    """List authorized GUI targets only after permission. Titles are omitted by default."""
    return engine.targets(backend, pid, include_titles)


@mcp.tool()
def screenshot_capture(kind: Literal['web', 'code', 'window', 'screen', 'region'], url: str | None = None, allow_origins: list[str] | None = None, repo: str | None = None, file: str | None = None, start_line: int = 1, end_line: int | None = None, backend: Literal['auto', 'niri', 'kde'] = 'auto', window_id: str | None = None, output: str | None = None, region: list[int] | None = None, allow_focus: bool = False, allow_clipboard_change: bool = False) -> dict:
    """Capture the exact approved target into private storage; no image bytes are returned. Web/code use a fresh isolated browser. GUI needs explicit IDs/output/region, plus permission for any focus/clipboard side effect."""
    return engine.capture(kind, url=url, allow_origins=allow_origins, repo=repo, file=file, start_line=start_line, end_line=end_line, backend=backend, window_id=window_id, output=output, region=region, allow_focus=allow_focus, allow_clipboard_change=allow_clipboard_change)


@mcp.tool()
def screenshot_read_capture(capture_id: str, image: str = 'capture', share_with_model: bool = False, crop: list[int] | None = None) -> list:
    """Read metadata by default. Set share_with_model=true only after operator consent and image-input capability verification. An explicit image crop can minimize disclosure."""
    metadata, data = engine.read_capture(capture_id, image, share_with_model, crop)
    return [json.dumps(metadata, ensure_ascii=False), Image(data=data, format='png')] if data is not None else [json.dumps(metadata, ensure_ascii=False)]


if __name__ == '__main__':
    if sys.argv[1:] == ['--help']:
        print('badwater-screenshot [mcp]\nLocal stdio MCP: capabilities, authorized target discovery, private capture and opt-in image sharing. No capture/focus/network operation on startup.')
    elif sys.argv[1:] in [[], ['mcp']]:
        mcp.run(transport='stdio')
    else:
        raise SystemExit('Only mcp or --help is supported; no arbitrary command runner')
