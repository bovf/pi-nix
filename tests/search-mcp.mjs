// Run with managed Node in the private filesystem/network sandbox from README.
// Expose managed env at /usr/bin/env and bash on PATH for the installed MCP wrapper.
// Usage: node tests/search-mcp.mjs <pi-search> <pi-search-mcp>
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { withStdioMcp } from "./mcp-stdio.mjs";

const [search, mcp] = process.argv.slice(2);
assert(search && mcp);
const usage = spawnSync(`${search}/bin/pi-search`, [], { encoding: "utf8", timeout: 10_000 });
assert.ifError(usage.error);
assert.equal(usage.status, 2);
assert.match(usage.stderr, /^Usage: pi-search/);
assert.equal(usage.stdout, "");
await withStdioMcp(`${mcp}/bin/pi-search-mcp`, [], async (request, initialized) => {
  assert.equal(initialized.serverInfo.name, "pi-search");
  assert.equal(initialized.serverInfo.version, "0.1.0");
  const { tools } = await request("tools/list", {});
  assert.equal(tools.length, 1);
  assert.equal(tools[0].name, "web_search");
  assert.equal(tools[0].description, "DuckDuckGo web search. Returns up to N results with title, URL, and snippet.");
  assert.deepEqual(tools[0].inputSchema, {
    type: "object", properties: { query: { type: "string" }, max_results: { type: "integer", default: 10, minimum: 1, maximum: 30 } }, required: ["query"],
  });
  const empty = await request("tools/call", { name: "web_search", arguments: { query: "  " } });
  assert.deepEqual(empty.content, [{ type: "text", text: "empty query" }]);
  assert(!empty.isError);
  const unknown = await request("tools/call", { name: "not-a-tool", arguments: {} });
  assert.deepEqual(unknown.content, [{ type: "text", text: "unknown tool not-a-tool" }]);
  assert(!unknown.isError);
  for (const arguments_ of [{}, { query: 1 }, { query: "", max_results: 0 },
    { query: "", max_results: 31 }, { query: "", max_results: 1.5 }, { query: "", max_results: true }]) {
    const error = await request("tools/call", { name: "web_search", arguments: arguments_ });
    assert.equal(error.isError, true);
    assert.match(error.content[0].text, /^Input validation error:/);
  }
});
console.log("PASS: installed search usage; MCP initialize/list/empty query, unknown tool and six schema negatives; zero stderr; no web query");
