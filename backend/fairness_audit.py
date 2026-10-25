"""
Fairness Audit Module for Applicant Shortlisting Console.
Computes selection rate, recall, and precision separately for each protected group,
evaluates the Four-Fifths (80%) Rule, identifies disparity driving attributes,
and conducts before-and-after feature ablation studies.
"""

from collections import defaultdict


def audit_single_attribute(test_rows, test_probs, threshold, attribute_name):
    """
    Computes group-by-group metrics for a specified protected attribute.
    Metrics per group: group size, selection rate, recall, precision, and 80% rule ratio.
    """
    # Group rows by attribute value
    groups = defaultdict(list)
    for idx, (row, prob) in enumerate(zip(test_rows, test_probs)):
        val = row.get(attribute_name, 'Unknown')
        groups[val].append((row, prob))

    group_metrics = []
    selection_rates = {}
    recalls = {}
    precisions = {}

    for val, items in groups.items():
        n_group = len(items)
        is_small = n_group < 30  # Warning threshold

        y_true = [item[0]['target'] for item in items]
        y_prob = [item[1] for item in items]
        y_pred = [1 if p >= threshold else 0 for p in y_prob]

        # Selected count
        n_selected = sum(y_pred)
        selection_rate = n_selected / n_group if n_group > 0 else 0.0

        # Recall (True Positive Rate) = TP / Actual Positives
        actual_positives = sum(y_true)
        true_positives = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1)
        recall = true_positives / actual_positives if actual_positives > 0 else 0.0

        # Precision = TP / Predicted Positives
        precision = true_positives / n_selected if n_selected > 0 else 0.0

        selection_rates[val] = selection_rate
        recalls[val] = recall
        precisions[val] = precision

        group_metrics.append({
            'group': val,
            'size': n_group,
            'is_small_group': is_small,
            'selected_count': n_selected,
            'actual_positive_count': actual_positives,
            'selection_rate': round(selection_rate, 4),
            'recall': round(recall, 4),
            'precision': round(precision, 4)
        })

    # Sort groups by size descending
    group_metrics.sort(key=lambda x: x['size'], reverse=True)

    # Determine highest selection rate for 80% rule
    max_sr = max(selection_rates.values()) if selection_rates else 0.0
    favoured_group = max(selection_rates, key=selection_rates.get) if selection_rates else 'None'
    disadvantaged_group = min(selection_rates, key=selection_rates.get) if selection_rates else 'None'

    min_ratio = 1.0
    for gm in group_metrics:
        ratio = (gm['selection_rate'] / max_sr) if max_sr > 0 else 1.0
        gm['four_fifths_ratio'] = round(ratio, 4)
        gm['violates_80_rule'] = ratio < 0.8
        if ratio < min_ratio:
            min_ratio = ratio

    # Gaps: max minus min
    sr_values = list(selection_rates.values())
    recall_values = list(recalls.values())
    precision_values = list(precisions.values())

    sr_gap = (max(sr_values) - min(sr_values)) if sr_values else 0.0
    recall_gap = (max(recall_values) - min(recall_values)) if recall_values else 0.0
    precision_gap = (max(precision_values) - min(precision_values)) if precision_values else 0.0

    return {
        'attribute': attribute_name,
        'groups': group_metrics,
        'favoured_group': favoured_group,
        'disadvantaged_group': disadvantaged_group,
        'max_selection_rate': round(max_sr, 4),
        'min_four_fifths_ratio': round(min_ratio, 4),
        'selection_rate_gap': round(sr_gap, 4),
        'recall_gap': round(recall_gap, 4),
        'precision_gap': round(precision_gap, 4),
        'adverse_impact_detected': min_ratio < 0.8
    }


def compute_fairness_audit(data_manager, ml_engine, threshold=0.5):
    """
    Runs full fairness audit across all three protected attributes:
    Gender, Age Band, and Institution.
    """
    test_rows = [data_manager.processed_data[i] for i in data_manager.test_indices]
    test_probs = ml_engine.cached_test_probs

    audit_gender = audit_single_attribute(test_rows, test_probs, threshold, 'gender')
    audit_age = audit_single_attribute(test_rows, test_probs, threshold, 'age_band')
    audit_inst = audit_single_attribute(test_rows, test_probs, threshold, 'institution')

    return {
        'gender': audit_gender,
        'age_band': audit_age,
        'institution': audit_inst,
        'threshold': threshold
    }


def compute_disparity_drivers(data_manager, ml_engine, protected_attribute='gender', top_k=10):
    """
    For Logistic Regression:
    For each feature, computes:
    driver_score = coefficient * (mean_in_favoured_group - mean_in_disadvantaged_group)
    Identifies attributes that drive the selection rate gap.
    """
    test_rows = [data_manager.processed_data[i] for i in data_manager.test_indices]
    test_probs = ml_engine.cached_test_probs
    threshold = ml_engine.threshold

    single_audit = audit_single_attribute(test_rows, test_probs, threshold, protected_attribute)
    fav_group = single_audit['favoured_group']
    dis_group = single_audit['disadvantaged_group']

    fav_indices = [i for i, r in enumerate(test_rows) if r.get(protected_attribute) == fav_group]
    dis_indices = [i for i, r in enumerate(test_rows) if r.get(protected_attribute) == dis_group]

    if not fav_indices or not dis_indices:
        return {'drivers': [], 'favoured_group': fav_group, 'disadvantaged_group': dis_group}

    active_features = ml_engine.active_features
    X_test = data_manager.get_feature_matrix(test_rows, active_features)

    # Feature weights
    if hasattr(ml_engine.model, 'coef_') and ml_engine.model.coef_:
        weights = ml_engine.model.coef_
    elif hasattr(ml_engine.model, 'feature_importances_') and ml_engine.model.feature_importances_:
        weights = ml_engine.model.feature_importances_
    else:
        weights = [1.0] * len(active_features)

    driver_results = []
    for j, feat in enumerate(active_features):
        mean_fav = sum(X_test[i][j] for i in fav_indices) / len(fav_indices)
        mean_dis = sum(X_test[i][j] for i in dis_indices) / len(dis_indices)
        diff = mean_fav - mean_dis
        w = weights[j] if j < len(weights) else 0.0
        score = w * diff

        orig_col = data_manager.column_origin_map.get(feat, feat)

        driver_results.append({
            'feature': feat,
            'original_column': orig_col,
            'coefficient': round(w, 4),
            'favoured_mean': round(mean_fav, 4),
            'disadvantaged_mean': round(mean_dis, 4),
            'diff': round(diff, 4),
            'driver_score': round(score, 5),
            'abs_impact': round(abs(score), 5),
            'favours': 'Favoured Group' if score > 0 else 'Disadvantaged Group'
        })

    # Sort by absolute impact descending
    driver_results.sort(key=lambda x: x['abs_impact'], reverse=True)

    return {
        'protected_attribute': protected_attribute,
        'favoured_group': fav_group,
        'disadvantaged_group': dis_group,
        'drivers': driver_results[:top_k]
    }


def compute_before_after_ablation(data_manager, ml_engine, attribute_to_drop, drop_proxies=False, protected_attribute='gender'):
    """
    Conducts Before vs After feature ablation:
    1. Records Baseline (Before) metrics: 80% ratio, selection rate gap, recall gap, accuracy, AUC.
    2. Retrains model with the chosen attribute removed from input features (and optionally top 3 proxies).
    3. Re-evaluates on test set and computes After metrics and deltas.
    4. Restores original model state.
    """
    # 1. Baseline state
    before_metrics = dict(ml_engine.latest_metrics)
    before_audit = audit_single_attribute(
        [data_manager.processed_data[i] for i in data_manager.test_indices],
        ml_engine.cached_test_probs,
        ml_engine.threshold,
        protected_attribute
    )

    before_state = {
        'four_fifths_ratio': before_audit['min_four_fifths_ratio'],
        'selection_rate_gap': before_audit['selection_rate_gap'],
        'recall_gap': before_audit['recall_gap'],
        'precision_gap': before_audit['precision_gap'],
        'accuracy': before_metrics.get('accuracy', 0.0),
        'auc': before_metrics.get('auc', 0.0),
        'active_features_count': len(ml_engine.active_features)
    }

    # 2. Retrain with ablation
    saved_model = ml_engine.model
    saved_probs = ml_engine.cached_test_probs
    saved_active = ml_engine.active_features
    saved_metrics = ml_engine.latest_metrics

    # Train ablated model
    ml_engine.train(
        model_type=ml_engine.model_type,
        threshold=ml_engine.threshold,
        attribute_to_drop=attribute_to_drop,
        drop_proxies=drop_proxies
    )

    after_metrics = dict(ml_engine.latest_metrics)
    after_audit = audit_single_attribute(
        [data_manager.processed_data[i] for i in data_manager.test_indices],
        ml_engine.cached_test_probs,
        ml_engine.threshold,
        protected_attribute
    )

    after_state = {
        'four_fifths_ratio': after_audit['min_four_fifths_ratio'],
        'selection_rate_gap': after_audit['selection_rate_gap'],
        'recall_gap': after_audit['recall_gap'],
        'precision_gap': after_audit['precision_gap'],
        'accuracy': after_metrics.get('accuracy', 0.0),
        'auc': after_metrics.get('auc', 0.0),
        'active_features_count': len(ml_engine.active_features),
        'dropped_features': [f for f in saved_active if f not in ml_engine.active_features]
    }

    # Compute deltas (After - Before)
    deltas = {
        'four_fifths_ratio': round(after_state['four_fifths_ratio'] - before_state['four_fifths_ratio'], 4),
        'selection_rate_gap': round(after_state['selection_rate_gap'] - before_state['selection_rate_gap'], 4),
        'recall_gap': round(after_state['recall_gap'] - before_state['recall_gap'], 4),
        'precision_gap': round(after_state['precision_gap'] - before_state['precision_gap'], 4),
        'accuracy': round(after_state['accuracy'] - before_state['accuracy'], 4),
        'auc': round(after_state['auc'] - before_state['auc'], 4)
    }

    # Restore original state so main model remains unaffected unless user commits
    ml_engine.model = saved_model
    ml_engine.cached_test_probs = saved_probs
    ml_engine.active_features = saved_active
    ml_engine.latest_metrics = saved_metrics

    return {
        'dropped_attribute': attribute_to_drop,
        'drop_proxies': drop_proxies,
        'protected_attribute_audited': protected_attribute,
        'before': before_state,
        'after': after_state,
        'delta': deltas,
        'explanation_note': (
            "If the gap barely changed, other features are acting as proxies for the dropped attribute."
        )
    }
