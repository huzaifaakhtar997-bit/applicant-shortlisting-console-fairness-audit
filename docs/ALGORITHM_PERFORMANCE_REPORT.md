# FairRecruit: Machine Learning Algorithm Performance Report

**Data Mining Project 5 | Comparative Algorithm Evaluation & Technical Selection Guide**  
*Empirical Benchmarks, Influencing Factors, Dimensionality Reduction & Algorithmic Rationale*

---

## 1. Executive Summary & Evaluation Framework

In automated employment decision tools (AEDTs) and algorithmic recruitment, selecting a machine learning classifier requires balancing **raw predictive accuracy and ranking discrimination** against **interpretability, algorithmic fairness, and legal defensibility**. 

To evaluate algorithms objectively, FairRecruit implements a zero-data-leakage testing harness:
- **Dataset:** Real-world Kaggle HR Analytics benchmark dataset ($19,158$ total records).
- **Stratified Partitioning:** $60\%$ Training ($11,494$ rows), $20\%$ Validation ($3,832$ rows), and $20\%$ Held-Out Test ($3,832$ rows).
- **Feature Space:** $10$ active raw predictors expanded into $45$ one-hot encoded dimensions.
- **Evaluation Split:** All models were evaluated under fixed $0.50$ probability thresholding on the exact same $3,832$ validation candidates.
- **Cross-Validation:** $5$-fold stratified cross-validation on the training set, where scalers, imputers, and encoders are fit *strictly within each fold*.

---

## 2. Empirical Benchmark Evaluation Across 5 Model Families

| Model Family | Algorithm Category | Accuracy | Precision | Recall | F1-Score | ROC-AUC | PR-AUC (AP) | 5-Fold Stratified CV Spread |
|---|---|---|---|---|---|---|---|---|
| **Decision Tree** | Tree (Interpretable) | **77.53%** | 54.90% | **55.65%** | **55.27%** | **0.7760** | 0.4889 | **79.43% ± 1.41%** |
| **Random Forest** | Ensemble Bagging | 76.57% | **56.36%** | 26.88% | 36.40% | **0.7795** | **0.5184** | 77.69% ± 0.44% |
| **Logistic Regression** | Linear ($L_2$ Regularized) | 76.15% | 54.38% | 27.30% | 36.35% | 0.7635 | 0.4895 | 77.49% ± 0.48% |
| **K-Nearest Neighbors** | Instance-Based ($k=15$) | 75.00% | 49.87% | 41.11% | 45.07% | 0.7206 | 0.4370 | 76.18% ± 0.35% |
| **Gaussian Naive Bayes** | Probabilistic | 75.05% | N/A* | 0.00% | 0.00% | 0.6280 | 0.3597 | 75.07% ± 0.02% |
| **Majority Baseline** | Zero-Rule Threshold | 75.05% | N/A | 0.00% | 0.00% | 0.5000 | 0.2495 | 75.05% ± 0.00% |

*\*Note on Naive Bayes:* Gaussian Naive Bayes predicted $0$ candidates above the $0.50$ threshold ($TP=0, FP=0$), making precision mathematically undefined ($0/0$). Its $75.05\%$ accuracy is completely trivial—it simply defaulted to the negative majority class.

---

## 3. Confusion Matrix Breakdown & Prediction Behavior

On the $3,832$ validation records ($956$ actual positives, $2,876$ actual negatives), the raw outcomes explain how each model behaves in practice:

| Model | True Neg (TN) | False Pos (FP) | False Neg (FN) | True Pos (TP) | Balanced Acc | Clinical Behavior in Shortlisting |
|---|---|---|---|---|---|---|
| **Decision Tree** | 2,439 | 437 | 424 | **532** | **70.23%** | **Balanced shortlister:** Recovers $55.7\%$ of qualified applicants with controlled False Positive rate ($15.2\%$). |
| **Random Forest** | 2,678 | 198 | 699 | 257 | 59.98% | **High specificity:** Conservative shortlister; low FP rate but misses $73.1\%$ of positive candidates at default cutoff. |
| **Logistic Regression** | 2,657 | 219 | 695 | 261 | 59.84% | **Linear threshold:** Misses $72.7\%$ of positive candidates at $0.50$; requires threshold tuning to compete on recall. |
| **K-Nearest Neighbors** | 2,481 | 395 | 563 | 393 | 63.69% | **Moderate recovery:** Recovers $41.1\%$ of positives; degrades due to Euclidean distance concentration in 45-D space. |
| **Gaussian Naive Bayes** | 2,876 | 0 | 956 | 0 | 50.00% | **Complete collapse:** Predicts $0$ candidates; degenerates into majority-class rule. |

---

## 4. Dimensionality Reduction vs. Feature Selection

To investigate whether reducing feature dimensions helps or hinders recruitment models, we benchmarked the primary decision tree under three feature regimes:

| Representation Technique | Input Dimensions | Accuracy | Precision | Recall | ROC-AUC | Impact on Recruitment Auditing |
|---|---|---|---|---|---|---|
| **All Raw Predictors** | 45 | **77.53%** | **54.90%** | **55.65%** | **0.7760** | Baseline full feature fidelity; complete explainability down to source columns. |
| **Importance-Based Selection** | 10 | 77.43% | 54.72% | 55.23% | 0.7714 | Preserves $99.8\%$ of performance using top 10 features; retains human-readable input names. |
| **PCA Orthogonal Components** | 10 | 75.37% | 51.09% | 29.39% | 0.7043 | **Severe degradation:** Recall drops to $29.4\%$; destroys legal transparency and explainability. |

### Why PCA Fails in Categorical HR Datasets:
1. **Low Variance Capture:** 10 PCA components capture only **$43.25\%$** of total variance.
2. **Eigenvector Distortion on One-Hot Data:** PCA assumes continuous, Gaussian-distributed variables. Projecting sparse $0/1$ categorical dummy variables into continuous orthogonal components introduces severe noise, blurring the clean axis-aligned step thresholds used by decision trees.
3. **Destruction of Legal Transparency:** Under employment law (EEOC / EU AI Act), you cannot justify a hiring decision to an applicant by stating *"You were rejected because Principal Component 3 was $-0.42$"*. Importance selection preserves exact feature names (`city_development_index`, `experience`, `company_size`), retaining full auditability.

---

## 5. Key Factors Influencing Model Performance

Five core data mining factors dictate how these algorithms perform:

### Factor 1: Severe Class Imbalance ($75\%$ Negative vs. $25\%$ Positive)
In HR recruitment, true positive outcomes (e.g. candidates seeking job change or passing interviews) represent the minority class ($24.95\%$). 
- This creates the **majority baseline trap**: predicting $0$ for everyone yields $75.05\%$ accuracy.
- Accuracy alone is a misleading metric; models must be evaluated on **F1-Score, Balanced Accuracy, and ROC-AUC**.
- Logistic Regression and Naive Bayes are heavily biased toward the majority class at a $0.50$ threshold, producing depressed recall ($0\%$ to $27\%$). Decision Trees partition the space hierarchically, isolating positive concentrations into pure leaves.

### Factor 2: Non-Linear Step Functions vs. Linear Hyperplanes
The most influential predictor is `city_development_index`:
- Candidates in cities with index $\le 0.62$ have a dramatic $>55\%$ probability of positive outcome.
- Candidates in high-index cities ($\ge 0.85$) have a probability $<15\%$.
This is a sharp, non-linear step function. Tree-based models capture this in a single binary cut (`city_development_index <= 0.62`), whereas linear hyperplanes in Logistic Regression struggle to fit abrupt step changes without polynomial feature engineering.

### Factor 3: High-Dimensional Categorical Sparsity (45 Encoded Features)
Converting 7 categorical variables into one-hot dummy columns expands the feature space to 45 dimensions.
- **Curse of Dimensionality:** For distance-based models like KNN, Euclidean distances between points converge in high-dimensional space. All applicants appear approximately equidistant, causing KNN's neighborhood voting ($k=15$) to be overwhelmed by the background $75\%$ majority class.

### Factor 4: Violation of Conditional Independence (Why Naive Bayes Collapses)
Gaussian Naive Bayes assumes all features are conditionally independent given the class label ($P(X_1, \dots, X_d \mid Y) = \prod P(X_i \mid Y)$).
- In recruitment data, features are heavily correlated: `education_level` correlates with `enrolled_university`, and `experience` correlates with `company_size` and `city_development_index`.
- Multiplying redundant probabilities compounds error, forcing posterior positive probabilities below $0.50$ for every candidate.

### Factor 5: Multicollinearity and Demographic Proxies
Even though sensitive demographics (Gender, Age, Institution) are excluded from model inputs, correlated proxies exist (e.g., `city_development_index` has an NMI of $\approx 0.30$ with demographic groups).
- Ensemble models distribute split criteria across correlated features, making proxy bias difficult to trace.
- A single Decision Tree makes proxy usage completely transparent by exposing the exact tree nodes.

---

## 6. Algorithmic Reasoning: Which Performs Better and Why?

### The Comparative Ranking Summary:

1. **Rank 1 (Overall Operational Winner): Decision Tree Classifier**
   - **Performance:** Validation Accuracy **$77.53\%$**, Precision **$54.90\%$**, Recall **$55.65\%$**, F1 **$55.27\%$**, ROC-AUC **$0.7760$**, Balanced Accuracy **$70.23\%$**.
   - **Why It Performs Better:** It strikes the optimal balance between high predictive accuracy and **$100\%$ faithful interpretability**. It recovers $55.7\%$ of qualified applicants (nearly double that of Random Forest and Logistic Regression at $0.50$) without sacrificing precision.
   - **Legal Compliance:** Unlike ensemble black boxes, every single candidate decision can be traced to exact, human-readable IF-THEN rules (e.g., `city_development_index <= 0.62 AND experience > 4.0`), satisfying EEOC and EU AI Act explainability mandates.

2. **Rank 2 (Best Ranking Discrimination): Random Forest Classifier**
   - **Performance:** ROC-AUC **$0.7795$**, Average Precision **$0.5184$**, Precision **$56.36\%$**.
   - **Why It Excels on Ranking:** Bagging 100 trees reduces variance and smooths probability estimates across the entire spectrum.
   - **Drawback:** Highly conservative at standard thresholds (Recall is only $26.88\%$, F1 $36.40\%$). It requires explicit threshold recalibration and cannot provide single-tree decision paths for legal review.

3. **Rank 3 (Linear Baseline): Logistic Regression**
   - **Performance:** Accuracy $76.15\%$, AUC $0.7635$, Precision $54.38\%$, Recall $27.30\%$.
   - **Why It Serves as a Strong Baseline:** Provides smooth, well-calibrated probabilities and fast inference, but misses abrupt non-linear threshold steps.

4. **Rank 4: K-Nearest Neighbors (KNN)**
   - **Performance:** Accuracy $75.00\%$, AUC $0.7206$, Recall $41.11\%$.
   - **Drawback:** Degraded by the Curse of Dimensionality across 45 one-hot sparse coordinates.

5. **Rank 5 (Unusable Failure Mode): Gaussian Naive Bayes**
   - **Performance:** Accuracy $75.05\%$, Recall $0.00\%$, F1 $0.00$, AUC $0.6280$.
   - **Drawback:** Total failure caused by severe class imbalance and violation of conditional independence across correlated tabular features.

---

## 7. Master Viva Defense Q&A

### Q1: "Random Forest has a slightly higher ROC-AUC (0.7795 vs 0.7760). Why did you choose Decision Tree as your primary operational classifier?"
> **Answer:** "ROC-AUC evaluates ranking discrimination across all theoretical thresholds from 0 to 1. In real-world recruitment, hiring systems operate at concrete decision thresholds. At the standard 0.50 threshold, Random Forest has a recall of only $26.88\%$ ($F1 = 36.40\%$), missing nearly three-quarters of positive candidates, whereas Decision Tree achieves $55.65\%$ recall and an $F1$ of $55.27\%$. Most importantly, automated hiring systems are classified as high-risk under the EU AI Act and EEOC guidelines. Random Forest is an opaque ensemble of 100 trees, whereas Decision Tree offers 100% faithful, auditable decision paths that allow recruiters and candidates to inspect the exact rules governing selection."

### Q2: "Why did Gaussian Naive Bayes get 75.05% accuracy with 0% precision and recall?"
> **Answer:** "$75.05\%$ is the majority-class baseline of our dataset ($14,381$ negatives out of $19,158$ total records). Gaussian Naive Bayes assumes all features are conditionally independent and normally distributed. Our dataset contains 45 one-hot dummy variables with heavy multicollinearity. Multiplying redundant probabilities compounded estimation error, forcing all posterior positive probabilities below $0.50$. Consequently, Naive Bayes predicted $0$ for every single applicant. It appears accurate only because the negative class dominates the dataset."

### Q3: "Why did PCA dimensionality reduction decrease accuracy from 77.53% to 75.37% and recall to 29.39%?"
> **Answer:** "PCA is an orthogonal linear projection designed for continuous Gaussian data. Our feature matrix consists of 10 continuous and 35 sparse dummy indicators. 10 PCA components captured only $43.25\%$ of total variance. Projecting discrete $0/1$ indicators into continuous coordinates introduced severe noise and destroyed the axis-aligned step boundaries that decision trees rely upon. Furthermore, PCA destroys audit explainability, making legal defense impossible."

---

## 8. Report Deliverable Locations
- **Master PDF Report:** [`output/pdf/FairRecruit_Algorithm_Performance_Report.pdf`](file:///c:/Users/Huzaifa/Downloads/Datamining/Datamining/applicant-shortlisting-console-fairness-audit/output/pdf/FairRecruit_Algorithm_Performance_Report.pdf)
- **Complete Viva Guide PDF:** [`output/pdf/FairRecruit_Complete_Viva_Guide.pdf`](file:///c:/Users/Huzaifa/Downloads/Datamining/Datamining/applicant-shortlisting-console-fairness-audit/output/pdf/FairRecruit_Complete_Viva_Guide.pdf)
