# Codex ↔ Claude filesystem relay

A deliberately small local experiment proving that two idle Python watchers can relay a finite conversation between disposable Codex CLI and Claude Code CLI processes.

The watchers do no AI reasoning and make no model/API calls while idle. They poll for plain-text message files, atomically rename an incoming message to an inflight file, launch exactly one non-interactive agent turn, wait synchronously for that process to exit, and then wait for the other watcher to claim the reply.

```text
Claude watcher
   ↓
Claude
   ↓
to_codex.txt
   ↓
Codex watcher
   ↓
Codex
   ↓
to_claude.txt
   ↓
...
```

The relay state is only the presence and contents of `.agent-comms/to_codex.txt` and `.agent-comms/to_claude.txt`. There is no queue, service, database, daemon, or hidden boolean state.

## 1. Clone on Windows

Open PowerShell:

```powershell
git clone https://github.com/jfairfaxball-348/Codex_Claude_Meet.git
cd .\Codex_Claude_Meet
```

## 2. Prerequisites

This repository targets native Windows 10/11 with PowerShell. WSL is not required.

Install:

- Python 3
- Git for Windows
- OpenAI Codex CLI
- Anthropic Claude Code CLI

### Python and Git

Install Python 3 from Python.org or the Microsoft Store, and Git from Git for Windows. Re-open PowerShell after installation so PATH changes are visible.

### Codex CLI

As of 5 October 2026, OpenAI's Codex repository documents a native Windows PowerShell installer:

```powershell
powershell -ExecutionPolicy Bypass -c "irm https://chatgpt.com/codex/install.ps1 | iex"
```

The npm package is also supported if Node.js/npm is already installed:

```powershell
npm install -g @openai/codex@latest
```

Official source: <https://github.com/openai/codex>

### Claude Code

Anthropic's current native Windows PowerShell installer is:

```powershell
irm https://claude.ai/install.ps1 | iex
```

WinGet alternative:

```powershell
winget install Anthropic.ClaudeCode
```

Official source: <https://code.claude.com/docs/en/setup>

## 3. Authenticate once

Before starting either watcher, run each CLI interactively once and complete sign-in.

```powershell
codex
```

Exit Codex after authentication, then:

```powershell
claude
```

Exit Claude after authentication.

Do not put API keys, tokens, or credentials in this repository.

## 4. Verify from a fresh PowerShell window

```powershell
codex --version
claude --version
python --version
git --version
```

If `claude` does not recognize `--permission-prompts`, update Claude Code. That flag is documented for Claude Code v2.1.259 or later and is intentionally used here so an unattended run denies any permission request it cannot answer instead of hanging.

## 5. Optional one-shot smoke tests

These tests use the same non-interactive style as the watchers but create harmless local files only.

### Codex

From the repository root:

```powershell
codex --ask-for-approval never exec --ephemeral --sandbox workspace-write -C "$PWD" "Follow AGENTS.md. Create .agent-comms/codex_smoke_test.txt containing exactly CODEX_OK, then exit."
Get-Content .\.agent-comms\codex_smoke_test.txt
Remove-Item .\.agent-comms\codex_smoke_test.txt
```

`--ask-for-approval` is deliberately placed before `exec`: current Codex CLI treats it as a global option.

### Claude

```powershell
claude -p --no-session-persistence --permission-mode acceptEdits --permission-prompts none --max-turns 5 --tools "Read,Write,Edit" "Follow CLAUDE.md. Create .agent-comms/claude_smoke_test.txt containing exactly CLAUDE_OK, then exit."
Get-Content .\.agent-comms\claude_smoke_test.txt
Remove-Item .\.agent-comms\claude_smoke_test.txt
```

Claude is deliberately restricted to `Read`, `Write`, and `Edit`; this relay does not require shell execution.

## 6. Three-terminal operating model

Open **three PowerShell terminals** in the repository and leave them visible side-by-side.

### Terminal 1 — Codex watcher

```powershell
python .\scripts\watch_codex.py
```

### Terminal 2 — Claude watcher

```powershell
python .\scripts\watch_claude.py
```

### Terminal 3 — live conversation monitor

The watchers append every claimed message exactly once to `.agent-comms/transcript.log`. The transcript is observational only; it never triggers an agent and is never authoritative relay state.

```powershell
New-Item -ItemType File -Force .\.agent-comms\transcript.log | Out-Null
Get-Content .\.agent-comms\transcript.log -Wait
```

Terminal 3 consumes no AI/model tokens. It only displays text appended by the two Python watcher processes.

The intended view is:

```text
TERMINAL 1                 TERMINAL 2                 TERMINAL 3
Codex watcher              Claude watcher             live transcript
     │                           │                           │
     │                     Claude wakes                    │
     │                           ├──── message ────────────>│
Codex wakes <──── file ─────────┘                           │
     ├──────────── message ────────────────────────────────>│
     │                           │                           │
     ... repeat until TURN 6 ...
```

## 7. Seed the conversation

With all three terminals running, create the initial message in a fourth temporary PowerShell prompt, or pause briefly in any terminal before its long-running command is started:

```powershell
@'
FROM: Human
TO: Claude
TURN: 1

Hello Claude. This is the first filesystem-relay test.
Introduce yourself briefly to Codex and ask Codex one question.
'@ | Set-Content -Encoding utf8 .\.agent-comms\to_claude.txt
```

Once that file exists, do not touch the relay. The Claude watcher claims it atomically, logs it to the transcript, launches one Claude turn, and waits. Claude's reply wakes Codex; Codex's reply wakes Claude; and so on.

## 8. Finite test limit

`AGENTS.md` sets:

```text
MAX_TEST_TURN = 6
```

Each normal reply increments `TURN`. If either agent receives `TURN: 6`, it must not send another normal reply. It creates `.agent-comms/TEST_COMPLETE.txt` and exits instead. Both watchers stop normally when that file exists.

This is intentionally a tiny convention, not a generic state machine.

## 9. Runtime/failure behaviour

The watcher owns transport:

```text
to_codex.txt  -> codex_inflight.txt
to_claude.txt -> claude_inflight.txt
```

The rename uses `pathlib.Path.replace()`, which is a same-filesystem atomic replacement operation. The AI agent never claims its own message.

If a CLI process exits non-zero, the watcher does not retry. It preserves the inflight message as a timestamped `codex_failed_*.txt` or `claude_failed_*.txt`, prints an error, and stops. A successful CLI exit that produced neither an outgoing message nor `TEST_COMPLETE.txt` is also treated as a protocol failure and preserved for diagnosis.

Runtime files, failures, smoke-test files, `TEST_COMPLETE.txt`, and `transcript.log` are all gitignored. Only `.agent-comms/.gitkeep` is committed.

## 10. Reset safely

Stop both watchers first. Then remove only the known runtime files; this preserves `.gitkeep` and avoids a broad recursive delete:

```powershell
Get-ChildItem .\.agent-comms -File |
  Where-Object { $_.Name -ne '.gitkeep' } |
  Remove-Item
```

Start the three terminals again and seed a new `TURN: 1` message.

## Commands executed by the watchers

The Codex watcher constructs an argument list equivalent to:

```powershell
codex --ask-for-approval never exec --ephemeral --sandbox workspace-write -C "<REPO_ROOT>" "<fixed relay instruction>"
```

The Claude watcher constructs an argument list equivalent to:

```powershell
claude -p --no-session-persistence --permission-mode acceptEdits --permission-prompts none --max-turns 5 --tools "Read,Write,Edit" "<fixed relay instruction>"
```

Both use Python `subprocess.run(..., shell=False, cwd=REPO_ROOT)` and pass every argument as a separate list element, so repository paths containing spaces are handled correctly.

Neither watcher uses `--dangerously-bypass-approvals-and-sandbox` or `--dangerously-skip-permissions`.

## Final local acceptance test

On the Windows laptop:

1. Open three PowerShell terminals in the cloned repository.
2. Start the Codex watcher in Terminal 1.
3. Start the Claude watcher in Terminal 2.
4. Start `Get-Content .\.agent-comms\transcript.log -Wait` in Terminal 3.
5. Create the initial human `to_claude.txt` message.
6. Do not touch anything else.
7. Observe Claude and Codex alternate automatically.
8. Confirm every claimed handoff appears live in Terminal 3.
9. Confirm `TURN: 6` produces `TEST_COMPLETE.txt` and terminates the relay.
10. Confirm both watcher processes stop without requiring interactive agent input.

Success means two disposable CLI agent processes held a short autonomous conversation through filesystem messages while the complete conversation was visible live in Terminal 3.

## Bootstrap-test limitation

The repository bootstrap can statically validate the Python, paths, Git ignore rules, instruction import, and subprocess construction without invoking either model. A real Codex↔Claude conversation is **not** considered tested until the final acceptance test above is run on a Windows machine with both installed, authenticated CLIs.
