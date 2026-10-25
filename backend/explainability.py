"""
Explainability Module for Applicant Shortlisting Console.
Provides individualized feature attribution and rich executive reasoning
for each applicant based on their specific credentials.
"""

def format_feature_label(feat, val, orig_col):
    """Formats raw machine learning feature name into clear recruiter criteria."""
    if orig_col == feat:
        if feat == 'city_development_index':
            return f"City Development Index ({val:.2f})"
        elif feat == 'training_hours':
            return f"Completed Training ({int(round(val * 100))} hrs)"
        return feat.replace('_', ' ').title()

    cat_val = feat[len(orig_col) + 1:]
    
    # Human-friendly descriptions
    if orig_col == 'experience':
        return f"Career Experience: {cat_val} yrs"
    elif orig_col == 'education_level':
        return f"Education Level: {cat_val}"
    elif orig_col == 'relevent_experience':
        return f"Industry Experience: {cat_val}"
    elif orig_col == 'company_size':
        return f"Employer Scale: {cat_val} employees"
    elif orig_col == 'major_discipline':
        return f"Discipline: {cat_val}"
    elif orig_col == 'enrolled_university':
        return f"Enrollment Status: {cat_val}"
    elif orig_col == 'company_type':
        return f"Company Type: {cat_val}"
    elif orig_col == 'last_new_job':
        return f"Time Since Job Switch: {cat_val} yrs"
    elif orig_col == 'gender':
        return f"Gender: {cat_val}"
    
    return f"{orig_col.replace('_', ' ').title()}: {cat_val}"


def generate_executive_reasoning(applicant_id, score, threshold, is_shortlisted, target_row, positive_drivers, negative_drivers):
    """
    Generates rich, individualized hiring reasoning explaining exactly
    why this specific candidate was selected or rejected.
    """
    score_pct = round(score * 100, 1)
    thresh_pct = round(threshold * 100, 1)
    diff_pct = round(abs(score_pct - thresh_pct), 1)

    if is_shortlisted:
        headline = (
            f"Candidate #{applicant_id} successfully qualified for the interview shortlist with an "
            f"estimated qualification score of {score_pct}%, exceeding the required threshold of {thresh_pct}% "
            f"by +{diff_pct}%."
        )
        verdict = "SHORTLISTED FOR INTERVIEW"
    else:
        headline = (
            f"Candidate #{applicant_id} did not meet the interview shortlisting cutoff, scoring {score_pct}% "
            f"(falling -{diff_pct}% short of the required {thresh_pct}% threshold)."
        )
        verdict = "NOT SHORTLISTED (REJECTED)"

    # Strengths summary
    strengths = []
    for d in positive_drivers[:4]:
        strengths.append(f"{d['label']} (contributed +{d['contribution']:.3f} to score)")

    # Risks summary
    risks = []
    for d in negative_drivers[:4]:
        strengths_drag = abs(d['contribution'])
        risks.append(f"{d['label']} (pulled score down by -{strengths_drag:.3f})")

    # Build comprehensive narrative
    narrative_parts = [headline]

    if is_shortlisted:
        top_pos = [d['label'] for d in positive_drivers[:3]]
        if top_pos:
            narrative_parts.append(
                f"The candidate's selection is driven by distinctive credentials: {', '.join(top_pos)}. "
                f"These credentials distinguish this applicant from the general candidate pool and strongly signal interview readiness."
            )
        if risks:
            top_neg = [d['label'] for d in negative_drivers[:2]]
            narrative_parts.append(
                f"Minor offsetting factors included {', '.join(top_neg)}, but their impact was outweighed by the applicant's core strengths."
            )
        narrative_parts.append(
            f"Recruiter Recommendation: Advance Candidate #{applicant_id} to the interview round."
        )
    else:
        top_neg = [d['label'] for d in negative_drivers[:3]]
        if top_neg:
            narrative_parts.append(
                f"The primary criteria preventing shortlisting are: {', '.join(top_neg)}. "
                f"Compared to shortlisted peers, these factors reduced the predicted likelihood of meeting the post's core requirements."
            )
        if strengths:
            top_pos = [d['label'] for d in positive_drivers[:2]]
            narrative_parts.append(
                f"Although the applicant demonstrated positive attributes in {', '.join(top_pos)}, they were insufficient to surpass the {thresh_pct}% interview threshold."
            )
        narrative_parts.append(
            f"Recruiter Recommendation: Keep profile on file; do not proceed to interview for this hiring round."
        )

    detailed_narrative = " ".join(narrative_parts)

    return {
        'verdict': verdict,
        'headline': headline,
        'key_strengths': strengths if strengths else ["No strong positive discriminators."],
        'key_risks': risks if risks else ["No notable profile risks."],
        'detailed_narrative': detailed_narrative
    }


def explain_applicant(applicant_id, data_manager, ml_engine):
    """
    Computes individualized criteria breakdown and local feature attribution
    for a single applicant based on credentials they possess.
    """
    target_row = None
    for r in data_manager.processed_data:
        if str(r.get('enrollee_id')) == str(applicant_id):
            target_row = r
            break

    if target_row is None:
        try:
            int_id = int(applicant_id)
            if 0 <= int_id < len(data_manager.processed_data):
                target_row = data_manager.processed_data[int_id]
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

    means_map = getattr(data_manager, 'feature_means', {})

    contributions = []

    # Logistic Regression feature impact
    if hasattr(ml_engine.model, 'coef_') and ml_engine.model.coef_:
        weights = ml_engine.model.coef_
        for j, feat in enumerate(active_features):
            val = x_vec[j]
            orig_col = data_manager.column_origin_map.get(feat, feat)

            # Continuous features: evaluated relative to pool mean
            if orig_col == feat:
                mean_val = means_map.get(feat, 0.0)
                diff = val - mean_val
                w = weights[j] if j < len(weights) else 0.0
                contrib = w * diff
                label = format_feature_label(feat, val, orig_col)
                if abs(contrib) > 1e-4:
                    contributions.append({
                        'feature': feat,
                        'label': label,
                        'original_column': orig_col,
                        'value': round(val, 3),
                        'weight': round(w, 4),
                        'contribution': round(contrib, 4),
                        'direction': 'Positive (Score Up)' if contrib > 0 else 'Negative (Score Down)'
                    })
            # One-hot features: ONLY evaluate credentials the candidate ACTUALLY POSSESSES (val == 1.0)
            elif val > 0.5:
                w = weights[j] if j < len(weights) else 0.0
                contrib = w  # Having this credential gives weight w
                label = format_feature_label(feat, val, orig_col)
                if abs(contrib) > 1e-4:
                    contributions.append({
                        'feature': feat,
                        'label': label,
                        'original_column': orig_col,
                        'value': 1.0,
                        'weight': round(w, 4),
                        'contribution': round(contrib, 4),
                        'direction': 'Positive (Score Up)' if contrib > 0 else 'Negative (Score Down)'
                    })

    # Random Forest feature impact
    elif hasattr(ml_engine.model, 'feature_importances_') and ml_engine.model.feature_importances_:
        importances = ml_engine.model.feature_importances_
        for j, feat in enumerate(active_features):
            val = x_vec[j]
            orig_col = data_manager.column_origin_map.get(feat, feat)
            imp = importances[j] if j < len(importances) else 0.0

            if orig_col == feat:
                mean_val = means_map.get(feat, 0.5)
                diff = val - mean_val
                contrib = imp * diff
                label = format_feature_label(feat, val, orig_col)
                if abs(contrib) > 1e-4:
                    contributions.append({
                        'feature': feat,
                        'label': label,
                        'original_column': orig_col,
                        'value': round(val, 3),
                        'weight': round(imp, 4),
                        'contribution': round(contrib, 4),
                        'direction': 'Positive (Score Up)' if contrib > 0 else 'Negative (Score Down)'
                    })
            elif val > 0.5:
                # Possessing this feature
                contrib = imp * 0.5
                label = format_feature_label(feat, val, orig_col)
                if abs(contrib) > 1e-4:
                    contributions.append({
                        'feature': feat,
                        'label': label,
                        'original_column': orig_col,
                        'value': 1.0,
                        'weight': round(imp, 4),
                        'contribution': round(contrib, 4),
                        'direction': 'Positive (Score Up)'
                    })

    # Sort contributions by absolute impact descending
    contributions.sort(key=lambda x: abs(x['contribution']), reverse=True)

    positive_drivers = [c for c in contributions if c['contribution'] > 0][:8]
    negative_drivers = [c for c in contributions if c['contribution'] < 0][:8]

    # Generate personalized executive reasoning
    executive_reasoning = generate_executive_reasoning(
        applicant_id=target_row.get('enrollee_id'),
        score=p_positive,
        threshold=ml_engine.threshold,
        is_shortlisted=is_shortlisted,
        target_row=target_row,
        positive_drivers=positive_drivers,
        negative_drivers=negative_drivers
    )

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
        'executive_reasoning': executive_reasoning,
        'top_contributions': contributions[:12],
        'positive_drivers': positive_drivers,
        'negative_drivers': negative_drivers
    }
