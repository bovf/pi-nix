// Installed lazy MCP interface only; never call a tool, analyze media or start Craft.
// Run in the README private filesystem/network sandbox: node tests/video-mcp.mjs <video>.
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readdir, writeFile } from "node:fs/promises";
import { withStdioMcp } from "./mcp-stdio.mjs";

const [video] = process.argv.slice(2);
assert(video);
assert.equal(process.cwd(), process.env.HOME);
await writeFile("config.json", JSON.stringify({
  readRoots: [`${process.cwd()}/raw`], writeRoot: `${process.cwd()}/derived`,
  filmcraft: "/forbidden-backend", soundcraft: "/forbidden-backend",
}));
const canonical = value => Array.isArray(value) ? value.map(canonical)
  : value && typeof value === "object" ? Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])])) : value;
await withStdioMcp(`${video}/bin/badwater-video`, ["--config", `${process.cwd()}/config.json`, "mcp"], async (request, initialized) => {
  assert.equal(initialized.serverInfo.name, "badwater-video");
  const { tools } = await request("tools/list", {});
  assert.equal(tools.length, 38);
  const inventory = tools.map(tool => Object.fromEntries(
    ["name", "description", "inputSchema", "outputSchema"].filter(key => key in tool).map(key => [key, tool[key]]),
  )).sort((a, b) => a.name.localeCompare(b.name));
  // All38 definitions in overlays/badwater-video/main.py, measured before the
  // MCP1→2 import-only migration. Includes every description/input/output schema.
  assert.equal(createHash("sha256").update(JSON.stringify(canonical(inventory))).digest("hex"),
    "71e97005cd86cdd0c846f02096135c61d4526433d0cad682522ef58561da1944",
    "review exact video tool/schema inventory changes, not merely startup");
});
assert((await readdir("derived")).every(name => /^jobs\.sqlite(?:-wal|-shm)?$/.test(name)), "no project/job/backend work during discovery");
console.log("PASS: installed video MCP initialize/list, unchanged38 tool descriptions/input/output schemas; zero stderr; no tool/backend/media calls");
