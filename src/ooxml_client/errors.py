"""Client transport failures and unchanged runtime operation errors."""


class ClientError(Exception):
    """A transport-level failure the client raises before the runtime decides.

    ``kind`` is a stable machine-readable category (for example
    ``runtime_unavailable`` or ``request_too_large``); ``details`` carries the
    runtime's structured error when one exists.
    """

    def __init__(self, kind, message, *, details=None):
        super().__init__(message)
        self.kind = kind
        self.details = details

    def as_dict(self):
        """Return the JSON-ready form used by the CLI and by callers."""
        result = {"kind": self.kind, "message": str(self)}
        if self.details is not None:
            result["details"] = self.details
        return result


class OperationError(ClientError):
    """The runtime rejected a well-formed operation; its error is preserved."""

    def __init__(self, error):
        super().__init__("runtime_error", error.get("message", "The runtime rejected the operation."))
        self.error = error

    def as_dict(self):
        """Return the JSON-ready form, keeping the runtime error unchanged."""
        return {"kind": self.kind, "runtime_error": self.error}
