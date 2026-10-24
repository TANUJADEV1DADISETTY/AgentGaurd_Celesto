"""
Tests for AgentGuard-Celesto report files, schemas, and API functionality.
Supports standard unittest and pytest.
"""
import json
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

from api.main import app

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"


class TestAgentGuard(unittest.TestCase):

    def test_all_reports_exist(self):
        required_files = [
            "problem.json",
            "capabilities.json",
            "lifecycle.json",
            "failure_policy.json",
            "reliability.json",
            "failure_trace.jsonl",
            "containment.json",
            "concurrency.json",
            "postmortem.md",
        ]
        for fname in required_files:
            fpath = REPORTS_DIR / fname
            self.assertTrue(fpath.exists(), f"Missing required report file: {fname}")

    def test_reliability_metrics(self):
        fpath = REPORTS_DIR / "reliability.json"
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertGreaterEqual(data.get("run_count", 0), 20, f"Expected >= 20 runs, got {data.get('run_count')}")
        self.assertIn("runs", data)
        self.assertGreaterEqual(len(data["runs"]), 20)

    def test_failure_policy_choice(self):
        fpath = REPORTS_DIR / "failure_policy.json"
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["policy"], "rollback")
        self.assertEqual(data["failed_step"], 7)
        self.assertEqual(data["total_steps"], 10)

    def test_containment_results(self):
        fpath = REPORTS_DIR / "containment.json"
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertTrue(data.get("blocked", False))
        self.assertTrue(data.get("host_untouched", False))

    def test_api_health_and_runs(self):
        client = TestClient(app)
        # Health check
        res_health = client.get("/health")
        self.assertEqual(res_health.status_code, 200)
        self.assertEqual(res_health.json()["status"], "ok")

        # List runs
        res_runs = client.get("/api/runs")
        self.assertEqual(res_runs.status_code, 200)
        runs = res_runs.json()
        self.assertIsInstance(runs, list)
        self.assertGreaterEqual(len(runs), 1)

        # Create run
        new_run = {
            "run_id": "test-unit-run-001",
            "sandbox_name": "sbx-unittest01",
            "problem_id": "grading-task",
            "state": "running",
            "execution_target": "celesto_sandbox",
        }
        res_create = client.post("/api/runs", json=new_run)
        self.assertEqual(res_create.status_code, 201)
        self.assertEqual(res_create.json()["run_id"], "test-unit-run-001")


if __name__ == "__main__":
    unittest.main()
