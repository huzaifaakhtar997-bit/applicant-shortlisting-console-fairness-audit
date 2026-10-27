"""Group rates, support-aware uncertainty, diagnostics, and isolated ablation."""

from collections import Counter, defaultdict

import numpy as np

from backend.data_manager import AUDIT_LABELS, NUMERIC_COLUMNS
from backend.ml_engine import ModelEngine
from backend.policy import SelectionPolicy


def wilson(successes, total):
    if not total:
        return None
    z = 1.959963984540054
    p = successes / total
    d = 1 + z * z / total
    mid = (p + z * z / (2 * total)) / d
    half = z * np.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / d
    return [max(0, float(mid - half)), min(1, float(mid + half))]


def gap(values):
    available = [x for x in values if x is not None]
    return max(available) - min(available) if len(available) > 1 else None


def bootstrap_gap(groups, success_key, total_key):
    valid = [g for g in groups if g[total_key] > 0]
    if len(valid) < 2:
        return None
    rng = np.random.default_rng(42)
    samples = np.asarray(
        [
            rng.binomial(g[total_key], g[success_key] / g[total_key], 1000)
            / g[total_key]
            for g in valid
        ]
    )
    return np.quantile(
        samples.max(axis=0) - samples.min(axis=0), [0.025, 0.975]
    ).tolist()


def audit_single_attribute(
    test_rows, test_probs, threshold=0.5, attribute_name="gender", decisions=None
):
    if len(test_rows) != len(test_probs):
        raise ValueError("Audit rows and scores must align.")
    if decisions is None:
        decisions = SelectionPolicy(threshold).select(test_rows, test_probs)[0]
    if len(decisions) != len(test_rows):
        raise ValueError("Audit decisions must align with rows.")
    grouped = defaultdict(list)
    for row, selected in zip(test_rows, decisions):
        grouped[str(row.get(attribute_name) or "Unknown")].append((row, int(selected)))
    groups = []
    for label, items in grouped.items():
        n = len(items)
        selected = sum(p for _, p in items)
        labeled = [(r, p) for r, p in items if r.get("target") is not None]
        positives = sum(r["target"] == 1 for r, p in labeled)
        selected_labeled = sum(p for r, p in labeled)
        tp = sum(r["target"] == 1 and p == 1 for r, p in labeled)
        negatives = len(labeled) - positives
        fp = sum(r["target"] == 0 and p == 1 for r, p in labeled)
        recall = tp / positives if positives else None
        precision = tp / selected_labeled if selected_labeled else None
        warnings = []
        if n < 30:
            warnings.append("Fewer than 30 records")
        if len(labeled) < n:
            warnings.append(
                "Outcomes missing; label metrics use observed outcomes only"
            )
        if positives < 20:
            warnings.append("Recall has fewer than 20 positive outcomes")
        if selected_labeled < 20:
            warnings.append("Precision has fewer than 20 labeled selections")
        groups.append(
            {
                "group": label,
                "size": n,
                "selected_count": selected,
                "labeled_count": len(labeled),
                "label_coverage": len(labeled) / n,
                "actual_positive_count": positives,
                "selected_labeled_count": selected_labeled,
                "true_positives": tp,
                "selection_rate": selected / n,
                "selection_rate_ci": wilson(selected, n),
                "recall": recall,
                "recall_ci": wilson(tp, positives),
                "precision": precision,
                "precision_ci": wilson(tp, selected_labeled),
                "false_positive_rate": fp / negatives if negatives else None,
                "warnings": warnings,
                "is_small_group": bool(warnings),
            }
        )
    groups.sort(key=lambda g: (-g["size"], g["group"]))
    rates = [g["selection_rate"] for g in groups]
    highest = max(rates) if rates else 0
    for g in groups:
        g["four_fifths_ratio"] = g["selection_rate"] / highest if highest else None
        g["violates_80_rule"] = g["four_fifths_ratio"] < 0.8 if highest else None
    ratios = [
        g["four_fifths_ratio"] for g in groups if g["four_fifths_ratio"] is not None
    ]
    return {
        "attribute": attribute_name,
        "label": AUDIT_LABELS.get(attribute_name, attribute_name.replace("__", " × ")),
        "groups": groups,
        "selection_rate_gap": gap(rates),
        "recall_gap": gap([g["recall"] for g in groups]),
        "precision_gap": gap([g["precision"] for g in groups]),
        "selection_rate_gap_ci": bootstrap_gap(groups, "selected_count", "size"),
        "recall_gap_ci": bootstrap_gap(
            groups, "true_positives", "actual_positive_count"
        ),
        "precision_gap_ci": bootstrap_gap(
            groups, "true_positives", "selected_labeled_count"
        ),
        "favoured_group": max(groups, key=lambda g: g["selection_rate"])["group"]
        if highest
        else None,
        "disadvantaged_group": min(groups, key=lambda g: g["selection_rate"])["group"]
        if highest
        else None,
        "min_four_fifths_ratio": min(ratios) if ratios else None,
        "adverse_impact_detected": any(x < 0.8 for x in ratios) if ratios else None,
        "status": "no_selections"
        if not highest
        else "review"
        if any(x < 0.8 for x in ratios)
        else "no_flag",
        "unknown_count": sum(g["size"] for g in groups if g["group"] == "Unknown"),
        "notes": [
            "Gaps compare max and min estimable group rates, including Unknown.",
            "95% Wilson intervals for rates; plug-in binomial bootstrap intervals for gaps (1,000 draws, seed 42). These are exploratory uncertainty estimates.",
            "A four-fifths flag is a screening heuristic, not a fairness certificate or legal conclusion.",
        ],
    }


def compute_fairness_audit(
    data_manager, ml_engine, threshold=0.5, *, rows=None, policy=None, attributes=None
):
    rows = rows if rows is not None else data_manager.rows_for("test")
    policy = policy or SelectionPolicy(threshold)
    scores = ml_engine.predict_rows(rows)
    decisions, _ = policy.select(rows, scores)
    return {
        a: audit_single_attribute(rows, scores, policy.threshold, a, decisions)
        for a in (attributes or data_manager.audit_attributes)
    }


def compute_disparity_drivers(
    data_manager,
    ml_engine,
    protected_attribute="gender",
    top_k=10,
    *,
    rows=None,
    policy=None,
):
    rows = rows if rows is not None else data_manager.rows_for("validation")
    policy = policy or SelectionPolicy(ml_engine.threshold)
    scores = ml_engine.predict_rows(rows)
    selected, _ = policy.select(rows, scores)
    audit = audit_single_attribute(
        rows, scores, policy.threshold, protected_attribute, selected
    )
    favored, other = audit["favoured_group"], audit["disadvantaged_group"]
    if not favored or favored == other:
        return {
            "drivers": [],
            "note": "No distinct selection-rate groups to investigate.",
        }
    # Deterministic bounded sample makes nonlinear diagnostics tractable for KNN.
    a = [r for r in rows if r.get(protected_attribute, "Unknown") == favored][:150]
    b = [r for r in rows if r.get(protected_attribute, "Unknown") == other][:150]
    sample = a + b
    base = ml_engine.predict_rows(sample)
    base_gap = float(np.mean(base[: len(a)]) - np.mean(base[len(a) :]))
    training = data_manager.rows_for("train")
    result = []
    for col in ml_engine.active_columns:
        values = [r[col] for r in training if r.get(col) is not None]
        reference = (
            (float(np.median(values)) if values else 0.0)
            if col in NUMERIC_COLUMNS
            else Counter(values).most_common(1)[0][0]
        )
        perturbed = [dict(r, **{col: reference}) for r in sample]
        probs = ml_engine.predict_rows(perturbed)
        after = float(np.mean(probs[: len(a)]) - np.mean(probs[len(a) :]))
        result.append(
            {
                "original_column": col,
                "feature": col,
                "driver_score": base_gap - after,
                "abs_impact": abs(base_gap - after),
                "reference_value": reference,
                "score_gap_after_replacement": after,
            }
        )
    return {
        "drivers": sorted(result, key=lambda x: -x["abs_impact"])[:top_k],
        "favoured_group": favored,
        "disadvantaged_group": other,
        "sample_size": len(sample),
        "baseline_mean_score_gap": base_gap,
        "method": "Difference in group mean scores after replacing one whole source attribute with its training median/mode. Model-aware diagnostic, not causal attribution or a selection-gap decomposition.",
    }


def compute_before_after_ablation(
    data_manager,
    ml_engine,
    attribute_to_drop,
    drop_proxies=False,
    protected_attribute="gender",
    *,
    rows=None,
    policy=None,
    attributes=None,
):
    if attribute_to_drop not in ml_engine.active_columns:
        raise ValueError(
            "Choose an active input; audit-only or already removed attributes cannot be ablated."
        )
    rows = rows if rows is not None else data_manager.rows_for("validation")
    policy = policy or SelectionPolicy(ml_engine.threshold)
    attrs = attributes or data_manager.audit_attributes
    if protected_attribute not in attrs:
        raise ValueError("Unknown audit grouping.")
    proxies = ml_engine.proxy_candidates(attribute_to_drop) if drop_proxies else []
    dropped = sorted(
        set(
            ml_engine.dropped_columns
            + [attribute_to_drop]
            + [p["column"] for p in proxies]
        )
    )
    candidate = ModelEngine(data_manager)
    candidate.train(ml_engine.model_type, policy.threshold, dropped_columns=dropped)

    def state(engine):
        audits = compute_fairness_audit(
            data_manager, engine, rows=rows, policy=policy, attributes=attrs
        )
        metrics = engine.evaluate(rows, policy)
        validation = engine.evaluate(data_manager.rows_for("validation"), policy)
        return {
            "audit": audits,
            "metrics": metrics,
            "validation_performance": validation,
            **{
                k: audits[protected_attribute][k]
                for k in [
                    "selection_rate_gap",
                    "recall_gap",
                    "precision_gap",
                    "min_four_fifths_ratio",
                ]
            },
            "accuracy": metrics["accuracy"],
            "auc": metrics["auc"],
            "active_features_count": len(engine.active_features),
        }

    before, after = state(ml_engine), state(candidate)
    keys = ["selection_rate_gap", "recall_gap", "precision_gap", "accuracy", "auc"]
    delta = {
        k: after[k] - before[k]
        if after[k] is not None and before[k] is not None
        else None
        for k in keys
    }
    result = {
        "dropped_attribute": attribute_to_drop,
        "dropped_columns": dropped,
        "additional_proxies": proxies,
        "protected_attribute_audited": protected_attribute,
        "before": before,
        "after": after,
        "delta": delta,
        "policy": policy.to_dict(),
        "baseline_model_version": ml_engine.version,
        "candidate_model_version": candidate.version,
        "evaluation_note": "Exploratory comparison. Validation rows support intervention choice; repeated exploration of test outcomes is not independent final evaluation.",
        "split_id": data_manager.dataset_id + ":seed42:60-20-20",
    }
    return result, candidate
