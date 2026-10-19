"""Status contract and the pinned MCP contract shipped by the release."""

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

from ooxml_client import distribute
from ooxml_client.distribute import _installed_license


def test_contract_pin_matches_real_probes():
    contract = json.loads((REPO / "contracts/mcp-contract.json").read_text())
    assert contract["contract_version"] == "1"
    assert contract["local_only"] is True
    assert len(contract["default_mcp"]["tool_names"]) == contract["default_mcp"]["tool_count"] == 8
    assert len(contract["workflow_mcp"]["tool_names"]) == contract["workflow_mcp"]["tool_count"] == 10
    assert contract["default_mcp"]["tool_names"][0] == "ooxml_man"
    assert contract["workflow_mcp"]["tool_names"][0] == "ooxml_template_extract_submit"


def test_contract_required_ranges():
    contract = json.loads((REPO / "contracts/mcp-contract.json").read_text())
    assert contract["required_client_range"] == ">=0.1.50,<0.2.0"
    assert contract["required_runtime_artifact"].startswith("ooxml-operation-engine-")
    assert contract["license_states"] == ["license_missing", "installed", "active"]


def test_agent_install_contract_is_public_and_secret_free():
    text = (REPO / "AGENT-INSTALL.md").read_text()
    secret = re.compile(r"fly\.dev/[a-z0-9-]+/v1/install/[a-z0-9]+|PEM|BEGIN [A-Z ]*PRIVATE", re.IGNORECASE)
    assert not secret.search(text)
    for error in ("incompatible_platform", "download_failed", "checksum_failed", "install_failed",
                  "activation_failed", "mcp_configuration_failed", "skill_install_failed",
                  "smoke_test_failed", "success"):
        assert error in text
    assert "sudo" in text and "curl | sh" in text


def test_installed_license_reads_artifact(tmp_path):
    path = tmp_path / "license.json"
    assert _installed_license(path) == {}
    path.write_text(json.dumps({"artifact_id": "ooxml-operation-engine-b1181f42-macosx_14_0-arm64-b2"}))
    assert _installed_license(path)["artifact_id"].endswith("arm64-b2")
    path.write_text("{broken")
    assert _installed_license(path) == {}


def test_status_reports_installed_and_serving(tmp_path, monkeypatch):
    monkeypatch.setattr(distribute, "LICENSE_DIR", tmp_path)
    first = distribute.status(runtime_python="absent-python")
    assert first["installed"] is False and first["serving"] == "runtime_not_configured"
    (tmp_path / "license.json").write_text(json.dumps({"artifact_id": "ooxml-operation-engine-b1181f42-macosx_14_0-arm64-b2"}))
    second = distribute.status(runtime_python="absent-python")
    assert second["installed"] is True
    assert second["artifact_id"].endswith("arm64-b2")


def test_status_serving_active_with_configured_probe(tmp_path, monkeypatch):
    class ProbeClient:
        def __init__(self, runtime_python=None):
            self.runtime_python = runtime_python

        def call(self, method, params):
            assert method == "ooxml_man"
            return {"operations": []}

    monkeypatch.setattr(distribute, "LICENSE_DIR", tmp_path)
    monkeypatch.setattr(distribute, "Client", ProbeClient)
    answer = distribute.status()
    assert answer["serving"] == "active"
