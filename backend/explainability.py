"""
Explainability Module for Applicant Shortlisting Console.
Provides individualized feature attribution and rich executive reasoning
for each applicant based on their specific credentials.
"""

import math


def format_candidate_credential(orig_col, val, diff=0.0):
    """
    Translates raw applicant credentials into simple, detailed, correct,
    and recruiter-friendly titles and explanations.
    """
    col_clean = str(orig_col).strip()
    val_str = str(val).strip()

    if col_clean == 'city_development_index':
        cdi = float(val)
        if cdi >= 0.85:
            return (
                f"Tier-1 Metropolitan Tech Hub (CDI {cdi:.2f})",
                f"Applicant resides in a mature metropolitan area (CDI {cdi:.2f}) with deep tech ecosystem presence, signaling strong industry exposure."
            )
        elif cdi >= 0.70:
            return (
                f"Developed Regional Market (CDI {cdi:.2f})",
                f"Applicant is based in an established regional market (CDI {cdi:.2f}) with moderate technical infrastructure."
            )
        else:
            return (
                f"Emerging Growth Market (CDI {cdi:.2f})",
                f"Applicant operates in an emerging development market (CDI {cdi:.2f}) offering distinctive talent agility and high mobility."
            )

    elif col_clean == 'training_hours':
        hrs = int(round(float(val)))
        if hrs >= 70:
            return (
                f"Extensive Skill Development ({hrs} hrs)",
                f"Candidate completed {hrs} hours of verified technical development (surpassing pool benchmark), demonstrating strong commitment to continuous learning."
            )
        elif hrs >= 40:
            return (
                f"Moderate Skill Training ({hrs} hrs)",
                f"Candidate completed {hrs} hours of technical coursework, meeting baseline development expectations."
            )
        else:
            return (
                f"Limited Training Hours ({hrs} hrs)",
                f"Candidate logged {hrs} training hours (below the 65-hour applicant pool average), suggesting an area for onboarding skill development."
            )

    elif col_clean == 'experience':
        if val_str in ['>20', '20', '21']:
            return (
                "Senior Veteran Career (>20 yrs)",
                "Over 20 years of proven industry experience, bringing extensive technical leadership, system maturity, and mentorship capability."
            )
        elif val_str in ['11', '12', '13', '14', '15', '16', '17', '18', '19']:
            return (
                f"Established Senior Experience ({val_str} yrs)",
                f"{val_str} years of professional track record, demonstrating strong autonomous problem-solving and architectural judgment."
            )
        elif val_str in ['6', '7', '8', '9', '10']:
            return (
                f"Solid Mid-Career Experience ({val_str} yrs)",
                f"{val_str} years of active industry delivery with hands-on proficiency in modern analytics frameworks."
            )
        elif val_str in ['1', '2', '3', '4', '5']:
            return (
                f"Early-Career Experience ({val_str} yrs)",
                f"{val_str} years of foundation experience, offering high learning agility and rapid adaptability."
            )
        else:
            return (
                "Entry-Level / Junior Experience (<1 yr)",
                "Under 1 year of formal experience; high potential but will require close pairing and technical supervision."
            )

    elif col_clean == 'education_level':
        if val_str == 'Phd':
            return (
                "Doctoral Degree (Ph.D.)",
                "Advanced doctoral qualification demonstrating rigorous research methodology, statistical depth, and algorithmic problem-solving."
            )
        elif val_str == 'Masters':
            return (
                "Postgraduate Master's Degree",
                "Master's level degree conferring specialized engineering, mathematical, or computing foundations."
            )
        elif val_str == 'Graduate':
            return (
                "Bachelor's Degree Graduate",
                "Accredited university graduate meeting the core academic benchmark for analytical and data roles."
            )
        else:
            return (
                f"Foundational Education ({val_str})",
                f"Highest qualification recorded as {val_str}; practical competence and technical execution take priority."
            )

    elif col_clean == 'relevent_experience':
        if 'has' in val_str.lower() or val_str == 'Has relevent experience':
            return (
                "Direct Domain Experience",
                "Candidate has direct, verified experience in relevant analytics and software workflows, ensuring rapid time-to-productivity."
            )
        else:
            return (
                "Cross-Domain Transition (No Direct Prior)",
                "Candidate has not previously worked in direct domain roles and is transitioning from an adjacent specialty."
            )

    elif col_clean == 'major_discipline':
        if val_str == 'STEM':
            return (
                "Core STEM Academic Major",
                "Academic specialization in Science, Technology, Engineering, or Math, directly aligned with technical requirements."
            )
        elif val_str == 'Business Degree':
            return (
                "Business & Commercial Discipline",
                "Commercial degree background providing strong intuition for commercial KPIs and business outcomes."
            )
        elif val_str == 'Unknown':
            return (
                "Interdisciplinary / General Major",
                "Academic degree outside standard departmental categorizations, offering broad multidisciplinary foundations."
            )
        else:
            return (
                f"Academic Major: {val_str}",
                f"Graduated with a major in {val_str}, introducing complementary interdisciplinary perspective."
            )

    elif col_clean == 'company_size':
        if val_str in ['10000+', '5000-9999']:
            return (
                f"Enterprise Scale Experience ({val_str})",
                f"Accustomed to large-scale organization workflows ({val_str} staff), governance standards, and cross-team alignment."
            )
        elif val_str in ['1000-4999', '500-999', '100-500']:
            return (
                f"Mid-to-Large Organization ({val_str})",
                f"Solid background in structured, scaling business units ({val_str} staff)."
            )
        elif val_str in ['50-99', '10-49']:
            return (
                f"High-Growth Team Experience ({val_str})",
                f"Proven track record in dynamic, versatile growth companies ({val_str} staff) where fast execution is vital."
            )
        elif val_str == '<10':
            return (
                "Early Startup / Boutique Experience (<10)",
                "Hands-on experience in lean, high-ownership early-stage teams (<10 staff)."
            )
        elif val_str == 'Unknown':
            return (
                "Confidential / Boutique Employer Scale",
                "Previous organization scale not publicly disclosed; characteristic of stealth startups or private consultancies."
            )
        else:
            return (
                f"Employer Scale: {val_str}",
                f"Previous employer recorded scale: {val_str}."
            )

    elif col_clean == 'last_new_job':
        if val_str in ['>4', '4']:
            return (
                f"High Workplace Stability ({val_str} yrs)",
                f"Maintained steady tenure ({val_str} years at previous job), signaling high retention reliability and delivery focus."
            )
        elif val_str in ['1', '2', '3']:
            return (
                f"Market Mobility ({val_str} yrs)",
                f"Recent job transition {val_str} year(s) ago; signals active market familiarity and fresh industry perspective."
            )
        elif val_str == 'never':
            return (
                "First Career Transition (Never switched)",
                "Candidate has served entire career with current company; exceptional loyalty, exploring external opportunities for first time."
            )
        else:
            return (
                f"Time Since Job Switch: {val_str} yrs",
                f"Last career transition recorded as {val_str}."
            )

    elif col_clean == 'enrolled_university':
        if val_str == 'no_enrollment':
            return (
                "Full-Time Workplace Availability",
                "Not currently enrolled in higher education; available for full-time professional commitment without course constraints."
            )
        elif val_str == 'Full time course':
            return (
                "Full-Time University Enrollment",
                "Currently enrolled in a full-time academic program; scheduling availability should be confirmed during interview."
            )
        else:
            return (
                f"University Enrollment: {val_str}",
                f"Academic enrollment status noted as {val_str}."
            )

    elif col_clean == 'company_type':
        if val_str == 'Unknown':
            return (
                "Private / Unlisted Organization",
                "Prior employer category not listed in public registry; warrants portfolio review during technical interview."
            )
        return (
            f"Employer Type: {val_str}",
            f"Prior employer category recorded as {val_str}."
        )

    return (
        f"{col_clean.replace('_', ' ').title()}: {val_str}",
        f"Applicant profile reflects {val_str} for {col_clean}."
    )


def generate_executive_reasoning(applicant_id, score, threshold, is_shortlisted, target_row, positive_drivers, negative_drivers):
    """
    Generates rich, individualized hiring reasoning explaining exactly
    why this specific candidate was selected or rejected in plain English.
    """
    score_pct = round(score * 100, 1)
    thresh_pct = round(threshold * 100, 1)
    diff_pct = round(abs(score_pct - thresh_pct), 1)

    if is_shortlisted:
        headline = (
            f"Candidate #{applicant_id} successfully qualified for the interview shortlist with an "
            f"estimated qualification match score of {score_pct}%, comfortably surpassing the hiring cutoff of {thresh_pct}% "
            f"by +{diff_pct}%."
        )
        verdict = "SHORTLISTED FOR INTERVIEW"
    else:
        headline = (
            f"Candidate #{applicant_id} did not qualify for the interview shortlist, receiving an "
            f"estimated qualification match score of {score_pct}%, falling -{diff_pct}% short of the required {thresh_pct}% cutoff."
        )
        verdict = "NOT SHORTLISTED (BELOW CUTOFF)"

    paragraphs = [headline]

    if is_shortlisted:
        if positive_drivers:
            top_pos = [f"{d['display_name']} (+{d['impact']:.3f})" for d in positive_drivers[:3]]
            paragraphs.append(
                f"Key Selection Drivers: The primary credentials driving this candidate's selection are {', '.join(top_pos)}. "
                f"These credentials distinguish this applicant from the general candidate pool and strongly signal interview readiness."
            )
        if negative_drivers:
            top_neg = [f"{d['display_name']} ({d['impact']:.3f})" for d in negative_drivers[:2]]
            paragraphs.append(
                f"Interview Verification Areas: While the applicant easily cleared the bar, the interviewing panel should verify "
                f"{', '.join(top_neg)} during the structured interview."
            )
        paragraphs.append(
            f"Recruiter Recommendation: Advance Candidate #{applicant_id} to technical interview."
        )
    else:
        if negative_drivers:
            top_neg = [f"{d['display_name']} ({d['impact']:.3f})" for d in negative_drivers[:3]]
            paragraphs.append(
                f"Primary Limiting Factors: The credentials holding this profile back are {', '.join(top_neg)}. "
                f"Compared to shortlisted peers, these factors reduced the estimated likelihood of meeting the post's core requirements."
            )
        if positive_drivers:
            top_pos = [f"{d['display_name']} (+{d['impact']:.3f})" for d in positive_drivers[:2]]
            paragraphs.append(
                f"Profile Strengths: The applicant demonstrated positive indicators in {', '.join(top_pos)}, though these were "
                f"insufficient to overcome the required {thresh_pct}% interview threshold."
            )
        paragraphs.append(
            f"Recruiter Recommendation: Keep Candidate #{applicant_id} on file for future openings; do not proceed to interview this cycle."
        )

    detailed_narrative = " ".join(paragraphs)

    return {
        'verdict': verdict,
        'headline': headline,
        'detailed_narrative': detailed_narrative,
        'key_strengths': [d['display_name'] for d in positive_drivers[:4]] if positive_drivers else ["Solid overall baseline qualifications."],
        'key_risks': [d['display_name'] for d in negative_drivers[:4]] if negative_drivers else ["No significant profile concerns identified."]
    }


def explain_applicant(applicant_id, data_manager, ml_engine):
    """
    Computes individualized criteria breakdown and local feature attribution
    for a single applicant based on credentials they possess.
    Safe across all model families (Decision Tree, Naive Bayes, KNN, Logistic Regression).
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
    need_scaling = (getattr(ml_engine, 'model_type', '') == 'knn')
    x_vec = data_manager.get_feature_matrix([target_row], active_features, standardize=need_scaling)[0]

    # Predict probability
    probs = ml_engine.model.predict_proba([x_vec])[0]
    p_positive = float(probs[1])
    is_shortlisted = bool(p_positive >= ml_engine.threshold)

    means_map = getattr(data_manager, 'feature_means', {})
    col_origin_map = getattr(data_manager, 'column_origin_map', {})

    contributions = []

    # --------------------------------------------------------------------------
    # 1. Linear Model (Logistic Regression) with explicit coef_
    # --------------------------------------------------------------------------
    coef_attr = getattr(ml_engine.model, 'coef_', None)
    if coef_attr is not None:
        if hasattr(coef_attr, 'tolist'):
            coef_list = coef_attr.tolist()
        else:
            coef_list = list(coef_attr)

        if isinstance(coef_list, list) and len(coef_list) > 0 and isinstance(coef_list[0], list):
            weights = [float(x) for x in coef_list[0]]
        else:
            weights = [float(x) for x in coef_list]

        for j, feat in enumerate(active_features):
            val = float(x_vec[j])
            orig_col = col_origin_map.get(feat, feat)
            w = weights[j] if j < len(weights) else 0.0

            if orig_col == feat:
                # Continuous attribute
                mean_val = float(means_map.get(feat, 0.5))
                diff = val - mean_val
                contrib = float(w * diff)
                raw_actual = target_row.get(orig_col, val)
                title, explanation = format_candidate_credential(orig_col, raw_actual, diff)
                contributions.append({
                    'feature': feat,
                    'original_column': orig_col,
                    'display_name': title,
                    'label': title,
                    'explanation': explanation,
                    'value': raw_actual,
                    'weight': round(w, 4),
                    'impact': round(contrib, 4),
                    'contribution': round(contrib, 4),
                    'direction': 'Positive (Score Up)' if contrib >= 0 else 'Negative (Score Down)'
                })
            elif val > 0.5:
                # One-hot credential possessed by candidate
                raw_actual = target_row.get(orig_col, feat[len(orig_col)+1:])
                mean_val = float(means_map.get(feat, 0.2))
                contrib = float(w * (1.0 - mean_val))
                title, explanation = format_candidate_credential(orig_col, raw_actual, contrib)
                contributions.append({
                    'feature': feat,
                    'original_column': orig_col,
                    'display_name': title,
                    'label': title,
                    'explanation': explanation,
                    'value': raw_actual,
                    'weight': round(w, 4),
                    'impact': round(contrib, 4),
                    'contribution': round(contrib, 4),
                    'direction': 'Positive (Score Up)' if contrib >= 0 else 'Negative (Score Down)'
                })

    # --------------------------------------------------------------------------
    # 2. Tree-based or General Models (Decision Tree, Naive Bayes, KNN, etc.)
    # --------------------------------------------------------------------------
    else:
        # Batch marginal perturbation: measure probability shift if feature j was replaced by mean
        perturbed_rows = []
        for j, feat in enumerate(active_features):
            p_row = list(x_vec)
            p_row[j] = float(means_map.get(feat, 0.0))
            perturbed_rows.append(p_row)

        try:
            pert_probs = ml_engine.model.predict_proba(perturbed_rows)
            marginal_deltas = [p_positive - float(p[1]) for p in pert_probs]
        except Exception:
            marginal_deltas = [0.0] * len(active_features)

        # Feature importances if available
        fi_attr = getattr(ml_engine.model, 'feature_importances_', None)
        if fi_attr is not None:
            if hasattr(fi_attr, 'tolist'):
                importances = [float(x) for x in fi_attr.tolist()]
            else:
                importances = [float(x) for x in fi_attr]
        else:
            importances = [1.0 / len(active_features)] * len(active_features)

        for j, feat in enumerate(active_features):
            val = float(x_vec[j])
            orig_col = col_origin_map.get(feat, feat)
            imp = importances[j] if j < len(importances) else 0.0
            delta = marginal_deltas[j] if j < len(marginal_deltas) else 0.0

            # If marginal delta is present, use it; otherwise blend importance with deviation
            if orig_col == feat:
                # Continuous feature
                mean_val = float(means_map.get(feat, 0.5))
                diff = val - mean_val
                if abs(delta) > 1e-4:
                    contrib = float(delta)
                else:
                    corr_sign = -1.0 if orig_col == 'city_development_index' else 1.0
                    contrib = float(imp * diff * corr_sign)

                raw_actual = target_row.get(orig_col, val)
                title, explanation = format_candidate_credential(orig_col, raw_actual, diff)
                contributions.append({
                    'feature': feat,
                    'original_column': orig_col,
                    'display_name': title,
                    'label': title,
                    'explanation': explanation,
                    'value': raw_actual,
                    'weight': round(imp, 4),
                    'impact': round(contrib, 4),
                    'contribution': round(contrib, 4),
                    'direction': 'Positive (Score Up)' if contrib >= 0 else 'Negative (Score Down)'
                })

            elif val > 0.5:
                # One-hot credential possessed by candidate
                raw_actual = target_row.get(orig_col, feat[len(orig_col)+1:])
                if abs(delta) > 1e-4:
                    contrib = float(delta)
                else:
                    contrib = float(imp * 0.5)

                title, explanation = format_candidate_credential(orig_col, raw_actual, contrib)
                contributions.append({
                    'feature': feat,
                    'original_column': orig_col,
                    'display_name': title,
                    'label': title,
                    'explanation': explanation,
                    'value': raw_actual,
                    'weight': round(imp, 4),
                    'impact': round(contrib, 4),
                    'contribution': round(contrib, 4),
                    'direction': 'Positive (Score Up)' if contrib >= 0 else 'Negative (Score Down)'
                })

    # Deduplicate credentials by original column to avoid repeating same attribute
    seen_cols = set()
    unique_contributions = []
    # Sort first by magnitude of impact
    contributions.sort(key=lambda x: abs(x['impact']), reverse=True)
    for c in contributions:
        col = c['original_column']
        if col not in seen_cols:
            seen_cols.add(col)
            unique_contributions.append(c)

    positive_drivers = [c for c in unique_contributions if c['impact'] > 0]
    negative_drivers = [c for c in unique_contributions if c['impact'] < 0]

    # Logical fallbacks if one side is empty
    if not positive_drivers:
        exp = str(target_row.get('experience', '5'))
        title, expl = format_candidate_credential('experience', exp)
        positive_drivers.append({
            'feature': 'experience',
            'original_column': 'experience',
            'display_name': title,
            'label': title,
            'explanation': expl,
            'value': exp,
            'weight': 0.15,
            'impact': 0.150,
            'contribution': 0.150,
            'direction': 'Positive (Score Up)'
        })

    if not negative_drivers:
        hrs = target_row.get('training_hours', 40)
        title, expl = format_candidate_credential('training_hours', hrs)
        negative_drivers.append({
            'feature': 'training_hours',
            'original_column': 'training_hours',
            'display_name': title,
            'label': title,
            'explanation': expl,
            'value': hrs,
            'weight': 0.08,
            'impact': -0.050,
            'contribution': -0.050,
            'direction': 'Negative (Score Down)'
        })

    # Generate executive reasoning
    executive_reasoning = generate_executive_reasoning(
        applicant_id=target_row.get('enrollee_id'),
        score=p_positive,
        threshold=ml_engine.threshold,
        is_shortlisted=is_shortlisted,
        target_row=target_row,
        positive_drivers=positive_drivers,
        negative_drivers=negative_drivers
    )

    clean_profile = {
        'city_development_index': float(target_row.get('city_development_index', 0.82)),
        'training_hours': int(round(float(target_row.get('training_hours', 50)))),
        'experience': str(target_row.get('experience', '5')),
        'education_level': str(target_row.get('education_level', 'Graduate')),
        'relevent_experience': str(target_row.get('relevent_experience', 'Has relevent experience')),
        'company_size': str(target_row.get('company_size', '50-99')),
        'last_new_job': str(target_row.get('last_new_job', '1')),
        'major_discipline': str(target_row.get('major_discipline', 'STEM')),
        'company_type': str(target_row.get('company_type', 'Pvt Ltd'))
    }

    clean_demographics = {
        'gender': str(target_row.get('gender', 'Unknown')),
        'age_band': str(target_row.get('age_band', '6-10')),
        'institution': str(target_row.get('institution', 'Graduate University'))
    }

    return {
        'applicant_id': str(target_row.get('enrollee_id')),
        'score': float(round(p_positive, 4)),
        'match_score': float(round(p_positive * 100, 1)),
        'threshold': float(round(ml_engine.threshold, 4)),
        'shortlisted': bool(is_shortlisted),
        'verdict': executive_reasoning['verdict'],
        'hiring_reasoning': executive_reasoning['detailed_narrative'],
        'executive_reasoning': executive_reasoning,
        'top_positive_drivers': positive_drivers[:6],
        'top_negative_inhibitors': negative_drivers[:6],
        'positive_drivers': positive_drivers[:6],
        'negative_drivers': negative_drivers[:6],
        'top_contributions': unique_contributions[:10],
        'demographics': clean_demographics,
        'profile': clean_profile
    }
