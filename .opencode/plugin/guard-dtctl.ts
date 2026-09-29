/**
 * OpenCode plugin: guard-dtctl
 *
 * Enforces read-only access to the Dynatrace Playground.
 * Shells out to tools/guard_dtctl.py — the same script used by Claude Code's
 * PreToolUse hook — so the deny logic lives in one place, tested once.
 *
 * NOTE: This plugin was written against OpenCode's plugin API as documented in
 * training data. If the API has changed, verify against the current opencode
 * release before merging. The key points to check:
 *   - Plugin export shape (default export vs named export)
 *   - Hook name (tool.execute.before vs hooks.before_tool)
 *   - How to block: throw an Error vs return { block: "reason" }
 *   - Tool name normalisation (OpenCode may use lowercase "bash")
 */

import { spawnSync } from "child_process";
import * as path from "path";
import * as url from "url";

const __dirname = path.dirname(url.fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..", "..");
const GUARD_SCRIPT = path.join(REPO_ROOT, "tools", "guard_dtctl.py");

function runGuard(toolName: string, command: string): void {
  const payload = JSON.stringify({
    tool_name: toolName,
    tool_input: { command },
  });

  const result = spawnSync("python", [GUARD_SCRIPT], {
    input: payload,
    encoding: "utf-8",
    timeout: 10_000,
  });

  if (result.status === 2) {
    const reason = result.stderr?.trim() || "Blocked: read-only Playground access policy.";
    throw new Error(reason);
  }
}

export default {
  tool: {
    execute: {
      before: (input: { tool: string; params: Record<string, unknown> }) => {
        // Normalise tool name: OpenCode may use lowercase "bash"
        const toolName = input.tool === "bash" ? "Bash" : input.tool;
        if (toolName !== "Bash") return;

        const command = (input.params.command as string | undefined) ?? "";
        runGuard(toolName, command);
      },
    },
  },
};
