"""Regression tests for scientific validity, shared policies and saved interventions."""

import csv
import io
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import numpy as np

from app import create_app
from backend.data_manager import DataManager, clean_row, validate
from backend.explainability import explain_row
from backend.fairness_audit import audit_single_attribute, compute_before_after_ablation
from backend.ml_engine import ModelEngine
from backend.policy import SelectionPolicy


def fixture_rows(n=400):
    rng = np.random.default_rng(7)
    return [
        dict(
            enrollee_id=str(i),
            city_development_index=str(round(0.45 + 0.5 * rng.random(), 3)),
            training_hours=str(10 + i % 150),
            experience=str(i % 22),
            education_level="Masters" if i % 3 == 0 else "Graduate",
            relevent_experience="Has relevent experience"
            if i % 2
            else "No relevent experience",
            gender=["Male", "Female", "", "Other"][i % 4],
            enrolled_university="no_enrollment",
            company_type="Pvt Ltd",
            company_size="10/49" if i % 5 == 0 else "50-99",
            target=str(int(i % 7 < 3)),
        )
        for i in range(n)
    ]


def csv_bytes(rows):
    output = io.StringIO(newline="")
    fields = list(dict.fromkeys(k for row in rows for k in row))
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = fixture_rows()
        cls.dm = DataManager(rows=cls.raw)
        cls.engine = ModelEngine(cls.dm)
        cls.engine.train()

    def test_reproducible_disjoint_split(self):
        dm = self.dm
        other = DataManager(rows=self.raw)
        sets = [set(dm.train_indices), set(dm.validation_indices), set(dm.test_indices)]
        self.assertEqual(set.union(*sets), set(range(400)))
        self.assertTrue(all(not sets[i] & sets[j] for i in range(3) for j in range(i)))
        self.assertEqual(dm.train_indices, other.train_indices)
        self.assertEqual(dm.dataset_id, other.dataset_id)
        self.assertEqual([len(x) for x in sets], [240, 80, 80])

    def test_real_demographics_preserved_and_missing_not_inferred(self):
        row = clean_row(
            dict(
                self.raw[0],
                age="42",
                age_band="Applicant-defined",
                institution="Real College",
                experience="",
            )
        )
        self.assertEqual(row["age_band"], "Applicant-defined")
        self.assertEqual(row["institution"], "Real College")
        self.assertIsNone(row["experience"])
        self.assertEqual(row["experience_band"], "Unknown")
        self.assertEqual(clean_row(self.raw[0])["age_band"], "Unknown")

    def test_missing_outcomes_remain_unknown(self):
        rows = [{k: v for k, v in r.items() if k != "target"} for r in self.raw[:20]]
        dm = DataManager(rows=rows, training=False)
        self.assertTrue(all(r["target"] is None for r in dm.processed_data))
        self.assertEqual(dm.get_summary()["label_coverage"], 0)
        self.assertIsNone(self.engine.evaluate(dm.processed_data)["accuracy"])
        with self.assertRaises(ValueError):
            DataManager(rows=rows)

    def test_invalid_schema_labels_and_duplicates_rejected(self):
        for c, v in [
            ("training_hours", "bad"),
            ("city_development_index", "1.2"),
            ("experience", "-2"),
            ("target", "2"),
        ]:
            with self.subTest(c=c), self.assertRaises(ValueError):
                DataManager(rows=[dict(self.raw[0], **{c: v})], training=False)
        with self.assertRaises(ValueError):
            DataManager(rows=[self.raw[0], self.raw[0]], training=False)
        with self.assertRaises(ValueError):
            DataManager(rows=[{"target": "1"}], training=False)
        self.assertTrue(validate(self.dm.processed_data)[0])
        self.assertFalse(validate(self.dm.raw_data)[0])

    def test_protected_fields_cannot_change_score(self):
        self.assertIn("experience", self.engine.active_columns)
        self.assertFalse(
            set(self.engine.active_columns)
            & {"gender", "age", "age_band", "institution", "target", "enrollee_id"}
        )
        row = self.dm.processed_data[0]
        self.assertEqual(
            self.engine.predict_rows([row]),
            self.engine.predict_rows(
                [dict(row, gender="other", age_band="other", institution="other")]
            ),
        )

    def test_all_model_scores_match_single_batch_and_explanation(self):
        for kind in [
            "decision_tree",
            "logistic_regression",
            "knn",
            "naive_bayes",
            "random_forest",
        ]:
            with self.subTest(model=kind):
                engine = ModelEngine(self.dm)
                engine.train(kind)
                rows = self.dm.rows_for("test")[:3]
                scores = engine.predict_rows(rows)
                for row, score in zip(rows, scores):
                    self.assertAlmostEqual(
                        score, engine.predict_rows([row])[0], places=10
                    )
                    self.assertAlmostEqual(
                        score, explain_row(row, engine)["score"], places=10
                    )

    def test_imputation_learns_only_training_values(self):
        dm = DataManager(rows=self.raw)
        for i in dm.validation_indices + dm.test_indices:
            dm.processed_data[i]["training_hours"] = 99999
        expected = np.median(
            [dm.processed_data[i]["training_hours"] for i in dm.train_indices]
        )
        engine = ModelEngine(dm)
        engine.train("knn")
        imputer = (
            engine.pipeline.named_steps["preprocess"]
            .named_transformers_["numeric"]
            .named_steps["imputer"]
        )
        self.assertEqual(imputer.statistics_[1], expected)
        row = clean_row(
            dict(
                self.raw[0],
                education_level="Unseen degree",
                experience="",
                training_hours="",
            )
        )
        self.assertTrue(0 <= engine.predict_rows([row])[0] <= 1)

    def test_explanations_are_actual_paths_and_measured_effects(self):
        row = self.dm.rows_for("validation")[0]
        result = explain_row(row, self.engine)
        self.assertTrue(result["decision_rules"])
        self.assertEqual(
            {c["feature"] for c in result["contributions"]},
            set(self.engine.active_columns),
        )
        for c in result["contributions"]:
            score = self.engine.predict_rows(
                [dict(row, **{c["feature"]: c["reference_value"]})]
            )[0]
            self.assertAlmostEqual(c["impact"], result["score"] - score)

    def test_cv_uses_pipeline_and_shuffled_stratification(self):
        from sklearn.model_selection import cross_validate

        with patch("backend.ml_engine.cross_validate", wraps=cross_validate) as wrapped:
            result = self.engine.run_kfold_cv()
        self.assertIn("preprocess", wrapped.call_args.args[0].named_steps)
        self.assertTrue(wrapped.call_args.kwargs["cv"].shuffle)
        self.assertEqual(len(result["scores"]), 5)

    def test_real_feature_selection_and_pca(self):
        result = self.engine.compare_feature_selection_vs_pca(5)
        self.assertEqual(len(result[1]["selected_features"]), 5)
        self.assertGreater(result[2]["explained_variance_ratio"], 0)
        self.assertLessEqual(result[2]["explained_variance_ratio"], 1)

    def test_ablation_is_isolated_even_when_training_fails(self):
        engine = self.engine
        version = engine.version
        pipeline = engine.pipeline
        columns = list(engine.active_columns)
        result, candidate = compute_before_after_ablation(self.dm, engine, "experience")
        self.assertNotIn("experience", candidate.active_columns)
        self.assertIn("precision_gap", result["delta"])
        self.assertEqual(engine.version, version)
        self.assertIs(engine.pipeline, pipeline)
        self.assertEqual(engine.active_columns, columns)
        with patch.object(ModelEngine, "train", side_effect=RuntimeError("failed")):
            with self.assertRaises(RuntimeError):
                compute_before_after_ablation(self.dm, engine, "experience")
        self.assertIs(engine.pipeline, pipeline)


class FairnessTests(unittest.TestCase):
    def test_exact_hand_calculation(self):
        rows = [
            {"enrollee_id": str(i), "gender": "A" if i < 4 else "B", "target": y}
            for i, y in enumerate([1, 1, 0, 0, 1, 0, 1, 0])
        ]
        a = audit_single_attribute(rows, [0.9, 0.8, 0.6, 0.2, 0.7, 0.4, 0.3, 0.1])
        groups = {g["group"]: g for g in a["groups"]}
        self.assertEqual(groups["A"]["selection_rate"], 0.75)
        self.assertAlmostEqual(groups["A"]["precision"], 2 / 3)
        self.assertEqual(groups["A"]["recall"], 1)
        self.assertEqual(groups["B"]["recall"], 0.5)
        self.assertEqual(a["selection_rate_gap"], 0.5)
        self.assertEqual(a["recall_gap"], 0.5)
        self.assertTrue(a["adverse_impact_detected"])
        self.assertIsNotNone(a["selection_rate_gap_ci"])

    def test_undefined_metrics_are_not_zero_or_compliant(self):
        rows = [
            {"enrollee_id": "1", "gender": "A", "target": 0},
            {"enrollee_id": "2", "gender": "B", "target": None},
        ]
        a = audit_single_attribute(rows, [0.1, 0.1])
        self.assertIsNone(a["adverse_impact_detected"])
        self.assertEqual(a["status"], "no_selections")
        self.assertTrue(
            all(g["precision"] is None and g["recall"] is None for g in a["groups"])
        )

    def test_four_fifths_boundary_support_and_alignment(self):
        rows = [
            {
                "enrollee_id": str(i),
                "gender": "A" if i < 5 else "B",
                "target": int(i % 3 == 0),
            }
            for i in range(10)
        ]
        a = audit_single_attribute(rows, [1] * 9 + [0])
        self.assertEqual(a["min_four_fifths_ratio"], 0.8)
        self.assertFalse(a["adverse_impact_detected"])
        self.assertTrue(all(g["warnings"] for g in a["groups"]))
        with self.assertRaises(ValueError):
            audit_single_attribute([{}], [])

    def test_unrounded_ties_and_strict_policy_validation(self):
        rows = [{"enrollee_id": x} for x in ["b", "a", "c"]]
        decisions, rank = SelectionPolicy(0.99, 2).select(
            rows, [0.123440, 0.123441, 0.123441]
        )
        self.assertEqual(rank, [1, 2, 0])
        self.assertEqual(decisions, [0, 1, 1])
        for data in [
            {"threshold": "nan"},
            {"threshold": -1},
            {"threshold": True},
            {"top_n": 1.1},
            {"top_n": True},
            {"top_n": 0},
        ]:
            with self.subTest(data=data), self.assertRaises(ValueError):
                SelectionPolicy.parse(data)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.dataset = root / "train.csv"
        self.dataset.write_bytes(csv_bytes(fixture_rows()))
        self.storage = root / "state"
        self.app = create_app(self.dataset, self.storage, testing=True)
        self.client = self.app.test_client()
        self.s = self.app.extensions["console"]

    def upload(self, rows, path="/api/pool/upload", **extra):
        return self.client.post(
            path,
            data={"file": (io.BytesIO(csv_bytes(rows)), "pool.csv"), **extra},
            content_type="multipart/form-data",
        )

    def test_unlabeled_upload_and_actual_demographics(self):
        version = self.s.engine.version
        rows = [
            {k: v for k, v in r.items() if k != "target"}
            | {"age_band": "35-44", "institution": "Real College"}
            for r in fixture_rows(20)
        ]
        r = self.upload(rows)
        self.assertEqual(r.status_code, 200, r.get_json())
        self.assertEqual(version, self.s.engine.version)
        audit = self.client.get("/api/fairness/audit?scope=current").get_json()["audit"]
        self.assertIn("age_band", audit)
        self.assertIn("institution", audit)
        self.assertIsNone(audit["gender"]["precision_gap"])

    def test_upload_and_training_failures_are_atomic(self):
        version = self.s.engine.version
        pool_id = self.s.pool_id
        self.assertEqual(self.upload([{"invalid": "data"}]).status_code, 400)
        self.assertEqual(
            self.upload(
                [dict(r, target="0") for r in fixture_rows(20)], "/api/training/upload"
            ).status_code,
            400,
        )
        self.assertEqual(version, self.s.engine.version)
        self.assertEqual(pool_id, self.s.pool_id)

    def test_policy_matches_export_explanation_and_audit(self):
        self.client.post("/api/policy", json={"threshold": 0.99, "top_n": 7})
        d = self.client.get("/api/shortlist?per_page=100").get_json()
        self.assertEqual(d["total_shortlisted"], 7)
        content = self.client.get(
            "/api/shortlist?filter=shortlisted&export=true"
        ).get_data(as_text=True)
        self.assertEqual(len(list(csv.DictReader(io.StringIO(content)))), 7)
        a = self.client.get("/api/fairness/audit?scope=current").get_json()["audit"][
            "gender"
        ]
        self.assertEqual(sum(g["selected_count"] for g in a["groups"]), 7)
        for row in d["applicants"][:10]:
            result = self.client.get("/api/explain/" + row["enrollee_id"]).get_json()
            self.assertEqual(result["shortlisted"], row["shortlisted"])
            self.assertAlmostEqual(result["score"], row["score"])
        self.assertIsNone(
            self.client.post("/api/predict/single", json=fixture_rows(1)[0]).get_json()[
                "shortlisted"
            ]
        )

    def test_preview_apply_restart_and_revert(self):
        original = self.s.engine.version
        r = self.client.post(
            "/api/fairness/ablate",
            json={"attribute_to_drop": "experience", "scope": "validation"},
        ).get_json()
        self.assertEqual(self.s.engine.version, original)
        applied = self.client.post("/api/fairness/apply", json={"run_id": r["run_id"]})
        self.assertEqual(applied.status_code, 200, applied.get_json())
        restored = create_app(self.dataset, self.storage).extensions["console"]
        self.assertEqual(restored.engine.version, self.s.engine.version)
        self.assertNotIn("experience", restored.engine.active_columns)
        self.assertEqual(self.client.post("/api/models/revert").status_code, 200)
        self.assertEqual(self.s.engine.version, original)

    def test_stale_preview_rejected(self):
        r = self.client.post(
            "/api/fairness/ablate", json={"attribute_to_drop": "experience"}
        ).get_json()
        self.client.post("/api/policy", json={"threshold": 0.2})
        self.assertEqual(
            self.client.post(
                "/api/fairness/apply", json={"run_id": r["run_id"]}
            ).status_code,
            409,
        )

    def test_invalid_requests_preserve_workspace(self):
        version = self.s.engine.version
        for url in [
            "/api/shortlist?per_page=0",
            "/api/shortlist?threshold=nan",
            "/api/shortlist?top_n=2.5",
            "/api/fairness/audit?scope=bogus",
            "/api/fairness/drivers?attribute=bogus",
        ]:
            r = self.client.get(url)
            self.assertEqual(r.status_code, 400, (url, r.get_json()))
        for data in [{"model_type": "bogus"}, {"threshold": "not a number"}]:
            self.assertEqual(self.client.post("/api/train", json=data).status_code, 400)
        self.assertEqual(version, self.s.engine.version)
        self.assertEqual(self.client.post("/api/policy", json=[]).status_code, 400)
        self.assertEqual(
            self.client.post(
                "/api/policy", json={}, headers={"Origin": "https://example.com"}
            ).status_code,
            403,
        )

    def test_formula_export_and_audit_provenance(self):
        self.assertEqual(
            self.upload(
                [dict(fixture_rows(1)[0], enrollee_id='=HYPERLINK("bad")')]
            ).status_code,
            200,
        )
        content = self.client.get("/api/shortlist?export=true").get_data(as_text=True)
        self.assertTrue(
            list(csv.DictReader(io.StringIO(content)))[0]["enrollee_id"].startswith(
                "'="
            )
        )
        exported = self.client.get("/api/fairness/export").get_json()
        self.assertIn("model_version", exported["model"])
        self.assertIn("history", exported)
        self.assertIn("policy", exported)

    def test_cost_capacity_and_validation_scope(self):
        r = self.client.post(
            "/api/settings/cost_matrix", json={"capacity": 10}
        ).get_json()
        self.assertEqual(r["evaluation_split"], "validation")
        if r["optimal_threshold"] is not None:
            entry = next(
                x for x in r["cost_curve"] if x["threshold"] == r["optimal_threshold"]
            )
            self.assertLessEqual(entry["shortlisted_count"], 10)

    def test_concurrent_previews_do_not_mutate_model(self):
        version = self.s.engine.version

        def preview(col):
            with self.app.test_client() as c:
                return c.post(
                    "/api/fairness/ablate", json={"attribute_to_drop": col}
                ).status_code

        with ThreadPoolExecutor(max_workers=2) as executor:
            statuses = list(executor.map(preview, ["experience", "training_hours"]))
        self.assertEqual(statuses, [200, 200])
        self.assertEqual(version, self.s.engine.version)

    def test_offline_assets_and_security_headers(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("script-src 'self'", r.headers["Content-Security-Policy"])
        self.assertNotIn("cdn.", r.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
