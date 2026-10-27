"""Deterministic CSV validation. Learned transformations belong in fitted ML pipelines."""

import csv
import hashlib
import io
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

NUMERIC_COLUMNS = ["city_development_index", "training_hours", "experience"]
CATEGORICAL_COLUMNS = [
    "relevent_experience",
    "enrolled_university",
    "education_level",
    "major_discipline",
    "company_size",
    "company_type",
    "last_new_job",
]
MODEL_COLUMNS = NUMERIC_COLUMNS + CATEGORICAL_COLUMNS
REQUIRED_COLUMNS = NUMERIC_COLUMNS + ["education_level", "relevent_experience"]
AUDIT_LABELS = {
    "gender": "Gender",
    "age_band": "Age band",
    "institution": "Institution",
    "experience_band": "Experience band · demo",
    "education_group": "Education group · demo",
}
TARGET_DESCRIPTIONS = {
    "qualification": "Candidate qualification & interview shortlisting suitability",
    "job_change": "Candidate qualification & interview shortlisting suitability",
    "interview": "Interview progression outcome",
}
EXCLUDED_COLUMNS_STATEMENT = "Identifiers and target are never predictors. Gender, age and institution are audit-only. Model predictions evaluate applicant qualification for interview shortlisting. Experience bands and education groups do not establish actual age or institution fairness."
DATA_DICTIONARY = (
    [
        {
            "column": c,
            "type": "Numeric" if c in NUMERIC_COLUMNS else "Categorical",
            "role": "Predictor",
            "description": "Imputed and encoded inside each training fold.",
        }
        for c in MODEL_COLUMNS
    ]
    + [
        {"column": c, "type": "Categorical", "role": "Audit only", "description": label}
        for c, label in AUDIT_LABELS.items()
    ]
    + [
        {
            "column": "enrollee_id",
            "type": "Identifier",
            "role": "Tracking only",
            "description": "Unique in the pool; excluded from predictions.",
        },
        {
            "column": "target",
            "type": "Binary",
            "role": "Outcome",
            "description": "0/1, optional for inference; missing labels remain unknown.",
        },
    ]
)


def text(value):
    value = "" if value is None else str(value).strip()
    return "" if value.lower() in {"", "nan", "none", "null", "na", "n/a"} else value


def number(value, column, row_number="input"):
    value = text(value)
    if not value:
        return None
    if column == "experience" and value in {"<1", ">20"}:
        return 0.0 if value == "<1" else 21.0
    try:
        result = float(value)
    except (ValueError, TypeError):
        raise ValueError(
            f"Row {row_number}: {column} must be numeric or blank."
        ) from None
    lower = 14 if column == "age" else 0
    upper = {
        "city_development_index": 1,
        "training_hours": 100000,
        "experience": 80,
        "age": 120,
    }[column]
    if not math.isfinite(result) or not lower <= result <= upper:
        raise ValueError(
            f"Row {row_number}: {column} must be between {lower} and {upper}."
        )
    return result


def derive_experience_band(value):
    y = number(value, "experience")
    return (
        "Unknown"
        if y is None
        else "0-5"
        if y <= 5
        else "6-10"
        if y <= 10
        else "11-15"
        if y <= 15
        else "16+"
    )


# Compatibility name only; actual age is never derived from experience.
derive_age_band = derive_experience_band


def derive_institution(enrolled, education):
    """Compatibility helper: produces an education grouping, NOT institution pedigree."""
    if text(education) in {"Phd", "Masters"}:
        return "Postgraduate"
    if text(education) == "Graduate":
        return (
            "Graduate · enrolled"
            if text(enrolled) not in {"", "no_enrollment"}
            else "Graduate"
        )
    return (
        "School / non-degree"
        if text(education) in {"High School", "Primary School"}
        else "Unknown"
    )


def clean_row(raw, index=0):
    row = {str(k).strip(): text(v) for k, v in raw.items() if k is not None}
    if any(len(v) > 200 for v in row.values()):
        raise ValueError(f"Row {index + 2}: field exceeds 200 characters.")
    row["enrollee_id"] = row.get("enrollee_id") or f"applicant-{index + 1:06d}"
    for c in NUMERIC_COLUMNS:
        original = row.get(c, "")
        row[c] = number(original, c, index + 2)
        row["_prov_" + c] = (
            "missing_for_pipeline_imputation"
            if row[c] is None
            else "boundary_mapping"
            if original in {"<1", ">20"}
            else "observed"
        )
    for c in CATEGORICAL_COLUMNS + ["gender"]:
        original = row.get(c, "")
        row[c] = original or "Unknown"
        if c == "company_size":
            row[c] = row[c].replace("/", "-")
        row["_prov_" + c] = (
            "missing_as_unknown"
            if not original
            else "delimiter_standardized"
            if original != row[c]
            else "observed"
        )
    t = row.get("target", "")
    if t and t not in {"0", "1", "0.0", "1.0"}:
        raise ValueError(f"Row {index + 2}: target must be 0, 1 or blank.")
    row["target"] = int(float(t)) if t else None
    row["experience_band"] = derive_experience_band(row["experience"])
    row["education_group"] = derive_institution(
        row["enrolled_university"], row["education_level"]
    )
    if row.get("age"):
        age = number(row["age"], "age", index + 2)
        row["age"] = age
        row["age_band"] = row.get("age_band") or (
            "Under 25"
            if age < 25
            else "25-34"
            if age < 35
            else "35-44"
            if age < 45
            else "45-54"
            if age < 55
            else "55+"
        )
    row["age_band"] = row.get("age_band") or "Unknown"
    row["institution"] = row.get("institution") or "Unknown"
    return row


def validate(rows):
    checks = [
        ("Dataset contains records", bool(rows)),
        (
            "Identifiers are unique",
            len({r.get("enrollee_id") for r in rows}) == len(rows),
        ),
        ("Every record has an identifier", all(r.get("enrollee_id") for r in rows)),
        (
            "Outcomes are binary or unavailable",
            all(r.get("target") in (0, 1, None) for r in rows),
        ),
        (
            "City index is bounded or explicitly missing",
            all(
                r.get("city_development_index") is None
                or isinstance(r.get("city_development_index"), (int, float))
                and 0 <= r["city_development_index"] <= 1
                for r in rows
            ),
        ),
        (
            "Hours are nonnegative or explicitly missing",
            all(
                r.get("training_hours") is None
                or isinstance(r.get("training_hours"), (int, float))
                and r["training_hours"] >= 0
                for r in rows
            ),
        ),
        (
            "Experience has numeric range mappings",
            all(
                r.get("experience") is None
                or isinstance(r.get("experience"), (int, float))
                for r in rows
            ),
        ),
        (
            "Categorical missingness is explicit",
            all(all(r.get(c) for c in CATEGORICAL_COLUMNS + ["gender"]) for r in rows),
        ),
        (
            "Company-size delimiters are standardized",
            all("/" not in str(r.get("company_size", "")) for r in rows),
        ),
        (
            "Repair provenance is present",
            all("_prov_experience" in r and "_prov_gender" in r for r in rows),
        ),
        (
            "Experience grouping is separate from age",
            all(
                r.get("experience_band") in {"0-5", "6-10", "11-15", "16+", "Unknown"}
                for r in rows
            ),
        ),
    ]
    report = [{"assertion": s, "passed": bool(p)} for s, p in checks]
    return all(x["passed"] for x in report), report


class DataManager:
    def __init__(
        self,
        filepath=None,
        *,
        rows=None,
        training=True,
        target_kind="qualification",
        name=None,
    ):
        if target_kind not in TARGET_DESCRIPTIONS:
            raise ValueError(f"Outcome type must be one of: {list(TARGET_DESCRIPTIONS.keys())}")
        self.target_kind = target_kind
        self.name = name or (
            Path(filepath).name if filepath else "Uploaded applicant pool"
        )
        if rows is None:
            with open(filepath, encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                if len(headers) != len(set(c.strip() for c in headers)):
                    raise ValueError("Duplicate CSV column names.")
                rows = list(reader)
        self.headers = [str(c).strip() for c in rows[0]] if rows else []
        missing = sorted(set(REQUIRED_COLUMNS) - set(self.headers))
        if missing:
            raise ValueError("Missing required columns: " + ", ".join(missing))
        if not 1 <= len(rows) <= 100000:
            raise ValueError("Provide 1 to 100,000 rows.")
        if any(None in r for r in rows):
            raise ValueError("CSV has extra values; check delimiters and quoting.")
        self.raw_data = [{str(k).strip(): v for k, v in r.items()} for r in rows]
        self.processed_data = [clean_row(r, i) for i, r in enumerate(self.raw_data)]
        for column in ["gender", "age_band", "institution"]:
            if len({r[column] for r in self.processed_data}) > 500:
                raise ValueError(f"{column} exceeds 500 audit groups. Supply meaningful grouped values.")
        if training and sum(len({r[c] for r in self.processed_data}) for c in CATEGORICAL_COLUMNS) > 250:
            raise ValueError("Training exceeds 250 combined categorical values. Group high-cardinality predictors first.")
        passed, report = validate(self.processed_data)
        if not passed:
            raise ValueError(
                "Validation failed: "
                + "; ".join(r["assertion"] for r in report if not r["passed"])
            )
        raw_pass, raw_report = validate(self.raw_data)
        self.validation_results = {
            "cleaned_passed": passed,
            "cleaned_assertions": report,
            "raw_passed": raw_pass,
            "raw_assertions": raw_report,
        }
        self.dataset_id = hashlib.sha256(
            json.dumps(self.processed_data, sort_keys=True).encode()
        ).hexdigest()[:16]
        self.train_indices, self.validation_indices, self.test_indices = [], [], []
        if training:
            labels = [r["target"] for r in self.processed_data]
            counts = Counter(labels)
            if None in counts or set(counts) != {0, 1} or min(counts.values()) < 10:
                raise ValueError(
                    "Training requires complete 0/1 labels and at least 10 rows per class. Use applicant upload for unlabeled pools."
                )
            dev, test = train_test_split(
                np.arange(len(labels)), test_size=0.2, random_state=42, stratify=labels
            )
            train, val = train_test_split(
                dev, test_size=0.25, random_state=42, stratify=np.asarray(labels)[dev]
            )
            self.train_indices, self.validation_indices, self.test_indices = [
                sorted(x.tolist()) for x in (train, val, test)
            ]
        self.audit_attributes = [
            "gender",
            "age_band"
            if any(r["age_band"] != "Unknown" for r in self.processed_data)
            else "experience_band",
            "institution"
            if any(r["institution"] != "Unknown" for r in self.processed_data)
            else "education_group",
        ]
        self._audit_quality()

    @classmethod
    def from_csv(cls, content, **kwargs):
        try:
            decoded = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise ValueError("CSV must use UTF-8 encoding.") from None
        reader = csv.DictReader(io.StringIO(decoded, newline=""))
        if not reader.fieldnames or len(reader.fieldnames) != len(
            set(c.strip() for c in reader.fieldnames)
        ):
            raise ValueError("CSV needs a header with unique column names.")
        return cls(rows=list(reader), **kwargs)

    def _audit_quality(self):
        self.before_after_table = []
        for c in NUMERIC_COLUMNS + CATEGORICAL_COLUMNS + ["gender"]:
            for action, n in Counter(
                r["_prov_" + c] for r in self.processed_data
            ).items():
                if action != "observed":
                    self.before_after_table.append(
                        {
                            "field": c,
                            "action": action,
                            "affected_count": n,
                            "resolution": "Imputed inside each fitted pipeline"
                            if action == "missing_for_pipeline_imputation"
                            else "Standardized with provenance",
                        }
                    )
        hours = [
            r["training_hours"]
            for r in self.processed_data
            if r["training_hours"] is not None
        ]
        q1, q3 = np.quantile(hours, [0.25, 0.75]) if hours else (0, 0)
        fence = float(q3 + 1.5 * (q3 - q1))
        self.quality_audit = {
            "missing": {
                c: sum(not text(r.get(c)) for r in self.raw_data)
                for c in NUMERIC_COLUMNS + CATEGORICAL_COLUMNS + ["gender"]
            },
            "outlier_fence": fence,
            "outlier_count": sum(v > fence for v in hours),
            "outlier_note": "Flagged for inspection. Scaling is not outlier removal.",
            "repairs": self.before_after_table,
        }

    def frame(self, rows, columns=None):
        columns = columns or MODEL_COLUMNS
        return pd.DataFrame(
            [
                {
                    c: (np.nan if r.get(c) is None else r[c])
                    if c in NUMERIC_COLUMNS
                    else r.get(c, "Unknown")
                    for c in columns
                }
                for r in rows
            ],
            columns=columns,
        )

    def rows_for(self, split):
        return [self.processed_data[i] for i in getattr(self, split + "_indices")]

    def get_summary(self):
        n = len(self.processed_data)
        labels = [r["target"] for r in self.processed_data if r["target"] is not None]
        counts = Counter(labels)
        return {
            "name": self.name,
            "dataset_id": self.dataset_id,
            "total_rows": n,
            "train_rows": len(self.train_indices),
            "validation_rows": len(self.validation_indices),
            "test_rows": len(self.test_indices),
            "num_source_features": len(MODEL_COLUMNS),
            "target_kind": self.target_kind,
            "target_description": TARGET_DESCRIPTIONS[self.target_kind],
            "label_coverage": len(labels) / n,
            "class_balance": {
                "positive": counts[1],
                "negative": counts[0],
                "unknown": n - len(labels),
                "positive_pct": round(100 * counts[1] / len(labels), 2)
                if labels
                else None,
            },
            "majority_baseline_accuracy": max(counts.values()) / len(labels)
            if labels
            else None,
            "audit_attributes": [
                {
                    "key": a,
                    "label": AUDIT_LABELS[a],
                    "observed": a in {"gender", "age_band", "institution"},
                }
                for a in self.audit_attributes
            ],
            "gender_coverage": sum(
                r["gender"] != "Unknown" for r in self.processed_data
            )
            / n,
            "quality_audit": self.quality_audit,
            "before_after_table": self.before_after_table,
            "validation_results": self.validation_results,
            "data_dictionary": DATA_DICTIONARY,
            "excluded_statement": EXCLUDED_COLUMNS_STATEMENT,
            "preview": self.processed_data[:5],
        }
