"""Reproducible classifiers with fold-local preprocessing and exact sklearn metrics."""

import math
import uuid
from collections import Counter
from datetime import datetime, timezone

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectFromModel
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    normalized_mutual_info_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier
from threadpoolctl import threadpool_limits

from backend.data_manager import (
    CATEGORICAL_COLUMNS,
    MODEL_COLUMNS,
    NUMERIC_COLUMNS,
    clean_row,
)
from backend.policy import SelectionPolicy

USE_SKLEARN = True
MODEL_NAMES = {
    "decision_tree": "Decision Tree",
    "logistic_regression": "Logistic Regression",
    "random_forest": "Random Forest",
    "naive_bayes": "Gaussian Naive Bayes",
    "knn": "K-Nearest Neighbors",
}
FAMILIES = {
    "decision_tree": "Tree",
    "logistic_regression": "Linear",
    "random_forest": "Ensemble",
    "naive_bayes": "Probabilistic",
    "knn": "Instance-based",
}


def metric_divide(a, b):
    return float(a / b) if b else None


def compute_classification_metrics(
    y_true, y_probs, threshold=0.5, majority_baseline=None, decisions=None
):
    mask = [i for i, y in enumerate(y_true) if y is not None]
    if not mask:
        return {
            k: None
            for k in [
                "accuracy",
                "precision",
                "recall",
                "f1",
                "auc",
                "average_precision",
                "balanced_accuracy",
                "majority_baseline",
                "baseline_delta",
                "confusion_matrix",
            ]
        } | {"labeled_count": 0, "label_coverage": 0}
    y = np.asarray([y_true[i] for i in mask], dtype=int)
    p = np.asarray([y_probs[i] for i in mask], dtype=float)
    pred = (
        np.asarray([decisions[i] for i in mask], dtype=int)
        if decisions is not None
        else (p >= threshold).astype(int)
    )
    tn, fp, fn, tp = [int(x) for x in confusion_matrix(y, pred, labels=[0, 1]).ravel()]
    precision, recall = metric_divide(tp, tp + fp), metric_divide(tp, tp + fn)
    accuracy = float(np.mean(y == pred))
    has_both = len(set(y)) == 2
    fpr, tpr, thresholds = roc_curve(y, p) if has_both else ([], [], [])
    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": metric_divide(2 * tp, 2 * tp + fp + fn),
        "auc": float(roc_auc_score(y, p)) if has_both else None,
        "average_precision": float(average_precision_score(y, p)) if has_both else None,
        "balanced_accuracy": float(balanced_accuracy_score(y, pred))
        if has_both
        else None,
        "majority_baseline": majority_baseline,
        "baseline_delta": accuracy - majority_baseline
        if majority_baseline is not None
        else None,
        "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
        "labeled_count": len(y),
        "label_coverage": len(y) / len(y_true),
        "roc_curve": [{"fpr": float(f), "tpr": float(t)} for f, t in zip(fpr, tpr)],
    }


def compute_cost_matrix_analysis(
    y_true,
    y_probs,
    cost_fp=500.0,
    cost_fn=3500.0,
    benefit_tp=5000.0,
    cost_tn=0.0,
    capacity=None,
):
    params = [cost_fp, cost_fn, benefit_tp, cost_tn]
    if any(not math.isfinite(x) or not 0 <= x <= 1e12 for x in params):
        raise ValueError(
            "Costs and benefits must be finite numbers between 0 and 1 trillion."
        )
    if not y_true or any(y is None for y in y_true):
        raise ValueError("Cost analysis requires complete validation outcomes.")
    curve = []
    for t in np.linspace(0, 1, 101):
        pred = np.asarray(y_probs) >= t
        y = np.asarray(y_true)
        tp = int(np.sum(pred & (y == 1)))
        fp = int(np.sum(pred & (y == 0)))
        fn = int(np.sum(~pred & (y == 1)))
        tn = int(np.sum(~pred & (y == 0)))
        curve.append(
            {
                "threshold": round(float(t), 2),
                "expected_cost": float(
                    fp * cost_fp + fn * cost_fn - tp * benefit_tp + tn * cost_tn
                ),
                "shortlisted_count": tp + fp,
                "feasible": capacity is None or tp + fp <= capacity,
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "tn": tn,
            }
        )
    feasible = [x for x in curve if x["feasible"]]
    best = (
        min(feasible, key=lambda x: (x["expected_cost"], -x["threshold"]))
        if feasible
        else None
    )
    return {
        "optimal_threshold": best["threshold"] if best else None,
        "min_expected_cost": best["expected_cost"] if best else None,
        "cost_curve": curve,
        "evaluation_split": "validation",
        "capacity": capacity,
        "parameters": dict(
            zip(["cost_fp", "cost_fn", "benefit_tp", "cost_tn"], params)
        ),
        "note": "Assumed costs, not measured financial returns. Threshold chosen on validation data. Capacity limits feasible thresholds.",
    }


class ModelEngine:
    def __init__(self, data_manager):
        self.dm = data_manager
        self.model_type = "decision_tree"
        self.threshold = 0.5
        self.dropped_columns = []
        self.active_columns = list(MODEL_COLUMNS)
        self.pipeline = None
        self.version = None
        self.models_comparison_cache = None
        self.dim_cache = None
        self.cached_test_probs = []
        self.cached_test_y = []
        self.latest_metrics = {}

    def instantiate_model(self, model_type):
        if model_type not in MODEL_NAMES:
            raise ValueError(
                "Unknown classifier. Choose one of: " + ", ".join(MODEL_NAMES)
            )
        return {
            "decision_tree": lambda: DecisionTreeClassifier(
                max_depth=5, min_samples_leaf=25, random_state=42
            ),
            "naive_bayes": lambda: GaussianNB(var_smoothing=1e-3),
            "knn": lambda: KNeighborsClassifier(
                n_neighbors=7, weights="distance", n_jobs=1
            ),
            "logistic_regression": lambda: LogisticRegression(
                max_iter=1000, random_state=42
            ),
            "random_forest": lambda: RandomForestClassifier(
                n_estimators=80,
                max_depth=8,
                min_samples_leaf=15,
                random_state=42,
                n_jobs=1,
            ),
        }[model_type]()

    def make_pipeline(self, model_type, columns=None):
        columns = columns or self.active_columns
        num = [c for c in NUMERIC_COLUMNS if c in columns]
        cat = [c for c in CATEGORICAL_COLUMNS if c in columns]
        numeric = [
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True))
        ]
        if model_type in {"knn", "logistic_regression"}:
            numeric.append(("scaler", StandardScaler()))
        transforms = []
        if num:
            transforms.append(("numeric", Pipeline(numeric), num))
        if cat:
            transforms.append(
                (
                    "categorical",
                    OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                    cat,
                )
            )
        return Pipeline(
            [
                (
                    "preprocess",
                    ColumnTransformer(transforms, verbose_feature_names_out=False),
                ),
                ("classifier", self.instantiate_model(model_type)),
            ]
        )

    def train(
        self,
        model_type="decision_tree",
        threshold=0.5,
        attribute_to_drop=None,
        drop_proxies=False,
        dropped_columns=None,
    ):
        if not isinstance(model_type,str) or model_type not in MODEL_NAMES:
            raise ValueError("Choose a supported classifier family.")
        SelectionPolicy(float(threshold))
        dropped = set(dropped_columns or [])
        if attribute_to_drop:
            if attribute_to_drop not in MODEL_COLUMNS:
                raise ValueError(
                    "Choose an actual predictor. Protected attributes are already audit-only."
                )
            dropped.add(attribute_to_drop)
            if drop_proxies:
                dropped.update(
                    p["column"] for p in self.proxy_candidates(attribute_to_drop)
                )
        if not dropped.issubset(MODEL_COLUMNS):
            raise ValueError("Unknown dropped predictor.")
        columns = [c for c in MODEL_COLUMNS if c not in dropped]
        if not columns:
            raise ValueError("Keep at least one predictor.")
        pipeline = self.make_pipeline(model_type, columns)
        train = self.dm.rows_for("train")
        with threadpool_limits(limits=2):
            pipeline.fit(self.dm.frame(train, columns), [r["target"] for r in train])
        # Commit only after fitting succeeds.
        self.pipeline = pipeline
        self.model_type = model_type
        self.threshold = float(threshold)
        self.active_columns = columns
        self.dropped_columns = sorted(dropped)
        self.version = uuid.uuid4().hex[:12]
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.active_features = list(
            pipeline.named_steps["preprocess"].get_feature_names_out()
        )
        self.model = pipeline.named_steps["classifier"]
        test = self.dm.rows_for("test")
        self.cached_test_y = [r["target"] for r in test]
        self.cached_test_probs = self.predict_rows(test)
        self.latest_metrics = self.evaluate(test, SelectionPolicy(self.threshold))
        self.models_comparison_cache = None
        self.dim_cache = None
        return self.latest_metrics | self.metadata()

    def predict_rows(self, rows):
        if not rows:
            return []
        if self.pipeline is None:
            raise ValueError("Train a model first.")
        with threadpool_limits(limits=2):
            probabilities = self.pipeline.predict_proba(
                self.dm.frame(rows, self.active_columns)
            )
        positive = list(self.pipeline.classes_).index(1)
        return [float(x) for x in probabilities[:, positive]]

    def evaluate(self, rows, policy=None):
        policy = policy or SelectionPolicy(self.threshold)
        scores = self.predict_rows(rows)
        decisions, _ = policy.select(rows, scores)
        train = self.dm.rows_for("train")
        majority = Counter(r["target"] for r in train).most_common(1)[0][0]
        known = [r["target"] for r in rows if r["target"] is not None]
        baseline = sum(y == majority for y in known) / len(known) if known else None
        result = compute_classification_metrics(
            [r["target"] for r in rows], scores, policy.threshold, baseline, decisions
        )
        result.update(
            selection_rate=sum(decisions) / len(rows) if rows else None,
            selected_count=sum(decisions),
            total_count=len(rows),
            policy=policy.to_dict(),
        )
        if known:
            order = sorted(
                range(len(rows)),
                key=lambda i: (-scores[i], str(rows[i]["enrollee_id"])),
            )
            top = order[: min(100, len(rows))]
            top_known = [i for i in top if rows[i]["target"] is not None]
            result["precision_at_100"] = (
                sum(rows[i]["target"] for i in top_known) / len(top_known)
                if top_known
                else None
            )
        return result

    def metadata(self):
        return {
            "model_type": self.model_type,
            "model_name": MODEL_NAMES[self.model_type],
            "model_version": self.version,
            "created_at": getattr(self, "created_at", None),
            "active_columns": self.active_columns,
            "dropped_columns": self.dropped_columns,
            "num_features": len(getattr(self, "active_features", [])),
            "dataset_id": self.dm.dataset_id,
            "target_kind": self.dm.target_kind,
        }

    def run_kfold_cv(self, model_type="decision_tree", k=5):
        rows = self.dm.rows_for("train")
        y = [r["target"] for r in rows]
        k = min(k, min(Counter(y).values()))
        if k < 2:
            raise ValueError("Too few training rows per class for cross-validation.")
        with threadpool_limits(limits=2):
            cv = cross_validate(
                self.make_pipeline(model_type),
                self.dm.frame(rows, self.active_columns),
                y,
                cv=StratifiedKFold(n_splits=k, shuffle=True, random_state=42),
                scoring=["accuracy", "roc_auc"],
                n_jobs=1,
                error_score="raise",
            )
        scores = cv["test_accuracy"]
        return {
            "k": k,
            "scores": scores.tolist(),
            "mean_accuracy": float(np.mean(scores)),
            "std_accuracy": float(np.std(scores)),
            "mean_auc": float(np.mean(cv["test_roc_auc"])),
            "spread_display": f"{np.mean(scores) * 100:.2f}% ± {np.std(scores) * 100:.2f}%",
            "method": "Shuffled stratified CV on training partition; preprocessing refitted inside each fold",
        }

    def compare_all_models(self):
        if self.models_comparison_cache is not None:
            return self.models_comparison_cache
        rows = self.dm.rows_for("validation")
        train = self.dm.rows_for("train")
        result = []
        for key in MODEL_NAMES:
            pipeline = self.make_pipeline(key)
            with threadpool_limits(limits=2):
                pipeline.fit(
                    self.dm.frame(train, self.active_columns),
                    [r["target"] for r in train],
                )
                scores = pipeline.predict_proba(
                    self.dm.frame(rows, self.active_columns)
                )[:, 1].tolist()
            majority = Counter(r["target"] for r in train).most_common(1)[0][0]
            baseline = sum(r["target"] == majority for r in rows) / len(rows)
            metrics = compute_classification_metrics(
                [r["target"] for r in rows], scores, 0.5, baseline
            )
            cv = self.run_kfold_cv(key)
            result.append(
                metrics
                | {
                    "model_id": key,
                    "model_name": MODEL_NAMES[key],
                    "family": FAMILIES[key],
                    "cv": cv,
                    "cv_spread": cv["spread_display"],
                    "evaluation_split": "validation",
                }
            )
        self.models_comparison_cache = result
        return result

    def compare_feature_selection_vs_pca(self, target_components=10):
        if self.dim_cache is not None:
            return self.dim_cache
        train = self.dm.rows_for("train")
        val = self.dm.rows_for("validation")
        base = self.make_pipeline("decision_tree")
        x = base.named_steps["preprocess"].fit_transform(
            self.dm.frame(train, self.active_columns)
        )
        xv = base.named_steps["preprocess"].transform(
            self.dm.frame(val, self.active_columns)
        )
        yt = [r["target"] for r in train]
        yv = [r["target"] for r in val]
        k = min(target_components, x.shape[1], x.shape[0])
        selector = SelectFromModel(
            DecisionTreeClassifier(max_depth=5, min_samples_leaf=25, random_state=42),
            threshold=-np.inf,
            max_features=k,
        )
        xs = selector.fit_transform(x, yt)
        xvs = selector.transform(xv)
        scaler = StandardScaler().fit(x)
        pca = PCA(n_components=k, svd_solver="full", random_state=42).fit(
            scaler.transform(x)
        )
        xp = pca.transform(scaler.transform(x))
        xvp = pca.transform(scaler.transform(xv))
        result = []
        for name, xt, xvt in [
            ("All features", x, xv),
            ("Train-fitted importance selection", xs, xvs),
            ("PCA · scaled, train-fitted", xp, xvp),
        ]:
            m = self.instantiate_model("decision_tree").fit(xt, yt)
            result.append(
                compute_classification_metrics(yv, m.predict_proba(xvt)[:, 1].tolist())
                | {
                    "technique": name,
                    "components_or_features": int(xt.shape[1]),
                    "evaluation_split": "validation",
                }
            )
        names = base.named_steps["preprocess"].get_feature_names_out()
        result[1]["selected_features"] = names[selector.get_support()].tolist()
        result[2]["explained_variance_ratio"] = float(
            np.sum(pca.explained_variance_ratio_)
        )
        self.dim_cache = result
        return result

    def proxy_candidates(self, attribute, limit=3):
        if attribute not in MODEL_COLUMNS:
            raise ValueError("Choose an input column for association analysis.")
        frame = self.dm.frame(self.dm.rows_for("train"))

        def bins(column):
            s = frame[column]
            if column in NUMERIC_COLUMNS:
                observed = s.dropna()
                if observed.nunique() < 2:
                    return np.zeros(len(s), dtype=int)
                edges = np.unique(np.quantile(observed, np.linspace(0, 1, 6)))
                return np.where(
                    s.isna(), -1, np.digitize(s.fillna(observed.median()), edges[1:-1])
                )
            return s.astype(str).to_numpy()

        reference = bins(attribute)
        result = [
            {
                "column": c,
                "association": float(normalized_mutual_info_score(reference, bins(c))),
                "method": "Normalized mutual information on training rows; numeric quintiles",
            }
            for c in self.active_columns
            if c != attribute
        ]
        return sorted(
            [r for r in result if r["association"] >= 0.3],
            key=lambda r: (-r["association"], r["column"]),
        )[:limit]

    def predict_single(self, applicant_dict):
        from backend.explainability import explain_row

        return explain_row(
            clean_row(applicant_dict), self, SelectionPolicy(self.threshold)
        )
