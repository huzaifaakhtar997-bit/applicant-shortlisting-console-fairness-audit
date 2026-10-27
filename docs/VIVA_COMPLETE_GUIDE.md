# FairRecruit: Comprehensive Viva Examination Handbook & Technical Reference

**Data Mining Project 5 | Local Applicant Shortlisting Console & Fairness Audit Workbench**  
*Verified Implementation & Technical Defense Guide | October 2026*

---

## 1. Executive Summary: Overarching Goal, Accomplishments & Reality

### The Business Problem vs. Engineering Goal
In modern corporate hiring, automated machine learning models are deployed to screen thousands of resumes. However, commercial black-box models frequently suffer from:
1. **Historical Bias Propagation:** Disproportionately filtering out protected demographic groups (e.g., gender, age, educational background).
2. **Data Leakage:** Naively fitting transformers (scalers, imputers) across the entire dataset before splitting, leading to inflated, unreproducible metrics.
3. **Lack of Explainability:** Providing opaque probability scores without defensible decision paths or sensitivity diagnostics.

**Our Goal:** To build a transparent, local, and reproducible recruitment shortlisting console and algorithmic fairness audit workbench that:
- Trains and benchmarks multiple supervised classification algorithms under strict train-only preprocessing.
- Implements dual decision policies: fixed-threshold screening and fixed-capacity Top-N quota ranking with deterministic tie-breaking.
- Audits selection disparity using three complementary fairness gap metrics: **Demographic Parity (Selection Rate Gap)**, **Equal Opportunity (Recall Gap)**, and **Predictive Parity (Precision Gap)**, supported by 95% Wilson confidence intervals.
- Extracts faithful decision-tree paths and source-column perturbation diagnostics.
- Supports controlled before-and-after feature ablation experiments with version-controlled rollback.

### What Was Achieved
- **Leakage Elimination:** Unified scikit-learn `Pipeline` fitted strictly on the 60% training partition; pipeline is independently refitted within each cross-validation fold.
- **Dual Selection Policies:** Explicit decoupling of model scoring from selection rules via `SelectionPolicy`.
- **Comprehensive Fairness Auditing:** Exact mathematical computation of all three gaps, adverse impact screening ratios (Four-Fifths Rule), and denominator-aware warnings.
- **Isolated Ablation Engine:** Controlled retraining without specific predictors (e.g. city development index) with active manifest versioning and SQLite audit logging.
- **Unlabeled Candidate Uploads:** Cleanly scored without fabricating ground-truth labels or contaminating the trained model.

> [!WARNING]
> ### Critical Viva Distinction: The Surrogate Label Limitation
> The demonstration data is the Kaggle HR Analytics dataset (19,158 records). In this dataset, `target = 1` denotes an enrollee **looking for a job change**, while `target = 0` denotes someone not actively seeking a change. In our console, this is treated as a demonstration surrogate for candidate shortlisting.
> 
> **Examiner Defense Rule:** Never claim this model predicts job competency, technical skill, or hiring success. Real recruitment systems require role-specific competency evaluations, defensible job criteria, and legal oversight. Conflating job-seeking interest with hiring qualification is a fatal conceptual flaw.

---

## 2. Data Architecture, Preprocessing & Leakage Elimination

### Dataset Splitting Hygiene
- **Total Dataset:** 19,158 tabular records.
- **Stratified Partitioning:** Deterministically partitioned using a stratified **60% Training (11,494), 20% Validation (3,832), and 20% Test (3,832)** split (`random_state=42`).
- **Feature Space:** 10 active model predictors expanded into 45 encoded features.

| Variable Name | Raw Type | Preprocessing & Cleaning Technique | Role in Console |
|---|---|---|---|
| `enrollee_id` | Integer ID | Preserved for tracking and tie-breaking; strictly excluded from feature matrices. | Excluded / Identifier |
| `gender` | Categorical | Missing values (~23.5%) mapped to explicit `'Unknown'`. Retained for auditing. | Excluded from Inputs (Audit Only) |
| `city_development_index` | Float (0.450 - 0.949) | Continuous urban development score; median imputed if missing. | Active Input Predictor |
| `experience` | Censored String | Censored strings mapped: `'<1'` -> 0, `'>20'` -> 21. Continuous numeric years. | Active Input Predictor |
| `training_hours` | Integer (1 - 336) | Continuous completed hours; median imputed. Outlier IQR fence flagged. | Active Input Predictor |
| `education_level` | Categorical (5 levels) | Missing mapped to `'Unknown'`; One-Hot Encoded (`handle_unknown='ignore'`). | Active Input (One-Hot) |
| `company_size` / `type` | Categorical | Missing mapped to `'Unknown'`; One-Hot Encoded with 0/1 dummy indicators. | Active Input (One-Hot) |
| `relevent_experience` | Binary Categorical | Mapped to dummy binary indicator (`'Has relevant experience'`). | Active Input (One-Hot) |

### Key Preprocessing Techniques
1. **Explicit Missing Token (`'Unknown'`):** 4,508 records (23.53%) lack gender information. Rather than dropping these records (which introduces selection bias) or guessing values, they are mapped to an explicit `'Unknown'` token. This allows auditing selection disparity among candidates who decline to state demographics.
2. **Boundary Mapping for Censored Categories:** Strings such as `'<1'` and `'>20'` are censored observations, not erroneous data. Mapping them to numeric boundaries (0 and 21) preserves monotonic ordering while documenting exact provenance in `_prov_` columns.
3. **Outlier Detection via IQR Fences:** For skewed features (`training_hours`), outlier fences are computed: $[Q_1 - 1.5 \cdot IQR, Q_3 + 1.5 \cdot IQR]$. Extreme values are flagged for human inspection, but not arbitrarily deleted. *Examiner note:* Standard scaling does NOT remove outliers; it merely rescales the distribution.
4. **Elimination of Data Leakage:** In naive implementations, scalers and imputers are fit across the entire dataset prior to splitting. This constitutes data leakage because validation and test distributions contaminate the training process. In our architecture, `SimpleImputer`, `StandardScaler`, and `OneHotEncoder` are fitted strictly on the 60% training split via a scikit-learn `Pipeline`. Test and live upload data only undergo `transform()`. Inside cross-validation, the entire pipeline is refitted independently inside every fold.

---

## 3. Machine Learning Techniques & What Happens Inside Each Algorithm

### A. Decision Tree Classifier (Active Default Model)
- **Algorithmic Workflow:** Recursively partitions the training space into orthogonal hyperplanes. At every internal node, the algorithm iterates over all 45 encoded features and candidate thresholds, selecting the split that maximizes the reduction in weighted Gini Impurity.
- **Gini Impurity Formula:**
  $$I_G(\text{Node}) = 1 - \sum_{c=0,1} (p_c)^2$$
  - Pure node (100% class 0 or 100% class 1): $I_G = 1 - (1.0^2 + 0^2) = 0.0$ (minimum impurity).
  - Maximum impurity (50% class 0, 50% class 1): $I_G = 1 - (0.5^2 + 0.5^2) = 0.50$.
- **Weighted Impurity Reduction (Information Gain):**
  $$\Delta I_G = I_G(\text{Parent}) - \left[ \frac{N_{\text{Left}}}{N_{\text{Parent}}} I_G(\text{Left}) + \frac{N_{\text{Right}}}{N_{\text{Parent}}} I_G(\text{Right}) \right]$$
- **Configured Hyperparameters:** `max_depth = 5`, `min_samples_leaf = 25`, `random_state = 42`.
  - *Why depth 5?* Restricts the tree to a maximum of 32 leaves, preventing deep memorization of noise while preserving white-box rule interpretability.
  - *Why leaf size 25?* Ensures leaf probability estimates have sufficient statistical support.

#### Hand-Worked Calculation of Gini Impurity Reduction (Viva Favorite)
Suppose a parent node has **100 applicants: 25 positive ($Y=1$) and 75 negative ($Y=0$)**.
1. **Parent Impurity:**
   $$I_G(\text{Parent}) = 1 - \left[\left(\frac{25}{100}\right)^2 + \left(\frac{75}{100}\right)^2\right] = 1 - [0.0625 + 0.5625] = 0.3750$$
2. **Split on `city_development_index <= 0.625`:**
   - **Left Child (40 applicants):** 20 positive, 20 negative.
     $$I_G(\text{Left}) = 1 - \left[\left(\frac{20}{40}\right)^2 + \left(\frac{20}{40}\right)^2\right] = 1 - [0.25 + 0.25] = 0.5000$$
   - **Right Child (60 applicants):** 5 positive, 55 negative.
     $$I_G(\text{Right}) = 1 - \left[\left(\frac{5}{60}\right)^2 + \left(\frac{55}{60}\right)^2\right] = 1 - [0.00694 + 0.84028] = 0.1528$$
3. **Weighted Child Impurity:**
   $$\text{Weighted Child } I_G = \left(\frac{40}{100}\right) \times 0.5000 + \left(\frac{60}{100}\right) \times 0.1528 = 0.2000 + 0.0917 = 0.2917$$
4. **Impurity Reduction:**
   $$\Delta I_G = 0.3750 - 0.2917 = +0.0833$$
   The tree commits this split because it significantly purifies the candidate groups.

---

### B. Logistic Regression (Linear Log-Odds & Sigmoid)
- **Algorithmic Workflow:** Models the log-odds of candidate interest as a linear combination of features:
  $$\ln\left(\frac{p}{1-p}\right) = w^T x + b$$
- **Sigmoid Activation:**
  $$p = \sigma(w^T x + b) = \frac{1}{1 + e^{-(w^T x + b)}}$$
- **Binary Cross-Entropy Loss:**
  $$\mathcal{L} = -\frac{1}{N} \sum_{i=1}^N \left[ y_i \ln(p_i) + (1 - y_i) \ln(1 - p_i) \right] + \frac{\lambda}{2} \|w\|^2$$
- *Why Scaling is Mandatory:* L-BFGS gradient optimization penalizes weight magnitude ($\|w\|^2$). Unscaled features with large ranges (`training_hours`: 1-336) would dominate features with small ranges (`city_index`: 0.45-0.95), corrupting the learned coefficients.

---

### C. Random Forest (Bootstrap Bagging Ensemble)
- **Algorithmic Workflow:** Builds an ensemble of 80 decorrelated trees (`n_estimators=80`, `max_depth=8`, `min_samples_leaf=15`).
- **Bootstrap Sampling:** Each tree is trained on a random sample of size $N$ drawn with replacement from the training set.
- **Random Feature Subspacing:** At each node, only $m = \sqrt{45} \approx 7$ random features are considered for splitting.
- **Averaging:** Final candidate probability is the mean of all 80 tree outputs:
  $$p(x) = \frac{1}{80} \sum_{t=1}^{80} p_t(x)$$
- *Tradeoff:* Reduces variance and slightly improves validation AUC (0.7845 vs 0.7760), but acts as a black box; decision paths cannot be verified by human recruiters.

---

### D. Gaussian Naive Bayes (Conditional Independence)
- **Algorithmic Workflow:** Applies Bayes' Theorem under the naive assumption that all features are conditionally independent given the target:
  $$P(Y=1 | x) \propto P(Y=1) \prod_{j=1}^M P(x_j | Y=1)$$
- **Gaussian Likelihood:**
  $$P(x_j | y) = \frac{1}{\sqrt{2\pi\sigma_y^2}} \exp\left( -\frac{(x_j - \mu_y)^2}{2\sigma_y^2} \right)$$
- **Variance Smoothing (`var_smoothing = 1e-3`):** Adds an epsilon fraction of the maximum feature variance to all variances, preventing division by zero.
- *Limitation:* Categorical one-hot dummy variables violate continuous normal distributions and feature independence.

---

### E. K-Nearest Neighbors (KNN - Instance-Based Learning)
- **Algorithmic Workflow:** Stores the entire scaled training matrix. Computes Euclidean distance to all 11,494 training records:
  $$d(x, x') = \sqrt{\sum_{j=1}^M (x_j - x'_j)^2}$$
- **Distance-Weighted Voting (`weights='distance'`):** The $k=7$ nearest neighbors vote with weight $w_i = 1 / d(x, x_i)$.
- **Bug Fixed:** The legacy codebase standardized train, test, and live applicants separately (a single row standardized against itself produced all zeros!). Our unified pipeline binds `StandardScaler` to the training set, ensuring exact score agreement.

---

### F. Dimensionality Reduction: PCA vs. Train-Fitted Feature Selection
- **Train-Fitted Importance Selection (`SelectFromModel`):** Fits a Decision Tree and selects the top 10 features ranked by Gini importance (e.g. `city_development_index`, `experience`, `company_size`). Retains original feature names and interpretability.
- **Principal Component Analysis (PCA):** Computes the covariance matrix of scaled training data, extracts orthogonal eigenvectors, and projects data onto the 10 principal components of greatest variance (explaining ~58.4% of total variance).
- *Viva Insight:* While PCA mathematically minimizes reconstruction loss, every principal component is a linear mixture of all 45 inputs, destroying human interpretability in recruitment audits.

---

## 4. Performance Evaluation Metrics & Hand Calculations

### Confusion Matrix Definitions
- **True Positive (TP):** Labeled candidate looking for change ($Y=1$), correctly shortlisted.
- **False Positive (FP):** Labeled candidate NOT looking for change ($Y=0$), incorrectly shortlisted (wasted interview).
- **False Negative (FN):** Labeled candidate looking for change ($Y=1$), mistakenly rejected (talent loss).
- **True Negative (TN):** Labeled candidate NOT looking for change ($Y=0$), correctly rejected.

### Metric Formulas
$$\text{Accuracy} = \frac{TP + TN}{TP + FP + FN + TN}$$
$$\text{Precision (PPV)} = \frac{TP}{TP + FP} \quad (\text{Undefined if } TP + FP = 0)$$
$$\text{Recall (TPR)} = \frac{TP}{TP + FN} \quad (\text{Undefined if } TP + FN = 0)$$
$$\text{Specificity (TNR)} = \frac{TN}{TN + FP}$$
$$\text{F1-Score} = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$$
$$\text{ROC-AUC} = P(\text{Score}(Pos) > \text{Score}(Neg)) + 0.5 \times P(\text{Tie})$$

### Hand-Worked Step-by-Step Viva Example
Suppose Demographic Group A has 4 applicants, 3 shortlisted, 2 True Positives, and 2 actual positives in ground truth.  
Suppose Demographic Group B has 4 applicants, 1 shortlisted, 1 True Positive, and 2 actual positives in ground truth.

- **Group A Selection Rate:** $(TP + FP) / N = 3 / 4 = \mathbf{75.0\%}$
- **Group A Recall:** $TP / (TP + FN) = 2 / 2 = \mathbf{100.0\%}$
- **Group A Precision:** $TP / (TP + FP) = 2 / 3 = \mathbf{66.67\%}$
- **Group B Selection Rate:** $(TP + FP) / N = 1 / 4 = \mathbf{25.0\%}$
- **Group B Recall:** $TP / (TP + FN) = 1 / 2 = \mathbf{50.0\%}$
- **Group B Precision:** $TP / (TP + FP) = 1 / 1 = \mathbf{100.0\%}$
- **Fairness Gaps:**
  - Selection Rate Gap = $75\% - 25\% = \mathbf{50.0\text{ percentage points (pp)}}$
  - Recall Gap = $100\% - 50\% = \mathbf{50.0\text{ pp}}$
  - Precision Gap = $100\% - 66.67\% = \mathbf{33.33\text{ pp}}$
- **Four-Fifths Ratio for Group B:** $25\% / 75\% = \mathbf{0.3333}$  
  *(Triggers Adverse Impact screening flag because $0.3333 < 0.80$)*

> [!NOTE]
> ### The Majority Baseline Trap
> In our dataset, 75.07% of records have $Y = 0$. A trivial dummy model that rejects everyone achieves **75.07% accuracy** with 0% recall. Therefore, our Decision Tree's 77.53% validation accuracy is only defensible when paired with its positive-class Recall (55.65%), Precision (54.90%), and ROC-AUC (0.7760).

---

## 5. Choosing Criteria: Model Selection, Thresholds & Quota Policies

### Model Comparison & Choosing Rationale

| Model Family | Val Accuracy | Val Precision | Val Recall | Val ROC-AUC | 5-Fold CV Accuracy | Choosing Assessment |
|---|---|---|---|---|---|---|
| **Decision Tree (Active)** | **77.53%** | **54.90%** | **55.65%** | **0.7760** | **78.24% ± 0.77%** | **CHOSEN DEFAULT:** Best balance of AUC, balanced recall, and direct explainability. |
| **Logistic Regression** | 76.88% | 53.20% | 49.12% | 0.7610 | 76.45% ± 0.62% | High precision, but linear assumption misses complex feature interactions. |
| **Random Forest** | 78.10% | 57.40% | 51.80% | 0.7845 | 78.60% ± 0.55% | Higher AUC, but ensemble structure acts as a black box; explanations are heuristic. |
| **Gaussian Naive Bayes** | 71.20% | 42.15% | 68.40% | 0.7320 | 71.50% ± 1.10% | High recall at cost of severe false positives; violates independence assumption. |
| **K-Nearest Neighbors** | 74.80% | 48.90% | 47.20% | 0.7250 | 74.30% ± 0.85% | Slow inference latency $O(N \cdot d)$; sensitive to local density variations. |

### Decision Policies: Threshold vs. Top-N Capacity Quota
1. **Probability Threshold Policy ($\tau = 0.50$):** Candidate is shortlisted if $P(Y=1|x) \ge \tau$. Evaluates each applicant independently against an absolute bar. Lowering threshold increases recall and shortlist size, but admits more false positives.
2. **Top-N Capacity Quota Policy:** Mimics real hiring where a committee has fixed interview slots (e.g. exactly 50 candidates). Ranks all candidates by predicted probability descending and selects the top $N$. **Top-N overrides thresholding.**
3. **Deterministic Tie-Breaking Rule:** When candidates share identical probabilities, ties are broken first by unrounded float score descending, then by `enrollee_id` ascending (lexicographical string sort).
4. **Single Applicant Limitation:** A single candidate cannot be evaluated under Top-N in isolation because their selection depends on the competitive scores of the entire candidate pool.

### Cost-Optimal Thresholding & The 0.06 Trap
$$\text{Expected Cost} = FP \times C_{FP} + FN \times C_{FN} - TP \times B_{TP} + TN \times C_{TN}$$
- Standard assumed costs: $C_{FP} = \$500$ (wasted interview), $C_{FN} = \$3,500$ (missed talent), $B_{TP} = \$5,000$ (hire value), $C_{TN} = \$0$.
- *Examiner Trap:* Because $B_{TP}$ and $C_{FN}$ heavily penalize misses, an unconstrained cost optimization yields an 'optimal' threshold of **0.06**, which shortlists 100% of candidates! Cost-optimal thresholding is only valid when constrained by maximum interview capacity.

---

## 6. Algorithmic Fairness Audits, Disparity Gaps & Uncertainty

### The Three Fairness Gaps
1. **Demographic Parity (Selection Rate Gap):**
   $$\text{Gap}_{SR} = \max_g(SR_g) - \min_g(SR_g) \quad \text{where } SR_g = \frac{TP_g + FP_g}{N_g}$$
   Measures whether demographic groups are selected at equal rates regardless of qualification.
2. **Equal Opportunity (Recall Gap):**
   $$\text{Gap}_{\text{Recall}} = \max_g(\text{Recall}_g) - \min_g(\text{Recall}_g) \quad \text{where } \text{Recall}_g = \frac{TP_g}{TP_g + FN_g}$$
   Measures whether qualified candidates across groups have equal chances of being shortlisted.
3. **Predictive Parity (Precision Gap):**
   $$\text{Gap}_{\text{Precision}} = \max_g(\text{Precision}_g) - \min_g(\text{Precision}_g) \quad \text{where } \text{Precision}_g = \frac{TP_g}{TP_g + FP_g}$$
   Measures whether shortlisted candidates across groups are equally likely to be genuine positives.
4. **Four-Fifths Rule (Adverse Impact Ratio):**
   $$\text{Ratio}_g = \frac{SR_g}{\max_a(SR_a)}$$
   Triggers a screening flag if $\text{Ratio}_g < 0.80$. *Examiner note:* An administrative screening heuristic, NOT legal proof of unlawful discrimination.

### Mathematical Impossibility Theorem of Fairness
A central theorem in machine learning theory (Chouldechova 2017, Kleinberg et al. 2016) proves that **Demographic Parity, Equal Opportunity, and Predictive Parity cannot be simultaneously satisfied** whenever demographic groups have different base prevalence rates ($P(Y=1|\text{Group A}) \ne P(Y=1|\text{Group B})$) and classification is imperfect. Hiring teams must consciously choose which objective to prioritize.

### Statistical Uncertainty & The Wilson Score Interval
Subgroups with few members produce volatile metrics. A group with $N=39$ total members and 4 selections has an observed precision of 100% (4/4), but extreme uncertainty. The console computes 95% Wilson Score Confidence Intervals:
$$p_{\text{mid}} = \frac{p + \frac{z^2}{2n}}{1 + \frac{z^2}{n}}, \quad \text{Margin} = \frac{z}{1 + \frac{z^2}{n}} \sqrt{\frac{p(1-p)}{n} + \frac{z^2}{4n^2}}$$
where $z = 1.95996$. Plug-in binomial bootstrap intervals (1,000 resamples) quantify gap uncertainty.

---

## 7. Fairness Interventions, Ablation Experiments & Influencing Factors

### What Influences Fairness and Performance?
1. **Proxy Correlations:** Features like `city_development_index` strongly correlate with both the target and demographic group distributions.
2. **Base Rate Disparities:** Underlying group prevalence differences create mathematical tension between parity and precision.
3. **Selection Thresholds:** Stricter thresholds amplify selection disparity by restricting entry to the extreme score tail.

### The Central Ablation Experiment: Dropping City Development Index
Retraining the Decision Tree on the identical 60% training split without `city_development_index`, evaluated on the 20% validation split at threshold 0.50:

| Metric / Audit Dimension | Before Ablation (Baseline) | After Dropping CDI | Observed Delta | Technical Interpretation |
|---|---|---|---|---|
| **Validation Accuracy** | 77.53% | 76.25% | -1.28 pp | Predictive accuracy moderately degraded. |
| **Validation ROC-AUC** | 0.7760 | 0.7086 | -0.0674 | Ranking discrimination significantly impaired. |
| **Gender Selection Rate Gap** | 17.62 pp | 7.74 pp | **-9.88 pp** | **DEMOGRAPHIC PARITY IMPROVED!** Selection rates became more equal. |
| **Gender Recall Gap** | 20.15 pp | 24.58 pp | **+4.43 pp** | **EQUAL OPPORTUNITY WORSENED!** Qualified candidates face greater disparity. |
| **Gender Precision Gap** | 12.88 pp | 15.52 pp | **+2.64 pp** | **PREDICTIVE PARITY WORSENED!** Interview quality disparity increased. |
| **Four-Fifths Minimum Ratio** | 0.5226 | 0.6840 | +0.1614 | Adverse impact ratio improved, but remains below 0.80 screening line. |

> [!CAUTION]
> ### The Central Viva Lesson: Fairness Through Omission is a Myth!
> Dropping an attribute is NOT an automatic fairness fix. While removing `city_development_index` reduced the selection rate gap by 9.88 pp, it **worsened both the recall gap (+4.43 pp) and precision gap (+2.64 pp)** while degrading ROC-AUC by 0.0674. Blind removal harms qualified candidates while reducing model utility.

### Proxy Detection via Normalized Mutual Information (NMI)
$$NMI(X; Y) = \frac{2 \cdot I(X; Y)}{H(X) + H(Y)}$$
Continuous features are binned into quintiles. Features exceeding $NMI \ge 0.30$ on training data are flagged as proxy candidates.

---

## 8. Explainability: Decision Paths & Perturbation Diagnostics

1. **Exact Decision Tree Paths:** For any applicant, `explain_row` traverses the fitted scikit-learn tree using `decision_path()`, extracting the exact boolean inequalities: e.g. `'City development index > 0.625' -> 'Years of experience > 4.5' -> 'Education level is Graduate'`. Provides 100% faithful verification of how the leaf probability was reached.
2. **Source-Column Perturbation Diagnostics:** Replaces an applicant's source feature with its training baseline (median for numeric, mode for categorical) and computes:
   $$\Delta P = P(\text{original}) - P(\text{perturbed})$$
   Measures model sensitivity, NOT real-world causal impact.

---

## 9. Master Viva Q&A Guide: Top 15 Examiner Questions & Answers

1. **Q: What is the mining task and how is ranking performed?**  
   *A:* Supervised binary classification on tabular data. Ranking is achieved by sorting predicted positive probabilities descending. It is not a separately trained learning-to-rank model.
2. **Q: What does target=1 mean and why does it matter?**  
   *A:* It means job-change interest in the Kaggle dataset. Treating it as interview suitability is an educational surrogate assumption, not validated hiring truth.
3. **Q: Why choose Decision Tree over Random Forest or XGBoost?**  
   *A:* Decision Tree provides competitive ROC-AUC (0.7760) and balanced recall (55.65%) while offering complete white-box interpretability via exact boolean decision paths.
4. **Q: How do you prevent data leakage?**  
   *A:* Split 60/20/20 first. Imputers, scalers, and encoders are fitted strictly on the 60% training partition within a scikit-learn Pipeline. Cross-validation refits pipelines locally inside each fold.
5. **Q: How does Gini Impurity work mathematically?**  
   *A:* $I_G = 1 - \sum p_i^2$. At each node, the tree evaluates candidate thresholds and picks the split maximizing weighted impurity reduction.
6. **Q: Why does KNN need scaling and what bug was fixed?**  
   *A:* KNN uses Euclidean distance. High-range features (training hours: 1-336) overwhelm low-range features (city index: 0.45-0.95). The legacy bug standardized single applicants against themselves (yielding all zeros); our unified pipeline binds StandardScaler to training data.
7. **Q: Why is 77.53% accuracy alone deceptive?**  
   *A:* The majority baseline is 75.07% (predicting all negative gets 75.07% accuracy with 0% recall). Our +2.46 pp delta is only meaningful when accompanied by positive-class Recall (55.65%) and ROC-AUC (0.7760).
8. **Q: How does Top-N policy differ from thresholding?**  
   *A:* Threshold evaluates applicants independently against an absolute cutoff. Top-N selects the top $N$ candidates to match fixed interview capacity. Top-N overrides thresholding. Ties break by unrounded probability descending, then enrollee ID ascending.
9. **Q: What happens when the threshold is lowered to 0.35?**  
   *A:* Shortlist size and recall cannot decrease; precision typically degrades. Group gaps can move either way. ROC-AUC remains unchanged because relative score ranking is unaffected.
10. **Q: Why did dropping CDI improve Demographic Parity but worsen Equal Opportunity?**  
    *A:* Removing CDI compressed score differences between groups, reducing selection gap from 17.62 pp to 7.74 pp. But because CDI was a valid predictor, removing it caused more misclassifications among qualified candidates, increasing recall gap from 20.15 pp to 24.58 pp.
11. **Q: Why is N >= 30 insufficient to prove subgroup reliability?**  
    *A:* Precision denominator is shortlisted count ($TP+FP$); Recall denominator is positive count ($TP+FN$). A group with $N=39$ total members but only 4 selections has an effective precision denominator of 4. We compute 95% Wilson intervals to capture this uncertainty.
12. **Q: Why must missing gender be audited as 'Unknown'?**  
    *A:* Missing gender comprises 23.53% of records (4,508 rows) and had the highest selection rate. Dropping it would distort baselines and hide discrimination among candidates withholding demographic info.
13. **Q: What does the Four-Fifths rule prove legally and statistically?**  
    *A:* An administrative screening heuristic under EEOC guidelines. It triggers investigation; it is NOT legal proof of discrimination, nor does a ratio > 0.80 prove fairness.
14. **Q: What is the difference between PCA and Feature Selection?**  
    *A:* Feature Selection retains top original encoded features by Gini importance, preserving feature semantics. PCA projects data into orthogonal linear combinations, destroying direct interpretability.
15. **Q: How does the console handle live, unlabeled applicant uploads?**  
    *A:* Uploads lack ground truth. They are scored and ranked via the pipeline. Selection rates and demographic parity are auditable, but Recall and Precision are displayed as 'Unavailable'.

---

## 10. Common Viva Pitfalls: Claims to NEVER Make

| Fatal Claim to Avoid | Why It Is Mathematically / Factually False | Defensible Statement to Use Instead |
|---|---|---|
| *"Our model predicts candidate job suitability and hiring success."* | Kaggle target measures job-change interest, not job competence or interview performance. | *"The model demonstrates binary classification on a job-change surrogate dataset under an educational recruitment framing."* |
| *"Excluding gender from predictors guarantees the model is fair."* | Fairness through Omission fails because unprotected features (city index, experience) act as proxies. | *"Audit-only protected attributes prevent direct disparate treatment, but disparate impact and proxy disparities must still be actively audited."* |
| *"A Four-Fifths ratio above 0.80 proves our shortlist is fair."* | The 80% rule is an administrative screening heuristic; it ignores recall disparities, precision gaps, and individual fairness. | *"The 4/5ths ratio is one exploratory screening check alongside multi-metric gap audits and Wilson confidence intervals."* |
| *"Our 5-fold CV standard deviation is a confidence interval."* | Fold standard deviation measures variability across training partitions; it is not a parametric confidence interval for deployment error. | *"The ±0.77% spread reflects observed standard deviation across 5 stratified training folds."* |
| *"N >= 30 means all our group fairness metrics are statistically reliable."* | Precision denominator is shortlisted count ($TP+FP$); Recall denominator is positive count ($TP+FN$). These can be tiny even when total $N > 30$. | *"We inspect metric-specific denominators and display 95% Wilson score intervals to convey small-sample uncertainty."* |
| *"Our perturbation diagnostics prove which features caused the hiring decision."* | Perturbations measure model output sensitivity under synthetic marginal feature replacement; they are NOT real-world causal proofs. | *"Perturbation diagnostics quantify model sensitivity to specific inputs, but do not establish real-world causal mechanisms."* |

---

## 11. The Perfect 7-Minute Viva Presentation Script & Sequence

- **Minute 0:00 - 1:00 (Business Problem & Surrogate Label):** Introduce FairRecruit as a local shortlisting console and fairness audit workbench. State clearly that the bundled dataset measures job-change interest as an educational demonstration surrogate for hiring.
- **Minute 1:00 - 2:00 (Data Engineering & Preprocessing):** Show the 60/20/20 split (11,494 / 3,832 / 3,832). Explain the handling of censored experience (`'<1'`, `'>20'`), missing gender retained as `'Unknown'`, and how unified train-fitted pipelines prevent data leakage.
- **Minute 2:00 - 3:00 (Model Benchmark & Decision Tree Selection):** Present the model comparison table. Justify selecting Decision Tree (ROC-AUC 0.7760, accuracy 77.53% vs 75.07% majority baseline, depth 5, min leaf 25, transparent boolean rules).
- **Minute 3:00 - 4:00 (Shortlisting Policies & Tie-Breaking):** Demonstrate candidate ranking. Contrast thresholding ($\ge 0.50$) with Top-N capacity quota shortlisting. Explain the deterministic tie-breaking rule.
- **Minute 4:00 - 5:00 (Fairness Auditing & Three Gaps):** Open the fairness audit view. Explain the three gaps: Selection Rate Gap (17.62 pp), Recall Gap (20.15 pp), and Precision Gap (12.88 pp). Point out Wilson confidence intervals and the Unknown group.
- **Minute 5:00 - 6:00 (The Central Ablation Experiment):** Run the CDI ablation preview. Highlight the central finding: selection gap dropped to 7.74 pp, but recall gap worsened to 24.58 pp and AUC fell to 0.7086. Explain why 'fairness through omission is a myth.' Show versioned apply/revert.
- **Minute 6:00 - 7:00 (Explainability & Live Uploads):** Open a shortlisted applicant drawer. Walk through their exact decision tree path and perturbation sensitivity. Conclude by demonstrating an unlabeled candidate upload where selection rates work but label metrics are marked unavailable.

---

## 12. Architecture & Codebase Dataflow Guide

| Backend Module | Primary Class / Functions | Architectural Role & Guarantees |
|---|---|---|
| `backend/data_manager.py` | `DataManager`, `clean_row`, `AUDIT_LABELS` | CSV loading, schema validation, boundary mapping (`'<1'`->0, `'>20'`->21), deterministic 60/20/20 split. |
| `backend/ml_engine.py` | `ModelEngine`, `make_pipeline`, `evaluate`, `run_kfold_cv` | Scikit-learn Pipeline construction, median imputation, scaling, 5-fold stratified CV, SelectFromModel, PCA. |
| `backend/policy.py` | `SelectionPolicy` (`select`, `parse`, `to_dict`) | Centralized decision logic. Enforces threshold vs Top-N quota and deterministic tie-breaking. |
| `backend/fairness_audit.py` | `audit_single_attribute`, `wilson`, `compute_before_after_ablation` | Per-group rates, 95% Wilson intervals, 1000-draw bootstrap gap intervals, driver diagnostics, isolated ablation. |
| `backend/explainability.py` | `explain_row`, `decision_path` traversal | Exact boolean inequality paths from fitted tree; single-attribute marginal perturbation deltas against median/mode. |
| `backend/storage.py` | SQLite persistence, model versioning manifest | Tracks active model UUID, parameter history, audit logs, and supports one-click rollback of ablated models. |
| `app.py` | Flask REST API routing | Exposes `/api/train`, `/api/predict`, `/api/shortlist`, `/api/fairness`, `/api/ablation`, `/api/candidate/<id>/explain`. |

---

## 13. Quick-Lookup Master Summary & Final Viva Checklist

| Verified Quantity | Exact Value | Recruitment & Evaluation Context |
|---|---|---|
| **Total Raw Records** | 19,158 | Full dataset size from Kaggle HR Analytics benchmark. |
| **Stratified Split (60 / 20 / 20)** | 11,494 / 3,832 / 3,832 | Deterministic split (Seed 42); prevents test data snooping. |
| **Base Rate (Pos / Neg)** | 24.93% / 75.07% | Majority class baseline is 75.07%. Always report baseline delta. |
| **Active Model Configuration** | Decision Tree (depth=5, leaf=25) | Gini splitting; max 32 leaves; transparent boolean rule extraction. |
| **Validation Performance** | Acc: 77.53% \| ROC-AUC: 0.7760 | Precision: 54.90% \| Recall: 55.65% (balanced operational performance). |
| **Test Final Performance** | Acc: 79.36% \| ROC-AUC: 0.8100 | Precision: 58.49% \| Recall: 59.16% (evaluated once on held-out test split). |
| **5-Fold Stratified CV Spread** | 78.24% ± 0.77% | Observed fold SD across training folds; NOT a confidence interval. |
| **Missing Gender Records** | 4,508 records (23.53%) | Audited explicitly as 'Unknown'; had highest group selection rate. |
| **CDI Ablation Delta (Gender)** | Gap: 17.62 pp -> 7.74 pp (-9.88 pp) | Selection parity improved, but Recall gap worsened from 20.15 pp to 24.58 pp. |

### Final 60-Second Viva Room Checklist
- [x] **Surrogate target:** Job-change interest $\ne$ verified job qualification.
- [x] **Gini Impurity:** $I_G = 1 - \sum p_i^2$; calculate parent vs weighted child split reduction by hand.
- [x] **Accuracy alone:** 75.07% majority baseline means predicting all-zeros gets 75.07% accuracy with 0% recall.
- [x] **Four-fifths rule:** 80% adverse impact ratio is an administrative screening flag, NOT legal proof of discrimination.
- [x] **Fairness through omission:** Dropping city index improved selection gap by 9.88 pp but worsened recall gap by 4.43 pp.
- [x] **Decision policy:** Top-N overrides threshold; tie-breaking uses score descending, then `enrollee_id` ascending.
