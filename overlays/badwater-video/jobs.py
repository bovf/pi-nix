"""A tiny durable local queue. GNU timeout owns each worker's private process group."""
import json
import os
import signal
import sqlite3
import subprocess
import time
import uuid
import threading
from pathlib import Path
from contextlib import contextmanager

from store import identifier, json_text, no_links

TERMINAL = {"done", "failed", "cancelled", "interrupted"}


def process_identity(pid):
    try:
        data = Path(f"/proc/{int(pid)}/stat").read_text().rsplit(")", 1)[1].split()
        if data[0] == "Z":
            return None
        return Path("/proc/sys/kernel/random/boot_id").read_text().strip() + ":" + data[19]
    except (FileNotFoundError, ProcessLookupError, ValueError):
        return None


class Jobs:
    def __init__(self, policy, config_path):
        self.policy = policy
        self.config_path = config_path
        policy.write_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = no_links(policy.write_root / "jobs.sqlite")
        with self.db() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, project TEXT NOT NULL, operation TEXT NOT NULL, args TEXT NOT NULL,
                state TEXT NOT NULL, pid INTEGER, process_identity TEXT, progress REAL NOT NULL DEFAULT 0,
                created REAL NOT NULL, updated REAL NOT NULL, result TEXT, error TEXT, retry_of TEXT)""")
            db.execute("CREATE INDEX IF NOT EXISTS queue_projects ON jobs(state,project,created,id)")

    @contextmanager
    def db(self):
        no_links(self.path)
        if self.path.exists() and self.path.stat().st_nlink != 1:
            raise ValueError("refusing a hard-linked job database")
        db = sqlite3.connect(self.path, timeout=5)
        try:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA journal_mode=WAL")
            os.chmod(self.path, 0o600)
            with db:
                yield db
        finally:
            db.close()

    def _recover(self, db):
        for row in db.execute("SELECT * FROM jobs WHERE state='running'").fetchall():
            if process_identity(row["pid"]) != row["process_identity"]:
                db.execute("UPDATE jobs SET state='interrupted', error=?, updated=? WHERE id=? AND state='running'",
                           ("worker/deadline supervisor stopped; inspect bounded logs and retry explicitly", time.time(), row["id"]))

    def pump(self):
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            self._recover(db)
            active = db.execute("SELECT COUNT(*) FROM jobs WHERE state='running'").fetchone()[0]
            slots = max(0, self.policy.config.get("concurrency", 1) - active)
            busy = {r[0] for r in db.execute("SELECT project FROM jobs WHERE state='running'")}
            for row in db.execute("""SELECT j.* FROM jobs j WHERE j.state='queued' AND NOT EXISTS
                (SELECT 1 FROM jobs earlier WHERE earlier.state='queued' AND earlier.project=j.project
                 AND (earlier.created<j.created OR (earlier.created=j.created AND earlier.id<j.id)))
                ORDER BY j.created,j.id LIMIT 100""").fetchall():
                if slots == 0:
                    break
                if row["project"] in busy:
                    continue
                folder = self.policy.write(self.policy.write_root / row["project"] / ".work" / row["id"] / "worker.log").parent
                with (folder / "worker.log").open("ab") as log:
                    argv = [self.policy.config["timeout"], "--kill-after=5s", str(self.policy.config.get("timeoutSeconds", 1200)) + "s",
                            self.policy.config["bash"], "-c", 'set -o pipefail; "$@" 2>&1 | head -c 8388608', "bounded-worker",
                            self.policy.config["engine"], "--config", str(self.config_path), "_worker", row["id"]]
                    process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                               start_new_session=True, close_fds=True,
                                               env={"PATH": self.policy.config["toolPath"], "HOME": str(folder), "PYTHONDONTWRITEBYTECODE": "1"})
                token = process_identity(process.pid)
                if token is None:
                    raise RuntimeError("deadline supervisor exited before its identity could be recorded")
                db.execute("UPDATE jobs SET state='running',pid=?,process_identity=?,updated=? WHERE id=?",
                           (process.pid, token, time.time(), row["id"]))
                slots -= 1
                busy.add(row["project"])
                threading.Thread(target=process.wait, daemon=True).start()

    def submit(self, project, operation, args, retry_of=None):
        identifier(project)
        job_id = uuid.uuid4().hex
        now = time.time()
        with self.db() as db:
            db.execute("INSERT INTO jobs(id,project,operation,args,state,created,updated,retry_of) VALUES (?,?,?,?,'queued',?,?,?)",
                       (job_id, project, operation, json_text(args), now, now, retry_of))
        self.pump()
        return {"job": job_id, "project": project, "operation": operation, "state": "submitted"}

    def raw(self, job_id):
        identifier(job_id)
        with self.db() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            raise ValueError("job not found")
        return dict(row)

    def status(self, job_id):
        self.pump()
        row = self.raw(job_id)
        return {k: json.loads(row[k]) if k == "result" and row[k] else row[k]
                for k in ["id", "project", "operation", "state", "progress", "created", "updated", "result", "error", "retry_of"]}

    def list(self, project):
        self.pump()
        with self.db() as db:
            return [dict(r) for r in db.execute("SELECT id,operation,state,progress,updated FROM jobs WHERE project=? ORDER BY created DESC LIMIT 50", (identifier(project),))]

    def update(self, job_id, progress=None, state=None, result=None, error=None):
        fields = {"updated": time.time()}
        if progress is not None:
            fields["progress"] = max(0, min(1, progress))
        if state:
            fields["state"] = state
        if result is not None:
            fields["result"] = json_text(result)
        if error is not None:
            fields["error"] = str(error)[-4000:]
        with self.db() as db:
            db.execute("UPDATE jobs SET " + ",".join(k + "=?" for k in fields) + " WHERE id=? AND state='running'", (*fields.values(), job_id))

    def cancel(self, job_id):
        row = self.raw(job_id)
        if row["state"] in TERMINAL:
            return self.status(job_id)
        with self.db() as db:
            db.execute("UPDATE jobs SET state='cancelled',updated=?,error='cancelled by caller' WHERE id=? AND state NOT IN ('done','failed','interrupted')", (time.time(), job_id))
        if row["state"] == "running" and process_identity(row["pid"]) == row["process_identity"]:
            try:
                os.killpg(row["pid"], signal.SIGTERM)
            except ProcessLookupError:
                pass
            deadline = time.monotonic() + 2
            while process_identity(row["pid"]) == row["process_identity"] and time.monotonic() < deadline:
                time.sleep(0.02)
            if process_identity(row["pid"]) == row["process_identity"]:
                try:
                    os.killpg(row["pid"], signal.SIGKILL)
                except ProcessLookupError:
                    pass
        self.pump()
        return self.status(job_id)

    def retry(self, job_id, automatic=False):
        row = self.raw(job_id)
        if type(automatic) is not bool:
            raise ValueError("automatic retry must be boolean")
        if row["state"] not in {"failed", "interrupted", "cancelled"}:
            raise ValueError("only a failed/interrupted/cancelled job can be retried")
        args = json.loads(row["args"])
        if automatic:
            prior = row
            count = 0
            for _ in range(100):
                count += int(json.loads(prior["args"]).get("_automaticRetry", False))
                if not prior["retry_of"]:
                    break
                prior = self.raw(prior["retry_of"])
            else:
                raise ValueError("retry ancestry is too long; require explicit manual intervention")
            if count >= self.policy.config.get("maxAutomaticRepairAttempts", 2):
                raise ValueError("automatic repair/re-render budget exhausted; ask the user")
        args["_automaticRetry"] = automatic
        return self.submit(row["project"], row["operation"], args, retry_of=job_id)

    def wait(self, job_id):
        deadline = time.monotonic() + self.policy.config.get("timeoutSeconds", 1200) + 15
        while time.monotonic() < deadline:
            state = self.status(job_id)
            if state["state"] in TERMINAL:
                if state["state"] != "done":
                    raise RuntimeError(state["error"] or state["state"])
                return state["result"]
            time.sleep(0.05)
        raise RuntimeError("wait deadline reached; job remains inspectable/cancellable")
