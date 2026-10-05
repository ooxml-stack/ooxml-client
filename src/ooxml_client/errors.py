"""Client transport failures and unchanged runtime operation errors."""


class ClientError(Exception):
    def __init__(self, kind, message, *, details=None):
        super().__init__(message)
        self.kind = kind
        self.details = details

    def as_dict(self):
        result = {"kind": self.kind, "message": str(self)}
        if self.details is not None:
            result["details"] = self.details
        return result


class OperationError(ClientError):
    def __init__(self, error):
        super().__init__("runtime_error", error.get("message", "The runtime rejected the operation."))
        self.error = error

    def as_dict(self):
        return {"kind": self.kind, "runtime_error": self.error}
