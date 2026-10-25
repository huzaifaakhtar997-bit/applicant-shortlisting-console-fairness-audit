"""
Machine Learning Engine for Applicant Shortlisting Console.
Supports Logistic Regression and Random Forest classifiers.
Computes Accuracy, Precision, Recall, F1, ROC-AUC, Confusion Matrix,
and ROC Curve points. Compatible with scikit-learn and pure-Python fallback.
"""

import math
import random

# Try importing scikit-learn
try:
    import numpy as np
    _test = np.array([1.0, 2.0])
    from sklearn.linear_model import LogisticRegression as SklearnLogReg
    from sklearn.ensemble import RandomForestClassifier as SklearnRF
    from sklearn.metrics import (
        accuracy_score, precision_score, recall_score, f1_score,
        roc_auc_score, confusion_matrix, roc_curve
    )
    USE_SKLEARN = True
except Exception:
    USE_SKLEARN = False


def sigmoid(z):
    """Numerically stable sigmoid function."""
    if z < -40:
        return 0.0
    elif z > 40:
        return 1.0
    return 1.0 / (1.0 + math.exp(-z))


class PurePythonLogisticRegression:
    """
    Fast and robust pure-Python Logistic Regression with L2 regularization
    using mini-batch gradient descent.
    """
    def __init__(self, lr=0.08, epochs=15, l2_reg=0.001, random_state=42):
        self.lr = lr
        self.epochs = epochs
        self.l2_reg = l2_reg
        self.random_state = random_state
        self.weights = []
        self.bias = 0.0
        self.coef_ = []

    def fit(self, X, y):
        n_samples = len(X)
        if n_samples == 0:
            return self
        n_features = len(X[0])

        rng = random.Random(self.random_state)
        # Initialize small random weights
        self.weights = [(rng.random() - 0.5) * 0.01 for _ in range(n_features)]
        self.bias = 0.0

        # Optimization loop
        batch_size = min(256, n_samples)
        indices = list(range(n_samples))

        for epoch in range(self.epochs):
            rng.shuffle(indices)
            for i in range(0, n_samples, batch_size):
                batch_idx = indices[i:i + batch_size]
                b_size = len(batch_idx)
                dw = [0.0] * n_features
                db = 0.0

                for idx in batch_idx:
                    xi = X[idx]
                    yi = y[idx]
                    # z = dot(w, x) + bias
                    z = self.bias
                    for j in range(n_features):
                        z += self.weights[j] * xi[j]
                    pred = sigmoid(z)
                    err = pred - yi

                    db += err
                    for j in range(n_features):
                        dw[j] += err * xi[j]

                # Update with L2 regularization
                lr_curr = self.lr / (1.0 + 0.05 * epoch)
                self.bias -= lr_curr * (db / b_size)
                for j in range(n_features):
                    grad = (dw[j] / b_size) + self.l2_reg * self.weights[j]
                    self.weights[j] -= lr_curr * grad

        self.coef_ = list(self.weights)
        return self

    def predict_proba(self, X):
        probs = []
        n_features = len(self.weights)
        for xi in X:
            z = self.bias
            for j in range(n_features):
                z += self.weights[j] * xi[j]
            p1 = sigmoid(z)
            probs.append([1.0 - p1, p1])
        return probs

    def predict(self, X, threshold=0.5):
        probs = self.predict_proba(X)
        return [1 if p[1] >= threshold else 0 for p in probs]


class PurePythonDecisionTree:
    """Lightweight single decision tree for Random Forest ensemble."""
    def __init__(self, max_depth=5, min_samples_split=20, max_features=None, random_state=42):
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.max_features = max_features
        self.random_state = random_state
        self.tree = None

    def fit(self, X, y):
        rng = random.Random(self.random_state)
        indices = list(range(len(X)))
        self.tree = self._build_tree(X, y, indices, depth=0, rng=rng)
        return self

    def _build_tree(self, X, y, indices, depth, rng):
        num_pos = sum(y[i] for i in indices)
        num_total = len(indices)
        if num_total == 0:
            return {'leaf': True, 'prob': 0.0}

        prob = num_pos / num_total
        if depth >= self.max_depth or num_total < self.min_samples_split or prob == 0.0 or prob == 1.0:
            return {'leaf': True, 'prob': prob}

        n_features = len(X[0])
        feat_subset = list(range(n_features))
        if self.max_features and self.max_features < n_features:
            feat_subset = rng.sample(feat_subset, self.max_features)

        best_feat = None
        best_thresh = None
        best_gini = 1.0
        best_left = []
        best_right = []

        # Current node Gini
        current_gini = 1.0 - (prob ** 2 + ((num_total - num_pos) / num_total) ** 2)

        for feat in feat_subset:
            vals = [X[i][feat] for i in indices]
            # Sample thresholds
            unique_vals = sorted(list(set(vals)))
            if len(unique_vals) <= 1:
                continue
            thresholds = [(unique_vals[k] + unique_vals[k+1]) / 2.0 for k in range(min(5, len(unique_vals)-1))]

            for thresh in thresholds:
                left = [i for i in indices if X[i][feat] <= thresh]
                right = [i for i in indices if X[i][feat] > thresh]
                if not left or not right:
                    continue

                p_left = sum(y[i] for i in left) / len(left)
                gini_left = 1.0 - (p_left**2 + (1.0 - p_left)**2)
                p_right = sum(y[i] for i in right) / len(right)
                gini_right = 1.0 - (p_right**2 + (1.0 - p_right)**2)

                weighted_gini = (len(left)/num_total)*gini_left + (len(right)/num_total)*gini_right
                if weighted_gini < best_gini:
                    best_gini = weighted_gini
                    best_feat = feat
                    best_thresh = thresh
                    best_left = left
                    best_right = right

        if best_feat is None or (current_gini - best_gini) < 1e-4:
            return {'leaf': True, 'prob': prob}

        return {
            'leaf': False,
            'feature': best_feat,
            'threshold': best_thresh,
            'left': self._build_tree(X, y, best_left, depth + 1, rng),
            'right': self._build_tree(X, y, best_right, depth + 1, rng)
        }

    def predict_one(self, node, x):
        if node['leaf']:
            return node['prob']
        if x[node['feature']] <= node['threshold']:
            return self.predict_one(node['left'], x)
        return self.predict_one(node['right'], x)


class PurePythonRandomForest:
    """
    Pure-Python Random Forest Classifier using bootstrap bagging
    and feature subsampling.
    """
    def __init__(self, n_estimators=10, max_depth=5, random_state=42):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.random_state = random_state
        self.trees = []
        self.feature_importances_ = []

    def fit(self, X, y):
        n_samples = len(X)
        if n_samples == 0:
            return self
        n_features = len(X[0])
        max_feat = max(1, int(math.sqrt(n_features)))

        rng = random.Random(self.random_state)
        self.trees = []
        counts = [0] * n_features

        for i in range(self.n_estimators):
            # Bootstrap sample
            boot_idx = [rng.randint(0, n_samples - 1) for _ in range(n_samples)]
            tree = PurePythonDecisionTree(
                max_depth=self.max_depth,
                min_samples_split=30,
                max_features=max_feat,
                random_state=self.random_state + i
            )
            tree.fit(X, y)
            self.trees.append(tree)

            # Accumulate feature usage for feature importances
            def collect_feats(node):
                if not node['leaf']:
                    counts[node['feature']] += 1
                    collect_feats(node['left'])
                    collect_feats(node['right'])
            collect_feats(tree.tree)

        total_splits = sum(counts)
        if total_splits > 0:
            self.feature_importances_ = [c / total_splits for c in counts]
        else:
            self.feature_importances_ = [1.0 / n_features for _ in range(n_features)]
        return self

    def predict_proba(self, X):
        probs = []
        for x in X:
            tree_probs = [tree.predict_one(tree.tree, x) for tree in self.trees]
            avg_p = sum(tree_probs) / len(tree_probs)
            probs.append([1.0 - avg_p, avg_p])
        return probs

    def predict(self, X, threshold=0.5):
        probs = self.predict_proba(X)
        return [1 if p[1] >= threshold else 0 for p in probs]


def compute_roc_curve(y_true, y_probs):
    """Computes FPR, TPR and thresholds for ROC curve."""
    thresholds = [i / 40.0 for i in range(41)]
    roc_points = []
    total_pos = sum(y_true)
    total_neg = len(y_true) - total_pos

    if total_pos == 0 or total_neg == 0:
        return [{'fpr': 0.0, 'tpr': 0.0, 'threshold': 1.0}, {'fpr': 1.0, 'tpr': 1.0, 'threshold': 0.0}]

    for t in sorted(thresholds, reverse=True):
        tp = sum(1 for yt, yp in zip(y_true, y_probs) if yp >= t and yt == 1)
        fp = sum(1 for yt, yp in zip(y_true, y_probs) if yp >= t and yt == 0)
        tpr = tp / total_pos
        fpr = fp / total_neg
        roc_points.append({'fpr': round(fpr, 4), 'tpr': round(tpr, 4), 'threshold': round(t, 3)})

    return roc_points


def compute_classification_metrics(y_true, y_probs, threshold=0.5):
    """
    Computes Accuracy, Precision, Recall, F1, ROC-AUC, Confusion Matrix,
    and ROC points on test predictions.
    """
    n = len(y_true)
    if n == 0:
        return {}

    y_pred = [1 if p >= threshold else 0 for p in y_probs]

    tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1)
    tn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 0)
    fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1)
    fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0)

    accuracy = (tp + tn) / n
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    # Approximate Mann-Whitney U / Trapezoidal AUC
    # Rank ordering for ROC-AUC
    pos_probs = [yp for yt, yp in zip(y_true, y_probs) if yt == 1]
    neg_probs = [yp for yt, yp in zip(y_true, y_probs) if yt == 0]
    
    if pos_probs and neg_probs:
        wins = 0.0
        for p in pos_probs:
            for q in neg_probs:
                if p > q:
                    wins += 1.0
                elif p == q:
                    wins += 0.5
        auc = wins / (len(pos_probs) * len(neg_probs))
    else:
        auc = 0.5

    roc_curve_data = compute_roc_curve(y_true, y_probs)

    return {
        'accuracy': round(accuracy, 4),
        'precision': round(precision, 4),
        'recall': round(recall, 4),
        'f1': round(f1, 4),
        'auc': round(auc, 4),
        'confusion_matrix': {
            'tn': tn, 'fp': fp,
            'fn': fn, 'tp': tp
        },
        'threshold': threshold,
        'roc_curve': roc_curve_data
    }


class ModelEngine:
    """
    Coordinates training, inference, and metric evaluation
    for Logistic Regression and Random Forest.
    """
    def __init__(self, data_manager):
        self.dm = data_manager
        self.model_type = 'logistic_regression' # or 'random_forest'
        self.threshold = 0.5
        self.model = None
        self.active_features = list(self.dm.feature_names)
        self.dropped_attribute = None
        self.drop_proxies = False
        self.cached_test_probs = []
        self.cached_test_y = []
        self.latest_metrics = {}

    def get_features_for_ablation(self, attribute_to_drop=None, drop_proxies=False):
        """
        Filters feature names when an attribute is dropped.
        If drop_proxies is True, drops top 3 proxy features correlated with this attribute.
        """
        if not attribute_to_drop:
            return list(self.dm.feature_names)

        active = []
        # Exclude features that belong to the dropped attribute
        for f in self.dm.feature_names:
            orig = self.dm.column_origin_map.get(f, f)
            if orig == attribute_to_drop or f == attribute_to_drop:
                continue
            active.append(f)

        # If also dropping top 3 proxies
        if drop_proxies:
            # Find top correlated features with this attribute from proxy table
            proxy_candidates = [
                row['feature'] for row in self.dm.correlations
                if row['original_column'] != attribute_to_drop and row['feature'] in active
            ]
            proxies_to_drop = proxy_candidates[:3]
            active = [f for f in active if f not in proxies_to_drop]

        return active

    def train(self, model_type='logistic_regression', threshold=0.5, attribute_to_drop=None, drop_proxies=False):
        """Trains chosen model on train set and evaluates on test set."""
        self.model_type = model_type
        self.threshold = float(threshold)
        self.dropped_attribute = attribute_to_drop
        self.drop_proxies = drop_proxies

        # Determine active features
        self.active_features = self.get_features_for_ablation(attribute_to_drop, drop_proxies)

        train_rows = [self.dm.processed_data[i] for i in self.dm.train_indices]
        test_rows = [self.dm.processed_data[i] for i in self.dm.test_indices]

        X_train = self.dm.get_feature_matrix(train_rows, self.active_features)
        y_train = [r['target'] for r in train_rows]

        X_test = self.dm.get_feature_matrix(test_rows, self.active_features)
        y_test = [r['target'] for r in test_rows]

        if model_type == 'random_forest':
            self.model = PurePythonRandomForest(n_estimators=12, max_depth=6, random_state=42)
        else:
            self.model = PurePythonLogisticRegression(lr=0.1, epochs=15, l2_reg=0.001, random_state=42)

        self.model.fit(X_train, y_train)

        # Evaluate on test set
        test_probs_matrix = self.model.predict_proba(X_test)
        self.cached_test_probs = [p[1] for p in test_probs_matrix]
        self.cached_test_y = y_test

        self.latest_metrics = compute_classification_metrics(y_test, self.cached_test_probs, self.threshold)
        self.latest_metrics['model_type'] = self.model_type
        self.latest_metrics['num_features'] = len(self.active_features)
        self.latest_metrics['dropped_attribute'] = self.dropped_attribute
        self.latest_metrics['drop_proxies'] = self.drop_proxies

        return self.latest_metrics
