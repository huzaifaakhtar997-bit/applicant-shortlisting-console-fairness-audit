# Applicant Shortlisting Console with Fairness Audit (FairRecruit)
### DSC306 Data Mining — Semester Project 5 Specification Guide

A comprehensive, production-ready data mining web application designed for recruitment professionals screening high-volume applicant pools. The console replaces subjective keyword matching and gut feeling with an auditable machine learning shortlisting engine and an actionable **Algorithmic Fairness Audit & Mitigation Dashboard**.

![Project Badge](https://img.shields.io/badge/Course-DSC306%20Data%20Mining-blue)
![Python](https://img.shields.io/badge/Python-3.12-green)
![Framework](https://img.shields.io/badge/Flask-3.1-orange)
![Frontend](https://img.shields.io/badge/Bootstrap-5.3-purple)
![Dataset](https://img.shields.io/badge/Dataset-Kaggle%20HR%20Analytics%20(19k)-red)
![Tests](https://img.shields.io/badge/Tests-8%2F8%20Passing%20(100%25)-brightgreen)

---

## Quick Start (Clean Machine Execution)

This application is completely self-contained. It ships with the dataset, requires zero external database setup, and runs with **one documented command**:

```bash
# 1. Clone or navigate to the repository
cd "d:\mid datamining lab"

# 2. Run the application server
python app.py
```

Open your browser to: **`http://127.0.0.1:5000`**

To execute the automated verification test suite:
```bash
python -m unittest tests/test_fairness_engine.py
python verify_spec.py
```

---

## Master Course Rubric Compliance: Stages A through G

Marks are allocated across all seven stages below. Every stage has been implemented and verified.

---

### STAGE A — Data and Documentation

1. **Dataset:**
   - Real Kaggle dataset: *"HR Analytics: Job Change of Data Scientists"* (`aug_train.csv`).
   - Size: **19,158 records** and **14 raw attributes** (plus 3 derived proxy attributes).
   - Contains all four measurement types from Lecture 2:
     - **Nominal:** `gender`, `enrolled_university`, `major_discipline`, `company_type`
     - **Ordinal:** `education_level`, `experience`, `company_size`, `last_new_job`
     - **Ratio:** `training_hours` (has a true absolute zero point at 0 hours)
     - **Interval:** `city_development_index` (standardized economic prosperity index)

2. **Data Dictionary:**
   - Complete data dictionary written and embedded in Screen 1 and `backend/data_manager.py`:
     - Every column, its measurement type, plausible range, and its role (Identifier, Explanatory Attribute, Protected Attribute, or Target Label).

3. **Written Statement of Excluded Columns:**
   - **`enrollee_id`:** Unique administrative database key (19,158 distinct IDs). Excluded from the feature vector because an arbitrary transaction identifier carries zero generalisable semantic signal; training on it causes severe identity memorization, overfitting, and leakage. Retained purely as an audit case index.
   - **`target`:** Ground-truth outcome label (whether the applicant changed jobs / proceeds to interview). At the exact moment the recruiter evaluates incoming applicants, this future outcome is completely unknown. Training on it as an input would constitute catastrophic target leakage. Strictly excluded from input predictors.

---

### STAGE B — Data Quality Audit and Repair (Lectures 2–3)

1. **Six Distinct Fault Categories (Lecture 2 Vocabulary):**
   - **Fault 1: Incompleteness (Missing Values):** Detected in `gender` (4,508 records), `company_size` (5,938), `company_type` (6,140), `major_discipline` (2,813), `education_level` (460), `enrolled_university` (386). Expression: `row[col] in [None, '', 'nan', 'NaN']`. Remediated via explicit `'Unknown'` category and median imputation.
   - **Fault 2: Syntactic Inconsistency (Boundary String Encodings):** Detected in `experience` with raw string bounds `'<1'` (522 records) and `'>20'` (3,286 records). Expression: `row['experience'] in ['<1', '>20']`. Remediated by mapping `<1` to 0 and `>20` to 21 years integer.
   - **Fault 3: Outliers & Extreme Values:** Detected in `training_hours` with values exceeding Tukey's upper fence $Q_3 + 1.5 \times IQR$ (> 185 hours, 984 records). Remediated via continuous scaling.
   - **Fault 4: Arbitrary Identifier / Leakage Risk:** Detected in `enrollee_id` (19,158 unique keys). Expression: `len(set(ids)) == len(records)`. Remediated by strictly excluding from predictive feature matrices.
   - **Fault 5: Delimiter Formatting Contamination:** Detected in `company_size` containing slash delimiters like `'10/49'` (1,471 records). Expression: `'/' in str(row['company_size'])`. Remediated by standardizing to hyphenated range `'10-49'`.
   - **Fault 6: Categorical Redundancy & Null Conflict:** Detected in `enrolled_university` where higher education degrees had missing enrollment status (386 records). Remediated by composite tier mapping.

2. **Provenance Columns & Before-and-After Repair Table:**
   - Every repaired field carries a dedicated provenance column: `_prov_gender`, `_prov_experience`, `_prov_company_size`, `_prov_city_development_index`, `_prov_training_hours`, etc.
   - Values indicate origin: `'raw_observed'`, `'imputed_unknown'`, `'imputed_median'`, `'mapped_lower_bound'`, `'mapped_upper_bound'`, `'fixed_slash_format'`.
   - Screen 1 displays a Before-and-After table showing the exact numeric impact of each repair.

3. **10-Assertion `validate()` Engine:**
   - Implemented in `backend/data_manager.py:validate(data)`.
   - **Passes 100% on cleaned data (10/10 green checks) and fails on raw uncleaned data.**
   - Assertions cover: missing values, valid interval bounds, positive ratios, string boundary removal, slash delimiter elimination, proxy validity, and provenance presence.

4. **Cleaned Dataset Download:**
   - One-click download available via `/api/dataset/cleaned/download`, providing `cleaned_applicants_with_provenance.csv`.

---

### STAGE C — Pre-Processing (Lectures 3–4)

1. **Attribute Rescaling Decision per Model Family:**
   - **Decision Tree:** Rescaling **not needed**. Tree split optimization depends purely on rank order and is invariant to monotonic transformations.
   - **Naïve Bayes:** Gaussian distributions model feature variance independently per class; univariate normalization applied.
   - **k-Nearest Neighbours (KNN):** Rescaling **strictly required**. Without standard scaling, Euclidean distance $\sqrt{\sum (x_i - y_i)^2}$ would be overwhelmed by `training_hours` (1 to 336) compared to `city_development_index` (0.4 to 0.95).

2. **Dimensionality Reduction (PCA) vs. Feature Subset Selection:**
   - Evaluated on the exact same Decision Tree classifier:
     - **Baseline (All 48 Features):** Accuracy = 79.1%, AUC = 0.791. High interpretability.
     - **Feature Subset Selection (Top 10 Features):** Accuracy = 78.1%, AUC = 0.745. Very high interpretability; eliminates noisy categories with zero loss in decision path readability.
     - **PCA Dimensionality Reduction (10 Orthogonal Components):** Accuracy = 76.3%, AUC = 0.681. Low interpretability; orthogonal eigenvectors destroy domain feature names, making recruiter-facing explanations impossible.

3. **Discretization & Binarization Justification:**
   - `experience` discretized into 4 Age Bands (`0-5`, `6-10`, `11-15`, `16+` years) based on career seniority stages.
   - `city_development_index` discretized into 3 development tiers (Low <0.65, Medium 0.65-0.85, High >0.85).

---

### STAGE D — Models (Lectures 5–14)

1. **Three Classifiers from Three Distinct Families:**
   - **Family 1 (Tree-Based): Decision Tree Classifier** (`decision_tree`) — self-explains via human-readable decision rules.
   - **Family 2 (Probabilistic / Bayesian): Naïve Bayes Classifier** (`naive_bayes`) — models class likelihoods and prior odds.
   - **Family 3 (Instance-Based): k-Nearest Neighbours Classifier** (`knn`) — evaluates $k=7$ nearest historical candidates.
   - *(Benchmark: Logistic Regression and Random Forest retained as linear/ensemble baselines).*

2. **Hyper-Parameter Selection Procedure:**
   - Hyper-parameters selected via 5-Fold Cross-Validation Grid Search over validation folds (e.g. `max_depth` $\in [3, 5, 8, 12]$, `min_samples_split` $\in [10, 20, 50]$ for Decision Tree; $k \in [3, 5, 7, 11]$ for KNN; smoothing $\alpha$ for Naïve Bayes).

---

### STAGE E — Evaluation (Lectures 9–10)

1. **Train/Test Split:**
   - 80/20 Stratified Split with fixed random seed `42` (15,326 train / 3,832 test). Stratification guarantees identical 24.9% positive class prevalence across both partitions.

2. **Majority-Class Baseline Reported Beside Every Accuracy Figure:**
   - Majority class in dataset is negative ($y=0$, 75.07%).
   - ZeroR majority-class baseline is **75.07%**.
   - Reported in all tables and cards: e.g., *"Accuracy: 79.1% (Baseline: 75.1%, Delta: +4.0%)"*.

3. **Two Metrics Beyond Accuracy with Written Justification:**
   - **Precision (Positive Predictive Value):** Recruiter and hiring manager interview bandwidth is tightly constrained. False positives waste hundreds of expensive interviewer hours on unqualified candidates.
   - **Recall (Sensitivity / True Positive Rate):** The opportunity cost of a false negative is severe: failing to shortlist a high-performing data scientist allows competitor firms to hire them.

4. **ROC Curve with AUC & Cost Matrix Operating Threshold:**
   - Screen 2 renders interactive ROC curves with trapezoidal AUC.
   - Screen 5 provides an interactive financial **Cost Matrix Editor**:
     - Cost of False Positive ($C_{FP}$): \$500 (interviewer cost)
     - Cost of False Negative ($C_{FN}$): \$3,500 (lost candidate value)
     - Benefit of True Positive ($B_{TP}$): \$5,000 (value of qualified hire)
     - Cost of True Negative ($C_{TN}$): \$0
   - Computes expected net financial cost across thresholds $\theta \in [0.05, 0.95]$ and identifies the **Cost-Optimal Operating Threshold $\theta^*$** rather than defaulting to arbitrary 0.50.

5. **k-Fold Cross Validation with Spread Reported:**
   - 5-Fold Cross-Validation run on the training portion for every model:
     - Decision Tree: $78.24\% \pm 0.77\%$ (Range: $77.2\% - 79.5\%$)
     - Naïve Bayes: $68.76\% \pm 0.82\%$ (Range: $67.8\% - 70.0\%$)
     - KNN: $74.90\% \pm 0.39\%$ (Range: $74.4\% - 75.4\%$)
     - Logistic Regression: $76.94\% \pm 0.33\%$ (Range: $76.6\% - 77.4\%$)

---

### STAGE F — Explanation

1. **Every Prediction Shows Its Reason:**
   - Decision path / rule written strictly in the user's language, not the model's:
     - Example: *"City Development Index is high (0.92) AND Education is Masters degree AND 12 years of industry experience"*, rather than *"node 14, gini 0.31"*.
   - Feature attribution breakdown highlighting top positive drivers advancing the candidate and top negative inhibitors holding them back.
   - Plain-English Executive Recruiter narrative summarizing candidate match probability.

---

### STAGE G — The Application (Six Screens)

| Screen | Name | Capabilities & Workflow |
|---|---|---|
| **Screen 1** | **Data & Quality** | Ingest data, inspect 6 fault categories quality audit report, run 10-point `validate()` engine, view data dictionary, read statement of excluded columns, and download cleaned CSV with provenance. |
| **Screen 2** | **Model Performance** | Comparison table across Decision Tree, Naïve Bayes, and KNN with majority-class baseline beside every figure, ROC curves, confusion matrix, PCA vs feature selection table, and 5-fold CV spread. |
| **Screen 3** | **Single Prediction** | Recruiter candidate profile form $\rightarrow$ real-time prediction verdict (PROCEED TO INTERVIEW vs HOLD), confidence %, and plain-English decision path explanation. |
| **Screen 4** | **Batch Scoring** | Batch scoring pool $\rightarrow$ ranked, filterable candidate table with probability threshold slider, top-N cutoff, inline criteria breakdown drawer, and CSV shortlist export. |
| **Screen 5** | **Settings** | Choose classifier family, move decision threshold slider, edit financial cost matrix, and observe consequences update live on the Expected Cost curve. |
| **Screen 6** | **Domain Screen: Fairness Audit** | **Project 5 Challenge:** Compute selection rate, recall, and precision across Gender, Age Band, and Institution. Detect EEOC 80% rule violations, diagnose disparity drivers ($\beta \times \Delta\bar{x}$), and execute Feature Ablation Remediation. |

---

## Technical Architecture & File Organization

```
mid datamining lab/
├── app.py                             # Flask application server (7 RESTful endpoints)
├── aug_train.csv                      # Kaggle HR Analytics dataset (19,158 records)
├── requirements.txt                   # Dependency manifest
├── verify_spec.py                     # Automated end-to-end specification verifier
├── generate_viva_pdf.py               # 8-page comprehensive Viva Voce Report PDF generator
├── Applicant_Shortlisting_...pdf      # 8-page technical and viva voce reference report
│
├── backend/
│   ├── data_manager.py                # Ingestion, proxies, 6 fault categories, provenance, 10-point validate()
│   ├── ml_engine.py                   # DT, NB, KNN, LogReg, Cost Matrix, 5-Fold CV, PCA vs Feature Selection
│   ├── fairness_audit.py              # EEOC 80% rule, group recall/precision, disparity drivers, ablation
│   └── explainability.py              # Individualized local marginal feature attribution and recruiter narratives
│
├── templates/
│   └── index.html                     # 6-screen responsive UI (Bootstrap 5, Chart.js)
│
├── static/
│   ├── css/style.css                  # Custom recruiter styling, audit alerts, criteria badges
│   └── js/app.js                      # Reactive frontend controllers for all 6 screens
│
└── tests/
    └── test_fairness_engine.py        # 8 automated unit tests (100% passing)
```

---

## Regulatory Compliance & Fairness Metrics

- **Demographic Parity (Selection Rate):** $SR(g) = \frac{N_{\text{shortlisted}}(g)}{N_{\text{total}}(g)}$
- **Equal Opportunity (Group Recall):** $\text{Recall}(g) = \frac{TP(g)}{TP(g) + FN(g)}$
- **Predictive Parity (Group Precision):** $\text{Precision}(g) = \frac{TP(g)}{TP(g) + FP(g)}$
- **EEOC 80% (Four-Fifths) Adverse Impact Rule:** $\text{Ratio}(g) = \frac{SR(g)}{\max_k SR(k)} \quad (\text{Flagged in RED if } < 0.80)$
- **Small Sample Size Warning:** Groups with $N < 30$ flagged as statistically volatile.
- **Disparity Driver Identification:** $\text{Driver Impact}_j = \beta_j \times (\bar{x}_{j, \text{fav}} - \bar{x}_{j, \text{dis}})$
- **Feature Ablation Remediation:** Retrains model without offending driver column and evaluates Before-vs-After tradeoff in Selection Rate Gap vs ROC-AUC.
