"""
Data Manager Module for Applicant Shortlisting Console.
Handles dataset loading, protected attribute derivation (proxies),
missing value imputation, one-hot encoding, stratified train/test splitting,
and proxy feature correlation detection.
"""

import os
import csv
import math
import random
from collections import Counter

# Try importing pandas and numpy if available and allowed by system policy
try:
    import numpy as np
    import pandas as pd
    _test = np.array([1.0, 2.0])
    HAS_PANDAS = True
except Exception:
    HAS_PANDAS = False


def derive_age_band(exp_str):
    """
    Derives age_band from experience column (proxy for candidate age).
    Bands: 0-5, 6-10, 11-15, 16+
    """
    if not exp_str or str(exp_str).strip() in ['', 'nan', 'None']:
        return '6-10'  # Median fallback
    val = str(exp_str).strip()
    if val == '<1':
        years = 0
    elif val == '>20':
        years = 21
    else:
        try:
            years = int(float(val))
        except ValueError:
            years = 5

    if years <= 5:
        return '0-5'
    elif years <= 10:
        return '6-10'
    elif years <= 15:
        return '11-15'
    else:
        return '16+'


def derive_institution(enrolled, education):
    """
    Derives institution from enrolled_university and education_level (proxy for institution pedigree).
    Categories: Postgraduate Institution, Graduate University, Continuing / Enrolled University,
                Non-Degree / School, Other / Unknown
    """
    enrolled = str(enrolled).strip() if enrolled and str(enrolled).strip() not in ['nan', 'None'] else ''
    edu = str(education).strip() if education and str(education).strip() not in ['nan', 'None'] else ''

    if edu in ['Phd', 'Masters']:
        return 'Postgraduate Institution'
    elif edu == 'Graduate':
        if enrolled == 'no_enrollment':
            return 'Graduate University'
        else:
            return 'Continuing / Enrolled University'
    elif edu in ['High School', 'Primary School']:
        return 'Non-Degree / School'
    else:
        return 'Other / Unknown'


class DataManager:
    """
    Manages data ingestion, preprocessing, proxy extraction,
    and train/test splitting.
    """

    def __init__(self, filepath='aug_train.csv'):
        self.filepath = filepath
        self.raw_data = []          # List of raw dict rows
        self.headers = []           # Original CSV headers
        self.processed_data = []    # Rows with derived attributes and cleaned values
        self.feature_names = []     # Names of encoded features for modeling
        self.column_origin_map = {} # Maps encoded feature -> original column name
        self.train_indices = []
        self.test_indices = []
        self.medians = {}           # Imputation values for numbers
        self.categories_map = {}    # Unique values for one-hot encoding
        self.correlations = {}      # Correlation of features with protected attributes

        if os.path.exists(filepath):
            self.load_dataset(filepath)

    def load_dataset(self, filepath):
        """Loads CSV dataset and populates raw records."""
        self.filepath = filepath
        self.raw_data = []
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            self.headers = reader.fieldnames
            for row in reader:
                self.raw_data.append(row)

        self.preprocess_and_encode()
        self.stratified_split(test_size=0.2, random_state=42)
        self.compute_proxy_correlations()

    def preprocess_and_encode(self):
        """
        Cleans data, derives protected attributes, computes medians,
        and constructs one-hot encoded feature matrices.
        """
        # Step 1: Extract numeric values to compute medians
        cdi_vals = []
        training_hours_vals = []
        for r in self.raw_data:
            try:
                cdi_vals.append(float(r.get('city_development_index', 0.8)))
            except Exception:
                pass
            try:
                training_hours_vals.append(float(r.get('training_hours', 50)))
            except Exception:
                pass

        cdi_vals.sort()
        training_hours_vals.sort()
        self.medians['city_development_index'] = cdi_vals[len(cdi_vals) // 2] if cdi_vals else 0.8
        self.medians['training_hours'] = training_hours_vals[len(training_hours_vals) // 2] if training_hours_vals else 50.0

        # Step 2: Categorical features to encode
        categorical_cols = [
            'gender', 'relevent_experience', 'enrolled_university',
            'education_level', 'major_discipline', 'company_size',
            'company_type', 'last_new_job'
        ]

        # Gather unique categories across rows
        cat_unique = {col: set() for col in categorical_cols}
        self.processed_data = []

        for idx, row in enumerate(self.raw_data):
            processed_row = dict(row)

            # Target label: 1.0 (proceed to interview) or 0.0 (reject)
            try:
                processed_row['target'] = int(float(row.get('target', 0)))
            except Exception:
                processed_row['target'] = 0

            # Derive protected attributes
            # 1. Gender: missing -> Unknown
            g = row.get('gender', '').strip()
            if not g or g.lower() in ['nan', 'none']:
                g = 'Unknown'
            processed_row['gender'] = g

            # 2. Age band: derived proxy from experience
            processed_row['age_band'] = derive_age_band(row.get('experience', ''))

            # 3. Institution: derived proxy from enrolled_university & education_level
            processed_row['institution'] = derive_institution(
                row.get('enrolled_university', ''),
                row.get('education_level', '')
            )

            # Impute numeric fields
            try:
                processed_row['city_development_index'] = float(row.get('city_development_index', self.medians['city_development_index']))
            except Exception:
                processed_row['city_development_index'] = self.medians['city_development_index']

            try:
                processed_row['training_hours'] = float(row.get('training_hours', self.medians['training_hours']))
            except Exception:
                processed_row['training_hours'] = self.medians['training_hours']

            # Impute categorical fields with 'Unknown'
            for col in categorical_cols:
                v = processed_row.get(col, '').strip()
                if not v or v.lower() in ['nan', 'none']:
                    v = 'Unknown'
                processed_row[col] = v
                cat_unique[col].add(v)

            # Unique enrollee id
            processed_row['enrollee_id'] = row.get('enrollee_id', str(idx + 1))
            self.processed_data.append(processed_row)

        self.categories_map = {col: sorted(list(vals)) for col, vals in cat_unique.items()}

        # Build feature names and mapping to original column
        self.feature_names = ['city_development_index', 'training_hours']
        self.column_origin_map = {
            'city_development_index': 'city_development_index',
            'training_hours': 'training_hours'
        }

        for col in categorical_cols:
            for cat_val in self.categories_map[col]:
                feat_name = f"{col}_{cat_val}"
                self.feature_names.append(feat_name)
                self.column_origin_map[feat_name] = col

    def get_feature_matrix(self, rows, active_features=None):
        """
        Constructs numeric feature vectors for the given rows.
        If active_features is specified, only include those features.
        """
        if active_features is None:
            active_features = self.feature_names

        matrix = []
        for r in rows:
            vec = []
            for f in active_features:
                if f == 'city_development_index':
                    # Scale to ~ [0, 1]
                    vec.append(r['city_development_index'])
                elif f == 'training_hours':
                    # Scale by dividing by 100 for numerical stability
                    vec.append(r['training_hours'] / 100.0)
                else:
                    # One-hot encoded feature: col_val
                    col = self.column_origin_map.get(f)
                    val = f[len(col) + 1:]
                    vec.append(1.0 if r.get(col) == val else 0.0)
            matrix.append(vec)
        return matrix

    def stratified_split(self, test_size=0.2, random_state=42):
        """
        Stratified train/test split on target label using fixed seed.
        Ensures consistent 80/20 split across runs and ablation tests.
        """
        pos_indices = [i for i, r in enumerate(self.processed_data) if r['target'] == 1]
        neg_indices = [i for i, r in enumerate(self.processed_data) if r['target'] == 0]

        rng = random.Random(random_state)
        rng.shuffle(pos_indices)
        rng.shuffle(neg_indices)

        n_pos_test = int(len(pos_indices) * test_size)
        n_neg_test = int(len(neg_indices) * test_size)

        test_idx = pos_indices[:n_pos_test] + neg_indices[:n_neg_test]
        train_idx = pos_indices[n_pos_test:] + neg_indices[n_neg_test:]

        # Sort indices for deterministic ordering
        self.train_indices = sorted(train_idx)
        self.test_indices = sorted(test_idx)

    def compute_proxy_correlations(self):
        """
        Computes Pearson correlation between all encoded features and
        protected attributes (gender, age_band, institution) to reveal
        implicit proxies.
        """
        # Create numeric dummy targets for protected groups
        protected_attrs = ['gender', 'age_band', 'institution']
        
        # Build one-hot vectors for protected categories
        prot_categories = {}
        for p in protected_attrs:
            unique_vals = sorted(list(set(r[p] for r in self.processed_data)))
            prot_categories[p] = unique_vals

        # Precompute values for features
        X = self.get_feature_matrix(self.processed_data)
        N = len(self.processed_data)
        if N == 0:
            return

        # Precompute means and standard deviations of features
        f_means = [sum(X[i][j] for i in range(N)) / N for j in range(len(self.feature_names))]
        f_stds = []
        for j in range(len(self.feature_names)):
            var = sum((X[i][j] - f_means[j]) ** 2 for i in range(N)) / N
            f_stds.append(math.sqrt(var) if var > 1e-9 else 1e-9)

        # Precompute for each protected attribute's one-hot subcategories
        corr_results = []
        for j, feat in enumerate(self.feature_names):
            orig_col = self.column_origin_map.get(feat, feat)
            row_entry = {
                'feature': feat,
                'original_column': orig_col,
                'corr_gender': 0.0,
                'corr_age_band': 0.0,
                'corr_institution': 0.0,
                'max_correlation': 0.0,
                'highest_proxy_group': 'None',
                'is_high_risk_proxy': False
            }

            for p in protected_attrs:
                max_p_corr = 0.0
                best_group = ''
                for cat in prot_categories[p]:
                    # Target binary vector for this protected category
                    p_vec = [1.0 if self.processed_data[i][p] == cat else 0.0 for i in range(N)]
                    p_mean = sum(p_vec) / N
                    p_var = sum((v - p_mean) ** 2 for v in p_vec) / N
                    p_std = math.sqrt(p_var) if p_var > 1e-9 else 1e-9

                    # Pearson r
                    cov = sum((X[i][j] - f_means[j]) * (p_vec[i] - p_mean) for i in range(N)) / N
                    r = abs(cov / (f_stds[j] * p_std))
                    if r > max_p_corr:
                        max_p_corr = r
                        best_group = f"{p}: {cat}"

                if p == 'gender':
                    row_entry['corr_gender'] = round(max_p_corr, 4)
                elif p == 'age_band':
                    row_entry['corr_age_band'] = round(max_p_corr, 4)
                elif p == 'institution':
                    row_entry['corr_institution'] = round(max_p_corr, 4)

                if max_p_corr > row_entry['max_correlation']:
                    row_entry['max_correlation'] = round(max_p_corr, 4)
                    row_entry['highest_proxy_group'] = best_group

            # Proxy risk threshold: >= 0.25 is notable proxy risk
            row_entry['is_high_risk_proxy'] = row_entry['max_correlation'] >= 0.25
            corr_results.append(row_entry)

        # Sort by max_correlation descending
        corr_results.sort(key=lambda x: x['max_correlation'], reverse=True)
        self.correlations = corr_results

    def get_summary(self):
        """Returns high-level statistics for Screen 1."""
        total = len(self.processed_data)
        if total == 0:
            return {}

        targets = Counter(r['target'] for r in self.processed_data)
        genders = Counter(r['gender'] for r in self.processed_data)
        age_bands = Counter(r['age_band'] for r in self.processed_data)
        institutions = Counter(r['institution'] for r in self.processed_data)

        # Missing values in original columns
        missing_summary = {}
        for h in self.headers:
            missing_count = sum(1 for r in self.raw_data if not r.get(h) or str(r.get(h)).strip() in ['', 'nan', 'None'])
            missing_summary[h] = {
                'missing_count': missing_count,
                'missing_pct': round((missing_count / total) * 100, 2)
            }

        return {
            'total_rows': total,
            'train_rows': len(self.train_indices),
            'test_rows': len(self.test_indices),
            'num_features': len(self.feature_names),
            'class_balance': {
                'positive': targets.get(1, 0),
                'negative': targets.get(0, 0),
                'positive_pct': round((targets.get(1, 0) / total) * 100, 2),
                'negative_pct': round((targets.get(0, 0) / total) * 100, 2)
            },
            'gender_dist': dict(genders),
            'age_band_dist': dict(age_bands),
            'institution_dist': dict(institutions),
            'missing_summary': missing_summary,
            'preview': self.processed_data[:10]
        }
