"""Live API verification; does not apply experiments or replace applicant/training data."""

import argparse
import json
import urllib.request
from pathlib import Path


def verify(base, include_test=False):
    def get(path):
        with urllib.request.urlopen(base + path, timeout=180) as response:
            return json.load(response)

    def post(path, data):
        request = urllib.request.Request(
            base + path,
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.load(response)

    workspace = get("/api/workspace")
    version = workspace["model"]["model_version"]
    shortlist = get("/api/shortlist?per_page=5")
    audit = get("/api/fairness/audit?scope=current")
    assert (
        sum(g["selected_count"] for g in audit["audit"]["gender"]["groups"])
        == shortlist["total_shortlisted"]
    )
    candidate = shortlist["applicants"][0]
    explanation = get("/api/explain/" + candidate["enrollee_id"])
    assert abs(explanation["score"] - candidate["score"]) < 1e-10
    assert explanation["shortlisted"] == candidate["shortlisted"]
    models = get("/api/models/compare")["comparison"]
    assert len(models) == 5 and all(
        m["cv"]["k"] == 5 and m["evaluation_split"] == "validation" for m in models
    )
    dimensions = get("/api/models/dim_reduction_compare")["comparison"]
    assert (
        dimensions[1]["selected_features"]
        and 0 < dimensions[2]["explained_variance_ratio"] <= 1
    )
    attribute = workspace["model"]["active_columns"][0]
    experiment = post(
        "/api/fairness/ablate",
        {
            "attribute_to_drop": attribute,
            "scope": "validation",
            "protected_attribute": "gender",
        },
    )
    assert attribute in experiment["dropped_columns"]
    assert get("/api/workspace")["model"]["model_version"] == version
    assert {
        "selection_rate_gap",
        "recall_gap",
        "precision_gap",
        "accuracy",
        "auc",
    } <= set(experiment["delta"])
    costs = get("/api/settings/cost_matrix?capacity=100")
    assert costs["evaluation_split"] == "validation"
    result = {
        "model": workspace["model"],
        "split": {
            key: workspace["training"][key]
            for key in ["train_rows", "validation_rows", "test_rows"]
        },
        "pool_rows": workspace["pool"]["total_rows"],
        "validation": get("/api/evaluation?scope=validation")["metrics"],
        "models": [
            {
                k: m[k]
                for k in [
                    "model_name",
                    "accuracy",
                    "precision",
                    "recall",
                    "auc",
                    "average_precision",
                    "cv_spread",
                ]
            }
            for m in models
        ],
        "ablation": {
            k: experiment[k]
            for k in [
                "dropped_attribute",
                "before",
                "after",
                "delta",
                "scope",
                "policy",
            ]
        },
        "checks": "All API checks passed; no preview was applied.",
    }
    if include_test:
        result["test"] = get("/api/evaluation?scope=test")["metrics"]
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    parser.add_argument("--include-test", action="store_true")
    parser.add_argument("--output", default=".local/verification.json")
    args = parser.parse_args()
    result = verify(args.base_url, args.include_test)
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(result, indent=2, allow_nan=False), encoding="utf-8"
    )
    print(result["checks"])
    print("Result:", destination)
    print("Split:", result["split"])
    print("Validation accuracy:", round(result["validation"]["accuracy"] * 100, 2))
