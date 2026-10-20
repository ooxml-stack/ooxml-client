"""Redacted activation and serving status tests."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ooxml_client.status import status


class StatusTests(unittest.TestCase):
    def test_missing_license_is_inactive_without_launching_runtime(self):
        with tempfile.TemporaryDirectory() as folder, patch("ooxml_client.status.Client") as client:
            result = status(license_dir=folder)
        self.assertFalse(result["installed"])
        self.assertEqual(result["serving"], "inactive")
        client.assert_not_called()

    def test_active_runtime_proves_serving(self):
        with tempfile.TemporaryDirectory() as folder, patch("ooxml_client.status.Client") as client:
            license_path = Path(folder) / "license.json"
            license_path.write_text(
                json.dumps(
                    {"license_id": "public-test", "artifact_id": "artifact-1", "expiry": "2099-01-01"}
                ),
                encoding="utf-8",
            )
            client.return_value.man.return_value = {
                "runtime_version": "0.1.50",
                "build": {"id": "sha256:abc", "status": "measured"},
            }
            result = status(license_dir=folder, runtime_executable="/abs/ooxml-engine")
        self.assertTrue(result["installed"])
        self.assertEqual(result["serving"], "active")
        self.assertEqual(result["artifact_id"], "artifact-1")
        self.assertEqual(result["runtime_version"], "0.1.50")
        client.assert_called_once_with(
            None,
            runtime_executable="/abs/ooxml-engine",
            timeout=120,
        )
