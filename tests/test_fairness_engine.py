"""
Test Suite for Applicant Shortlisting Console with Fairness Audit.
Covers:
1. Data loading and protected proxy attribute derivation
2. Model training and valid metrics computation
3. Hand-calculated exact fairness metrics verification
4. Attribute dropping (absent from model features, retained for audit)
5. Fixed stratified split invariance before and after ablation
"""

import unittest
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.data_manager import DataManager, derive_age_band, derive_institution
from backend.ml_engine import ModelEngine, compute_classification_metrics
from backend.fairness_audit import (
    audit_single_attribute,
    compute_fairness_audit,
    compute_disparity_drivers,
    compute_before_after_ablation
)


class TestFairnessEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Load the real dataset
        cls.data_manager = DataManager('aug_train.csv')
        cls.ml_engine = ModelEngine(cls.data_manager)
        cls.ml_engine.train(model_type='logistic_regression', threshold=0.5)

    def test_1_data_loads(self):
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

    def test_2_model_trains_and_gives_valid_metrics(self):
        """Verifies model trains and produces valid evaluation metrics."""
        metrics = self.ml_engine.latest_metrics
        self.assertIn('accuracy', metrics)
        self.assertIn('precision', metrics)
        self.assertIn('recall', metrics)
        self.assertIn('f1', metrics)
        self.assertIn('auc', metrics)
        self.assertIn('confusion_matrix', metrics)

        # Range checks
        self.assertTrue(0.0 <= metrics['accuracy'] <= 1.0)
        self.assertTrue(0.0 <= metrics['auc'] <= 1.0)
        self.assertTrue(0.0 <= metrics['f1'] <= 1.0)

        # Test Random Forest model training as well
        rf_engine = ModelEngine(self.data_manager)
        rf_metrics = rf_engine.train(model_type='random_forest', threshold=0.5)
        self.assertTrue(0.0 <= rf_metrics['accuracy'] <= 1.0)

    def test_3_fairness_metrics_match_hand_calculated_example(self):
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
            # Group A
            {'gender': 'A', 'target': 1},
            {'gender': 'A', 'target': 1},
            {'gender': 'A', 'target': 0},
            {'gender': 'A', 'target': 0},
            # Group B
            {'gender': 'B', 'target': 1},
            {'gender': 'B', 'target': 0},
            {'gender': 'B', 'target': 1},
            {'gender': 'B', 'target': 0},
        ]
        mini_probs = [0.9, 0.8, 0.6, 0.2, 0.7, 0.4, 0.3, 0.1]

        audit = audit_single_attribute(mini_test_rows, mini_probs, threshold=0.5, attribute_name='gender')

        # Find Group A and Group B
        group_map = {g['group']: g for g in audit['groups']}
        gA = group_map['A']
        gB = group_map['B']

        # Verify Group A
        self.assertAlmostEqual(gA['selection_rate'], 0.75, places=2)
        self.assertAlmostEqual(gA['recall'], 1.0, places=2)
        self.assertAlmostEqual(gA['precision'], 0.6667, places=2)
        self.assertAlmostEqual(gA['four_fifths_ratio'], 1.0, places=2)
        self.assertFalse(gA['violates_80_rule'])

        # Verify Group B
        self.assertAlmostEqual(gB['selection_rate'], 0.25, places=2)
        self.assertAlmostEqual(gB['recall'], 0.5, places=2)
        self.assertAlmostEqual(gB['precision'], 1.0, places=2)
        self.assertAlmostEqual(gB['four_fifths_ratio'], 0.3333, places=2)
        self.assertTrue(gB['violates_80_rule'])

        # Verify Gaps
        self.assertAlmostEqual(audit['selection_rate_gap'], 0.50, places=2)
        self.assertAlmostEqual(audit['recall_gap'], 0.50, places=2)
        self.assertAlmostEqual(audit['precision_gap'], 0.3333, places=2)
        self.assertTrue(audit['adverse_impact_detected'])

    def test_4_dropped_attribute_absent_from_model_features_but_available_for_audit(self):
        """Verifies dropped attribute is absent from model inputs, yet audit still measures its groups."""
        dm = self.data_manager
        engine = ModelEngine(dm)

        # Train model with 'gender' dropped
        engine.train(model_type='logistic_regression', threshold=0.5, attribute_to_drop='gender')

        # Check model active features do NOT contain any gender_* feature
        for feat in engine.active_features:
            self.assertFalse(feat.startswith('gender_'), f"Feature {feat} should be absent from model inputs")

        # But test rows still contain 'gender' column and audit can run on it
        audit = audit_single_attribute(
            [dm.processed_data[i] for i in dm.test_indices],
            engine.cached_test_probs,
            threshold=0.5,
            attribute_name='gender'
        )
        group_names = [g['group'] for g in audit['groups']]
        self.assertIn('Male', group_names)
        self.assertIn('Female', group_names)

    def test_5_before_and_after_runs_use_same_split(self):
        """Verifies stratified split indices remain strictly identical before and after ablation."""
        dm = self.data_manager
        engine = ModelEngine(dm)

        # Baseline split
        train_idx_before = list(dm.train_indices)
        test_idx_before = list(dm.test_indices)

        # Perform ablation
        res = compute_before_after_ablation(
            dm, engine, attribute_to_drop='gender', drop_proxies=False, protected_attribute='gender'
        )

        train_idx_after = list(dm.train_indices)
        test_idx_after = list(dm.test_indices)

        self.assertEqual(train_idx_before, train_idx_after, "Train indices must not change across ablation")
        self.assertEqual(test_idx_before, test_idx_after, "Test indices must not change across ablation")
        self.assertIn('before', res)
        self.assertIn('after', res)
        self.assertIn('delta', res)


if __name__ == '__main__':
    unittest.main()
