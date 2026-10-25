"""Command-line access to local Engine operations and its existing MCP server."""

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__, distribute
from .client import COMMANDS, Client
from .transport import _invalid_constant
from .errors import ClientError
from .probe import run_probe
from .runtime import runtime_command
from .status import status as runtime_status


def _parser():
    parser = argparse.ArgumentParser(
        description="Office operations using a separately installed local Engine."
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--runtime-python", help="Absolute Python executable path inside the licensed runtime"
    )
    parser.add_argument("--runtime-executable", help="Absolute path to the native ooxml-engine executable")
    parser.add_argument(
        "--timeout", type=float, default=120, help="Per-operation timeout in seconds (default: 120)"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name in COMMANDS:
        command = commands.add_parser(name, help=f"Call ooxml_{name} with the runtime's JSON parameters")
        inputs = command.add_mutually_exclusive_group()
        inputs.add_argument("--params", default=None, help="JSON object of runtime parameters")
        inputs.add_argument("--params-file", type=Path, help="Read a UTF-8 JSON parameter object from a file")
    commands.choices["validate"].add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 when the validation result reports failure",
    )
    mcp = commands.add_parser("mcp", help="Run the installed Engine's MCP server over stdio")
    mcp.add_argument("--profile", choices=["core", "workflow"], default="core")
    probe = commands.add_parser("probe", help="Probe an MCP profile through the packaged runtime")
    probe.add_argument("--profile", choices=["core", "workflow", "pdf"], required=True)
    probe.add_argument("--sample", type=Path, help="Workflow probe source document")
    register = commands.add_parser("register", help="Register the MCP server with an agent application")
    register.add_argument("agent", choices=["claude", "codex"])
    register.add_argument("--scope", choices=["local", "project"], default="local", help="claude only")
    register.add_argument("--force", action="store_true", help="Replace an existing ooxml registration")
    register.add_argument("--dry-run", action="store_true", help="Print the write without performing it")
    skill = commands.add_parser(
        "install-skill", help="Copy the bundled SKILL.md where your agent discovers skills"
    )
    skill.add_argument("--target", type=Path, default=None, help="Explicit SKILL.md path")
    skill.add_argument("--force", action="store_true", help="Overwrite an existing SKILL.md")
    act = commands.add_parser("activate", help="Install a delivery license file")
    act.add_argument("--license", type=Path, required=True, help="Path to the license file")
    commands.add_parser("status", help="Report activation and real runtime serving status")
    return parser


def _params(args):
    raw = args.params_file.read_text(encoding="utf-8") if args.params_file else args.params
    result = {} if raw is None else json.loads(raw, parse_constant=_invalid_constant)
    if not isinstance(result, dict):
        raise ValueError("Parameters must be a JSON object.")
    return result


def _dispatch(args):
    if args.command == "register":
        return distribute.register(
            args.agent,
            scope=args.scope,
            force=args.force,
            dry_run=args.dry_run,
            runtime_python=args.runtime_python or os.environ.get("OOXML_RUNTIME_PYTHON"),
            runtime_executable=args.runtime_executable or os.environ.get("OOXML_RUNTIME_EXECUTABLE"),
        )
    if args.command == "install-skill":
        return distribute.install_skill(args.target, force=args.force)
    if args.command == "activate":
        return distribute.activate(args.license)
    if args.command == "probe":
        return run_probe(
            args.profile,
            sample=str(args.sample) if args.sample else None,
            runtime_python=args.runtime_python,
            runtime_executable=args.runtime_executable,
        )
    if args.command == "status":
        return runtime_status(args.runtime_python, args.runtime_executable, timeout=args.timeout)
    client = Client(
        args.runtime_python,
        runtime_executable=args.runtime_executable,
        timeout=args.timeout,
    )
    return client.call("ooxml_" + args.command, _params(args))


def main(argv=None):
    """Run the command-line entry point and return its exit status."""

    args = _parser().parse_args(argv)
    try:
        if args.command == "mcp":
            command = runtime_command(args.runtime_python, args.runtime_executable)
            os.environ["OOXML_MCP_PROFILE"] = args.profile
            os.execv(command[0], command)
        result = _dispatch(args)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        if (
            args.command == "validate"
            and args.strict
            and (result.get("passed") is False or result.get("status") == "failed")
        ):
            print("Validation reported failure.", file=sys.stderr)
            return 1
        return 0
    except ClientError as exc:
        print(json.dumps({"error": exc.as_dict()}), file=sys.stderr)
        return 1
    except (ValueError, OSError) as exc:
        print(json.dumps({"error": {"kind": "client_input", "message": str(exc)}}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
