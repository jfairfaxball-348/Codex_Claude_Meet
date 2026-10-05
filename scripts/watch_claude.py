from __future__ import annotations

import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
COMMS_DIR = REPO_ROOT / ".agent-comms"
INCOMING = COMMS_DIR / "to_claude.txt"
INFLIGHT = COMMS_DIR / "claude_inflight.txt"
OUTGOING = COMMS_DIR / "to_codex.txt"
TEST_COMPLETE = COMMS_DIR / "TEST_COMPLETE.txt"
TRANSCRIPT = COMMS_DIR / "transcript.log"
POLL_SECONDS = 1.5

PROMPT = """This is one turn in the Claude/Codex filesystem relay experiment.

Follow CLAUDE.md and the imported AGENTS.md instructions.

Read:
.agent-comms/claude_inflight.txt

Respond to the substance of that message.

Write your response for Codex to:
.agent-comms/to_codex.txt

The outgoing message file is the actual handoff.

Write it as your final substantive action, then exit.
Do not launch Codex yourself.
Do not wait for another message.
Do not continue beyond one relay turn.
Keep your terminal final response to a very short status line.
"""


def status(message: str) -> None:
    print(f"[Claude watcher] {message}", flush=True)


def append_transcript(message: str) -> None:
    headers = {}
    for line in message.splitlines()[:6]:
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip().lstrip("\ufeff").upper()] = value.strip()

    sender = headers.get("FROM", "UNKNOWN")
    recipient = headers.get("TO", "CLAUDE")
    turn = headers.get("TURN", "?")
    separator = "=" * 60

    with TRANSCRIPT.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"{separator}\n{sender.upper()} → {recipient.upper()}\nTURN {turn}\n{separator}\n\n")
        handle.write(message.rstrip() + "\n\n")


def preserve_failure(reason: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    failed = COMMS_DIR / f"claude_failed_{stamp}.txt"
    if INFLIGHT.exists():
        INFLIGHT.replace(failed)
    status(f"ERROR: {reason}")
    status(f"preserved inflight message as {failed.name}")
    return failed


def main() -> int:
    COMMS_DIR.mkdir(parents=True, exist_ok=True)

    claude = shutil.which("claude")
    if claude is None:
        status("ERROR: claude CLI was not found on PATH")
        status("install/authenticate Claude Code, open a fresh PowerShell window, and try again")
        return 1

    if INFLIGHT.exists():
        status("ERROR: {} is already present from an earlier interrupted run".format(INFLIGHT.name))
        status("inspect or reset .agent-comms before restarting this watcher")
        return 1

    status("waiting")

    try:
        while True:
            if TEST_COMPLETE.exists():
                status("TEST_COMPLETE.txt found; stopping")
                return 0

            if not INCOMING.exists():
                time.sleep(POLL_SECONDS)
                continue

            try:
                INCOMING.replace(INFLIGHT)
            except FileNotFoundError:
                continue

            message = INFLIGHT.read_text(encoding="utf-8")
            append_transcript(message)
            status("message received")

            if OUTGOING.exists():
                preserve_failure(f"{OUTGOING.name} already exists; refusing to overwrite an unclaimed message")
                return 1

            command = [
                claude,
                "-p",
                "--no-session-persistence",
                "--permission-mode",
                "acceptEdits",
                "--permission-prompts",
                "none",
                "--max-turns",
                "5",
                "--tools",
                "Read,Write,Edit",
                PROMPT,
            ]

            status("launching Claude")
            result = subprocess.run(command, cwd=REPO_ROOT, shell=False, check=False)

            if result.returncode != 0:
                preserve_failure(f"Claude exited with code {result.returncode}; watcher will not retry")
                return result.returncode or 1

            status("Claude exited successfully")

            if not OUTGOING.exists() and not TEST_COMPLETE.exists():
                preserve_failure("Claude exited successfully but produced neither a reply nor TEST_COMPLETE.txt")
                return 1

            INFLIGHT.unlink(missing_ok=True)

            if TEST_COMPLETE.exists():
                status("test complete; stopping")
                return 0

            status("reply handed to Codex")

    except KeyboardInterrupt:
        status("stopped by Ctrl+C")
        return 0


if __name__ == "__main__":
    sys.exit(main())
