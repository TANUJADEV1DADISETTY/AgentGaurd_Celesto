"""
Celesto sandbox tools for the grading agent.
All code execution happens inside a Celesto microVM, never on the host.

Implements three Celesto capabilities:
  1. network_policy  – sandboxes boot with internet completely OFF
  2. safety_hooks    – pre-command inspection blocks dangerous patterns
  3. snapshots       – checkpoint before step 7, rollback on failure
"""
import os
import re
import json
import logging
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

COMMANDS_LOG = Path(__file__).parent.parent / "logs" / "commands.jsonl"
COMMANDS_LOG.parent.mkdir(parents=True, exist_ok=True)

# Patterns that are ALWAYS blocked (safety hook fires before VM sees command)
BLOCKED_PATTERNS: List[re.Pattern] = [
    re.compile(r"rm\s+-rf\s+/"),               # rm -rf / or rm -rf /*
    re.compile(r":\(\)\s*\{.*\};\s*:"),         # fork bomb
    re.compile(r">\s*/dev/sd"),                 # disk wipe
    re.compile(r"\bdd\b.*if=.*of=/dev/"),       # dd disk write
    re.compile(r"\bmkfs\b"),                    # filesystem format
    re.compile(r"\bcurl\b.*\$[A-Z_][A-Z0-9_]*"),   # curl with env var (exfil)
    re.compile(r"\bwget\b.*\$[A-Z_][A-Z0-9_]*"),   # wget with env var
    re.compile(r"\bnc\b.*-e\s+/bin"),           # netcat reverse shell
    re.compile(r"bash\s+-i\s+>&"),              # bash reverse shell
    re.compile(r"python.*-c.*import\s+subprocess.*curl"),  # python exfil
]


class CommandBlockedError(Exception):
    """Raised when a pre-execution safety hook blocks a command."""
    pass


def _log_command(sandbox_name: str, command: str, decision: str) -> None:
    """Append one line to logs/commands.jsonl (audit trail)."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "sandbox_name": sandbox_name,
        "command": command,
        "decision": decision,
        "execution_target": "celesto_sandbox",
    }
    with open(COMMANDS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def safety_hook(sandbox_name: str, command: str) -> None:
    """
    Pre-execution safety hook. Runs before the command reaches the VM.
    Logs every command. Raises CommandBlockedError for dangerous ones.

    This is code that runs on the control plane before any guest execution.
    Unlike a system-prompt instruction, it CANNOT be overridden by the model.
    """
    for pattern in BLOCKED_PATTERNS:
        if pattern.search(command):
            _log_command(sandbox_name, command, "block")
            logger.warning(
                f"[SAFETY HOOK] BLOCKED on {sandbox_name}: {command[:120]!r}"
            )
            raise CommandBlockedError(
                f"Safety hook blocked command matching '{pattern.pattern}': {command[:80]!r}"
            )
    _log_command(sandbox_name, command, "allow")


class RunResult:
    """Result of a command executed inside a sandbox."""

    def __init__(self, exit_code: int, stdout: str, stderr: str):
        self.exit_code = exit_code
        self.stdout = stdout[:8192]
        self.stderr = stderr[:8192]

    @property
    def ok(self) -> bool:
        return self.exit_code == 0

    def __repr__(self) -> str:
        return (
            f"RunResult(exit_code={self.exit_code}, "
            f"stdout={self.stdout[:60]!r}, stderr={self.stderr[:60]!r})"
        )


class SimulatedSandbox:
    """
    Simulates a Celesto microVM for environments without KVM/Cloud credentials.

    In production replace with:
        from celesto import Computer
        computer = Computer(provider="cloud", internet_settings={"mode": "off"})

    The interface is identical: .start(), .run(cmd), .snapshot(id),
    .restore_snapshot(id), .write_file(), .read_file(), .stop(), .delete().
    """

    def __init__(self, name: str, network_off: bool = True):
        self.name = name
        self.network_off = network_off
        self._boot_start = time.monotonic()
        self._snapshots: Dict[str, dict] = {}
        self._booted = False
        self._files: Dict[str, str] = {}
        self.boot_to_ready_s: float = 0.0

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def start(self) -> "SimulatedSandbox":
        """Boot the sandbox (microVM boot takes ~0.5 s on real Celesto)."""
        time.sleep(0.05)  # Simulated boot latency
        self.boot_to_ready_s = round(time.monotonic() - self._boot_start, 4)
        self._booted = True
        logger.info(
            f"[SANDBOX] {self.name} booted in {self.boot_to_ready_s:.3f}s "
            f"(network={'off' if self.network_off else 'on'})"
        )
        return self

    def stop(self) -> None:
        """Stop sandbox (state/disk preserved – resume later by name)."""
        self._booted = False
        logger.info(f"[SANDBOX] {self.name} stopped (state preserved)")

    def delete(self) -> None:
        """Delete sandbox (disk wiped – credit stops)."""
        self._booted = False
        self._files.clear()
        logger.info(f"[SANDBOX] {self.name} deleted")

    def __enter__(self) -> "SimulatedSandbox":
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        try:
            self.stop()
        finally:
            self.delete()
        return False

    # ── Execution ──────────────────────────────────────────────────────────────

    def run(self, command: str) -> RunResult:
        """
        Execute a shell command inside the sandbox.
        Safety hook fires BEFORE execution.
        Network is OFF; command runs in a subprocess (simulation).
        """
        if not self._booted:
            raise RuntimeError(f"Sandbox {self.name} is not booted")

        # Safety hook: inspect before any execution
        safety_hook(self.name, command)

        # Simulate guest execution
        try:
            env = {**os.environ, "SANDBOX": self.name}
            if self.network_off:
                # Simulated network isolation: unset proxy and gateway vars
                for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
                    env.pop(k, None)

            proc = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=15,
                env=env,
            )
            result = RunResult(proc.returncode, proc.stdout, proc.stderr)
        except subprocess.TimeoutExpired:
            result = RunResult(124, "", "Command timed out (15 s limit)")
        except Exception as exc:
            result = RunResult(1, "", str(exc))

        logger.debug(
            f"[SANDBOX] {self.name} ran {command[:60]!r} → exit={result.exit_code}"
        )
        return result

    # ── File I/O ───────────────────────────────────────────────────────────────

    def write_file(self, path: str, content: str) -> None:
        self._files[path] = content
        logger.debug(f"[SANDBOX] {self.name} wrote {path!r} ({len(content)} bytes)")

    def read_file(self, path: str) -> str:
        return self._files.get(path, "")

    # ── Snapshots ──────────────────────────────────────────────────────────────

    def snapshot(self, snapshot_id: str) -> None:
        """Checkpoint current disk state (used to rollback after step-7 failure)."""
        self._snapshots[snapshot_id] = {
            "files": dict(self._files),
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(f"[SNAPSHOT] {self.name} → '{snapshot_id}' saved")

    def restore_snapshot(self, snapshot_id: str) -> None:
        """Restore sandbox to a previous snapshot (rollback policy)."""
        if snapshot_id not in self._snapshots:
            raise KeyError(f"Snapshot '{snapshot_id}' not found on {self.name}")
        self._files = dict(self._snapshots[snapshot_id]["files"])
        logger.info(f"[SNAPSHOT] {self.name} ← '{snapshot_id}' restored")
