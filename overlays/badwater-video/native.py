"""Small client for the pinned Craft newline-JSON stdio protocol; no GUI/network bridge."""
import json
import queue
import subprocess
import threading
import time


class NativeError(RuntimeError):
    pass


class NativeMCP:
    def __init__(self, argv, stderr, timeout=60):
        self.timeout = timeout
        self.serial = 0
        self.replies = queue.Queue(maxsize=32)
        self.diagnostic = None
        self.log = stderr
        self.process = subprocess.Popen(
            argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8",
        )
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.log_reader = threading.Thread(target=self._read_stderr, daemon=True)
        self.reader.start()
        self.log_reader.start()
        try:
            self.call("initialize", {
                "protocolVersion": "2024-11-05", "capabilities": {},
                "clientInfo": {"name": "badwater-video", "version": "0.1.0"},
            })
            self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        except BaseException:
            self.close()
            raise

    def _read_stderr(self):
        try:
            for line in iter(lambda: self.process.stderr.readline(8193), ""):
                self.diagnostic = "unexpected native editor diagnostic; inspect native.stderr"
                size = len(line.encode("utf-8"))
                if size > 8192 or self.log.tell() + size > 1024 * 1024:
                    self.diagnostic = "native diagnostics exceed the 1 MiB/8 KiB-line limit"
                    self.process.kill()
                    break
                self.log.write(line)
                self.log.flush()
        except (UnicodeError, OSError):
            self.diagnostic = "native diagnostic stream is not valid UTF-8 or could not be read"
            if self.process.poll() is None:
                self.process.kill()

    def _read(self):
        try:
            while line := self.process.stdout.readline(2_000_001):
                if len(line) > 2_000_000:
                    raise NativeError("native response exceeds the bounded protocol limit")
                self.replies.put(json.loads(line))
        except (ValueError, OSError, NativeError) as exc:
            self.replies.put(exc)
        finally:
            self.replies.put(NativeError("native server closed its output"))

    def _send(self, value):
        try:
            self.process.stdin.write(json.dumps(value, allow_nan=False) + "\n")
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise NativeError("native server disconnected") from exc

    def call(self, method, params):
        self.serial += 1
        request_id = self.serial
        self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        deadline = time.monotonic() + self.timeout
        try:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise queue.Empty
                reply = self.replies.get(timeout=remaining)
                if isinstance(reply, Exception):
                    raise reply
                if reply.get("id") == request_id:
                    if "error" in reply:
                        raise NativeError(str(reply["error"])[:2000])
                    return reply["result"]
        except queue.Empty as exc:
            raise NativeError("native request timed out") from exc

    def tool(self, name, arguments):
        result = self.call("tools/call", {"name": name, "arguments": arguments})
        text = "\n".join(c["text"] for c in result.get("content", []) if c["type"] == "text")
        if result.get("isError"):
            raise NativeError(text[:2000])
        try:
            return json.loads(text)
        except ValueError:
            return {"text": text[:8000]}

    def close(self):
        if self.process.poll() is None:
            self.process.stdin.close()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
        self.log_reader.join(timeout=2)
        self.process.stderr.close()
        self.process.stdout.close()
        if self.log_reader.is_alive():
            raise NativeError("native diagnostic pipe failed to close within deadline")
        if self.diagnostic:
            raise NativeError(self.diagnostic)
        if self.process.returncode != 0:
            raise NativeError("native editor exited unsuccessfully during bounded shutdown")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
