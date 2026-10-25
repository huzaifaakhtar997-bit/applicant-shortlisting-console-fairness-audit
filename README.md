# Applicant Shortlisting Console with Fairness Audit (FairRecruit)

A comprehensive data mining web application designed for recruitment professionals screening high-volume applicant pools. The console replaces subjective keyword filtering and gut feeling with an auditable machine learning shortlisting engine and an actionable **Algorithmic Fairness Audit Dashboard**.

![Project Badge](https://img.shields.io/badge/Data%20Mining-Lab%20Project%205-blue)
![Python](https://img.shields.io/badge/Python-3.12-green)
![Framework](https://img.shields.io/badge/Flask-3.1-orange)
![Frontend](https://img.shields.io/badge/Bootstrap-5.3-purple)
![Dataset](https://img.shields.io/badge/Dataset-Kaggle%20HR%20Analytics%20(19k)-red)

---

## The Problem
Recruiters screening several hundred applications for a handful of posts often rely on keyword matching and intuition. This process is slow, inconsistent, and offers no empirical audit trail to prove whether decisions were fair across demographic groups.

## What the Product Does
The recruiter uploads the applicant pool (or uses the built-in 19,158-record dataset) and receives a ranked shortlist with the criteria behind each ranking. Beside it, an actionable audit evaluates whether the shortlist's selection rate, recall, and precision differ across **Gender**, **Age Band**, and **Institution**.

---

## The 6 Screens

1. **Screen 1: Data Ingestion**  
   - Loads the real Kaggle *"HR Analytics: Job Change of Data Scientists"* dataset (19,158 rows).
   - Class balance breakdown (24.9% interview selection baseline).
   - Demographic distribution charts (Gender, Age Band, Institution).
   - Preview table with first 10 candidate records + CSV file upload.

2. **Screen 2: Preprocessing & Proxy Feature Intelligence**  
   - Missing value imputation (medians for numericals, `"Unknown"` for categoricals).
   - One-hot encoding summary (48 binary predictors).
   - **Proxy Detection Table**: Computes Pearson correlation between all predictors and protected attributes to highlight proxy risks ($\ge 0.25$).

3. **Screen 3: Classification Engine**  
   - Models: **Logistic Regression** (L2 regularized) and **Random Forest**.
   - Stratified 80/20 train/test split (fixed seed `42`).
   - Interactive probability threshold slider ($\tau \in [0.10, 0.90]$).
   - Accuracy, Precision, Recall, F1, ROC-AUC, Confusion Matrix, and interactive ROC Curve.

4. **Screen 4: Candidate Shortlisting & Ranking Console**  
   - Ranked candidate pool sorted by qualification score $P(\text{interview})$.
   - Filter by threshold $\tau$ or Top-$N$ cutoff (e.g. Top 25, 50, 100).
   - One-click CSV export of the shortlisted cohort (`applicant_shortlist.csv`).
   - Quick navigation to inspect criteria for any applicant.

5. **Screen 5: Decision Criteria Explainability**  
   - Local feature attribution: $\text{Contribution}_j = \beta_j \times x_{i,j}$.
   - Waterfall / Bar chart in green (pushed score up) and red (pushed score down).
   - Individual candidate dossier and predictor weights.

6. **Screen 6: Fairness Audit & Mitigation Dashboard (Technical Challenge)**  
   - **Group-by-Group Metrics**: Group size, selection rate, recall (TPR), and precision across Gender, Age Band, and Institution.
   - **80% Rule (Four-Fifths Rule)**: Flags any group where $\frac{\text{Selection Rate}(g)}{\max_k \text{Selection Rate}(k)} < 0.80$ with a red warning badge.
   - **Small-Group Warning**: Flags groups with $<30$ test records as statistically unreliable.
   - **Disparity Driver Panel**: Identifies which features drive the gap using $\beta_j \times (\bar{x}_{j, \text{favoured}} - \bar{x}_{j, \text{disadvantaged}})$.
   - **Before vs After Feature Ablation Sandbox**: Select an attribute to drop (with optional top-3 proxy dropping). Retrains model on the same split and presents side-by-side Before, After, and Delta comparison table.
   - **Recruiter Diagnostic Callout**: *"If the gap barely changed, other features are acting as proxies for the dropped attribute."*

---

## Methodological Note on Proxies

- **Age Band (Proxy)**: Derived from the `experience` column (`0-5`, `6-10`, `11-15`, and `16+` years).
- **Institution (Proxy)**: Derived from `enrolled_university` and `education_level` (`Postgraduate Institution`, `Graduate University`, `Continuing/Enrolled University`, `Non-Degree/School`).
- **Proceed to Interview (Proxy Target)**: The binary target (`target` = 1) represents candidate qualification / proceed to interview.

---

## Installation & Quickstart

```bash
# Clone the repository
git clone https://github.com/huzaifaakhtar997-bit/applicant-shortlisting-console-fairness-audit.git
cd applicant-shortlisting-console-fairness-audit

# Install dependencies
pip install -r requirements.txt

# Run automated tests
python tests/test_fairness_engine.py

# Launch the console
python app.py
```

Open your browser at **`http://127.0.0.1:5000`**.

---

## Verification Test Suite

The test suite in `tests/test_fairness_engine.py` verifies:
1. Full dataset loading (19,158 records) and proxy attribute derivation.
2. Model training and metric validation (Accuracy, AUC, F1, Confusion Matrix).
3. Exact match against hand-calculated fairness metrics (Selection Rate, Recall, Precision, Four-Fifths ratio, Gaps).
4. Dropped attributes are excluded from model features but retained for group auditing.
5. Invariance of the stratified split before and after feature ablation.
