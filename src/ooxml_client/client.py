"""Stateless Office operations over the runtime's public MCP interface."""

import asyncio
import math
from typing import Any, Sequence

from .runtime import runtime_command
from .transport import check_params, exchange

COMMANDS = ("man", "inspect", "locate", "view", "apply", "validate", "diff", "render")


class Client:
    """One MCP session per core call; no automatic mutation retries."""

    def __init__(
        self,
        runtime_python: str | None = None,
        *,
        runtime_executable: str | None = None,
        command: Sequence[str] | None = None,
        timeout: float = 120,
    ) -> None:
        """Configure a native/Python runtime path or explicit MCP command."""
        if sum(value is not None for value in (runtime_python, runtime_executable, command)) > 1:
            raise ValueError("Choose only one of runtime_python, runtime_executable, or command.")
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout)
            or timeout <= 0
        ):
            raise ValueError("timeout must be a positive finite number.")
        if command is not None:
            if (
                not isinstance(command, (list, tuple))
                or not command
                or any(not isinstance(v, str) or not v for v in command)
            ):
                raise ValueError("command must be a nonempty list of nonempty arguments.")
        self.runtime_python = runtime_python
        self.runtime_executable = runtime_executable
        self.command = list(command) if command is not None else None
        self.timeout = timeout

    def call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        """Run one stateless core operation synchronously."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.acall(method, params))
        raise RuntimeError("Use await client.acall(method, params) inside an async application.")

    async def acall(self, method: str, params: dict[str, Any] | None = None) -> Any:
        """Run one stateless core operation asynchronously."""
        if method not in {"ooxml_" + name for name in COMMANDS}:
            raise ValueError("Only the eight stateless core operations are supported by this client.")
        params = {} if params is None else params
        check_params(params)
        command = self.command or runtime_command(self.runtime_python, self.runtime_executable)
        return await exchange(command, method, params, self.timeout)

    def man(self, **params: Any) -> Any:
        """Call the runtime protocol manifest operation."""
        return self.call("ooxml_man", params)

    def inspect(self, **params: Any) -> Any:
        """Call the runtime inspection operation."""
        return self.call("ooxml_inspect", params)

    def locate(self, **params: Any) -> Any:
        """Call the runtime locate operation."""
        return self.call("ooxml_locate", params)

    def view(self, **params: Any) -> Any:
        """Call the runtime view operation."""
        return self.call("ooxml_view", params)

    def apply(self, **params: Any) -> Any:
        """Call the runtime apply operation."""
        return self.call("ooxml_apply", params)

    def validate(self, **params: Any) -> Any:
        """Call the runtime validation operation."""
        return self.call("ooxml_validate", params)

    def diff(self, **params: Any) -> Any:
        """Call the runtime diff operation."""
        return self.call("ooxml_diff", params)

    def render(self, **params: Any) -> Any:
        """Call the runtime render operation."""
        return self.call("ooxml_render", params)
