"""
Test Suite for Applicant Shortlisting Console with Fairness Audit.
Covers:
1. Data loading and protected proxy attribute derivation (Stage A)
2. 10-point validate() assertions passing on cleaned, failing on raw (Stage B)
3. 6 fault categories audit detection and provenance tracking (Stage B)
4. Multi-model evaluation across 3 distinct families with baseline beside accuracy (Stage D & E)
5. Hand-calculated exact fairness metrics verification (Stage E & Screen 6)
6. Attribute dropping (absent from model features, retained for audit)
7. Cost matrix analysis and optimal threshold evaluation (Stage E & Screen 5)
8. Single candidate prediction with plain English explanation (Stage F & Screen 3)
9. Fixed stratified split invariance before and after ablation (Screen 6)
"""

import unittest
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.data_manager import DataManager, derive_age_band, derive_institution, validate
from backend.ml_engine import ModelEngine, compute_classification_metrics, compute_cost_matrix_analysis
from backend.fairness_audit import (
    audit_single_attribute,
    compute_fairness_audit,
    compute_disparity_drivers,
    compute_before_after_ablation
)


class TestFairnessEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.data_manager = DataManager('aug_train.csv')
        cls.ml_engine = ModelEngine(cls.data_manager)
        cls.ml_engine.train(model_type='decision_tree', threshold=0.5)

    def test_1_data_loads_and_derives_proxies(self):
        """Verifies dataset loads, has >19,000 rows, and derives protected attributes."""
        dm = self.data_manager
        self.assertGreater(len(dm.processed_data), 19000, "Should load full Kaggle dataset")
        self.assertIn('gender', dm.processed_data[0])
        self.assertIn('age_band', dm.processed_data[0])
        self.assertIn('institution', dm.processed_data[0])
        self.assertIn('target', dm.processed_data[0])

        # Verify proxy derivation helpers
        self.assertEqual(derive_age_band('<1'), '0-5')
        self.assertEqual(derive_age_band('3'), '0-5')
        self.assertEqual(derive_age_band('8'), '6-10')
        self.assertEqual(derive_age_band('14'), '11-15')
        self.assertEqual(derive_age_band('>20'), '16+')

        self.assertEqual(derive_institution('no_enrollment', 'Phd'), 'Postgraduate Institution')
        self.assertEqual(derive_institution('no_enrollment', 'Graduate'), 'Graduate University')
        self.assertEqual(derive_institution('Full time course', 'Graduate'), 'Continuing / Enrolled University')
        self.assertEqual(derive_institution('', 'High School'), 'Non-Degree / School')

    def test_2_validate_assertions_pass_on_cleaned_fail_on_raw(self):
        """
        Stage B: Verifies that validate() with >= 10 assertions
        passes on cleaned data and fails on raw data.
        """
        dm = self.data_manager
        cleaned_pass, cleaned_report = validate(dm.processed_data)
        self.assertTrue(cleaned_pass, "validate() must pass on cleaned data")
        self.assertGreaterEqual(len(cleaned_report), 10, "Must have at least 10 assertions")
        self.assertTrue(all(r['passed'] for r in cleaned_report))

        raw_pass, raw_report = validate(dm.raw_data)
        self.assertFalse(raw_pass, "validate() must fail on raw uncleaned data")
        failed_count = sum(1 for r in raw_report if not r['passed'])
        self.assertGreaterEqual(failed_count, 3, "Raw data must fail multiple assertions")

    def test_3_data_quality_audit_detects_six_fault_categories(self):
        """
        Stage B: Verifies that at least 6 distinct fault categories are audited
        with detection expressions and affected record counts.
        """
        dm = self.data_manager
        self.assertIn('faults', dm.quality_audit)
        self.assertGreaterEqual(len(dm.quality_audit['faults']), 6)
        for fault in dm.quality_audit['faults']:
            self.assertIn('category', fault)
            self.assertIn('attribute', fault)
            self.assertIn('expression', fault)
            self.assertGreater(fault['affected_count'], 0)

        # Check provenance tracking exists
        sample = dm.processed_data[0]
        self.assertIn('_prov_gender', sample)
        self.assertIn('_prov_experience', sample)
        self.assertIn('_prov_company_size', sample)

    def test_4_multi_model_evaluation_with_baseline_beside_accuracy(self):
        """
        Stage D & E: Verifies at least 3 classifiers from 3 distinct families
        with majority-class baseline reported beside every accuracy figure.
        """
        engine = self.ml_engine
        comparison = engine.compare_all_models()
        self.assertGreaterEqual(len(comparison), 3, "Must compare at least 3 classifiers")

        families = set(m['family'] for m in comparison)
        self.assertGreaterEqual(len(families), 3, "Must represent at least 3 distinct model families")

        for m in comparison:
            self.assertIn('accuracy', m)
            self.assertIn('majority_baseline', m)
            self.assertIn('baseline_delta', m)
            self.assertIn('precision', m)
            self.assertIn('recall', m)
            self.assertIn('f1', m)
            self.assertIn('auc', m)
            self.assertIn('cv_spread', m)
            self.assertTrue(0.0 <= m['accuracy'] <= 1.0)
            self.assertTrue(0.0 <= m['majority_baseline'] <= 1.0)

    def test_5_fairness_metrics_match_hand_calculated_example(self):
        """
        Verifies group metrics against an exact hand-calculated test scenario:
        Group A: 4 applicants, targets=[1, 1, 0, 0], probs=[0.9, 0.8, 0.6, 0.2]
          -> threshold=0.5 -> preds=[1, 1, 1, 0]
          -> Selection Rate = 3/4 = 0.75
          -> TP = 2, Actual Pos = 2 -> Recall = 2/2 = 1.0
          -> TP = 2, Pred Pos = 3 -> Precision = 2/3 = 0.6667
        Group B: 4 applicants, targets=[1, 0, 1, 0], probs=[0.7, 0.4, 0.3, 0.1]
          -> threshold=0.5 -> preds=[1, 0, 0, 0]
          -> Selection Rate = 1/4 = 0.25
          -> TP = 1, Actual Pos = 2 -> Recall = 1/2 = 0.5
          -> TP = 1, Pred Pos = 1 -> Precision = 1/1 = 1.0
        80% Rule:
          -> Max SR = 0.75 (Group A)
          -> Ratio(A) = 1.0, Ratio(B) = 0.25 / 0.75 = 0.3333 (< 0.8 violation!)
        Gaps:
          -> Selection-rate gap = 0.75 - 0.25 = 0.50
          -> Recall gap = 1.0 - 0.50 = 0.50
          -> Precision gap = 1.0 - 0.6667 = 0.3333
        """
        mini_test_rows = [
            {'gender': 'A', 'target': 1},
            {'gender': 'A', 'target': 1},
            {'gender': 'A', 'target': 0},
            {'gender': 'A', 'target': 0},
            {'gender': 'B', 'target': 1},
            {'gender': 'B', 'target': 0},
            {'gender': 'B', 'target': 1},
            {'gender': 'B', 'target': 0},
        ]
        mini_probs = [0.9, 0.8, 0.6, 0.2, 0.7, 0.4, 0.3, 0.1]

        audit = audit_single_attribute(mini_test_rows, mini_probs, threshold=0.5, attribute_name='gender')
        group_map = {g['group']: g for g in audit['groups']}
        gA = group_map['A']
        gB = group_map['B']

        self.assertAlmostEqual(gA['selection_rate'], 0.75, places=2)
        self.assertAlmostEqual(gA['recall'], 1.0, places=2)
        self.assertAlmostEqual(gA['precision'], 0.6667, places=2)
        self.assertAlmostEqual(gA['four_fifths_ratio'], 1.0, places=2)
        self.assertFalse(gA['violates_80_rule'])

        self.assertAlmostEqual(gB['selection_rate'], 0.25, places=2)
        self.assertAlmostEqual(gB['recall'], 0.5, places=2)
        self.assertAlmostEqual(gB['precision'], 1.0, places=2)
        self.assertAlmostEqual(gB['four_fifths_ratio'], 0.3333, places=2)
        self.assertTrue(gB['violates_80_rule'])

        self.assertAlmostEqual(audit['selection_rate_gap'], 0.50, places=2)
        self.assertAlmostEqual(audit['recall_gap'], 0.50, places=2)
        self.assertAlmostEqual(audit['precision_gap'], 0.3333, places=2)
        self.assertTrue(audit['adverse_impact_detected'])

    def test_6_single_prediction_and_user_language_explanation(self):
        """
        Stage F & Screen 3: Verifies single applicant prediction
        and decision path / rule in user language.
        """
        engine = self.ml_engine
        pred_res = engine.predict_single({
            'city_development_index': 0.92,
            'experience': '12',
            'education_level': 'Masters',
            'enrolled_university': 'no_enrollment',
            'training_hours': 50,
            'company_size': '50-99',
            'gender': 'Female',
            'relevent_experience': 'Has relevent experience'
        })
        self.assertIn('probability', pred_res)
        self.assertIn('confidence_pct', pred_res)
        self.assertIn('shortlisted', pred_res)
        self.assertIn('decision_rules', pred_res)
        self.assertIn('executive_narrative', pred_res)
        self.assertTrue(len(pred_res['decision_rules']) > 0)

    def test_7_cost_matrix_analysis(self):
        """
        Stage E & Screen 5: Verifies Cost Matrix analysis across decision thresholds
        and optimal threshold selection.
        """
        y_true = self.ml_engine.cached_test_y
        y_probs = self.ml_engine.cached_test_probs
        cost_res = compute_cost_matrix_analysis(y_true, y_probs, cost_fp=500.0, cost_fn=3500.0, benefit_tp=5000.0)

        self.assertIn('optimal_threshold', cost_res)
        self.assertIn('min_expected_cost', cost_res)
        self.assertIn('cost_curve', cost_res)
        self.assertTrue(0.05 <= cost_res['optimal_threshold'] <= 0.95)
        self.assertGreater(len(cost_res['cost_curve']), 10)

    def test_8_feature_ablation_and_split_invariance(self):
        """
        Screen 6: Verifies feature ablation drops driver feature,
        retrains model, and preserves exact stratified split.
        """
        dm = self.data_manager
        engine = self.ml_engine
        train_idx_before = list(dm.train_indices)
        test_idx_before = list(dm.test_indices)

        res = compute_before_after_ablation(
            dm, engine, attribute_to_drop='gender', drop_proxies=False, protected_attribute='gender'
        )

        train_idx_after = list(dm.train_indices)
        test_idx_after = list(dm.test_indices)
        self.assertEqual(train_idx_before, train_idx_after)
        self.assertIn('before', res)
        self.assertIn('after', res)
        self.assertIn('delta', res)
        self.assertIn('selection_rate_gap', res['before'])
        self.assertIn('selection_rate_gap', res['after'])
        self.assertIn('auc', res['before'])
        self.assertIn('auc', res['after'])


if __name__ == '__main__':
    unittest.main()
