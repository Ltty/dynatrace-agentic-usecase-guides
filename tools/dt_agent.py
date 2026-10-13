#!/usr/bin/env python3
"""
dt_agent.py — Deploy the Playground demo skill, and its agent, to a Dynatrace tenant.

The skill folder (dynatrace-intelligence/skills/<name>/) is uploaded as shared
(isPrivate: false), user-owned `ai-agent-resource` documents named /skills/<name>/SKILL.md
and /skills/<name>/references/<ref>.md, the names `dt-app deploy` would use. These are NOT
ready-made: ready-made documents are shipped by an app or extension (originAppId), are
owned by the system, and are read-only for users. Every command that writes is a dry run
unless --apply is given; nothing is ever deleted.

Usage:
    python tools/dt_agent.py check
    python tools/dt_agent.py pack --out <app-repo> [--apply]
    python tools/dt_agent.py --tenant https://<id>.dev.apps.dynatracelabs.com docs
    python tools/dt_agent.py --tenant ... docs --apply [--only <substring>]
    python tools/dt_agent.py --tenant ... status

`check` and `pack` need no network or token. `docs` and `status` read the token from the
DT_DEV_AGENT_TOKEN environment variable and never print it.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SKILLS_DIR = REPO_ROOT / "dynatrace-intelligence" / "skills"
DOC_API = "/platform/document/v1/documents"
DOC_TYPE = "ai-agent-resource"
TOKEN_VAR = "DT_DEV_AGENT_TOKEN"
REF_SUFFIXES = {".md", ".yaml", ".json"}
AGENT_DIR = REPO_ROOT / "dynatrace-intelligence" / "agents" / "demo-agent"
AI_API = "/platform-reserved/ai/v0.1"
MAX_SKILL_LINES = 150
LINK_RE = re.compile(r"\]\((references/[^)#\s]+)\)")


def parse_frontmatter(text: str) -> dict[str, str] | None:
    match = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not match:
        return None
    lines, fields, i = match.group(1).split("\n"), {}, 0
    while i < len(lines):
        key_match = re.match(r"([A-Za-z_-]+):\s*(.*)$", lines[i])
        i += 1
        if not key_match:
            continue
        key, value = key_match.groups()
        if value in ("", ">", "|", ">-", "|-"):
            block = []
            while i < len(lines) and (lines[i].startswith(" ") or not lines[i].strip()):
                block.append(lines[i].strip())
                i += 1
            value = " ".join(b for b in block if b)
        fields[key] = value.strip().strip("\"'")
    return fields


def check_skill(skill_dir: Path) -> list[str]:
    """The app's skill rules: layout, frontmatter, size, flat references, and resolvable links."""
    errors: list[str] = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [f"{skill_dir.name}: no SKILL.md"]
    text = skill_md.read_bytes().decode("utf-8").replace("\r\n", "\n")
    front = parse_frontmatter(text)
    if front is None:
        errors.append("SKILL.md: no frontmatter block")
        front = {}
    name, description = front.get("name", ""), front.get("description", "")
    if name != skill_dir.name:
        errors.append(f"frontmatter name '{name}' must equal the folder name '{skill_dir.name}'")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) or len(name) > 64 \
            or "anthropic" in name or "claude" in name:
        errors.append(f"name '{name}': lowercase letters, digits and single hyphens, at most 64 "
                      "characters, no reserved words")
    if not description or len(description) > 1024 or re.search(r"<[^>]+>", description):
        errors.append("description: required, at most 1024 characters, no XML tags")
    if text.count("\n") >= MAX_SKILL_LINES:
        errors.append(f"SKILL.md has {text.count(chr(10))} lines; keep it under {MAX_SKILL_LINES}")
    refs_dir = skill_dir / "references"
    refs = sorted(refs_dir.iterdir()) if refs_dir.is_dir() else []
    stems: dict[str, str] = {}
    for ref in refs:
        if ref.is_dir():
            errors.append(f"references/{ref.name}/: references must be flat, no subfolders")
        elif ref.suffix not in REF_SUFFIXES:
            errors.append(f"references/{ref.name}: unsupported type (use .md, .yaml or .json)")
        elif ref.stem in stems:
            errors.append(f"references/{ref.name}: same name as {stems[ref.stem]} once the type is dropped")
        else:
            stems[ref.stem] = ref.name
    for source in [skill_md, *(r for r in refs if r.is_file() and r.suffix == ".md")]:
        body = source.read_bytes().decode("utf-8")
        for link in LINK_RE.findall(body):
            target = Path(link)
            if target.suffix != ".md":
                errors.append(f"{source.name}: link {link} must end in .md")
            elif "/" in link[len("references/"):] or target.stem not in stems:
                errors.append(f"{source.name}: link {link} does not resolve to a flat reference")
    return errors


def check_template(template_path: Path = AGENT_DIR / "template.json",
                   instructions_path: Path = AGENT_DIR / "instructions.md") -> list[str]:
    """The agent's rules: least-privilege tools, the skill mount, and instructions that name the skill."""
    errors: list[str] = []
    try:
        template = json.loads(template_path.read_text(encoding="utf-8"))
        data = template["data"]
    except (OSError, ValueError, KeyError) as e:
        return [f"template.json: {e}"]
    if template.get("agent_type") != "deep-agent":
        errors.append("agent_type must be deep-agent (react-agent has no skills)")
    if not re.fullmatch(r"[A-Za-z0-9-]+", template.get("name", "")):
        errors.append("name must match [A-Za-z0-9-]+")
    for key in ("title", "description"):
        if not template.get(key):
            errors.append(f"{key} is required")
    if not data.get("llm"):
        errors.append("data.llm must pin a model")
    if data.get("enable_platform_control") is not False:
        errors.append("data.enable_platform_control must be false")
    for server, config in data.get("mcp_servers", {}).items():
        if config.get("tools") != ["execute-dql"]:
            errors.append(f"mcp server {server}: tools must be exactly ['execute-dql'] (least privilege)")
    if not data.get("mcp_servers"):
        errors.append("an mcp server is required, or the agent has no tools and cannot run DQL")
    skills = [d.name for d in skill_dirs()]
    mounted = [s for s in skills
               if data.get("resources", {}).get("/resources/documents/")
               == f"documents://name starts-with '/skills/{s}/'"]
    if not mounted:
        errors.append("data.resources must mount /resources/documents/ with the filter "
                      "documents://name starts-with '/skills/<skill>/' for an existing skill")
    for entry in data.get("skills", []):
        if entry not in [f"/resources/documents/skills/{s}/" for s in skills]:
            errors.append(f"data.skills entry {entry} is not a mounted skill directory")
    text = data.get("agent_instructions", {}).get("text")
    if text != "@file:instructions.md":
        errors.append("agent_instructions.text must be '@file:instructions.md'")
    elif not instructions_path.is_file():
        errors.append("instructions.md is missing")
    else:
        instructions = instructions_path.read_text(encoding="utf-8")
        for skill in mounted:
            if f"/resources/documents/skills/{skill}/SKILL.md" not in instructions:
                errors.append(f"instructions.md must name /resources/documents/skills/{skill}/SKILL.md")
    return errors


def skill_dirs(only: str | None = None) -> list[Path]:
    found = sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir())
    return [p for p in found if only in (None, p.name)]


def checked_skill_dirs(only: str | None = None) -> list[Path]:
    dirs = skill_dirs(only)
    if not dirs:
        sys.exit(f"error: no skill found under {SKILLS_DIR}")
    failed = False
    for skill in dirs:
        for error in check_skill(skill):
            print(f"  FAIL {skill.name}: {error}", file=sys.stderr)
            failed = True
    if failed:
        sys.exit("error: skill checks failed, nothing was done")
    return dirs


class ApiError(Exception):
    def __init__(self, status: int, body: str):
        super().__init__(f"HTTP {status}: {body[:300]}")
        self.status = status
        self.body = body


class Tenant:
    def __init__(self, host: str, token_var: str = TOKEN_VAR):
        token = os.environ.get(token_var)
        if not token:
            sys.exit(f"error: {token_var} is not set")
        self.host = host.rstrip("/")
        self._token = token

    def request(self, method: str, path: str, body: bytes | None = None,
                content_type: str | None = None, timeout: int = 60) -> tuple[int, bytes]:
        headers = {"Authorization": f"Bearer {self._token}", "Accept": "*/*"}
        if content_type:
            headers["Content-Type"] = content_type
        req = urllib.request.Request(self.host + path, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            raise ApiError(e.code, e.read().decode("utf-8", "replace")) from None

    def json(self, method: str, path: str, **kw):
        status, data = self.request(method, path, **kw)
        return json.loads(data) if data else {}


def multipart(fields: dict[str, str], filename: str, content: bytes, ctype: str) -> tuple[bytes, str]:
    boundary = "----dtagent" + uuid.uuid4().hex
    parts = [
        f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
        for k, v in fields.items()
    ]
    parts.append(
        (f'--{boundary}\r\nContent-Disposition: form-data; name="content"; '
         f'filename="{filename}"\r\nContent-Type: {ctype}\r\n\r\n').encode() + content + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def local_documents() -> dict[str, bytes]:
    """Map document name -> content for every skill file, named the way dt-app deploy names them."""
    docs: dict[str, bytes] = {}
    for skill_dir in checked_skill_dirs():
        docs[f"/skills/{skill_dir.name}/SKILL.md"] = normalize(skill_dir / "SKILL.md")
        refs = skill_dir / "references"
        for ref in sorted(refs.iterdir()) if refs.is_dir() else []:
            docs[f"/skills/{skill_dir.name}/references/{ref.stem}.md"] = normalize(ref)
    return docs


def normalize(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n")


def remote_documents(tenant: Tenant, prefixes: list[str]) -> dict[str, dict]:
    query = urllib.parse.urlencode({"filter": f"type == '{DOC_TYPE}'", "page-size": 500})
    found = tenant.json("GET", f"{DOC_API}?{query}").get("documents", [])
    return {d["name"]: d for d in found if any(d["name"].startswith(p) for p in prefixes)}


def remote_content(tenant: Tenant, doc_id: str) -> bytes:
    return tenant.request("GET", f"{DOC_API}/{doc_id}/content")[1]


def upload(tenant: Tenant, name: str, content: bytes, existing: dict | None) -> str:
    """Create or update one document. Tries text/markdown, then application/json (what existing docs report)."""
    last: ApiError | None = None
    for ctype in ("text/markdown", "application/json"):
        try:
            if existing is None:
                fields = {"name": name, "type": DOC_TYPE, "isPrivate": "false"}
                body, mp = multipart(fields, name.rsplit("/", 1)[-1], content, ctype)
                tenant.request("POST", DOC_API, body, mp)
                return "created"
            body, mp = multipart({}, name.rsplit("/", 1)[-1], content, ctype)
            version = existing["version"]
            tenant.request("PATCH", f"{DOC_API}/{existing['id']}?optimistic-locking-version={version}", body, mp)
            return "updated"
        except ApiError as e:
            last = e
            if e.status not in (400, 415):
                break
    raise last  # type: ignore[misc]


def cmd_docs(tenant: Tenant, args: argparse.Namespace) -> int:
    local = local_documents()
    prefixes = sorted({"/skills/" + n.split("/")[2] + "/" for n in local})
    remote = remote_documents(tenant, prefixes)
    todo: list[tuple[str, str]] = []
    for name, content in local.items():
        if args.only and args.only not in name:
            continue
        doc = remote.get(name)
        if doc is None:
            todo.append(("+", name))
        elif remote_content(tenant, doc["id"]).replace(b"\r\n", b"\n") != content:
            todo.append(("~", name))
        else:
            todo.append(("=", name))
    for name in sorted(set(remote) - set(local)):
        todo.append(("?", name))
    for mark, name in todo:
        print(f"  {mark} {name}")
    changes = [(m, n) for m, n in todo if m in "+~"]
    print(f"\n{sum(m == '+' for m, _ in todo)} to create, {sum(m == '~' for m, _ in todo)} to update, "
          f"{sum(m == '=' for m, _ in todo)} unchanged, {sum(m == '?' for m, _ in todo)} on the tenant "
          f"but not in the repo (left alone)")
    if not args.apply:
        print("dry run: nothing written (use --apply)")
        return 0
    for mark, name in changes:
        try:
            print(f"  {upload(tenant, name, local[name], remote.get(name))}: {name}")
        except ApiError as e:
            print(f"  FAILED {name}: {e}", file=sys.stderr)
            return 1
    return 0


def cmd_status(tenant: Tenant, args: argparse.Namespace) -> int:
    local = local_documents()
    prefixes = sorted({"/skills/" + n.split("/")[2] + "/" for n in local})
    remote = remote_documents(tenant, prefixes)
    for name in sorted(remote):
        d = remote[name]
        print(f"  {name}  v{d.get('version')}  private={d.get('isPrivate')}  app={d.get('originAppId')}")
    print(f"\n{len(remote)} skill documents on the tenant, {len(local)} in the repo")
    name = json.loads((AGENT_DIR / "template.json").read_text(encoding="utf-8"))["name"]
    deployed = deployed_template(tenant, name)
    if deployed is None:
        print(f"{name}: not deployed")
    else:
        text = deployed.get("data", {}).get("agent_instructions", {}).get("text", "")
        build = text.rsplit("Build: ", 1)[-1].strip() if "Build: " in text else "unknown"
        print(f"{name}: v{deployed.get('version')}, build {build}")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    dirs = skill_dirs()
    if not dirs:
        sys.exit(f"error: no skill found under {SKILLS_DIR}")
    failed = False
    for skill in dirs:
        errors = check_skill(skill)
        for error in errors:
            print(f"  FAIL {skill.name}: {error}")
        failed = failed or bool(errors)
        print(f"  {'FAIL' if errors else 'ok  '} {skill.name}")
    template_errors = check_template()
    for error in template_errors:
        print(f"  FAIL demo-agent template: {error}")
    print(f"  {'FAIL' if template_errors else 'ok  '} demo-agent template")
    return 1 if failed or template_errors else 0


def cmd_pack(args: argparse.Namespace) -> int:
    """Copy the checked skill folder into an app repo's dynatrace-intelligence/skills/ tree."""
    out = Path(args.out)
    if not out.is_dir():
        sys.exit(f"error: {out} is not a directory")
    if not (out / "app.config.json").is_file():
        print(f"  warning: {out} has no app.config.json; is it the app repo root?", file=sys.stderr)
    counts = {"+": 0, "~": 0, "=": 0, "?": 0}
    for skill in checked_skill_dirs():
        source = {p.relative_to(skill).as_posix(): normalize(p) for p in skill.rglob("*") if p.is_file()}
        dest = out / "dynatrace-intelligence" / "skills" / skill.name
        present = ({p.relative_to(dest).as_posix(): p for p in dest.rglob("*") if p.is_file()}
                   if dest.is_dir() else {})
        for rel, content in sorted(source.items()):
            if rel not in present:
                mark = "+"
            elif normalize(present[rel]) != content:
                mark = "~"
            else:
                mark = "="
            counts[mark] += 1
            print(f"  {mark} {skill.name}/{rel}")
            if args.apply and mark in "+~":
                target = dest / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
        for rel in sorted(set(present) - set(source)):
            counts["?"] += 1
            print(f"  ? {skill.name}/{rel}  (only in the app; kept)")
    print(f"\n{counts['+']} new, {counts['~']} changed, {counts['=']} unchanged, "
          f"{counts['?']} only in the app (kept)")
    drift = counts["+"] + counts["~"]
    if not args.apply:
        print("dry run: nothing written (use --apply)")
        return 1 if args.check and drift else 0
    return 0


def build_stamp() -> str:
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True).stdout.strip()
    dirty = git("status", "--porcelain", "--", "dynatrace-intelligence")
    return (git("rev-parse", "--short", "HEAD") or "unknown") + ("-dirty" if dirty else "")


def render_template() -> dict:
    """The API payload: template.json with the instructions file inlined and a build stamp."""
    template = json.loads((AGENT_DIR / "template.json").read_text(encoding="utf-8"))
    instructions = (AGENT_DIR / "instructions.md").read_text(encoding="utf-8").replace("\r\n", "\n").strip()
    if template["data"]["agent_instructions"].get("text") != "@file:instructions.md":
        sys.exit("error: template.json must carry agent_instructions.text = '@file:instructions.md'")
    template["data"]["agent_instructions"]["text"] = f"{instructions}\n\nBuild: {build_stamp()}"
    return template


def deployed_template(tenant: Tenant, name: str) -> dict | None:
    try:
        return tenant.json("GET", f"{AI_API}/operator/agent-templates/{name}")
    except ApiError as e:
        if e.status == 404:
            return None
        raise


def cmd_render(args: argparse.Namespace) -> int:
    print(json.dumps(render_template(), indent=2, ensure_ascii=False))
    return 0


def cmd_template(tenant: Tenant, args: argparse.Namespace) -> int:
    errors = check_template()
    if errors:
        sys.exit("error: template checks failed, nothing was done:\n  " + "\n  ".join(errors))
    wanted = render_template()
    name, data = wanted["name"], wanted["data"]
    current = deployed_template(tenant, name)
    tools = {s: v.get("tools", "all tools") for s, v in data.get("mcp_servers", {}).items()}
    print(f"  template {name}: {wanted['agent_type']}, model {data['llm']}, tools {tools}")
    print(f"  mounts {list(data['resources'])}\n  skills {data['skills']}")
    changed = current is None
    if current is None:
        print(f"  + {name} does not exist on the tenant: would create it")
    else:
        for key in ("title", "description"):
            if current.get(key) != wanted[key]:
                changed = True
                print(f"  ~ {key}")
        for key in sorted(set(data) | set(current.get("data", {}))):
            if current.get("data", {}).get(key) != data.get(key):
                changed = True
                print(f"  ~ data.{key}")
                old = str(current.get("data", {}).get(key, "")).splitlines()
                new = str(data.get(key, "")).splitlines()
                for line in list(difflib.unified_diff(old, new, "deployed", "local", lineterm="", n=0))[:12]:
                    print(f"      {line}")
        if not changed:
            print(f"  = {name} v{current.get('version')} is up to date")
    if not changed:
        return 0
    if not args.apply:
        print("dry run: nothing written (use --apply)")
        return 0
    path = f"{AI_API}/operator/agent-templates"
    if current is None:
        tenant.request("POST", path, json.dumps(wanted).encode(), "application/json")
    else:
        body = json.dumps({**wanted, "version": current["version"]}).encode()
        try:
            tenant.request("PUT", f"{path}/{name}", body, "application/json")
        except ApiError as e:
            if e.status != 405:
                raise
            tenant.request("PATCH", f"{path}/{name}", body, "application/json")
    after = deployed_template(tenant, name)
    print(f"  deployed {name} v{after.get('version') if after else '?'}")
    return 0


def invoke_agent(tenant: Tenant, agent: str, text: str, conversation: str | None = None,
                 timeout: int = 480) -> tuple[str | None, list[dict]]:
    """Send one message; returns (conversation_id, the event stream)."""
    body = {"agent": agent, "conversation_id": conversation or "create", "text": text}
    _, data = tenant.request("POST", f"{AI_API}/operator/agents:invoke", json.dumps(body).encode(),
                             "application/json", timeout=timeout)
    events = json.loads(data)
    started = next((e["conversation_id"] for e in events if e.get("type") == "conversation_started"), None)
    return conversation or started, events


def cmd_invoke(tenant: Tenant, args: argparse.Namespace) -> int:
    _, events = invoke_agent(tenant, args.agent, args.text, args.conversation, args.timeout)
    if args.raw:
        print(json.dumps(events, indent=2, ensure_ascii=False)[: args.max_chars])
        return 0
    for event in events:
        kind = event.get("type")
        text = " ".join(c.get("text", "") for c in event.get("content") or [] if isinstance(c, dict))
        if kind == "conversation_started":
            print(f"conversation {event.get('conversation_id')}")
        elif kind == "tool_invocation":
            call = event.get("tool_call", {})
            print(f"-> {call.get('name')} {json.dumps(call.get('args'), ensure_ascii=False)[:300]}")
        elif kind == "tool_response":
            flag = "ERROR " if event.get("is_error") else ""
            print(f"<- {flag}{text[:400]}")
        elif kind == "agent_response" and text:
            print(f"\n{text}")
        elif kind in ("error", "interaction_failed"):
            print(f"!! {json.dumps(event, ensure_ascii=False)[:500]}")
    return 0


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--tenant", help="https://<id>.dev.apps.dynatracelabs.com (docs, status)")
    parser.add_argument("--token-var", default=TOKEN_VAR,
                        help=f"environment variable holding the token (default {TOKEN_VAR})")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="validate the skill against the app's rules (offline)")
    pack = sub.add_parser("pack", help="copy the checked skill into an app repo (offline)")
    pack.add_argument("--out", required=True, help="path to the app repo root")
    pack.add_argument("--apply", action="store_true", help="write the files (default: dry run)")
    pack.add_argument("--check", action="store_true", help="dry run: exit 1 if the app copy has drifted")
    docs = sub.add_parser("docs", help="plan or apply the skill document upload")
    docs.add_argument("--apply", action="store_true", help="write to the tenant (default: dry run)")
    docs.add_argument("--only", help="only documents whose name contains this text")
    sub.add_parser("status", help="list the skill documents on the tenant (read-only)")
    sub.add_parser("render", help="print the demo-agent template payload (offline)")
    template = sub.add_parser("template", help="plan or apply the demo-agent template")
    template.add_argument("--apply", action="store_true", help="create or update it (default: dry run)")
    invoke = sub.add_parser("invoke", help="send one message to an agent (smoke test)")
    invoke.add_argument("text")
    invoke.add_argument("--agent", default="demo-agent")
    invoke.add_argument("--conversation", help="conversation_id to continue (default: start a new one)")
    invoke.add_argument("--timeout", type=int, default=300)
    invoke.add_argument("--max-chars", type=int, default=6000, help="limit for --raw output")
    invoke.add_argument("--raw", action="store_true", help="print the raw event stream as JSON")
    args = parser.parse_args(argv[1:])
    offline = {"check": cmd_check, "pack": cmd_pack, "render": cmd_render}
    if args.cmd in offline:
        return offline[args.cmd](args)
    if not args.tenant:
        parser.error(f"--tenant is required for {args.cmd}")
    online = {"docs": cmd_docs, "status": cmd_status, "template": cmd_template, "invoke": cmd_invoke}
    return online[args.cmd](Tenant(args.tenant, args.token_var), args)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
