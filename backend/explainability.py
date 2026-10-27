"""Faithful model paths and measured, source-column perturbations. No invented effects."""

from collections import Counter

import numpy as np

from backend.data_manager import NUMERIC_COLUMNS, TARGET_DESCRIPTIONS
from backend.policy import SelectionPolicy

LABELS = {
    "city_development_index": "City development index",
    "training_hours": "Training hours",
    "experience": "Years of experience",
    "relevent_experience": "Relevant experience",
    "enrolled_university": "University enrollment",
    "education_level": "Education level",
    "major_discipline": "Major discipline",
    "company_size": "Company size",
    "company_type": "Company type",
    "last_new_job": "Years since last job transition",
}


def explain_row(row, engine, policy=None, *, pool_rows=None, pool_scores=None):
    policy = policy or SelectionPolicy(engine.threshold)
    score = engine.predict_rows([row])[0]
    if pool_rows is not None:
        scores = (
            pool_scores if pool_scores is not None else engine.predict_rows(pool_rows)
        )
        selected, ranked = policy.select(pool_rows, scores)
        index = next(
            (
                i
                for i, r in enumerate(pool_rows)
                if r["enrollee_id"] == row["enrollee_id"]
            ),
            None,
        )
        decision = bool(selected[index]) if index is not None else None
        rank = ranked.index(index) + 1 if index is not None else None
    else:
        decision = bool(score >= policy.threshold) if policy.top_n is None else None
        rank = None
    rules = []
    if engine.model_type == "decision_tree":
        x = engine.pipeline.named_steps["preprocess"].transform(
            engine.dm.frame([row], engine.active_columns)
        )
        tree = engine.model.tree_
        for node in engine.model.decision_path(x).indices:
            j = tree.feature[node]
            if j < 0:
                continue
            name = engine.active_features[j]
            value = float(x[0, j])
            cutoff = float(tree.threshold[node])
            source = next(
                (
                    c
                    for c in engine.active_columns
                    if c not in NUMERIC_COLUMNS and name.startswith(c + "_")
                ),
                None,
            )
            rule = (
                f"{LABELS[source]} is {'not ' if value <= cutoff else ''}{name[len(source) + 1 :]}"
                if source
                else f"{LABELS.get(name, name)} {'≤' if value <= cutoff else '>'} {cutoff:.3g} (value {value:.3g})"
            )
            rules.append(
                {
                    "feature": name,
                    "operator": "≤" if value <= cutoff else ">",
                    "threshold": cutoff,
                    "value": value,
                    "text": rule,
                }
            )
    training = engine.dm.rows_for("train")
    perturbed = []
    references = []
    for c in engine.active_columns:
        values = [r[c] for r in training if r.get(c) is not None]
        reference = (
            float(np.median(values))
            if c in NUMERIC_COLUMNS and values
            else Counter(values).most_common(1)[0][0]
            if values
            else 0
        )
        references.append(reference)
        perturbed.append(dict(row, **{c: reference}))
    probabilities = engine.predict_rows(perturbed)
    effects = [
        {
            "feature": c,
            "label": LABELS.get(c, c),
            "value": row.get(c),
            "reference_value": reference,
            "impact": float(score - p),
            "explanation": f"Actual value compared with the training {'median' if c in NUMERIC_COLUMNS else 'mode'}. Change measured by rescoring the complete input.",
        }
        for c, reference, p in zip(engine.active_columns, references, probabilities)
    ]
    effects.sort(key=lambda e: -abs(e["impact"]))
    return {
        "applicant_id": str(row["enrollee_id"]),
        "probability": score,
        "score": score,
        "shortlisted": decision,
        "rank": rank,
        "policy": policy.to_dict(),
        "model_version": engine.version,
        "model_type": engine.model_type,
        "outcome_description": TARGET_DESCRIPTIONS[engine.dm.target_kind],
        "decision_rules": [r["text"] for r in rules],
        "rule_details": rules,
        "contributions": effects,
        "positive_drivers": [e for e in effects if e["impact"] > 1e-8],
        "negative_drivers": [e for e in effects if e["impact"] < -1e-8],
        "profile": {c: row.get(c) for c in engine.active_columns},
        "demographics": {
            c: row.get(c)
            for c in [
                "gender",
                "age_band",
                "institution",
                "experience_band",
                "education_group",
            ]
        },
        "note": "Uncalibrated model score, not verified qualification or confidence. Perturbations are sensitivity estimates; they are not additive or causal. Audit-only fields are excluded from the input.",
        "decision_note": "Selection requires comparison with the full pool under a top-N policy."
        if decision is None
        else "Decision uses the same pool policy as the shortlist.",
    }


def explain_applicant(
    applicant_id, data_manager, ml_engine, *, rows=None, policy=None, scores=None
):
    rows = rows if rows is not None else data_manager.rows_for("test")
    row = next((r for r in rows if str(r["enrollee_id"]) == str(applicant_id)), None)
    if row is None:
        return {"error": "Applicant not found in the current pool."}
    return explain_row(row, ml_engine, policy, pool_rows=rows, pool_scores=scores)
