"""Produce real API responses for browser-consumer regression tests."""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from tests.test_fairness_engine import csv_bytes, fixture_rows

with tempfile.TemporaryDirectory() as folder:
    root = Path(folder)
    dataset = root / "train.csv"
    dataset.write_bytes(csv_bytes(fixture_rows()))
    app = create_app(dataset, root / "state", testing=True)
    client = app.test_client()
    result = {
        path: client.get(path).get_json()
        for path in [
            "/api/workspace",
            "/api/fairness/audit?scope=validation&intersectional=false",
            "/api/fairness/audit?scope=current",
            "/api/shortlist?page=1&per_page=20&filter=all&search=",
            "/api/evaluation?scope=validation",
            "/api/history",
        ]
    }
    result["experiment"] = client.post(
        "/api/fairness/ablate",
        json={"attribute_to_drop": "experience", "scope": "validation"},
    ).get_json()
    result["explanation"] = client.get(
        "/api/explain/"
        + result["/api/shortlist?page=1&per_page=20&filter=all&search="]["applicants"][
            0
        ]["enrollee_id"]
    ).get_json()
    print(json.dumps(result, allow_nan=False))
