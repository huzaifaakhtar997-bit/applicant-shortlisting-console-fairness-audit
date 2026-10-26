"""
Applicant Shortlisting Console with Fairness Audit
Main Flask Application Server
Compliant with DSC306 Data Mining Course Master Specification (Stages A through G)
"""

import os
import io
import csv
import math
from flask import Flask, render_template, request, jsonify, Response, send_file
from backend.data_manager import DataManager, DATA_DICTIONARY, EXCLUDED_COLUMNS_STATEMENT
from backend.ml_engine import ModelEngine, compute_cost_matrix_analysis
from backend.fairness_audit import (
    compute_fairness_audit,
    compute_disparity_drivers,
    compute_before_after_ablation
)
from backend.explainability import explain_applicant

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32 MB max upload

# Initialize Core Services
DATASET_PATH = os.path.join(os.path.dirname(__file__), 'aug_train.csv')
data_manager = DataManager(DATASET_PATH)
ml_engine = ModelEngine(data_manager)

# Train baseline Decision Tree model on startup
print("Initializing baseline Decision Tree model...")
ml_engine.train(model_type='decision_tree', threshold=0.5)
print("Baseline model trained successfully.")


@app.route('/')
def index():
    """Renders the main six-screen recruiting console."""
    return render_template('index.html')


# ==============================================================================
# SCREEN 1: DATA & QUALITY (Stage A & B)
# ==============================================================================

@app.route('/api/dataset', methods=['GET', 'POST'])
def handle_dataset():
    """
    GET: Returns dataset summary, demographic distributions, 6 fault categories,
         before-and-after repair counts, 10-point validate() report, and data dictionary.
    POST: Accepts uploaded CSV applicant pool, reloads data, re-audits, and retrains baseline.
    """
    global data_manager, ml_engine

    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No file part in request'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        try:
            upload_path = os.path.join(os.path.dirname(__file__), 'uploaded_applicants.csv')
            file.save(upload_path)
            data_manager = DataManager(upload_path)
            ml_engine = ModelEngine(data_manager)
            ml_engine.train(model_type='decision_tree', threshold=0.5)
            summary = data_manager.get_summary()
            return jsonify({'message': 'File uploaded, audited and processed successfully', 'summary': summary})
        except Exception as e:
            return jsonify({'error': f'Failed to process file: {str(e)}'}), 500

    summary = data_manager.get_summary()
    return jsonify(summary)


@app.route('/api/dataset/cleaned/download', methods=['GET'])
def download_cleaned_dataset():
    """
    Stage B: Allows the marker/user to download the cleaned CSV file
    containing all repaired fields and provenance tracking columns.
    """
    output = io.StringIO()
    if not data_manager.processed_data:
        return Response("Dataset is empty", mimetype="text/plain")

    fieldnames = list(data_manager.processed_data[0].keys())
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in data_manager.processed_data:
        writer.writerow(row)

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=cleaned_applicants_with_provenance.csv"}
    )


@app.route('/api/preprocess', methods=['GET'])
def get_preprocessing_info():
    """Returns proxy correlation matrix and encoding mapping."""
    return jsonify({
        'num_features': len(data_manager.feature_names),
        'feature_names': data_manager.feature_names,
        'column_origins': data_manager.column_origin_map,
        'categories_map': data_manager.categories_map,
        'medians': data_manager.medians,
        'correlations': data_manager.correlations
    })


# ==============================================================================
# SCREEN 2: MODEL PERFORMANCE (Stage C, D, E)
# ==============================================================================

@app.route('/api/models/compare', methods=['GET'])
def compare_models():
    """
    Stage D & E: Comparison table across classifiers from distinct families
    (Decision Tree, Naive Bayes, KNN, Logistic Regression) on the same test set.
    Reports majority-class baseline beside EVERY accuracy figure, precision,
    recall, F1, ROC-AUC, 5-fold CV spread, and confusion matrix.
    """
    comparison = ml_engine.compare_all_models()
    return jsonify({
        'comparison': comparison,
        'majority_baseline_accuracy': data_manager.get_summary().get('majority_baseline_accuracy', 0.751),
        'metrics_justification': {
            'precision': 'Recruiter interview bandwidth is constrained. High precision minimizes wasted interviewer hours on false-positive candidates.',
            'recall': 'Opportunity cost of missing a high-performing data scientist is severe. High recall prevents false-negative talent loss to competitors.'
        }
    })


@app.route('/api/models/dim_reduction_compare', methods=['GET'])
def compare_dimensionality_reduction():
    """
    Stage C: Compares Feature Subset Selection vs PCA Dimensionality Reduction
    on the exact same model (Decision Tree).
    """
    results = ml_engine.compare_feature_selection_vs_pca(target_components=10)
    return jsonify({
        'comparison': results,
        'rescaling_decisions': {
            'decision_tree': 'Rescaling NOT needed. Decision tree splits are invariant to monotonic transformations.',
            'naive_bayes': 'Gaussian distribution scales feature variance independently per class.',
            'knn': 'Rescaling STRICTLY REQUIRED. Euclidean distance would be overwhelmed by training_hours (1-336) without standard scaling.'
        }
    })


@app.route('/api/train', methods=['POST'])
def train_model():
    """Trains specified model with chosen threshold."""
    data = request.get_json() or {}
    model_type = data.get('model_type', 'decision_tree')
    threshold = float(data.get('threshold', 0.5))

    try:
        metrics = ml_engine.train(model_type=model_type, threshold=threshold)
        return jsonify(metrics)
    except Exception as e:
        return jsonify({'error': f'Model training failed: {str(e)}'}), 500


# ==============================================================================
# SCREEN 3: SINGLE PREDICTION (Stage F)
# ==============================================================================

@app.route('/api/predict/single', methods=['POST'])
def predict_single_applicant():
    """
    Stage F: A form for one applicant case -> prediction (Interview / Hold),
    confidence score %, and explanation written in user's language.
    """
    data = request.get_json() or {}
    try:
        result = ml_engine.predict_single(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Single prediction failed: {str(e)}'}), 500


# ==============================================================================
# SCREEN 4: BATCH SCORING
# ==============================================================================

@app.route('/api/shortlist', methods=['GET'])
def get_shortlist():
    """
    Screen 4: Ranked, filterable shortlist table with thresholding, top-n cutoff,
    pagination, and CSV export.
    """
    threshold = float(request.args.get('threshold', ml_engine.threshold))
    top_n = request.args.get('top_n', type=int)
    filter_status = request.args.get('filter', 'all')
    export_csv = request.args.get('export', 'false').lower() == 'true'

    # Score all processed applicants
    X_all = data_manager.get_feature_matrix(
        data_manager.processed_data,
        ml_engine.active_features,
        standardize=(ml_engine.model_type == 'knn')
    )
    probs_matrix = ml_engine.model.predict_proba(X_all)

    ranked_list = []
    for idx, (row, prob_pair) in enumerate(zip(data_manager.processed_data, probs_matrix)):
        p1 = float(prob_pair[1])
        is_short = bool(p1 >= float(threshold))
        ranked_list.append({
            'rank': 0,
            'enrollee_id': str(row.get('enrollee_id')),
            'score': float(round(p1, 4)),
            'shortlisted': is_short,
            'gender': str(row.get('gender')),
            'age_band': str(row.get('age_band')),
            'institution': str(row.get('institution')),
            'education_level': str(row.get('education_level')),
            'experience': str(row.get('experience')),
            'city_development_index': float(row.get('city_development_index', 0.8)),
            'company_size': str(row.get('company_size')),
            'target': int(row.get('target', 0))
        })

    # Sort descending by score
    ranked_list.sort(key=lambda x: x['score'], reverse=True)
    for r_idx, item in enumerate(ranked_list):
        item['rank'] = r_idx + 1

    if top_n and top_n > 0:
        for idx, item in enumerate(ranked_list):
            item['shortlisted'] = bool(idx < top_n)

    if filter_status == 'shortlisted':
        filtered = [x for x in ranked_list if x['shortlisted']]
    elif filter_status == 'rejected':
        filtered = [x for x in ranked_list if not x['shortlisted']]
    else:
        filtered = ranked_list

    if export_csv:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'Rank', 'Enrollee_ID', 'Shortlist_Score', 'Shortlist_Status',
            'Gender', 'Age_Band', 'Institution', 'Education_Level',
            'Experience', 'City_Dev_Index', 'Company_Size', 'Target_Ground_Truth'
        ])
        for row in filtered:
            writer.writerow([
                row['rank'], row['enrollee_id'], row['score'],
                'SHORTLISTED' if row['shortlisted'] else 'NOT_SHORTLISTED',
                row['gender'], row['age_band'], row['institution'],
                row['education_level'], row['experience'],
                row['city_development_index'], row['company_size'], row['target']
            ])
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=applicant_shortlist.csv"}
        )

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    start = (page - 1) * per_page
    end = start + per_page

    total_shortlisted = sum(1 for x in ranked_list if x['shortlisted'])

    return jsonify({
        'total_candidates': len(ranked_list),
        'total_shortlisted': total_shortlisted,
        'selection_rate': round(total_shortlisted / len(ranked_list), 4) if ranked_list else 0.0,
        'threshold': threshold,
        'top_n': top_n,
        'page': page,
        'per_page': per_page,
        'total_pages': math.ceil(len(filtered) / per_page),
        'applicants': filtered[start:end]
    })


@app.route('/api/explain/<applicant_id>', methods=['GET'])
def explain_candidate(applicant_id):
    """Returns candidate-specific feature attribution and hiring reasoning."""
    result = explain_applicant(applicant_id, data_manager, ml_engine)
    if 'error' in result:
        return jsonify(result), 404
    return jsonify(result)


# ==============================================================================
# SCREEN 5: SETTINGS & COST MATRIX (Stage E)
# ==============================================================================

@app.route('/api/settings/cost_matrix', methods=['GET', 'POST'])
def handle_cost_matrix():
    """
    Stage E: Evaluates Cost Matrix across decision thresholds.
    Allows editing cost parameters (cost_fp, cost_fn, benefit_tp, cost_tn)
    and reports live expected cost curve with optimal threshold theta*.
    """
    if request.method == 'POST':
        data = request.get_json() or {}
        cost_fp = float(data.get('cost_fp', 500.0))
        cost_fn = float(data.get('cost_fn', 3500.0))
        benefit_tp = float(data.get('benefit_tp', 5000.0))
        cost_tn = float(data.get('cost_tn', 0.0))
    else:
        cost_fp = float(request.args.get('cost_fp', 500.0))
        cost_fn = float(request.args.get('cost_fn', 3500.0))
        benefit_tp = float(request.args.get('benefit_tp', 5000.0))
        cost_tn = float(request.args.get('cost_tn', 0.0))

    y_test = ml_engine.cached_test_y
    y_probs = ml_engine.cached_test_probs

    if not y_test or not y_probs:
        ml_engine.train(ml_engine.model_type, ml_engine.threshold)
        y_test = ml_engine.cached_test_y
        y_probs = ml_engine.cached_test_probs

    analysis = compute_cost_matrix_analysis(y_test, y_probs, cost_fp, cost_fn, benefit_tp, cost_tn)
    return jsonify(analysis)


# ==============================================================================
# SCREEN 6: DOMAIN SCREEN — FAIRNESS AUDIT & REMEDIATION
# ==============================================================================

@app.route('/api/fairness/audit', methods=['GET'])
def get_fairness_audit():
    """
    Project 5 Domain Screen: Audits selection rate, recall, and precision
    across gender, age band, and institution; detects EEOC 80% rule violations,
    small-group warnings, and calculates disparity drivers.
    """
    threshold = float(request.args.get('threshold', ml_engine.threshold))
    protected_attr = request.args.get('attribute', 'gender')

    audit_data = compute_fairness_audit(data_manager, ml_engine, threshold=threshold)
    driver_data = compute_disparity_drivers(data_manager, ml_engine, protected_attribute=protected_attr, top_k=8)

    return jsonify({
        'audit': audit_data,
        'drivers': driver_data,
        'active_protected_attribute': protected_attr,
        'model_type': ml_engine.model_type,
        'threshold': threshold
    })


@app.route('/api/fairness/ablate', methods=['POST'])
def ablate_attribute():
    """
    Project 5 Domain Screen: Feature Ablation Remediation.
    Drops driver feature, retrains model on same fixed split,
    and returns Before vs After fairness gap and ROC-AUC tradeoff.
    """
    data = request.get_json() or {}
    attribute_to_drop = data.get('attribute_to_drop')
    drop_proxies = bool(data.get('drop_proxies', False))
    protected_attribute = data.get('protected_attribute', 'gender')

    if not attribute_to_drop:
        return jsonify({'error': 'Missing attribute_to_drop parameter'}), 400

    try:
        result = compute_before_after_ablation(
            data_manager,
            ml_engine,
            attribute_to_drop=attribute_to_drop,
            drop_proxies=drop_proxies,
            protected_attribute=protected_attribute
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Ablation failed: {str(e)}'}), 500


if __name__ == '__main__':
    # Starts cleanly with one documented command: python app.py
    print("Starting Applicant Shortlisting Console on http://127.0.0.1:5000 ...")
    app.run(host='127.0.0.1', port=5000, debug=False)
