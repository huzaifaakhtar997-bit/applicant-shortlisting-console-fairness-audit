"""
Explainability Module for Applicant Shortlisting Console.
Provides local feature attribution for individual applicants.
For Logistic Regression, computes coefficient * feature_value.
For Random Forest, computes feature_importance * (value - mean).
"""

def explain_applicant(applicant_id, data_manager, ml_engine):
    """
    Computes criteria breakdown and local feature contributions
    for a single applicant.
    """
    # Locate candidate by enrollee_id or row index
    target_row = None
    row_idx = None
    for idx, r in enumerate(data_manager.processed_data):
        if str(r.get('enrollee_id')) == str(applicant_id):
            target_row = r
            row_idx = idx
            break

    if target_row is None:
        try:
            int_id = int(applicant_id)
            if 0 <= int_id < len(data_manager.processed_data):
                target_row = data_manager.processed_data[int_id]
                row_idx = int_id
        except Exception:
            pass

    if target_row is None:
        return {'error': f'Applicant ID {applicant_id} not found.'}

    # Extract feature vector
    active_features = ml_engine.active_features
    x_vec = data_manager.get_feature_matrix([target_row], active_features)[0]

    # Predict probability
    probs = ml_engine.model.predict_proba([x_vec])[0]
    p_positive = probs[1]
    is_shortlisted = p_positive >= ml_engine.threshold

    contributions = []

    # Logistic Regression: coefficient * feature_value
    if hasattr(ml_engine.model, 'coef_') and ml_engine.model.coef_:
        weights = ml_engine.model.coef_
        bias = getattr(ml_engine.model, 'bias', 0.0)

        for j, feat in enumerate(active_features):
            val = x_vec[j]
            w = weights[j] if j < len(weights) else 0.0
            contrib = w * val
            orig_col = data_manager.column_origin_map.get(feat, feat)

            # Only include non-zero or notable contributions
            if abs(contrib) > 1e-4:
                contributions.append({
                    'feature': feat,
                    'original_column': orig_col,
                    'value': round(val, 3),
                    'weight': round(w, 4),
                    'contribution': round(contrib, 4),
                    'direction': 'Positive (Score Up)' if contrib > 0 else 'Negative (Score Down)'
                })

    # Random Forest: feature_importance * (x - mean)
    elif hasattr(ml_engine.model, 'feature_importances_') and ml_engine.model.feature_importances_:
        importances = ml_engine.model.feature_importances_
        # Use mean approximation
        for j, feat in enumerate(active_features):
            val = x_vec[j]
            imp = importances[j] if j < len(importances) else 0.0
            # Centered around median/0.5
            diff = val - 0.5
            contrib = imp * diff
            orig_col = data_manager.column_origin_map.get(feat, feat)

            if abs(contrib) > 1e-4:
                contributions.append({
                    'feature': feat,
                    'original_column': orig_col,
                    'value': round(val, 3),
                    'weight': round(imp, 4),
                    'contribution': round(contrib, 4),
                    'direction': 'Positive (Score Up)' if contrib > 0 else 'Negative (Score Down)'
                })
    else:
        bias = 0.0

    # Sort contributions by absolute value descending
    contributions.sort(key=lambda x: abs(x['contribution']), reverse=True)

    positive_drivers = [c for c in contributions if c['contribution'] > 0][:8]
    negative_drivers = [c for c in contributions if c['contribution'] < 0][:8]

    return {
        'applicant_id': target_row.get('enrollee_id'),
        'score': round(p_positive, 4),
        'threshold': ml_engine.threshold,
        'shortlisted': is_shortlisted,
        'target_ground_truth': target_row.get('target'),
        'demographics': {
            'gender': target_row.get('gender'),
            'age_band': target_row.get('age_band'),
            'institution': target_row.get('institution')
        },
        'profile': {
            'city_development_index': target_row.get('city_development_index'),
            'training_hours': target_row.get('training_hours'),
            'relevent_experience': target_row.get('relevent_experience'),
            'education_level': target_row.get('education_level'),
            'company_size': target_row.get('company_size'),
            'last_new_job': target_row.get('last_new_job')
        },
        'top_contributions': contributions[:12],
        'positive_drivers': positive_drivers,
        'negative_drivers': negative_drivers
    }
