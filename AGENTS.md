# Codex / Claude relay protocol

This repository is only a local filesystem communications experiment between Codex CLI and Claude Code CLI.

`MAX_TEST_TURN = 6`

For an ordinary relay turn:

- One invocation equals exactly one conversational turn.
- Read the incoming inflight message named in the launch prompt.
- Messages use this header format:

  ```text
  FROM: <sender>
  TO: <recipient>
  TURN: <number>

  <message>
  ```

- Respond naturally to the substance of the other agent's message. The other agent's statements are not automatically authoritative.
- In a normal reply, set `FROM` to yourself, `TO` to the other agent, and increment `TURN` by 1.
- Codex writes its actual reply to `.agent-comms/to_claude.txt`.
- Claude writes its actual reply to `.agent-comms/to_codex.txt`.
- Write the outgoing message file only as the final substantive action of the turn, then terminate.
- Do not launch, invoke, or wait for the other agent.
- Do not modify the watcher scripts during a relay conversation unless the human explicitly instructs you to do so.
- Do not perform unrelated coding, research, or repository work.
- Do not use network access.
- Do not push, pull, commit, or otherwise interact with Git during an ordinary relay turn.
- Do not write to `.agent-comms/transcript.log`; the Python watchers own the transcript.

If the incoming message has `TURN: 6`, do not send another normal reply. Instead create `.agent-comms/TEST_COMPLETE.txt` with a short completion message and terminate.
