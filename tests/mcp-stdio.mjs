// Sequential installed-stdio fixture: MCP2 cancels pending requests on stdin EOF.
// Keep stdin open through every response; no prompts, provider or remote requests.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { once } from "node:events";
import { createInterface } from "node:readline";

export async function withStdioMcp(command, args, check) {
  const child = spawn(command, args, { stdio: ["pipe", "pipe", "pipe"] });
  const exited = once(child, "exit");
  const lines = createInterface({ input: child.stdout })[Symbol.asyncIterator]();
  let stderr = "";
  let writeError;
  child.stdin.on("error", error => { writeError = error; });
  child.stderr.setEncoding("utf8");
  child.stderr.on("data", chunk => { stderr += chunk; });
  let nextId = 0;
  let timedOut = false;
  const deadline = setTimeout(() => { timedOut = true; child.kill("SIGKILL"); }, 20_000);
  const transcript = [];
  const send = message => child.stdin.write(JSON.stringify({ jsonrpc: "2.0", ...message }) + "\n");
  async function request(method, params) {
    const id = ++nextId;
    send({ id, method, params });
    for (;;) {
      const line = await lines.next();
      if (line.done) {
        const status = await exited;
        assert.fail(`MCP exited ${JSON.stringify(status)} before ${method} response: ${stderr}`);
      }
      const response = JSON.parse(line.value);
      transcript.push(response);
      if (response.id === id) {
        assert.equal(response.error, undefined, JSON.stringify(response));
        return response.result;
      }
      assert.equal(response.id, undefined, "unexpected MCP response identity");
    }
  }
  try {
    const initialized = await request("initialize", {
      protocolVersion: "2025-06-18", capabilities: {}, clientInfo: { name: "offline-fixture", version: "1" },
    });
    send({ method: "notifications/initialized" });
    await check(request, initialized);
    child.stdin.end();
    assert.deepEqual(await exited, [0, null], stderr);
    assert.equal(stderr, "", "unexpected MCP diagnostics");
    assert.ifError(writeError);
    assert.equal(timedOut, false, "MCP deadline exceeded");
    return transcript;
  } finally {
    clearTimeout(deadline);
    if (child.exitCode === null && child.signalCode === null) child.kill("SIGKILL");
    await exited;
  }
}
