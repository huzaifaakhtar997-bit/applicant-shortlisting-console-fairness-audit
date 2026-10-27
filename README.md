# FairRecruit

A local applicant-ranking and fairness-audit workbench for Data Mining Project 5. The application separates model training, incoming applicant scoring, and evaluation. It supports controlled attribute-removal experiments with saved apply/revert versions.

**Outcome limitation:** the bundled Kaggle dataset measures **job-change interest**, not interview suitability. The application labels it as a demonstration throughout. Uploaded labeled training data can explicitly define an interview-progression outcome. Label validity and historical bias remain human review tasks.

## Run locally

Verified with Python 3.13. Node is only needed for frontend development checks; the application has no frontend build step, CDN or external font dependency.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:5000. `python app.py` uses Waitress on loopback, with debug disabled. On Linux/macOS, use `.venv/bin/python` instead of the Windows interpreter path.

Models, training records and audit history are saved under `.local/`, which is Git-ignored. Set `FAIRRECRUIT_DATA_DIR` before launch to choose another local directory. Incoming applicant pools stay in memory and reset to the validation demo pool after restart. Use one server process per workspace. This is a local educational workbench, not an authenticated multi-user hiring service.

## Six connected views

1. **Overview:** pool counts, actual selection volume, coverage, model context and group-rate overview.
2. **Applicant pool:** ranked records, search, status filters, pagination, exact-policy CSV export, candidate evidence and single-record assessment.
3. **Model performance:** baseline, accuracy, precision, recall, F1, balanced accuracy, ROC-AUC, average precision, precision@100, confusion matrix, five-family benchmarks, CV and real feature selection/PCA.
4. **Data & quality:** schema checks, raw missingness, provenance, descriptive outlier flags, dictionary, split counts and cleaned export.
5. **Model & policy:** classifier, threshold or top-N capacity, validation-only cost analysis, training replacement, version revert and audit history.
6. **Fairness audit:** selection, recall and precision by group; all gaps; denominator support; intervals; intersectional inspection; measured driver sensitivity; before/after ablation; apply and revert.

## Use your own applicants

Upload `examples/unlabeled_applicants.csv` using **Upload applicants**. It contains fictional records, no targets, actual example age bands/institutions and some missing inputs. It demonstrates scoring without retraining. Selection rates remain available while precision, recall and accuracy correctly show N/A without outcomes.

Required CSV headers: `city_development_index`, `training_hours`, `experience`, `education_level`, `relevent_experience` (the original dataset's spelling). Blank numeric inputs are allowed and are imputed by the existing training pipeline. Optional predictor columns are `enrolled_university`, `major_discipline`, `company_size`, `company_type`, `last_new_job`; absent values become Unknown.

Optional columns: unique `enrollee_id`, binary `target`, `gender`, `age` or `age_band`, and `institution`. Provided actual age bands and institution names are preserved. CSV must be UTF-8, at most 32 MB and 100,000 records; individual fields are limited to 200 characters. Duplicate IDs, invalid numeric ranges and malformed labels are rejected before the active pool changes. Download a template from the upload dialog.

To train on different outcomes, use **Model & policy → Replace labeled training data**, choose the outcome meaning, and supply complete 0/1 targets with at least 10 records per class. This fits a new model and creates a version; it does not silently relabel missing outcomes.

## Scientific design

- Target-stratified 60/20/20 train/validation/test partitions with seed 42. The default pool is the validation partition, never the training set.
- A persisted scikit-learn Pipeline learns numeric median imputation, categorical vocabularies and optional numeric scaling on training rows. Unknown categories are handled consistently. The same pipeline scores batch, single, explanations and audit routes.
- Gender, actual age and institution are audit-only. Years of experience are a numeric predictor. When actual audit fields are absent, **experience band · demo** and **education group · demo** are clearly named substitutes, not claims of age/institution fairness.
- Five model families: Decision Tree, Logistic Regression, Random Forest, Gaussian NB and KNN. Benchmarks use validation data and shuffled stratified training CV with fold-local preprocessing. Gaussian NB is a baseline whose Gaussian/independence assumptions are imperfect for categorical indicators.
- Feature selection actually ranks train-fitted tree importances; PCA fits on scaled training features. There is no silently different pure-Python/PCA fallback.
- One selection policy governs ranking, explanations, audits and exports. Top-N overrides the threshold; ties use unrounded scores then lexicographic applicant ID. A standalone record has no top-N verdict until compared against a pool.
- Tree explanations show the real path. Source-attribute perturbations measure actual score changes against training references. No contribution, direction or qualification narrative is fabricated. Perturbations are not additive or causal; scores are not calibrated confidence.
- Four-fifths ratios are exploratory screening flags, not proof of compliance or discrimination. Zero denominators return null/N/A. Small-group warnings consider total size, known positives and labeled selections. Rate intervals use Wilson; gap intervals use a reproducible plug-in binomial bootstrap. Missing outcomes may still bias label-dependent estimates.
- Driver diagnostics measure model sensitivity by replacing whole source attributes. Optional associated-input removal uses training-only normalized mutual information with the chosen attribute, not arbitrary protected dummy columns. Association does not establish proxy discrimination.
- Ablations fit separate models, preserve all baseline state and evaluate the same rows/policy. Preview returns all group metrics and performance. Apply checks dataset/policy/model freshness, saves a new version and updates the complete workspace. Revert restores a previous snapshot.
- Cost thresholds are selected from validation outcomes, with optional capacity limits. Costs are user assumptions, not measured financial returns. Test access is explicit and should be reserved for final evaluation.

## Tests and verification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
npm ci
npm test
```

The Python regression suite covers formulas, data validation, score-path consistency across all five models, fold-local preprocessing, missing labels, policy/export/audit consistency, isolated ablation, stale previews, apply/revert/restart and concurrent previews. Frontend tests execute the real page consumers against responses produced by the real Flask API, including the formerly broken nested fairness contract, escaped uploaded values and automated accessibility checks. Color contrast and responsive layout also require a real browser; JSDOM does not measure rendered contrast.

With the server running:

```powershell
.\.venv\Scripts\python.exe verify_spec.py
```

This checks the full bundled dataset and all five benchmarks. It creates an unapplied experiment and saves `.local/verification.json`. Use `--include-test` only for the final evaluation. It never replaces uploads or applies an intervention.

For development formatting/lint:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m ruff check app.py backend tests verify_spec.py
npm run format:check
```

## Code map

- `backend/data_manager.py`: schema, deterministic repairs, provenance, demographics and fixed partitions.
- `backend/ml_engine.py`: fitted pipelines, metrics, CV, feature selection/PCA and training associations.
- `backend/policy.py`: validated, deterministic threshold/top-N decisions.
- `backend/fairness_audit.py`: grouped metrics, uncertainty, driver diagnostics and isolated ablation.
- `backend/explainability.py`: real tree paths and measured perturbations.
- `backend/storage.py`: model snapshots and append-only SQLite events; no candidate files loaded from uploads as executable artifacts.
- `app.py`: app factory, serialized workspace changes, APIs, input errors and local serving.
- `static/js/app.js`, `static/css/style.css`, `templates/index.html`: offline, responsive interface with native dialogs, explicit loading/error states and accessible controls.

See [the complete viva examination handbook](docs/VIVA_COMPLETE_GUIDE.md), [the algorithm performance report](docs/ALGORITHM_PERFORMANCE_REPORT.md), and the generated publication PDFs:
- [Complete Viva Guide PDF](output/pdf/FairRecruit_Complete_Viva_Guide.pdf)
- [Algorithm Performance Report PDF](output/pdf/FairRecruit_Algorithm_Performance_Report.pdf)

## Data and interpretation references

- [Dataset publisher](https://www.kaggle.com/datasets/arashnic/hr-analytics-job-change-of-data-scientists)
- [scikit-learn preprocessing and leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html)
- [Fairlearn metric definitions and limitations](https://fairlearn.org/main/user_guide/assessment/common_fairness_metrics.html)
- [EEOC clarification of the four-fifths screening rule](https://www.eeoc.gov/laws/guidance/questions-and-answers-clarify-and-provide-common-interpretation-uniform-guidelines)
