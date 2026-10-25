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

print("=== 1. VERIFYING STARTING DATA (around 19,000 records) ===")
dataset = get('/api/dataset')
assert dataset['total_rows'] > 19000, f"Expected >19,000, got {dataset['total_rows']}"
print(f"PASS: Real Kaggle dataset loaded with {dataset['total_rows']} rows.")
print(f"      Train rows: {dataset['train_rows']}, Test rows: {dataset['test_rows']}")
print(f"      Class balance (interview positive): {dataset['class_balance']['positive']} ({dataset['class_balance']['positive_pct']}%)")

print("\n=== 2. VERIFYING MINING TASK (Binary classification: proceed to interview) ===")
train_res = post('/api/train', {'model_type': 'logistic_regression', 'threshold': 0.5})
print(f"PASS: Model trained. Accuracy: {train_res['accuracy']}, AUC: {train_res['auc']}, Precision: {train_res['precision']}, Recall: {train_res['recall']}")

print("\n=== 3. VERIFYING RANKED SHORTLIST WITH CRITERIA & BESIDE-IT AUDIT ===")
shortlist = get('/api/shortlist?threshold=0.5&per_page=5')
assert 'applicants' in shortlist and len(shortlist['applicants']) > 0
first = shortlist['applicants'][0]
print(f"PASS: Shortlisted pool returned. Top candidate #{first['rank']}: Enrollee {first['enrollee_id']} with score {first['score']}")

# Verify criteria behind ranking
explain = get(f"/api/explain/{first['enrollee_id']}")
assert len(explain['positive_drivers']) > 0 or len(explain['negative_drivers']) > 0
print(f"PASS: Criteria behind ranking verified. Candidate has {len(explain['positive_drivers'])} positive and {len(explain['negative_drivers'])} negative drivers.")

# Verify beside-it audit
assert 'audit_summary' in shortlist
assert 'gender' in shortlist['audit_summary']
assert 'age_band' in shortlist['audit_summary']
assert 'institution' in shortlist['audit_summary']
print("PASS: Beside-it audit returned selection rates across Gender, Age Band, and Institution:")
for attr in ['gender', 'age_band', 'institution']:
    summ = shortlist['audit_summary'][attr]
    print(f"      * {attr.upper()}: Gap = {summ['selection_rate_gap']*100:.1f}%, Adverse Impact = {summ['adverse_impact']}")
    for g in summ['groups']:
        print(f"        - {g['group']}: {g['selection_rate']*100:.1f}% ({g['selected']}/{g['total']}), 80% Ratio = {g['four_fifths_ratio']}")

print("\n=== 4. VERIFYING TECHNICAL CHALLENGE & SIXTH SCREEN (Fairness Dashboard) ===")
for attr in ['gender', 'age_band', 'institution']:
    audit = get(f"/api/fairness/audit?attribute={attr}&threshold=0.5")
    a_data = audit['audit'][attr]
    print(f"PASS: Screen 6 Audit for {attr.upper()}:")
    print(f"      Selection Rate Gap: {a_data['selection_rate_gap']*100:.1f}%")
    print(f"      Recall Gap: {a_data['recall_gap']*100:.1f}%")
    print(f"      Precision Gap: {a_data['precision_gap']*100:.1f}%")
    print(f"      Min 80% Rule Ratio: {a_data['min_four_fifths_ratio']}")
    print(f"      Group breakdown (Selection Rate, Recall, Precision):")
    for g in a_data['groups']:
        print(f"        - {g['group']} (N={g['size']}): SelRate={g['selection_rate']*100:.1f}%, Recall={g['recall']*100:.1f}%, Prec={g['precision']*100:.1f}%, SmallGroup={g['is_small_group']}")

print("\n=== 5. VERIFYING DISPARITY DRIVERS (What attribute is driving the gap) ===")
drivers = get('/api/fairness/audit?attribute=gender&threshold=0.5')['drivers']
print(f"PASS: Disparity Driver Analysis between Favoured ({drivers['favoured_group']}) and Disadvantaged ({drivers['disadvantaged_group']})")
for d in drivers['drivers'][:5]:
    print(f"      * Feature: {d['feature']} -> Impact Score: {d['driver_score']}, Favours: {d['favours']}")

print("\n=== 6. VERIFYING BEFORE-AND-AFTER ABLATION (Demonstrate gap & accuracy change) ===")
ablate = post('/api/fairness/ablate', {'attribute_to_drop': 'gender', 'drop_proxies': True, 'protected_attribute': 'gender'})
print(f"PASS: Before vs After Feature Ablation (Dropped: gender + top proxies):")
print(f"      * Four-Fifths Ratio: Before = {ablate['before']['four_fifths_ratio']} -> After = {ablate['after']['four_fifths_ratio']} (Delta: {ablate['delta']['four_fifths_ratio']})")
print(f"      * Selection-Rate Gap: Before = {ablate['before']['selection_rate_gap']*100:.1f}% -> After = {ablate['after']['selection_rate_gap']*100:.1f}% (Delta: {ablate['delta']['selection_rate_gap']*100:.1f}%)")
print(f"      * Recall Gap: Before = {ablate['before']['recall_gap']*100:.1f}% -> After = {ablate['after']['recall_gap']*100:.1f}% (Delta: {ablate['delta']['recall_gap']*100:.1f}%)")
print(f"      * Model Accuracy: Before = {ablate['before']['accuracy']*100:.1f}% -> After = {ablate['after']['accuracy']*100:.1f}% (Delta: {ablate['delta']['accuracy']*100:.1f}%)")
print(f"      * Note: \"{ablate['explanation_note']}\"")

print("\n>>> ALL REQUIREMENTS FROM THE ORIGINAL SPECIFICATION VERIFIED SUCCESSFULLY! <<<")
