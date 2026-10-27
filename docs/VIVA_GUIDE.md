# FairRecruit - Revised Viva Guide

Data Mining Project 5 | Revised implementation | 26 October 2026

## Your 60-second opening

Our project is a local shortlisting and fairness-audit workbench. It trains a binary classifier on labeled tabular data, ranks incoming records, explains model behavior and measures selection rate, recall and precision separately by group. The key experiment removes an input, retrains a separate model on the same training split and compares performance with all three fairness gaps under the same selection policy. The recruiter can apply the compared model or revert it. The bundled outcome is job-change interest, so we explicitly treat it as a course demonstration, not validated interview suitability.

## What changed since the original repository

- All prediction routes share one train-fitted preprocessing pipeline. KNN single/batch/explanation scores now agree.
- Labeled training replacement and unlabeled applicant uploads are separate. Missing outcomes remain unknown.
- Actual age bands and institutions are preserved. Experience and education substitutions are clearly labeled demo groupings.
- Protected fields are audit-only; numeric years of experience are now an actual predictor.
- The fairness frontend consumes the actual API schema. All three gaps, support counts and uncertainty intervals are visible.
- Explanations use real decision paths and measured attribute perturbations, with no invented effects.
- Ablations are isolated previews. Apply/revert saves model versions and checks whether the preview is stale.
- Cross-validation refits a pipeline inside shuffled stratified folds. Feature selection ranks learned importances; PCA is actual scaled, train-fitted PCA.

## Numbers to understand

Default Decision Tree; threshold 0.50; depth 5; minimum leaf size 25. Seed 42.

| Quantity | Verified value |
| --- | --- |
| Total records | 19,158 |
| Training / validation / test | 11,494 / 3,832 / 3,832 |
| Source predictors / encoded features | 10 / 45 |
| Validation accuracy / precision / recall | 77.53% / 54.90% / 55.65% |
| Validation ROC-AUC | 0.7760 |
| Test accuracy / precision / recall | 79.36% / 58.49% / 59.16% |
| Test ROC-AUC | 0.8100 |

These are revised results. The earlier review described a different split, feature set and preprocessing implementation. Do not mix its numbers with the new app. The default model was not selected by searching test-set outcomes.

## Formulas you should calculate by hand

Selection rate = (TP + FP) / number of applicants in the group.

Recall = TP / (TP + FN). Precision = TP / (TP + FP).

Accuracy = (TP + TN) / all labeled records. F1 = 2 TP / (2 TP + FP + FN).

Metric gap = maximum group metric - minimum group metric. A difference between 30% and 20% is 10 percentage points, not a 10% relative reduction.

Selection-rate ratio = group rate / highest group rate. A ratio below 0.80 produces a screening flag. No selections means the ratio is unavailable, not automatic compliance.

Precision is unavailable when there are no labeled selections; recall is unavailable when there are no known positives. New applicants do not magically have ground truth.

Worked example: A has four applicants, three selected, two true positives and two actual positives. B has four applicants, one selected, one true positive and two actual positives. A has selection 75%, recall 100%, precision 66.67%. B has selection 25%, recall 50%, precision 100%. Gaps are 50, 50 and 33.33 percentage points. B's rate ratio is 0.3333.

## The experiment to demonstrate

On the validation partition, remove city_development_index only. Keep the default tree and threshold unchanged; leave associated-input removal OFF.

| Metric | Before | After |
| --- | --- | --- |
| Accuracy | 77.53% | 76.25% |
| ROC-AUC | 0.7760 | 0.7086 |
| Gender selection-rate gap | 17.62 pp | 7.74 pp |
| Gender recall gap | 20.15 pp | 24.58 pp |
| Gender precision gap | 12.88 pp | 15.52 pp |

Your explanation: selection parity improved, while both label-dependent gaps worsened and predictive performance fell. Therefore removing an attribute is an experiment, not an automatic fairness fix. Inspect each group, its support and its intervals. Apply only after reviewing the complete tradeoff. Applying changes every view; reverting restores the saved previous model.

## Questions about data and the business problem

**1. What is the mining task?** Supervised binary classification. The ranking is created by sorting the classifier's positive-outcome scores; it is not a separately trained learning-to-rank algorithm.

**2. What does target actually mean?** The bundled data concerns job-change interest. The interface explicitly labels that surrogate. A real hiring model needs defensible role-specific outcome labels and relevant competency measurements.

**3. Why is this dataset acceptable for the course?** The project brief permits it as starting data. We can demonstrate classification, auditing and intervention without falsely changing what its labels mean.

**4. Why separate training from incoming pools?** Training requires complete binary labels. Incoming applicants generally have no outcomes yet. They should be scored by a fitted model, not assigned fabricated negative labels and used to retrain it.

**5. Are experience and age equivalent?** No. Experience bands are demo groupings when actual age data are absent. Actual age/age_band and institution fields are preserved when supplied, and never inferred from experience or qualification.

**6. Why exclude IDs and protected attributes?** An arbitrary ID can encourage memorization or spurious patterns. Protected fields are retained for auditing, but are not inputs. Their exclusion alone does not guarantee fairness.

**7. What is provenance?** A field-level record of its origin or deterministic repair, such as observed, boundary mapping or missing-as-Unknown. Numeric missingness remains visible until the fitted pipeline imputes it.

**8. Are range strings and outliers always errors?** No. '<1' and '>20' are censored categories with documented numeric mappings. Large training-hour values are flagged using an IQR fence. Scaling does not remove outliers.

## Questions about models and evaluation

**9. Why a Decision Tree?** It models nonlinear interactions and exposes actual split rules. Depth and minimum leaf size limit complexity. Interpretable rules still require correct data and labels.

**10. What are the other families?** Logistic Regression fits linear log-odds; Random Forest aggregates trees; Gaussian NB combines class-conditional likelihoods under strong assumptions; KNN scores nearby training examples. Each has different strengths and limitations.

**11. How does the tree split?** By reducing weighted Gini impurity: 1 - the sum of squared class proportions. The configured tree uses depth 5 and at least 25 training records per leaf.

**12. Why scale features?** KNN distances and Logistic Regression optimization mix numeric units. Gaussian NB's variance smoothing can also depend on feature scales. A fitted preprocessing pipeline learns transforms on training data and reuses them everywhere.

**13. How do you prevent leakage?** Split first. Fit imputation, encoding, scaling, PCA and selection only on the training partition. Refit the entire pipeline inside every CV fold. Use validation for model/policy decisions and reserve the test set for the final check.

**14. Why three partitions?** Training fits parameters. Validation supports model, threshold and intervention choices. Test estimates final behavior after choices are fixed. Repeatedly tuning from test outcomes removes its independence.

**15. Why show a majority baseline?** Roughly three quarters of labels are negative. A model can have apparently high accuracy by predicting the majority class. Report positive-class retrieval and ranking metrics alongside accuracy.

**16. What is ROC-AUC?** The chance that a randomly chosen positive receives a higher score than a randomly chosen negative, with half credit for ties. It is independent of a single threshold. Average precision describes retrieval quality across the precision-recall curve.

**17. What changes when you lower a threshold?** For fixed scores, selection and recall cannot decrease. Precision and group gaps can move either way. ROC-AUC does not change because the score ordering is unchanged.

**18. What does CV spread mean?** Variation across five shuffled stratified training folds, each with its own fitted preprocessing. The reported fold standard deviation is not a confidence interval or proof of deployment stability.

**19. Is feature selection different from PCA?** Selection retains train-ranked original encoded features. PCA projects scaled training features into orthogonal components. Both are evaluated on validation data. Neither is fitted to test outcomes.

**20. What does a score mean?** An uncalibrated positive-outcome probability estimated by the model. It is not verified qualification, a confidence interval or a guarantee. Tree paths and perturbations describe model behavior, not causation.

## Questions about fairness and interventions

**21. What is demographic parity?** Equal selection rates across groups, regardless of labels. Equal opportunity concerns equal recall. Predictive parity concerns equal precision. Equalized odds also includes false-positive rates.

**22. Can fairness metrics disagree?** Yes. Different group prevalences and imperfect predictions can make fairness criteria conflict. Our city-index experiment improves selection parity while worsening recall and precision gaps.

**23. What does the four-fifths flag establish?** A numerical screening concern requiring investigation. It is neither a universal fairness certificate nor a finding of unlawful discrimination. It also does not measure individual fairness.

**24. Why keep Unknown in the audit?** Missing demographics are substantial and can change reference groups and maximum gaps. Show its coverage, rates and group comparisons explicitly instead of quietly excluding those records.

**25. Why is total N=30 insufficient?** Recall depends on known positives; precision depends on labeled selections. A group with 39 total records but four selections has very uncertain precision. The app shows those denominators, Wilson rate intervals and exploratory gap intervals.

**26. Do intervals prove fairness?** No. They express sampling uncertainty under assumptions. Small samples, missing outcomes, unrepresentative records and biased labels can undermine interpretation even when an interval is narrow.

**27. What is a driver diagnostic?** The measured change in group mean scores when a whole source attribute is replaced by its training reference. It works with the fitted classifier; it is not a causal explanation or an exact decomposition of selection gaps.

**28. How are associated inputs chosen?** Training-only normalized mutual information with the selected attribute, using numeric quintiles where needed. Candidates must exceed 0.30. Whole source columns are listed and removed, not arbitrary one-hot indicators. Association does not prove a discriminatory proxy.

**29. Why use the same split and policy for ablation?** To hold the evaluation records and decision rule fixed while changing model inputs. A separate candidate model preserves the baseline even if fitting fails. Model-version/policy/scope checks prevent applying a stale comparison.

**30. Does dropping an input guarantee a smaller gap?** No. Correlated inputs, interactions and differing group distributions can preserve or worsen disparity. That is why the product measures before and after instead of calling every removal a mitigation success.

## Questions about the implementation

**31. How do top-N and threshold decisions interact?** Top-N is an explicit capacity policy that overrides the threshold. Every route uses the same implementation. Ties use unrounded probability, then lexicographic ID. Single records need the full pool for a top-N verdict.

**32. How are explanations made faithful?** Tree explanations traverse actual fitted nodes. Source-column perturbations rescore the entire input against a training median/mode. Zero effects stay zero. There are no invented positive or negative fallbacks.

**33. What does apply/revert persist?** The fitted pipeline, training data context and model version are stored locally. An active manifest records policy and version history. SQLite records preview, apply, revert, upload and policy events. Incoming applicant pools are not persisted across restart.

**34. What do the tests prove?** They check hand-calculated metrics, shared-policy behavior, input validation, pipeline score consistency, train-only transforms, isolated experiments, restart/revert, concurrency and actual frontend/API contracts. They do not validate whether historical labels are fair or whether job-change interest measures job suitability.

**35. Why did the original tests miss the broken dashboard?** They inspected backend response contents without executing its JavaScript consumer. The new frontend tests render the actual response structure and assert group rows and all three gap measures.

**36. What is cost-optimal thresholding?** Minimizing assumed FP/FN/TP/TN costs on validation records, optionally constrained by interview capacity. A cheap all-positive solution can be mathematically optimal under the assumptions but operationally useless. Costs are not measured financial returns.

## A seven-minute demonstration

1. State the business problem and the surrogate-label limitation.
2. Show the data dictionary, missingness, genuine audit fields and 60/20/20 split.
3. Explain the active model with baseline, precision, recall and AUC.
4. Review rankings and a candidate's actual path. Show that export follows the same policy.
5. Open the fairness view; explain Unknown, denominators, intervals and all three gaps.
6. Preview city-index removal on validation data, with associated removal off. Explain every tradeoff, then show apply and revert.
7. Upload the fictional unlabeled example. Show that the model is preserved and label metrics become unavailable while selection rates remain available.

## Claims to avoid

- Do not say job-change interest is proven hiring suitability.
- Do not call experience bands actual age or education groups institution pedigree.
- Do not claim audit-only protected inputs make the model fair.
- Do not describe an 80% ratio as legal compliance.
- Do not call fold standard deviation a confidence interval.
- Do not add independent perturbation impacts or call them causal.
- Do not claim operational multi-user readiness, authenticated access or calibrated probabilities.

## Reading pointers

Start with backend/policy.py, then data_manager.py, ml_engine.py, fairness_audit.py, explainability.py, storage.py and app.py. Read the revised README for the current API/data workflow and limitations. The earlier external review is a historical assessment, not documentation of this revised implementation.
