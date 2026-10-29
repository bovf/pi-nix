"""MCP2 public Image helper serialization; tiny synthetic bytes, no media backend.

Run with badwater-video.python in the private filesystem/network sandbox.
"""
import base64
from pathlib import Path

from mcp.server.mcpserver import Image

encoded = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jK9kAAAAASUVORK5CYII="
data = base64.b64decode(encoded)
path = Path("synthetic.png")
path.write_bytes(data)
expected = {"type": "image", "data": encoded, "mimeType": "image/png"}
for image in (Image(path=path), Image(data=data, format="png")):
    assert image.to_image_content().model_dump(by_alias=True, exclude_none=True) == expected
print("PASS: MCP2 public Image path/bytes serialize unchanged synthetic PNG content and MIME type")
