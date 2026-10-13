#!/usr/bin/env python3
"""
local_agent.py — Run the demo-agent on your machine, for evals and smoke tests.

The agent is a Claude model driven through the Anthropic Messages API. It gets what the
Dynatrace agent gets: the instructions in dynatrace-intelligence/agents/demo-agent/ as its
system prompt, a `read_file` tool that serves the skill documents from this repo under
/resources/documents/skills/, and an `execute-dql` tool that runs read-only DQL through
dtctl on the read-only context of the scenario's tenant. It returns the same event shape as
dt_agent.invoke_agent, so run_dt_evals.py checks it with the same assertions.

It tests the skill and the instructions, not the Dynatrace runtime: no platform guardrail,
and a result carries a queryId unless you ask for --metadata strip.

Usage:
    python tools/local_agent.py --context playground "Are there any open issues right now?"
    python tools/run_dt_evals.py --local [--case survey-dev] [--include-draft]

Needs ANTHROPIC_API_KEY (never printed). No SDK: standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

TOOLS_DIR = Path(__file__).parent
REPO_ROOT = TOOLS_DIR.parent
sys.path.insert(0, str(TOOLS_DIR))

import guard_dtctl  # noqa: E402  (the same write-construct check the hook uses)
import preflight  # noqa: E402  (finds the dtctl executable)

INSTRUCTIONS = REPO_ROOT / "dynatrace-intelligence" / "agents" / "demo-agent" / "instructions.md"
TEMPLATE = REPO_ROOT / "dynatrace-intelligence" / "agents" / "demo-agent" / "template.json"
SKILLS_ROOT = REPO_ROOT / "dynatrace-intelligence" / "skills"
MOUNT = "/resources/documents/skills/"
API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
CONTEXTS = {"playground", "dev"}
MAX_RESULT_CHARS = 40000

TOOLS = [
    {
        "name": "read_file",
        "description": "Read a document by its path.",
        "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}},
                         "required": ["file_path"]},
    },
    {
        "name": "execute-dql",
        "description": "Run one read-only DQL query and return its records and query metadata.",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}},
                         "required": ["query"]},
    },
]


def default_model() -> str:
    """The model the deployed agent uses, from its template."""
    return json.loads(TEMPLATE.read_text(encoding="utf-8"))["data"]["llm"]


def read_document(file_path: str) -> tuple[str, bool]:
    """Serve a skill document from the repo. Returns (text, is_error)."""
    if not file_path.startswith(MOUNT):
        return f"Error: no such file: {file_path}", True
    target = (SKILLS_ROOT / file_path[len(MOUNT):]).resolve()
    if SKILLS_ROOT.resolve() not in target.parents or not target.is_file():
        return f"Error: no such file: {file_path}", True
    return target.read_text(encoding="utf-8").replace("\r\n", "\n"), False


def dql_blocked(dql: str) -> str | None:
    """Block reason for a DQL string that contains a write construct, else None."""
    for pattern in guard_dtctl.DQL_WRITE_PATTERNS:
        if re.search(pattern, dql, re.IGNORECASE):
            return f"BLOCKED: DQL contains a write construct '{pattern}'. Only read queries are permitted."
    return None


def run_dtctl_query(dql: str, context: str) -> dict:
    """Run one query on a named dtctl context. Returns the parsed envelope (or an error envelope)."""
    cmd = [preflight.DTCTL, "query", dql, "--context", context, "--agent", "-o", "json", "--plain",
           "--max-field-chars", "0", "-M=all"]
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=120)
    except FileNotFoundError:
        return {"ok": False, "error": "dtctl executable not found"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "query timed out"}
    envelope = preflight.parse_envelope(done.stdout)
    if envelope is None:
        return {"ok": False, "error": (done.stderr or done.stdout or "no output").strip()[:500]}
    return envelope


def format_result(envelope: dict, metadata: str) -> tuple[str, bool]:
    """What the model sees for one query. Returns (text, is_error)."""
    if not envelope.get("ok"):
        err = envelope.get("error") or envelope.get("message") or envelope
        return "Error: " + (err if isinstance(err, str) else json.dumps(err, ensure_ascii=False))[:800], True
    body: dict = {"records": preflight._flatten_records(envelope)}
    meta = envelope.get("metadata") or {}
    if metadata == "keep" and meta:
        body["query_metadata"] = {k: meta[k] for k in ("queryId", "scannedRecords", "executionTimeMilliseconds")
                                  if k in meta}
    text = json.dumps(body, ensure_ascii=False)
    if len(text) > MAX_RESULT_CHARS:
        text = text[:MAX_RESULT_CHARS] + " …[result truncated]"
    return text, False


class AnthropicClient:
    """One Messages API call with retries; the key is read from the environment and never printed."""

    def __init__(self, model: str, api_key: str | None = None, max_tokens: int = 4096):
        self.model = model
        self.max_tokens = max_tokens
        self._key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self._key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")

    def __call__(self, system: str, messages: list[dict], tools: list[dict]) -> dict:
        body = json.dumps({"model": self.model, "max_tokens": self.max_tokens, "system": system,
                           "messages": messages, "tools": tools}).encode("utf-8")
        headers = {"content-type": "application/json", "x-api-key": self._key,
                   "anthropic-version": API_VERSION}
        for attempt in range(5):
            request = urllib.request.Request(API_URL, data=body, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(request, timeout=180) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503, 529) and attempt < 4:
                    time.sleep(2 ** attempt * 2)
                    continue
                detail = e.read().decode("utf-8", "replace")[:300]
                raise RuntimeError(f"Anthropic API HTTP {e.code}: {detail}") from None
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt < 4:
                    time.sleep(2 ** attempt * 2)
                    continue
                raise RuntimeError(f"Anthropic API unreachable: {e}") from None
        raise RuntimeError("Anthropic API: retries exhausted")


class LocalAgent:
    """The demo-agent, run locally. invoke_agent matches dt_agent.invoke_agent for run_dt_evals."""

    def __init__(self, context: str, model: str | None = None, complete=None, run_query=None,
                 metadata: str = "keep", max_rounds: int = 30):
        if context not in CONTEXTS:
            raise ValueError(f"context must be one of {sorted(CONTEXTS)}")
        self.context = context
        self.metadata = metadata
        self.max_rounds = max_rounds
        self.model = model or default_model()
        self.complete = complete or AnthropicClient(self.model)
        self.run_query = run_query or (lambda dql: run_dtctl_query(dql, context))
        self.system = INSTRUCTIONS.read_text(encoding="utf-8").replace("\r\n", "\n")
        self._conversations: dict[str, list[dict]] = {}
        self._lock = threading.Lock()

    def _run_tool(self, block: dict) -> dict:
        name, args = block["name"], block.get("input") or {}
        if name == "read_file":
            text, is_error = read_document(str(args.get("file_path", "")))
        elif name == "execute-dql":
            dql = str(args.get("query", ""))
            reason = dql_blocked(dql)
            text, is_error = (reason, True) if reason else format_result(self.run_query(dql), self.metadata)
        else:
            text, is_error = f"Error: unknown tool {name}", True
        result = {"type": "tool_result", "tool_use_id": block["id"], "content": text}
        if is_error:
            result["is_error"] = True
        return result

    def invoke_agent(self, tenant, agent, text: str, conversation: str | None = None):
        """Send one user turn; run the tool loop to the final answer. Returns (conversation_id, events)."""
        conversation = conversation or uuid.uuid4().hex
        with self._lock:
            messages = self._conversations.setdefault(conversation, [])
        messages.append({"role": "user", "content": text})
        events: list[dict] = []
        for _ in range(self.max_rounds):
            reply = self.complete(self.system, messages, TOOLS)
            blocks = []
            for block in reply.get("content", []):
                if block["type"] == "text":
                    blocks.append({"type": "text", "text": block["text"]})
                    if block["text"].strip():
                        events.append({"type": "agent_response", "content": [{"text": block["text"]}]})
                elif block["type"] == "tool_use":
                    blocks.append({k: block[k] for k in ("type", "id", "name", "input")})
                    events.append({"type": "tool_invocation",
                                   "tool_call": {"name": block["name"], "args": block.get("input") or {}}})
            messages.append({"role": "assistant", "content": blocks})
            uses = [b for b in blocks if b["type"] == "tool_use"]
            if not uses:
                return conversation, events
            with ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(self._run_tool, uses))
            messages.append({"role": "user", "content": results})
        raise RuntimeError(f"tool loop did not finish in {self.max_rounds} rounds")


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("message", help="one user message")
    parser.add_argument("--context", choices=sorted(CONTEXTS), default="playground")
    parser.add_argument("--model", help="default: the model in template.json")
    parser.add_argument("--metadata", choices=["keep", "strip"], default="keep",
                        help="strip the queryId from results, as the Dynatrace runtime often does")
    args = parser.parse_args(argv[1:])
    agent = LocalAgent(args.context, args.model, metadata=args.metadata)
    _, events = agent.invoke_agent(None, "demo-agent", args.message)
    for event in events:
        if event["type"] == "tool_invocation":
            call = event["tool_call"]
            shown = call["args"].get("file_path") or (call["args"].get("query", "")[:70] + "…")
            print(f"  [{call['name']}] {shown}")
        else:
            print(event["content"][0]["text"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
