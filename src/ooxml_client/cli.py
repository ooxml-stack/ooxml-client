"""Command-line access to local Engine operations and its existing MCP server."""

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__
from .client import COMMANDS, Client
from .transport import _invalid_constant
from .errors import ClientError
from .runtime import runtime_command


def _parser():
    parser = argparse.ArgumentParser(
        description="Office operations using a separately installed local Engine."
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--runtime-python", help="Absolute Python executable path inside the licensed runtime"
    )
    parser.add_argument(
        "--timeout", type=float, default=120, help="Per-operation timeout in seconds (default: 120)"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name in COMMANDS:
        command = commands.add_parser(name, help=f"Call ooxml_{name} with the runtime's JSON parameters")
        inputs = command.add_mutually_exclusive_group()
        inputs.add_argument("--params", default=None, help="JSON object of runtime parameters")
        inputs.add_argument("--params-file", type=Path, help="Read a UTF-8 JSON parameter object from a file")
    mcp = commands.add_parser("mcp", help="Run the installed Engine's MCP server over stdio")
    mcp.add_argument("--profile", choices=["core", "workflow"], default="core")
    return parser


def _params(args):
    raw = args.params_file.read_text(encoding="utf-8") if args.params_file else args.params
    result = {} if raw is None else json.loads(raw, parse_constant=_invalid_constant)
    if not isinstance(result, dict):
        raise ValueError("Parameters must be a JSON object.")
    return result


def main(argv=None):
    """Run the command-line entry point and return its exit status."""

    args = _parser().parse_args(argv)
    try:
        if args.command == "mcp":
            command = runtime_command(args.runtime_python)
            os.environ["OOXML_MCP_PROFILE"] = args.profile
            os.execv(command[0], command)
        client = Client(args.runtime_python, timeout=args.timeout)
        result = client.call("ooxml_" + args.command, _params(args))
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except ClientError as exc:
        print(json.dumps({"error": exc.as_dict()}), file=sys.stderr)
        return 1
    except (ValueError, OSError) as exc:
        print(json.dumps({"error": {"kind": "client_input", "message": str(exc)}}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
