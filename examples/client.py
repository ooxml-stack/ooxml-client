"""Small runnable example for ooxml-client."""

from ooxml_client import Client

client = Client(timeout=30)
print(client.call("ooxml_man", {"topic": "protocol-manifest"}))
