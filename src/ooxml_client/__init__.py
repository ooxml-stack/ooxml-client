"""Public client; Office execution belongs to the separately installed runtime."""

from .client import Client
from .errors import ClientError, OperationError

__all__ = ["Client", "ClientError", "OperationError"]
__version__ = "0.1.0"
