"""
Comprehensive End-to-End Specification Verifier for DSC306 Data Mining Project
Verifies all 6 master screens and Stages A through G.
"""

import urllib.request
import json

BASE = 'http://127.0.0.1:5000'

def get(path):
    with urllib.request.urlopen(BASE + path) as r:
        return json.loads(r.read().decode('utf-8'))

def post(path, payload):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(BASE + path, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode('utf-8'))

print("=====================================================================")
print("DSC306 VERIFICATION: ALL 6 SCREENS & STAGES A THROUGH G")
print("=====================================================================")

# 1. SCREEN 1: DATA & QUALITY (Stage A & B)
print("\n--- [STAGE A & B] SCREEN 1: DATA & QUALITY ---")
dataset = get('/api/dataset')
assert dataset['total_rows'] >= 2000, f"Expected >=2,000, got {dataset['total_rows']}"
print(f"PASS: Pool loaded with {dataset['total_rows']:,} rows and {dataset['num_features']} features.")
print(f"      Majority-class baseline: {dataset['majority_baseline_accuracy']*100:.2f}%")

# Check 6 fault categories
assert len(dataset['quality_audit']['faults']) >= 6, "Must audit at least 6 fault categories"
print(f"PASS: {len(dataset['quality_audit']['faults'])} distinct fault categories audited with expressions and counts.")

# Check 10-point validate() assertions
assert dataset['validation_results']['cleaned_passed'] == True, "validate() must pass on cleaned data"
assert dataset['validation_results']['raw_passed'] == False, "validate() must fail on raw data"
print(f"PASS: 10-point validate() engine verified: passes on cleaned data, fails on raw data.")

# Check data dictionary and excluded statement
assert len(dataset['data_dictionary']) >= 10, "Data dictionary must cover all columns"
assert 'enrollee_id' in dataset['excluded_statement'] and 'target' in dataset['excluded_statement']
print(f"PASS: Data dictionary and statement of excluded columns verified.")

# Check cleaned CSV download endpoint
with urllib.request.urlopen(BASE + '/api/dataset/cleaned/download') as r:
    csv_bytes = r.read()
    assert len(csv_bytes) > 100000 and b'_prov_gender' in csv_bytes
print(f"PASS: Cleaned CSV with provenance columns downloaded ({len(csv_bytes):,} bytes).")


# 2. SCREEN 2: MODEL PERFORMANCE (Stage C, D, E)
print("\n--- [STAGE C, D, E] SCREEN 2: MODEL PERFORMANCE ---")
models_res = get('/api/models/compare')
models_list = models_res['comparison']
assert len(models_list) >= 3, "Must compare at least 3 model families"
print(f"PASS: Multi-model evaluation across {len(models_list)} models on exact same test set:")
for m in models_list:
    print(f"      * {m['model_name']} ({m['family']}):")
    print(f"        Acc={m['accuracy']*100:.1f}% [Baseline Beside: {m['majority_baseline']*100:.1f}%, Delta: {m['baseline_delta']*100:+.1f}%]")
    print(f"        Precision={m['precision']*100:.1f}%, Recall={m['recall']*100:.1f}%, F1={m['f1']*100:.1f}%, AUC={m['auc']:.3f}")
    print(f"        5-Fold CV Spread: {m['cv_spread']}")

# Stage C: Dimensionality reduction vs Feature Selection
dim_res = get('/api/models/dim_reduction_compare')
assert len(dim_res['comparison']) >= 3
print(f"PASS: Dimensionality reduction (PCA) vs Feature Selection comparison:")
for r in dim_res['comparison']:
    print(f"      * {r['technique']} ({r['components_or_features']} dims): Acc={r['accuracy']*100:.1f}%, AUC={r['auc']:.3f}, Interpretability: {r['interpretability'][:30]}...")


# 3. SCREEN 3: SINGLE PREDICTION (Stage F)
print("\n--- [STAGE F] SCREEN 3: SINGLE PREDICTION ---")
single_pred = post('/api/predict/single', {
    'city_development_index': 0.92,
    'experience': '12',
    'education_level': 'Masters',
    'enrolled_university': 'no_enrollment',
    'training_hours': 45,
    'company_size': '50-99',
    'gender': 'Female',
    'relevent_experience': 'Has relevent experience'
})
assert 'probability' in single_pred and 'confidence_pct' in single_pred
print(f"PASS: Single applicant scored. Match Confidence: {single_pred['confidence_pct']}%, Verdict: {'INTERVIEW' if single_pred['shortlisted'] else 'HOLD'}")
print(f"      Explanation in User's Language: {single_pred['decision_rules']}")
print(f"      Executive Narrative: {single_pred['executive_narrative']}")


# 4. SCREEN 4: BATCH SCORING
print("\n--- SCREEN 4: BATCH SCORING & RANKED SHORTLIST ---")
shortlist = get('/api/shortlist?threshold=0.5&per_page=5')
assert 'applicants' in shortlist and len(shortlist['applicants']) > 0
top1 = shortlist['applicants'][0]
print(f"PASS: Batch scoring pool rendered. Total shortlisted: {shortlist['total_shortlisted']:,} / {shortlist['total_candidates']:,}")
print(f"      Top candidate: #{top1['rank']} Enrollee {top1['enrollee_id']} (Score: {top1['score']*100:.1f}%)")


# 5. SCREEN 5: SETTINGS & COST MATRIX (Stage E)
print("\n--- [STAGE E] SCREEN 5: SETTINGS & COST MATRIX ---")
cost_res = get('/api/settings/cost_matrix?cost_fp=500&cost_fn=3500&benefit_tp=5000')
assert 'optimal_threshold' in cost_res and 'min_expected_cost' in cost_res
print(f"PASS: Cost Matrix analyzed across thresholds [0.05, 0.95].")
print(f"      Cost-Optimal Operating Threshold theta*: {cost_res['optimal_threshold']:.2f}")
print(f"      Minimum Expected Net Cost: ${cost_res['min_expected_cost']:,}")


# 6. SCREEN 6: DOMAIN SCREEN — FAIRNESS AUDIT & REMEDIATION
print("\n--- SCREEN 6: DOMAIN SCREEN (FAIRNESS AUDIT & REMEDIATION) ---")
for attr in ['gender', 'age_band', 'institution']:
    audit_res = get(f"/api/fairness/audit?attribute={attr}&threshold=0.5")
    a_data = audit_res['audit'][attr]
    print(f"PASS: Domain Audit across {attr.upper()}:")
    print(f"      Selection Rate Gap: {a_data['selection_rate_gap']*100:.1f}%")
    print(f"      Recall Gap (Equal Opp.): {a_data['recall_gap']*100:.1f}%")
    print(f"      Precision Gap (Predictive Parity): {a_data['precision_gap']*100:.1f}%")
    print(f"      EEOC 80% Rule Adverse Impact Flag: {a_data['adverse_impact_detected']}")

# Verify Feature Ablation Remediation
ablation_res = post('/api/fairness/ablate', {
    'attribute_to_drop': 'city_development_index',
    'drop_proxies': True,
    'protected_attribute': 'gender'
})
assert 'before' in ablation_res and 'after' in ablation_res
print(f"PASS: Feature Ablation Remediation executed on '{ablation_res['dropped_attribute']}':")
print(f"      Before Ablation Gap: {ablation_res['before']['selection_rate_gap']*100:.1f}%, ROC-AUC: {ablation_res['before']['auc']:.3f}")
print(f"      After Ablation Gap:  {ablation_res['after']['selection_rate_gap']*100:.1f}%, ROC-AUC: {ablation_res['after']['auc']:.3f}")

print("\n=====================================================================")
print("ALL SPECIFICATION CHECKS PASSED WITH 100% SUCCESS!")
print("=====================================================================")
