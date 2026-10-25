"""
Applicant Shortlisting Console with Fairness Audit
Main Flask Application Server
"""

import os
import io
import csv
import math
from flask import Flask, render_template, request, jsonify, Response, send_file
from backend.data_manager import DataManager
from backend.ml_engine import ModelEngine
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

# Train baseline Logistic Regression model on startup
print("Initializing baseline Logistic Regression model...")
ml_engine.train(model_type='logistic_regression', threshold=0.5)
print("Baseline model trained successfully.")


@app.route('/')
def index():
    """Renders the main single-page recruiting console."""
    return render_template('index.html')


@app.route('/api/dataset', methods=['GET', 'POST'])
def handle_dataset():
    """
    GET: Returns dataset summary, demographic distributions, and preview.
    POST: Accepts uploaded CSV applicant pool, reloads data and retrains baseline.
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
            ml_engine.train(model_type='logistic_regression', threshold=0.5)
            summary = data_manager.get_summary()
            return jsonify({'message': 'File uploaded and processed successfully', 'summary': summary})
        except Exception as e:
            return jsonify({'error': f'Failed to process file: {str(e)}'}), 500

    # GET request
    summary = data_manager.get_summary()
    return jsonify(summary)


@app.route('/api/preprocess', methods=['GET'])
def get_preprocessing_info():
    """
    Returns missing value handling summary, one-hot encoding summary,
    and the proxy feature correlation table.
    """
    return jsonify({
        'num_features': len(data_manager.feature_names),
        'feature_names': data_manager.feature_names,
        'column_origins': data_manager.column_origin_map,
        'categories_map': data_manager.categories_map,
        'medians': data_manager.medians,
        'correlations': data_manager.correlations
    })


@app.route('/api/train', methods=['POST'])
def train_model():
    """
    Trains chosen model (Logistic Regression or Random Forest) with specified threshold.
    Returns evaluation metrics, confusion matrix, and ROC curve data.
    """
    data = request.get_json() or {}
    model_type = data.get('model_type', 'logistic_regression')
    threshold = float(data.get('threshold', 0.5))

    try:
        metrics = ml_engine.train(model_type=model_type, threshold=threshold)
        return jsonify(metrics)
    except Exception as e:
        return jsonify({'error': f'Model training failed: {str(e)}'}), 500


@app.route('/api/shortlist', methods=['GET'])
def get_shortlist():
    """
    Returns ranked applicants ordered by interview probability score.
    Supports probability thresholding or top-N cutoff, filtering,
    and CSV export.
    """
    threshold = float(request.args.get('threshold', ml_engine.threshold))
    top_n = request.args.get('top_n', type=int)
    filter_status = request.args.get('filter', 'all') # 'all', 'shortlisted', 'rejected'
    export_csv = request.args.get('export', 'false').lower() == 'true'

    # Score all processed applicants
    X_all = data_manager.get_feature_matrix(data_manager.processed_data, ml_engine.active_features)
    probs_matrix = ml_engine.model.predict_proba(X_all)

    ranked_list = []
    for idx, (row, prob_pair) in enumerate(zip(data_manager.processed_data, probs_matrix)):
        p1 = prob_pair[1]
        is_short = p1 >= threshold
        ranked_list.append({
            'rank': 0,
            'enrollee_id': row.get('enrollee_id'),
            'score': round(p1, 4),
            'shortlisted': is_short,
            'gender': row.get('gender'),
            'age_band': row.get('age_band'),
            'institution': row.get('institution'),
            'education_level': row.get('education_level'),
            'experience': row.get('experience'),
            'city_development_index': row.get('city_development_index'),
            'company_size': row.get('company_size'),
            'target': row.get('target')
        })

    # Sort descending by score
    ranked_list.sort(key=lambda x: x['score'], reverse=True)

    # Assign ranks
    for r_idx, item in enumerate(ranked_list):
        item['rank'] = r_idx + 1

    # Apply top_n cutoff if specified
    if top_n and top_n > 0:
        for idx, item in enumerate(ranked_list):
            item['shortlisted'] = (idx < top_n)

    # Apply filter
    if filter_status == 'shortlisted':
        filtered = [x for x in ranked_list if x['shortlisted']]
    elif filter_status == 'rejected':
        filtered = [x for x in ranked_list if not x['shortlisted']]
    else:
        filtered = ranked_list

    # Handle CSV Export
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

    # Paginate / limit output for UI performance
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
    """
    Returns feature attribution and criteria breakdown for an individual applicant.
    Uses coefficient * feature_value for Logistic Regression.
    """
    result = explain_applicant(applicant_id, data_manager, ml_engine)
    if 'error' in result:
        return jsonify(result), 404
    return jsonify(result)


@app.route('/api/fairness/audit', methods=['GET'])
def get_fairness_audit():
    """
    Main Fairness Challenge Route:
    Returns group-by-group metrics (size, selection rate, recall, precision),
    80% rule violations, recall and precision gaps, small-group alerts,
    and disparity driver analysis.
    """
    threshold = float(request.args.get('threshold', ml_engine.threshold))
    protected_attr = request.args.get('attribute', 'gender') # 'gender', 'age_band', 'institution'

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
    Fairness Challenge Route: Before vs After Feature Ablation.
    Drops selected attribute (and optionally top 3 proxies) from model input features only.
    Retrains on same fixed split, calculates Before vs After metrics and deltas.
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
    # Start web server on 127.0.0.1:5000
    app.run(host='127.0.0.1', port=5000, debug=False)
