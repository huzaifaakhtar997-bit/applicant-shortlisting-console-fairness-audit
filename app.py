"""FairRecruit: a local, auditable classification and shortlisting workbench."""

import csv
import io
import json
import math
import os
import threading
import uuid
from functools import wraps
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, Response, current_app, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from backend.data_manager import (
    AUDIT_LABELS,
    TARGET_DESCRIPTIONS,
    DataManager,
    clean_row,
)
from backend.explainability import explain_applicant, explain_row
from backend.fairness_audit import (
    compute_before_after_ablation,
    compute_disparity_drivers,
    compute_fairness_audit,
)
from backend.ml_engine import MODEL_NAMES, ModelEngine, compute_cost_matrix_analysis
from backend.policy import SelectionPolicy
from backend.storage import AuditStore

ROOT = Path(__file__).resolve().parent


class Console:
    def __init__(self, dataset, storage, restore=True):
        self.lock = threading.RLock()
        self.store = AuditStore(storage)
        saved = self.store.load_active() if restore else None
        if saved:
            if saved.get("schema_version") != 2:
                raise ValueError(
                    "Saved workspace schema is unsupported; choose another FAIRRECRUIT_DATA_DIR."
                )
            self.engine = self.store.load_model(saved["model_version"])
            self.policy = SelectionPolicy.parse(saved["policy"])
            self.version_history = saved["version_history"]
        else:
            self.engine = ModelEngine(DataManager(dataset))
            self.engine.train()
            self.policy = SelectionPolicy()
            self.version_history = [self.engine.version]
            self.store.save_model(self.engine)
            self.persist()
            self.store.event("workspace_created", self.engine.metadata())
        self.pool = None
        self.pool_name = "Validation demo pool"
        self.pool_id = self.engine.dm.dataset_id + ":validation"
        self.scores_cache = {}
        self.experiments = {}

    def persist(self):
        self.store.save_active(self.engine.version, self.policy, self.version_history)

    def rows(self, scope="current"):
        if not isinstance(scope,str) or scope not in {"current", "validation", "test"}:
            raise ValueError("Scope must be current, validation or test.")
        return (
            (
                self.pool.processed_data
                if self.pool is not None
                else self.engine.dm.rows_for("validation")
            )
            if scope == "current"
            else self.engine.dm.rows_for(scope)
        )

    def attributes(self, scope="current"):
        return (
            self.pool.audit_attributes
            if scope == "current" and self.pool is not None
            else self.engine.dm.audit_attributes
        )

    def scope_id(self, scope):
        return (
            self.pool_id
            if scope == "current"
            else self.engine.dm.dataset_id + ":" + scope
        )

    def scores(self, scope="current"):
        key = (self.engine.version, self.scope_id(scope))
        if key not in self.scores_cache:
            self.scores_cache[key] = self.engine.predict_rows(self.rows(scope))
        return self.scores_cache[key]

    def activate(self, candidate, action, details):
        self.store.save_model(candidate)
        history = self.version_history + [candidate.version]
        self.store.save_active(candidate.version, self.policy, history)
        self.engine = candidate
        self.version_history = history
        self.scores_cache = {}
        if self.pool is None:
            self.pool_id = candidate.dm.dataset_id + ":validation"
        self.store.event(action, candidate.metadata() | details)


def service():
    return current_app.extensions["console"]


def locked(function):
    @wraps(function)
    def inner(*args, **kwargs):
        with service().lock:
            return function(*args, **kwargs)

    return inner


def payload():
    value = request.get_json(silent=False)
    if not isinstance(value, dict):
        raise ValueError("Send a JSON object.")
    return value


def current_policy():
    return SelectionPolicy.parse(request.args, service().policy)


def integer_arg(name, default, lower=1, upper=100000):
    value = request.args.get(name, str(default))
    try:
        result = int(value)
    except (ValueError, TypeError):
        raise ValueError(f"{name} must be an integer.") from None
    if str(result) != str(value) or not lower <= result <= upper:
        raise ValueError(f"{name} must be between {lower} and {upper}.")
    return result


def csv_response(rows, filename):
    output = io.StringIO(newline="")
    fields = list(dict.fromkeys(k for row in rows for k in row))
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        safe = {
            k: (
                "'" + v
                if isinstance(v, str)
                and v.lstrip().startswith(("=", "+", "-", "@", "\t", "\r"))
                else v
            )
            for k, v in row.items()
        }
        writer.writerow(safe)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def create_app(dataset=None, storage=None, testing=False):
    app = Flask(__name__)
    app.json.sort_keys = False
    app.config.update(
        MAX_CONTENT_LENGTH=32 * 1024 * 1024, TESTING=testing, JSON_SORT_KEYS=False,
        TRUSTED_HOSTS=["127.0.0.1", "localhost", "[::1]"]
    )
    app.extensions["console"] = Console(
        dataset or ROOT / "aug_train.csv",
        storage or os.environ.get("FAIRRECRUIT_DATA_DIR", ROOT / ".local"),
        restore=not testing,
    )

    @app.before_request
    def same_origin():
        origin = request.headers.get("Origin")
        if (
            request.method == "POST"
            and origin
            and urlparse(origin).netloc != request.host
        ):
            return jsonify(error="Cross-origin workspace changes are not allowed."), 403

    @app.after_request
    def response_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'self'"
        )
        response.headers["Cache-Control"] = (
            "no-store" if request.path.startswith("/api/") else "no-cache"
        )
        return response

    @app.errorhandler(ValueError)
    def invalid(error):
        return jsonify(error=str(error)), 400

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error=error.description), error.code

    @app.errorhandler(Exception)
    def unexpected(error):
        app.logger.exception("Request failed")
        return jsonify(
            error="The request could not be completed. Refresh workspace status and check the server log."
        ), 500

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/workspace")
    @locked
    def workspace():
        s = service()
        dm = s.engine.dm
        source = s.pool or dm
        rows = s.rows()
        scores = s.scores()
        decisions, _ = s.policy.select(rows, scores)
        return jsonify(
            model=s.engine.metadata(),
            policy=s.policy.to_dict(),
            training=dm.get_summary(),
            pool={
                "name": s.pool_name,
                "dataset_id": s.pool_id,
                "total_rows": len(rows),
                "selected_count": sum(decisions),
                "selection_rate": sum(decisions) / len(rows),
                "label_coverage": sum(r["target"] is not None for r in rows)
                / len(rows),
                "attributes": [
                    {"key": a, "label": AUDIT_LABELS[a]} for a in s.attributes()
                ],
                "source": "uploaded" if s.pool is not None else "validation",
                "target_description": TARGET_DESCRIPTIONS[dm.target_kind],
            },
            models=MODEL_NAMES,
            can_revert=len(s.version_history) > 1,
            source_summary=source.get_summary(),
        )

    @app.route("/api/dataset", methods=["GET", "POST"])
    @locked
    def dataset_route():
        s = service()
        if request.method == "GET":
            return jsonify(s.engine.dm.get_summary())
        return upload_pool()

    def uploaded(training):
        file = request.files.get("file")
        if file is None or not file.filename:
            raise ValueError("Choose a CSV file.")
        if not file.filename.lower().endswith(".csv"):
            raise ValueError("Upload a .csv file.")
        kind = request.form.get("target_kind", service().engine.dm.target_kind)
        return DataManager.from_csv(
            file.read(),
            training=training,
            target_kind=kind,
            name=Path(file.filename).name,
        )

    @app.post("/api/pool/upload")
    @locked
    def upload_pool():
        s = service()
        pool = uploaded(False)
        if (
            any(r["target"] is not None for r in pool.processed_data)
            and pool.target_kind != s.engine.dm.target_kind
        ):
            raise ValueError(
                "Pool outcomes must have the same meaning as training outcomes. Change outcome type or omit target."
            )
        s.engine.predict_rows(pool.processed_data[:1])
        s.store.event(
            "pool_uploaded",
            {
                "pool_id": pool.dataset_id,
                "rows": len(pool.processed_data),
                "label_coverage": pool.get_summary()["label_coverage"],
            },
        )
        s.pool = pool
        s.pool_name = pool.name
        s.pool_id = pool.dataset_id
        s.scores_cache = {}
        return jsonify(
            message="Applicant pool loaded. The trained model was not changed.",
            pool=pool.get_summary(),
        )

    @app.post("/api/pool/reset")
    @locked
    def reset_pool():
        s = service()
        s.pool = None
        s.pool_name = "Validation demo pool"
        s.pool_id = s.engine.dm.dataset_id + ":validation"
        s.scores_cache = {}
        s.store.event("pool_reset", {"pool_id": s.pool_id})
        return jsonify(message="Validation demo pool restored.")

    @app.post("/api/training/upload")
    @locked
    def upload_training():
        s = service()
        dm = uploaded(True)
        candidate = ModelEngine(dm)
        candidate.train(s.engine.model_type, s.policy.threshold)
        s.activate(
            candidate,
            "training_replaced",
            {"previous_dataset_id": s.engine.dm.dataset_id},
        )
        s.pool = None
        s.pool_name = "Validation demo pool"
        s.pool_id = dm.dataset_id + ":validation"
        return jsonify(
            message="New labeled training data fitted successfully.",
            model=candidate.metadata(),
        )

    @app.get("/api/pool/template")
    def template():
        row = {
            "enrollee_id": "example-001",
            "city_development_index": 0.8,
            "training_hours": 50,
            "experience": 5,
            "education_level": "Graduate",
            "relevent_experience": "Has relevent experience",
            "gender": "Unknown",
            "age_band": "",
            "institution": "",
        }
        return csv_response([row], "applicant_template.csv")

    @app.get("/api/dataset/cleaned/download")
    @locked
    def cleaned():
        return csv_response(
            (service().pool or service().engine.dm).processed_data,
            "cleaned_with_provenance.csv",
        )

    @app.get("/api/preprocess")
    @locked
    def preprocess():
        engine = service().engine
        return jsonify(
            active_columns=engine.active_columns,
            feature_names=engine.active_features,
            method="Train-only imputation and encoding; numeric scaling for KNN and Logistic Regression. Pipeline refitted in every CV fold.",
            excluded=[
                "target",
                "enrollee_id",
                "gender",
                "age",
                "age_band",
                "institution",
            ],
            split={
                "train": len(engine.dm.train_indices),
                "validation": len(engine.dm.validation_indices),
                "test": len(engine.dm.test_indices),
            },
        )

    @app.post("/api/policy")
    @locked
    def update_policy():
        s = service()
        policy = SelectionPolicy.parse(payload(), s.policy)
        s.store.save_active(s.engine.version, policy, s.version_history)
        s.policy = policy
        s.engine.threshold = policy.threshold
        s.store.event(
            "policy_updated",
            {"policy": policy.to_dict(), "model_version": s.engine.version},
        )
        return jsonify(policy.to_dict())

    @app.post("/api/train")
    @locked
    def train():
        s = service()
        data = payload()
        candidate = ModelEngine(s.engine.dm)
        policy = SelectionPolicy.parse(data, s.policy)
        candidate.train(
            data.get("model_type", s.engine.model_type),
            policy.threshold,
            dropped_columns=s.engine.dropped_columns,
        )
        old_policy = s.policy
        s.policy = policy
        try:
            s.activate(
                candidate, "model_trained", {"previous_version": s.engine.version}
            )
        except Exception:
            s.policy = old_policy
            raise
        return jsonify(candidate.metadata(), metrics=candidate.latest_metrics)

    @app.get("/api/models/compare")
    @locked
    def compare():
        return jsonify(
            comparison=service().engine.compare_all_models(),
            evaluation_split="validation",
            note="Use training CV and validation to choose a model. Test data are reserved for final evaluation.",
        )

    @app.get("/api/models/dim_reduction_compare")
    @locked
    def dimensions():
        return jsonify(
            comparison=service().engine.compare_feature_selection_vs_pca(),
            evaluation_split="validation",
        )

    @app.get("/api/evaluation")
    @locked
    def evaluation():
        s = service()
        scope = request.args.get("scope", "validation")
        if scope not in {"validation", "test"}:
            raise ValueError("Evaluation scope must be validation or test.")
        return jsonify(
            metrics=s.engine.evaluate(s.rows(scope), current_policy()),
            scope=scope,
            model=s.engine.metadata(),
            note="Repeated test-set exploration invalidates its use as an untouched final evaluation."
            if scope == "test"
            else "Validation supports model, threshold and intervention choice.",
        )

    @app.get("/api/shortlist")
    @locked
    def shortlist():
        s = service()
        policy = current_policy()
        rows = s.rows()
        scores = s.scores()
        selected, ranked = policy.select(rows, scores)
        status = request.args.get("filter", "all")
        search = request.args.get("search", "").casefold()
        if status not in {"all", "shortlisted", "held"}:
            raise ValueError("Filter must be all, shortlisted or held.")
        candidates = []
        for rank, i in enumerate(ranked, 1):
            r = rows[i]
            if (
                status == "shortlisted"
                and not selected[i]
                or status == "held"
                and selected[i]
            ):
                continue
            if search and search not in str(r["enrollee_id"]).casefold():
                continue
            candidates.append(
                {
                    k: r.get(k)
                    for k in [
                        "enrollee_id",
                        "gender",
                        "experience",
                        "education_level",
                        "age_band",
                        "institution",
                        "experience_band",
                        "education_group",
                        "target",
                    ]
                }
                | {"rank": rank, "score": scores[i], "shortlisted": bool(selected[i])}
            )
        if request.args.get("export") == "true":
            s.store.event(
                "shortlist_exported",
                {
                    "pool_id": s.pool_id,
                    "model_version": s.engine.version,
                    "policy": policy.to_dict(),
                    "rows": len(candidates),
                },
            )
            return csv_response(candidates, "shortlist.csv")
        page = integer_arg("page", 1)
        size = integer_arg("per_page", 20, 1, 100)
        return jsonify(
            total_candidates=len(rows),
            total_filtered=len(candidates),
            total_shortlisted=sum(selected),
            selection_rate=sum(selected) / len(rows),
            page=page,
            per_page=size,
            total_pages=max(1, math.ceil(len(candidates) / size)),
            applicants=candidates[(page - 1) * size : page * size],
            policy=policy.to_dict(),
            pool_id=s.pool_id,
            model_version=s.engine.version,
        )

    @app.get("/api/explain/<applicant_id>")
    @locked
    def explain(applicant_id):
        s = service()
        result = explain_applicant(
            applicant_id,
            s.engine.dm,
            s.engine,
            rows=s.rows(),
            policy=current_policy(),
            scores=s.scores(),
        )
        return jsonify(result), 404 if "error" in result else 200

    @app.post("/api/predict/single")
    @locked
    def single():
        return jsonify(
            explain_row(clean_row(payload()), service().engine, service().policy)
        )

    @app.route("/api/settings/cost_matrix", methods=["GET", "POST"])
    @locked
    def costs():
        s = service()
        data = payload() if request.method == "POST" else request.args
        try:
            params = {
                k: float(data.get(k, v))
                for k, v in {
                    "cost_fp": 500,
                    "cost_fn": 3500,
                    "benefit_tp": 5000,
                    "cost_tn": 0,
                }.items()
            }
        except (TypeError, ValueError):
            raise ValueError(
                "Costs and benefits must be numeric, nonnegative values."
            ) from None
        raw_capacity = data.get("capacity")
        capacity = (
            SelectionPolicy.parse({"top_n": raw_capacity}).top_n
            if raw_capacity not in (None, "")
            else None
        )
        rows = s.engine.dm.rows_for("validation")
        return jsonify(
            compute_cost_matrix_analysis(
                [r["target"] for r in rows],
                s.engine.predict_rows(rows),
                capacity=capacity,
                **params,
            )
        )

    @app.get("/api/fairness/audit")
    @locked
    def fairness():
        s = service()
        scope = request.args.get("scope", "current")
        rows = s.rows(scope)
        policy = current_policy()
        attrs = s.attributes(scope)
        if request.args.get("intersectional") == "true":
            joint = "gender__" + attrs[1]
            rows = [dict(r, **{joint: r["gender"] + " × " + r[attrs[1]]}) for r in rows]
            attrs = attrs + [joint]
        audits = compute_fairness_audit(
            s.engine.dm, s.engine, rows=rows, policy=policy, attributes=attrs
        )
        return jsonify(
            audit=audits,
            scope=scope,
            pool_id=s.scope_id(scope),
            policy=policy.to_dict(),
            model_version=s.engine.version,
            total_rows=len(rows),
            outcome_description=TARGET_DESCRIPTIONS[s.engine.dm.target_kind],
        )

    @app.get("/api/fairness/drivers")
    @locked
    def drivers():
        s = service()
        scope = request.args.get("scope", "current")
        attr = request.args.get("attribute", "gender")
        if attr not in s.attributes(scope):
            raise ValueError("Unknown grouping.")
        return jsonify(
            compute_disparity_drivers(
                s.engine.dm, s.engine, attr, rows=s.rows(scope), policy=current_policy()
            )
        )

    @app.get("/api/fairness/proxies")
    @locked
    def proxies():
        return jsonify(
            candidates=service().engine.proxy_candidates(
                request.args.get("attribute", "experience")
            )
        )

    @app.post("/api/fairness/ablate")
    @locked
    def ablate():
        s = service()
        data = payload()
        scope = data.get("scope", "validation")
        rows = s.rows(scope)
        if not isinstance(data.get("drop_proxies", False), bool):
            raise ValueError("drop_proxies must be boolean.")
        result, candidate = compute_before_after_ablation(
            s.engine.dm,
            s.engine,
            data.get("attribute_to_drop"),
            data.get("drop_proxies", False),
            data.get("protected_attribute", "gender"),
            rows=rows,
            policy=s.policy,
            attributes=s.attributes(scope),
        )
        run_id = uuid.uuid4().hex
        result.update(
            run_id=run_id, scope=scope, pool_id=s.scope_id(scope), status="preview"
        )
        s.store.save_model(candidate)
        s.store.event("ablation_preview", result)
        s.experiments[run_id] = result
        return jsonify(result)

    @app.post("/api/fairness/apply")
    @locked
    def apply_ablation():
        s = service()
        data = payload()
        run = s.experiments.get(data.get("run_id"))
        if not run:
            raise ValueError("Preview an ablation in this session first.")
        if (
            run["baseline_model_version"] != s.engine.version
            or run["pool_id"] != s.scope_id(run["scope"])
            or run["policy"] != s.policy.to_dict()
        ):
            return jsonify(
                error="Workspace changed since this preview. Run a fresh comparison before applying."
            ), 409
        candidate = s.store.load_model(run["candidate_model_version"])
        s.activate(
            candidate,
            "ablation_applied",
            {
                "run_id": run["run_id"],
                "previous_version": s.engine.version,
                "dropped_columns": run["dropped_columns"],
            },
        )
        return jsonify(
            message="Compared model applied. Shortlist and audits now use this model.",
            model=candidate.metadata(),
        )

    @app.post("/api/models/revert")
    @locked
    def revert():
        s = service()
        if len(s.version_history) < 2:
            raise ValueError("No previous model version to restore.")
        history = s.version_history[:-1]
        candidate = s.store.load_model(history[-1])
        if s.pool is not None and s.pool.target_kind != candidate.dm.target_kind:
            raise ValueError(
                "Reset the applicant pool before reverting to a different outcome type."
            )
        s.store.save_active(candidate.version, s.policy, history)
        previous = s.engine.version
        s.engine = candidate
        s.version_history = history
        s.scores_cache = {}
        if s.pool is None:
            s.pool_id = candidate.dm.dataset_id + ":validation"
        s.store.event(
            "model_reverted", candidate.metadata() | {"previous_version": previous}
        )
        return jsonify(message="Previous model restored.", model=candidate.metadata())

    @app.get("/api/history")
    @locked
    def history():
        return jsonify(events=service().store.history())

    @app.get("/api/fairness/export")
    @locked
    def audit_export():
        s = service()
        scope = request.args.get("scope", "current")
        rows = s.rows(scope)
        result = {
            "schema_version": 2,
            "model": s.engine.metadata(),
            "policy": s.policy.to_dict(),
            "pool_id": s.scope_id(scope),
            "scope": scope,
            "outcome": TARGET_DESCRIPTIONS[s.engine.dm.target_kind],
            "audit": compute_fairness_audit(
                s.engine.dm,
                s.engine,
                rows=rows,
                policy=s.policy,
                attributes=s.attributes(scope),
            ),
            "performance": s.engine.evaluate(rows, s.policy),
            "history": s.store.history(limit=None),
            "split": {
                "seed": 42,
                "train": len(s.engine.dm.train_indices),
                "validation": len(s.engine.dm.validation_indices),
                "test": len(s.engine.dm.test_indices),
            },
        }
        return Response(
            json.dumps(result, indent=2, allow_nan=False),
            mimetype="application/json",
            headers={
                "Content-Disposition": 'attachment; filename="fairness_audit.json"'
            },
        )

    return app


if __name__ == "__main__":
    from waitress import serve

    print("FairRecruit is available at http://127.0.0.1:5000", flush=True)
    serve(create_app(), host="127.0.0.1", port=5000, threads=4)
