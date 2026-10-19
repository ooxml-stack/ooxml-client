"""Agent distribution commands: MCP registration and skill installation.

The client is the public, MIT-licensed surface of the product. These helpers
only write agent configuration and copy the bundled skill; they never import
the runtime or touch document content.
"""

import shutil
import subprocess
import sys
from importlib.resources import files
from pathlib import Path

from .errors import ClientError

CODEX_CONFIG = Path.home() / ".codex" / "config.toml"
CLAUDE_SKILLS = Path.home() / ".claude" / "skills"
LICENSE_DIR = Path.home() / ".ooxml"
MCP_ARGS = ["mcp", "--profile", "core"]
SERVER_NAME = "ooxml"


def launcher():
    """Return the command prefix that runs this client."""
    found = shutil.which(SERVER_NAME)
    if found:
        return [found]
    return [sys.executable, "-m", "ooxml_client"]


def _mcp_command(runtime_python=None):
    """The `ooxml mcp` invocation, resolving the runtime when one is known."""
    parts = launcher()
    if runtime_python:
        parts.append(f"--runtime-python={runtime_python}")
    return parts + MCP_ARGS


def _skill_resource():
    return files("ooxml_client.skills") / "ooxml" / "SKILL.md"


def _exists_error(kind, message):
    """Collision and input errors exit 2, matching the CLI convention."""
    return ValueError(f"{kind}: {message}")


def register(agent, scope="local", force=False, dry_run=False, runtime_python=None):
    """Write MCP registration for ``claude`` or ``codex`` and return its result."""
    if agent == "claude":
        return register_claude(scope=scope, force=force, dry_run=dry_run, runtime_python=runtime_python)
    if agent == "codex":
        return register_codex(force=force, dry_run=dry_run, runtime_python=runtime_python)
    raise _exists_error("agent_unknown", f"Unknown agent {agent!r}; expected 'claude' or 'codex'.")


def _claude_binary():
    found = shutil.which("claude")
    if not found:
        raise _exists_error("agent_not_found", "The claude executable was not found on PATH.")
    return found


def _claude_listed(claude):
    """Best-effort duplicate check before touching the agent configuration.

    Matches only the exact server name (``ooxml`` or ``ooxml:``) so a
    differently named server such as ``ooxml-foo`` never causes a refusal.
    """
    try:
        result = subprocess.run([claude, "mcp", "list"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return False
    for line in result.stdout.splitlines():
        tokens = line.strip().split()
        if tokens and tokens[0].rstrip(":") == SERVER_NAME:
            return True
    return False


def register_claude(scope="local", force=False, dry_run=False, runtime_python=None):
    claude = _claude_binary()
    command = _claude_add_command(claude, scope, runtime_python)
    if not force and _claude_listed(claude):
        raise _exists_error(
            "server_exists", "An 'ooxml' MCP server already exists; use --force to replace it."
        )
    if dry_run:
        return {"agent": "claude", "scope": scope, "command": command, "dry_run": True}
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ClientError("register_failed", f"claude mcp add failed: {exc}") from exc
    return {
        "agent": "claude",
        "scope": scope,
        "command": command,
        "next": [
            "ooxml install-skill",
            "Say: analyze /abs/path/document.pptx",
        ],
    }


def _claude_add_command(claude, scope, runtime_python=None):
    return [
        claude,
        "mcp",
        "add",
        "--transport",
        "stdio",
        "--scope",
        scope,
        SERVER_NAME,
        "--",
        *_mcp_command(runtime_python),
    ]


def _codex_block(launcher_parts):
    command = launcher_parts[0]
    args = launcher_parts[1:]
    quoted = ", ".join(f'"{arg}"' for arg in args)
    # Backslash first, then quote: Windows launchers like C:\...\bin\ooxml.exe
    # must survive as valid TOML basic strings.
    escaped = command.replace("\\", "\\\\").replace('"', '\\"')
    return f"\n[mcp_servers.{SERVER_NAME}]\ncommand = \"{escaped}\"\nargs = [{quoted}]\n"


def _without_block(existing):
    """Drop an existing ooxml table so --force replaces rather than duplicates it."""
    marker = f"[mcp_servers.{SERVER_NAME}]"
    if marker not in existing:
        return existing
    out, skipping = [], False
    for line in existing.splitlines(keepends=True):
        if line.strip() == marker:
            skipping = True
            continue
        if skipping and not line.startswith("["):
            continue
        skipping = False
        out.append(line)
    return "".join(out)


def register_codex(force=False, dry_run=False, runtime_python=None):
    block = _codex_block(_mcp_command(runtime_python))
    path = CODEX_CONFIG
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if not force and f"[mcp_servers.{SERVER_NAME}]" in existing:
        raise _exists_error(
            "server_exists", f"'{SERVER_NAME}' is already configured in {path}; use --force to replace it."
        )
    if dry_run:
        return {"agent": "codex", "config": str(path), "block": block, "dry_run": True}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_without_block(existing) + block, encoding="utf-8")
    except OSError as exc:
        raise ClientError("register_failed", f"Could not update {path}: {exc}") from exc
    return {
        "agent": "codex",
        "config": str(path),
        "next": ["ooxml install-skill", "Say: analyze /abs/path/document.pptx"],
    }


def install_skill(target=None, force=False):
    """Copy the bundled SKILL.md where the agent looks for skills."""
    path = Path(target).expanduser() if target else CLAUDE_SKILLS / SERVER_NAME / "SKILL.md"
    if target is None and not CLAUDE_SKILLS.parent.exists():
        raise _exists_error(
            "skill_target_missing",
            "~/.claude/skills is missing; create it, or pass "
            "--target <project>/.claude/skills/ooxml/SKILL.md.",
        )
    if path.exists() and not force:
        raise _exists_error("skill_exists", f"{path} already exists; use --force to overwrite it.")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_skill_resource().read_text(encoding="utf-8"), encoding="utf-8")
    except OSError as exc:
        raise ClientError("skill_write_failed", f"Could not write {path}: {exc}") from exc
    return {"skill": str(path.resolve()), "next": ["The skill takes effect in your next agent session."]}


def activate(license_file):
    """Install a delivery license file (keyless copy; the gate verifies it)."""
    source = Path(license_file).expanduser()
    if not source.exists():
        raise _exists_error("license_missing", f"{source} does not exist.")
    target = LICENSE_DIR / "license.json"
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    except OSError as exc:
        raise ClientError("license_write_failed", f"Could not write {target}: {exc}") from exc
    return {
        "license": str(target.resolve()),
        "next": ["The license gate allows serving on the next command."],
    }
