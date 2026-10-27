"""
generate_algorithm_performance_pdf.py
Builds an authoritative, publication-quality technical report PDF evaluating
the performance of all machine learning algorithms in FairRecruit.

Covers:
1. Executive Summary & Benchmark Framework
2. Empirical Results Table (Accuracy, Precision, Recall, F1, AUC, AP, CV Spread, Balanced Accuracy)
3. Confusion Matrix & Decision Analysis across Models
4. Feature Selection vs. PCA Dimensionality Reduction Analysis
5. Deep Dive: Key Factors Influencing Algorithmic Performance
   - Class Imbalance (75/25 distribution & majority baseline trap)
   - Non-Linear Step Functions vs. Linear Hyperplanes
   - High-Dimensional Categorical Sparsity & Curse of Dimensionality
   - Feature Multicollinearity & Failure of Naive Bayes
   - Outliers & Missingness Imputation Hygiene
6. Decision Rationale: Why Decision Tree is the Optimal Operational Benchmark
   - Explainability vs. Accuracy Frontier
   - Legal & Ethical Requirements for Automated Shortlisting
7. Practical Viva Examination Defense Q&A
"""

import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, PageBreak, HRFlowable
)
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent
PDF_PATH = ROOT / "output" / "pdf" / "FairRecruit_Algorithm_Performance_Report.pdf"


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas for dynamic 'Page X of Y' numbering with running headers/footers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, page_count):
        self.saveState()
        page_num = self._pageNumber
        width, height = A4

        # Running Header (pages after page 1)
        if page_num > 1:
            self.setFont("Helvetica-Bold", 7.5)
            self.setFillColor(colors.HexColor("#0f2942"))
            self.drawString(16 * mm, height - 11 * mm, "FAIRRECRUIT RESEARCH REPORT")
            self.setFont("Helvetica", 7.5)
            self.setFillColor(colors.HexColor("#64748b"))
            self.drawString(56 * mm, height - 11 * mm, "|  Algorithmic Benchmarks, Influencing Factors & Decision Reasoning")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(16 * mm, height - 13 * mm, width - 16 * mm, height - 13 * mm)

        # Running Footer (all pages)
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(16 * mm, 13 * mm, width - 16 * mm, 13 * mm)
        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor("#64748b"))
        self.drawString(16 * mm, 8.5 * mm, "Data Mining Project 5  *  Comparative Algorithm Evaluation & Fairness Audit")
        self.drawRightString(width - 16 * mm, 8.5 * mm, f"Page {page_num} of {page_count}")
        self.restoreState()


def get_styles():
    sheet = getSampleStyleSheet()

    c_primary = colors.HexColor("#0f2942")     # Deep Navy
    c_secondary = colors.HexColor("#0d9488")   # Deep Teal Accent
    c_dark = colors.HexColor("#1e293b")        # Slate 800
    c_body = colors.HexColor("#334155")        # Slate 700

    return {
        "DocTitle": ParagraphStyle(
            "DocTitle",
            fontName="Helvetica-Bold",
            fontSize=21,
            leading=25,
            textColor=c_primary,
            spaceAfter=4,
        ),
        "DocSubtitle": ParagraphStyle(
            "DocSubtitle",
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=c_secondary,
            spaceAfter=10,
        ),
        "MetaBanner": ParagraphStyle(
            "MetaBanner",
            fontName="Helvetica",
            fontSize=8,
            leading=11.5,
            textColor=colors.HexColor("#475569"),
            spaceAfter=12,
        ),
        "SecHeading": ParagraphStyle(
            "SecHeading",
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=c_primary,
            spaceBefore=11,
            spaceAfter=5,
            keepWithNext=True,
        ),
        "SubHeading": ParagraphStyle(
            "SubHeading",
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=13,
            textColor=c_dark,
            spaceBefore=8,
            spaceAfter=3,
            keepWithNext=True,
        ),
        "Body": ParagraphStyle(
            "Body",
            fontName="Helvetica",
            fontSize=8.3,
            leading=11.8,
            textColor=c_body,
            spaceAfter=5,
        ),
        "BodyBold": ParagraphStyle(
            "BodyBold",
            fontName="Helvetica-Bold",
            fontSize=8.3,
            leading=11.8,
            textColor=c_dark,
            spaceAfter=5,
        ),
        "BulletText": ParagraphStyle(
            "BulletText",
            fontName="Helvetica",
            fontSize=8.3,
            leading=11.5,
            textColor=c_body,
            leftIndent=12,
            firstLineIndent=-8,
            spaceAfter=3,
        ),
        "CodeText": ParagraphStyle(
            "CodeText",
            fontName="Courier",
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#0f172a"),
        ),
        "TableHeader": ParagraphStyle(
            "TableHeader",
            fontName="Helvetica-Bold",
            fontSize=7.8,
            leading=10.5,
            textColor=colors.white,
            alignment=1,
        ),
        "TableCell": ParagraphStyle(
            "TableCell",
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.5,
            textColor=c_dark,
            alignment=0,
        ),
        "TableCellCenter": ParagraphStyle(
            "TableCellCenter",
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.5,
            textColor=c_dark,
            alignment=1,
        ),
        "TableCellBold": ParagraphStyle(
            "TableCellBold",
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9.5,
            textColor=c_dark,
            alignment=1,
        ),
        "CalloutText": ParagraphStyle(
            "CalloutText",
            fontName="Helvetica",
            fontSize=8,
            leading=11.5,
            textColor=colors.HexColor("#1e293b"),
        ),
    }


def make_callout(title, body_paras, style_dict, kind="info"):
    accent_map = {
        "info": ("#0d9488", "#f0fdfa", "#ccfbf1"),
        "warning": ("#d97706", "#fffbeb", "#fef3c7"),
        "danger": ("#dc2626", "#fef2f2", "#fee2e2"),
        "success": ("#16a34a", "#f0fdf4", "#dcfce7"),
    }
    c_accent, c_bg, c_border = [colors.HexColor(x) for x in accent_map.get(kind, accent_map["info"])]

    story = [
        Paragraph(f"<b>{title}</b>", ParagraphStyle(
            "CTitle", fontName="Helvetica-Bold", fontSize=8.5, leading=12, textColor=c_accent
        )),
        Spacer(1, 1.5 * mm),
    ]
    if isinstance(body_paras, str):
        body_paras = [body_paras]
    for p in body_paras:
        story.append(Paragraph(p, style_dict["CalloutText"]))
        story.append(Spacer(1, 1 * mm))

    cell = Table([[story]], colWidths=[178 * mm])
    cell.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), c_bg),
        ("BOX", (0, 0), (-1, -1), 0.75, c_border),
        ("LINEBEFORE", (0, 0), (0, -1), 3.5, c_accent),
        ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
        ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5 * mm),
    ]))
    return cell


def build_pdf():
    PDF_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )
    styles = get_styles()
    story = []

    # -------------------------------------------------------------------------
    # 1. TITLE & METADATA
    # -------------------------------------------------------------------------
    story.append(Paragraph("FairRecruit: Machine Learning Algorithm Performance Report", styles["DocTitle"]))
    story.append(Paragraph(
        "Empirical Benchmark Evaluation, Dimensionality Reduction Trade-offs, Influencing Factors & Decision Rationale",
        styles["DocSubtitle"]
    ))
    story.append(Paragraph(
        "<b>Project:</b> Data Mining Project 5 &bull; <b>Evaluation Split:</b> Stratified Validation Partition (3,832 records) "
        "&bull; <b>Training Split:</b> 11,494 records (5-Fold Stratified CV) &bull; <b>Baseline Majority:</b> 75.05%",
        styles["MetaBanner"]
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0f2942"), spaceAfter=8))

    # -------------------------------------------------------------------------
    # 2. EXECUTIVE SUMMARY & EXPERIMENTAL HYGIENE
    # -------------------------------------------------------------------------
    story.append(Paragraph("1. Executive Summary & Evaluation Framework", styles["SecHeading"]))
    story.append(Paragraph(
        "In algorithmic hiring and applicant shortlisting, selecting a classification algorithm requires balancing "
        "<b>raw predictive performance</b> (ranking candidates with genuine qualification/interest) against "
        "<b>interpretability, algorithmic fairness, and legal defensibility</b>. "
        "To rigorously compare model families, FairRecruit implements a zero-data-leakage testing harness: "
        "imputation, standard scaling, and one-hot encoding are fit <i>exclusively</i> on training records, "
        "and every cross-validation fold refits its feature pipelines independently.",
        styles["Body"]
    ))

    story.append(make_callout(
        "Methodological Rigor & Data Leakage Elimination",
        "A common flaw in academic ML submissions is calculating scalers and imputers across the entire dataset prior to splitting. "
        "In this audit, all 5 model families were evaluated on the <b>20% validation partition (3,832 candidates)</b> with identical "
        "feature spaces (10 raw predictors expanded to 45 one-hot encoded dimensions). Cross-validation scores reflect "
        "5-fold stratified cross-validation on the 60% training partition (11,494 rows), where each fold executes its own independent pipeline fit.",
        styles, kind="info"
    ))
    story.append(Spacer(1, 4 * mm))

    # -------------------------------------------------------------------------
    # 3. EMPIRICAL BENCHMARK RESULTS TABLE (5 MODELS)
    # -------------------------------------------------------------------------
    story.append(Paragraph("2. Empirical Benchmark Evaluation Across 5 Model Families", styles["SecHeading"]))
    story.append(Paragraph(
        "All five algorithms were evaluated on the held-out validation cohort under fixed 0.50 probability thresholding. "
        "The majority-class zero-rule baseline is <b>75.05%</b> (predicting no candidate qualifies for shortlisting).",
        styles["Body"]
    ))

    # Table of 5 models
    headers = [
        Paragraph("<b>Model Family</b>", styles["TableHeader"]),
        Paragraph("<b>Category</b>", styles["TableHeader"]),
        Paragraph("<b>Accuracy</b>", styles["TableHeader"]),
        Paragraph("<b>Precision</b>", styles["TableHeader"]),
        Paragraph("<b>Recall</b>", styles["TableHeader"]),
        Paragraph("<b>F1-Score</b>", styles["TableHeader"]),
        Paragraph("<b>ROC-AUC</b>", styles["TableHeader"]),
        Paragraph("<b>PR-AUC (AP)</b>", styles["TableHeader"]),
        Paragraph("<b>5-Fold CV Spread</b>", styles["TableHeader"]),
    ]
    data = [headers]

    model_rows = [
        ("Decision Tree", "Tree (Interpretable)", "77.53%", "54.90%", "55.65%", "55.27%", "0.7760", "0.4889", "79.43% +/- 1.41%", True),
        ("Random Forest", "Ensemble Bagging", "76.57%", "56.36%", "26.88%", "36.40%", "0.7795", "0.5184", "77.69% +/- 0.44%", False),
        ("Logistic Regression", "Linear (L2)", "76.15%", "54.38%", "27.30%", "36.35%", "0.7635", "0.4895", "77.49% +/- 0.48%", False),
        ("K-Nearest Neighbors", "Instance-Based (k=15)", "75.00%", "49.87%", "41.11%", "45.07%", "0.7206", "0.4370", "76.18% +/- 0.35%", False),
        ("Gaussian Naive Bayes", "Probabilistic", "75.05%", "N/A*", "0.00%", "0.00%", "0.6280", "0.3597", "75.07% +/- 0.02%", False),
        ("Majority Baseline", "Zero-Rule Threshold", "75.05%", "N/A", "0.00%", "0.00%", "0.5000", "0.2495", "75.05% +/- 0.00%", False),
    ]

    for name, cat, acc, prec, rec, f1, auc, ap, cv, is_best in model_rows:
        b_tag = "<b>" if is_best else ""
        b_end = "</b>" if is_best else ""
        data.append([
            Paragraph(f"{b_tag}{name}{b_end}", styles["TableCell"]),
            Paragraph(cat, styles["TableCellCenter"]),
            Paragraph(f"{b_tag}{acc}{b_end}", styles["TableCellCenter"]),
            Paragraph(prec, styles["TableCellCenter"]),
            Paragraph(rec, styles["TableCellCenter"]),
            Paragraph(f"{b_tag}{f1}{b_end}", styles["TableCellCenter"]),
            Paragraph(f"{b_tag}{auc}{b_end}", styles["TableCellCenter"]),
            Paragraph(ap, styles["TableCellCenter"]),
            Paragraph(cv, styles["TableCellCenter"]),
        ])

    col_widths = [26 * mm, 25 * mm, 16 * mm, 16 * mm, 16 * mm, 16 * mm, 16 * mm, 18 * mm, 29 * mm]
    t_models = Table(data, colWidths=col_widths)
    t_models.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f2942")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f8fafc")]),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f0fdf4")), # Highlight Decision Tree
        ("LINEBELOW", (0, 1), (-1, 1), 1.2, colors.HexColor("#16a34a")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f1f5f9")), # Baseline row
    ]))
    story.append(t_models)
    story.append(Paragraph(
        "<font size='7' color='#64748b'>* Gaussian Naive Bayes predicted 0 positive candidates at the 0.50 threshold (TP=0, FP=0), "
        "making precision mathematically undefined. The 75.05% accuracy is completely trivial (identical to predicting all 0s).</font>",
        styles["Body"]
    ))
    story.append(Spacer(1, 3 * mm))

    # Confusion Matrix comparison
    story.append(Paragraph("3. Confusion Matrix Breakdown & Prediction Behavior", styles["SecHeading"]))
    story.append(Paragraph(
        "Examining raw classification outcomes on the 3,832 validation applicants (956 actual positives, 2,876 actual negatives) "
        "reveals stark differences in how each algorithm approaches shortlisting:",
        styles["Body"]
    ))

    cm_headers = [
        Paragraph("<b>Model</b>", styles["TableHeader"]),
        Paragraph("<b>True Neg (TN)</b>", styles["TableHeader"]),
        Paragraph("<b>False Pos (FP)</b>", styles["TableHeader"]),
        Paragraph("<b>False Neg (FN)</b>", styles["TableHeader"]),
        Paragraph("<b>True Pos (TP)</b>", styles["TableHeader"]),
        Paragraph("<b>Balanced Acc</b>", styles["TableHeader"]),
        Paragraph("<b>Clinical Behavior Summary</b>", styles["TableHeader"]),
    ]
    cm_data = [cm_headers]
    cm_rows = [
        ("Decision Tree", "2,439", "437", "424", "532", "70.23%", "<b>Balanced shortlister:</b> Recovers 55.7% of positives with controlled FP rate (15.2%)."),
        ("Random Forest", "2,678", "198", "699", "257", "59.98%", "<b>High specificity:</b> Conservative shortlister; low FP rate but misses 73.1% of positives."),
        ("Logistic Regression", "2,657", "219", "695", "261", "59.84%", "<b>Linear threshold:</b> Similar to RF, misses 72.7% of positive cohort at default 0.50."),
        ("K-Nearest Neighbors", "2,481", "395", "563", "393", "63.69%", "<b>Moderate recovery:</b> Recovers 41.1% of positives; suffers from distance degradation."),
        ("Gaussian Naive Bayes", "2,876", "0", "956", "0", "50.00%", "<b>Complete collapse:</b> Predicts 0 candidates; identical to trivial majority baseline."),
    ]
    for m, tn, fp, fn, tp, ba, note in cm_rows:
        cm_data.append([
            Paragraph(f"<b>{m}</b>", styles["TableCellBold"]),
            Paragraph(tn, styles["TableCellCenter"]),
            Paragraph(fp, styles["TableCellCenter"]),
            Paragraph(fn, styles["TableCellCenter"]),
            Paragraph(tp, styles["TableCellCenter"]),
            Paragraph(f"<b>{ba}</b>", styles["TableCellCenter"]),
            Paragraph(note, styles["TableCell"]),
        ])
    t_cm = Table(cm_data, colWidths=[28 * mm, 18 * mm, 18 * mm, 18 * mm, 18 * mm, 20 * mm, 58 * mm])
    t_cm.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f2942")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f0fdf4")),
    ]))
    story.append(t_cm)
    story.append(Spacer(1, 4 * mm))

    # -------------------------------------------------------------------------
    # 4. DIMENSIONALITY REDUCTION & FEATURE SELECTION
    # -------------------------------------------------------------------------
    story.append(Paragraph("4. Feature Selection vs. PCA Dimensionality Reduction", styles["SecHeading"]))
    story.append(Paragraph(
        "To evaluate whether dimensionality reduction improves generalization or aids algorithmic transparency, "
        "we benchmarked the Decision Tree architecture across three feature representations on the validation split:",
        styles["Body"]
    ))

    dim_headers = [
        Paragraph("<b>Representation Technique</b>", styles["TableHeader"]),
        Paragraph("<b>Input Dim</b>", styles["TableHeader"]),
        Paragraph("<b>Accuracy</b>", styles["TableHeader"]),
        Paragraph("<b>Precision</b>", styles["TableHeader"]),
        Paragraph("<b>Recall</b>", styles["TableHeader"]),
        Paragraph("<b>ROC-AUC</b>", styles["TableHeader"]),
        Paragraph("<b>Practical Impact on Hiring Audits</b>", styles["TableHeader"]),
    ]
    dim_data = [dim_headers]
    dim_rows = [
        ("All Raw Predictors", "45", "77.53%", "54.90%", "55.65%", "0.7760", "Preserves full feature fidelity; complete explainability down to source columns."),
        ("Importance-Based Selection", "10", "77.43%", "54.72%", "55.23%", "0.7714", "Preserves 99.8% of performance using 10 key features; retains input names."),
        ("PCA Orthogonal Components", "10", "75.37%", "51.09%", "29.39%", "0.7043", "Severe degradation: Recall drops to 29.4%; destroys audit explainability."),
    ]
    for rep, dim, acc, prec, rec, auc, imp in dim_rows:
        dim_data.append([
            Paragraph(f"<b>{rep}</b>", styles["TableCellBold"]),
            Paragraph(dim, styles["TableCellCenter"]),
            Paragraph(acc, styles["TableCellCenter"]),
            Paragraph(prec, styles["TableCellCenter"]),
            Paragraph(rec, styles["TableCellCenter"]),
            Paragraph(auc, styles["TableCellCenter"]),
            Paragraph(imp, styles["TableCell"]),
        ])
    t_dim = Table(dim_data, colWidths=[36 * mm, 14 * mm, 16 * mm, 16 * mm, 16 * mm, 16 * mm, 64 * mm])
    t_dim.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f2942")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(t_dim)
    story.append(Spacer(1, 2 * mm))

    story.append(make_callout(
        "Critical Data Mining Finding: Why PCA Fails in HR Categorical Pipelines",
        "<b>Why PCA harms performance:</b> The 10 PCA components account for only 43.25% of total variance. "
        "PCA relies on orthogonal linear combinations of continuous variables. Because the HR feature matrix consists largely of "
        "sparse one-hot dummy variables (company type, education level, major), projecting discrete 0/1 indicators into continuous eigenvectors "
        "creates noisy coordinates that destroy the sharp, axis-aligned decision boundaries required by decision trees.<br/>"
        "<b>Audit implication:</b> A candidate cannot be given an explanation like 'You were rejected because Component 3 was -0.42'. "
        "PCA obliterates legal transparency.",
        styles, kind="warning"
    ))
    story.append(Spacer(1, 4 * mm))

    # -------------------------------------------------------------------------
    # 5. KEY FACTORS INFLUENCING ALGORITHM PERFORMANCE
    # -------------------------------------------------------------------------
    story.append(Paragraph("5. Deep Dive: Key Factors Influencing Model Performance", styles["SecHeading"]))
    story.append(Paragraph(
        "Why do these algorithms perform so differently on the exact same dataset? Five structural factors govern their behavior:",
        styles["Body"]
    ))

    factors = [
        ("Factor 1: Severe Class Imbalance (75% Class 0 vs. 25% Class 1)",
         "In HR candidate screening, highly qualified candidates shortlisted for interviews represent a selective minority (24.95%). "
         "This imbalance creates a dangerous <i>majority baseline trap</i>: a trivial model predicting 'No' for every candidate achieves 75.05% accuracy. "
         "Linear models (Logistic Regression) and Naive Bayes struggle with this imbalance under a default 0.50 threshold, "
         "predicting overly conservative probabilities. Decision trees handle this significantly better by isolating pure leaf nodes based on key continuous splits."),

        ("Factor 2: Non-Linear Step Functions vs. Linear Hyperplanes",
         "The single most dominant predictor in the dataset is <code>city_development_index</code>. Candidates residing in cities with an index "
         "&le; 0.62 have a significantly higher rate of meeting qualification criteria (>55%), while candidates in high-index cities (&ge; 0.85) qualify at lower rates (<15%). "
         "This is an abrupt non-linear step function. Tree-based models (Decision Tree, Random Forest) model this with a single orthogonal split. "
         "Logistic Regression must fit a smooth sigmoid curve across the entire feature space, blunting the threshold effect and dampening sensitivity."),

        ("Factor 3: High-Dimensional Categorical Sparsity (45 Encoded Features)",
         "Expanding 7 categorical variables into one-hot dummy columns creates a 45-dimensional feature space. "
         "This triggers the <b>Curse of Dimensionality</b> for distance-based models like K-Nearest Neighbors (KNN). "
         "In 45 dimensions, Euclidean distances between points concentrate (all candidates appear equidistant), so KNN's neighborhood voting is "
         "overwhelmed by the 75% majority class, degrading precision to 49.87% and recall to 41.11%."),

        ("Factor 4: Violation of Conditional Independence (Why Naive Bayes Collapses)",
         "Gaussian Naive Bayes assumes all features are conditionally independent given the class label. "
         "In recruitment data, features are heavily correlated (e.g., <code>education_level</code> is correlated with <code>enrolled_university</code>, "
         "and <code>experience</code> correlates with <code>company_size</code> and <code>city_development_index</code>). "
         "Multiplying redundant probabilities double-counts evidence, pushing posterior probabilities toward extreme 0 or 1 boundaries, "
         "causing Naive Bayes to predict 0 positive cases at the 0.50 cutoff."),

        ("Factor 5: Feature Multicollinearity and Proxies",
         "Even when sensitive attributes like Gender, Age, and Institution are excluded from predictors, proxy correlations exist "
         "(e.g., <code>city_development_index</code> has an NMI of ~0.30 with certain demographic distributions). "
         "Ensemble models like Random Forest distribute split criteria across proxy features, making bias auditing harder. "
         "A single Decision Tree makes proxy usage completely transparent by exposing the exact tree nodes."),
    ]

    for title, desc in factors:
        story.append(Paragraph(f"<b>{title}</b>", styles["SubHeading"]))
        story.append(Paragraph(desc, styles["Body"]))
        story.append(Spacer(1, 1.5 * mm))

    story.append(Spacer(1, 2 * mm))

    # -------------------------------------------------------------------------
    # 6. DECISION RATIONALE: WHY DECISION TREE IS THE OPERATIONAL BENCHMARK
    # -------------------------------------------------------------------------
    story.append(Paragraph("6. Algorithmic Reasoning: Which Performs Better and Why", styles["SecHeading"]))
    story.append(Paragraph(
        "A superficial evaluation might look solely at Random Forest's slightly higher ROC-AUC (0.7795 vs 0.7760) and conclude it is superior. "
        "However, rigorous data science engineering requires evaluating models against <b>both performance and operational requirements</b>.",
        styles["Body"]
    ))

    story.append(Paragraph("<b>The Comparative Ranking Summary:</b>", styles["BodyBold"]))
    story.append(Paragraph(
        "&bull; <b>Rank 1 (Overall Operational Winner): Decision Tree.</b> Achieves the highest validation accuracy (77.53%), "
        "highest F1-score (55.27%), highest balanced accuracy (70.23%), and strong ROC-AUC (0.7760) while providing <b>100% faithful explainability</b>.<br/>"
        "&bull; <b>Rank 2 (Best Ranking Discrimination): Random Forest.</b> Wins on ROC-AUC (0.7795) and Average Precision (0.5184), but suffers from "
        "low recall at default thresholds (26.88%) and acts as an uninterpretable black box.<br/>"
        "&bull; <b>Rank 3 (Linear Baseline): Logistic Regression.</b> Competitive ROC-AUC (0.7635) and well-calibrated probabilities, but misses non-linear step thresholds.<br/>"
        "&bull; <b>Rank 4: K-Nearest Neighbors.</b> Suffers from high-dimensional distance concentration; high inference latency.<br/>"
        "&bull; <b>Rank 5 (Unusable Failure Mode): Gaussian Naive Bayes.</b> Complete collapse on imbalanced, correlated tabular data; identical to majority rule.",
        styles["BulletText"]
    ))
    story.append(Spacer(1, 3 * mm))

    story.append(make_callout(
        "Why Decision Tree is the Primary Operational Benchmark in FairRecruit",
        "<b>1. Regulatory Compliance (EU AI Act & EEOC Guidelines):</b> Automated employment decision tools (AEDTs) require defensible, "
        "candidate-specific explanations. A candidate shortlisted or rejected by a Decision Tree can be provided with their exact decision path "
        "(e.g., <i>'Applicant 11600: city_development_index &le; 0.62 AND experience &gt; 4.0'</i>).<br/>"
        "<b>2. Superior F1-Score & Balanced Recall:</b> At the operational 0.50 threshold, Random Forest and Logistic Regression miss over 73% of qualified candidates "
        "(recall &lt; 27.3%), whereas Decision Tree recovers 55.65% of positives with an F1 of 55.27%.<br/>"
        "<b>3. Controlled Feature Ablation:</b> Testing bias interventions (dropping <code>city_development_index</code> or proxies) is "
        "deterministic and directly auditable in a single tree, whereas ensemble feature interactions obscure the source of disparity reduction.",
        styles, kind="success"
    ))
    story.append(Spacer(1, 4 * mm))

    # -------------------------------------------------------------------------
    # 7. VIVA EXAMINATION DEFENSE Q&A
    # -------------------------------------------------------------------------
    story.append(Paragraph("7. Master Viva Examination Defense Questions & Script", styles["SecHeading"]))

    qas = [
        ("Q1: 'Random Forest has a higher ROC-AUC (0.7795 vs 0.7760). Why did you choose Decision Tree as your primary classifier?'",
         "<b>Examiner Defense:</b> 'While Random Forest edges out Decision Tree by 0.0035 in ROC-AUC, in an automated recruitment system, "
         "ROC-AUC measures only ranking discrimination across all theoretical thresholds. In practice, hiring decisions operate at concrete thresholds. "
         "At the standard 0.50 threshold, Random Forest's recall is only 26.88% (F1: 36.40%), missing nearly three-quarters of positive applicants, "
         "whereas Decision Tree achieves 55.65% recall and 55.27% F1. Most crucially, hiring algorithms are classified as high-risk under the EU AI Act. "
         "Random Forest combines 100 trees with random subspace sampling, creating a black box. Decision Tree offers 100% faithful explainability, "
         "allowing candidates and legal auditors to inspect the exact rules governing selection.'"),

        ("Q2: 'Why did Gaussian Naive Bayes achieve 75.05% accuracy with 0% precision and recall?'",
         "<b>Examiner Defense:</b> '75.05% is the majority-class baseline of our dataset. In our training split, 75% of candidates are labeled 0. "
         "Gaussian Naive Bayes assumes all features are conditionally independent and normally distributed. Because our feature matrix contains "
         "45 correlated one-hot dummy variables, the conditional independence assumption is catastrophically violated. "
         "Redundant probability multiplication forced all posterior positive probabilities below 0.50, meaning Naive Bayes predicted 0 for every single applicant. "
         "It appears accurate only because the negative class dominates the dataset.'"),

        ("Q3: 'Why did PCA dimensionality reduction decrease accuracy from 77.53% to 75.37% and recall to 29.39%?'",
         "<b>Examiner Defense:</b> 'PCA is a linear orthogonal transformation designed for continuous, Gaussian-distributed data. "
         "Our data consists of 10 continuous and 35 sparse categorical indicators. 10 PCA components captured only 43.25% of total variance. "
         "Projecting discrete 0/1 indicator categories into continuous eigenvectors introduced high noise and blurred the sharp axis-aligned decision boundaries "
         "that decision trees excel at finding. Furthermore, PCA destroys audit provenance, making legal compliance impossible.'"),
    ]

    for q, a in qas:
        story.append(Paragraph(f"<b>{q}</b>", styles["SubHeading"]))
        story.append(Paragraph(a, styles["Body"]))
        story.append(Spacer(1, 2 * mm))

    # Build the PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Report PDF successfully generated at: {PDF_PATH}")
    return PDF_PATH


if __name__ == "__main__":
    build_pdf()
