"""
Comprehensive Viva Voce & Technical Report PDF Generator for DSC306 Project 5.
Covers Stages A through G:
- Stage A: Data & Documentation (Measurement types, Data Dictionary, Statement of Excluded Columns)
- Stage B: Data Quality Audit & Repair (6 fault categories, provenance, before/after table, 10 validate assertions)
- Stage C: Pre-processing (Rescaling decisions, Feature Selection vs PCA, Discretization)
- Stage D: Models (Three families: Decision Tree, Naïve Bayes, KNN + hyperparameter tuning)
- Stage E: Evaluation (80/20 stratified split, majority baseline beside accuracy, precision/recall justification, Cost Matrix & optimal theta*, 5-fold CV spread)
- Stage F: Explanation (Decision paths in user language, executive hiring reasoning)
- Stage G: Six Screens Breakdown & 40 Master Viva Voce Questions & Answers
"""

import os
import sys
import math
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        if self._pageNumber > 1:
            # Running Header
            self.setFont('Helvetica-Bold', 8)
            self.setFillColor(colors.HexColor('#1A365D'))
            self.drawString(40, letter[1] - 30, 'DSC306 DATA MINING — PROJECT 5: APPLICANT SHORTLISTING CONSOLE WITH FAIRNESS AUDIT')
            
            self.setFont('Helvetica', 8)
            self.setFillColor(colors.HexColor('#718096'))
            self.drawRightString(letter[0] - 40, letter[1] - 30, 'VIVA VOCE MASTER GUIDE & TECHNICAL SPECIFICATION (STAGES A-G)')
            
            self.setStrokeColor(colors.HexColor('#CBD5E0'))
            self.setLineWidth(0.6)
            self.line(40, letter[1] - 34, letter[0] - 40, letter[1] - 34)

            # Running Footer
            self.line(40, 36, letter[0] - 40, 36)
            self.setFont('Helvetica', 8)
            self.setFillColor(colors.HexColor('#718096'))
            self.drawString(40, 24, 'DSC306 Semester Project Defense | Comprehensive Mathematical Formulations & Architecture')
            page_text = f'Page {self._pageNumber} of {page_count}'
            self.drawRightString(letter[0] - 40, 24, page_text)
        self.restoreState()


def build_pdf(filename='Applicant_Shortlisting_Fairness_Audit_Viva_Guide.pdf'):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=46,
        bottomMargin=46
    )

    styles = getSampleStyleSheet()
    
    # Custom Palette
    c_primary = colors.HexColor('#1A365D')   # Deep Navy
    c_secondary = colors.HexColor('#2B6CB0') # Slate Blue
    c_accent = colors.HexColor('#C53030')    # Crimson Red
    c_dark = colors.HexColor('#2D3748')      # Charcoal Text
    c_light = colors.HexColor('#F7FAFC')     # Off White
    c_border = colors.HexColor('#E2E8F0')    # Light Gray
    c_code_bg = colors.HexColor('#EDF2F7')   # Code Box

    title_style = ParagraphStyle(
        'CoverTitle', parent=styles['Heading1'],
        fontName='Helvetica-Bold', fontSize=20, leading=24,
        textColor=c_primary, spaceAfter=5
    )

    subtitle_style = ParagraphStyle(
        'CoverSubtitle', parent=styles['Normal'],
        fontName='Helvetica', fontSize=10.5, leading=14,
        textColor=c_secondary, spaceAfter=10
    )

    h1_style = ParagraphStyle(
        'CustomH1', parent=styles['Heading1'],
        fontName='Helvetica-Bold', fontSize=13, leading=17,
        textColor=c_primary, spaceBefore=11, spaceAfter=4, keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'CustomH2', parent=styles['Heading2'],
        fontName='Helvetica-Bold', fontSize=10.5, leading=14,
        textColor=c_secondary, spaceBefore=7, spaceAfter=3, keepWithNext=True
    )

    body_style = ParagraphStyle(
        'CustomBody', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8.5, leading=12,
        textColor=c_dark, spaceAfter=4
    )

    body_bold = ParagraphStyle('CustomBodyBold', parent=body_style, fontName='Helvetica-Bold')

    bullet_style = ParagraphStyle(
        'CustomBullet', parent=body_style,
        leftIndent=12, firstLineIndent=-8, spaceAfter=2
    )

    formula_style = ParagraphStyle(
        'FormulaText', parent=styles['Normal'],
        fontName='Courier-Bold', fontSize=8, leading=11,
        textColor=colors.HexColor('#742A2A'), spaceAfter=2
    )

    code_style = ParagraphStyle(
        'CodeSnippet', parent=styles['Normal'],
        fontName='Courier', fontSize=7.5, leading=10,
        textColor=colors.HexColor('#2C5282'), spaceAfter=2
    )

    qa_q_style = ParagraphStyle(
        'QAQuestion', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=9, leading=12.5,
        textColor=c_primary, spaceBefore=6, spaceAfter=2, keepWithNext=True
    )

    qa_a_style = ParagraphStyle(
        'QAAnswer', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8.5, leading=11.5,
        textColor=c_dark, spaceAfter=5
    )

    story = []

    # -------------------------------------------------------------------------
    # COVER / HEADER BLOCK
    # -------------------------------------------------------------------------
    story.append(Spacer(1, 4))
    story.append(Paragraph('DSC306 DATA MINING — PROJECT 5 TECHNICAL REPORT & VIVA GUIDE', title_style))
    story.append(Paragraph('Applicant Shortlisting Console with Fairness Audit | Stages A through G Comprehensive Defense', subtitle_style))
    story.append(HRFlowable(width='100%', thickness=2, color=c_primary, spaceBefore=0, spaceAfter=8))

    meta_table_data = [
        [Paragraph('<b>Course:</b> DSC306 Data Mining (Lectures 1–14)', body_style),
         Paragraph('<b>Project:</b> Project 5 — Applicant Shortlisting Console', body_style)],
        [Paragraph('<b>Dataset:</b> Kaggle HR Analytics (19,158 records, 14 attributes)', body_style),
         Paragraph('<b>Model Families:</b> Tree-Based (DT), Bayesian (NB), Instance (KNN)', body_style)],
        [Paragraph('<b>Evaluation:</b> Majority Baseline (75.1%) beside every accuracy', body_style),
         Paragraph('<b>Auditing Standards:</b> US EEOC 80% Rule, Selection Rate, Recall, Precision', body_style)],
    ]
    meta_table = Table(meta_table_data, colWidths=[270, 270])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_code_bg),
        ('BOX', (0,0), (-1,-1), 1, c_border),
        ('INNERGRID', (0,0), (-1,-1), 0.5, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 6))

    # -------------------------------------------------------------------------
    # STAGE A: DATA AND DOCUMENTATION
    # -------------------------------------------------------------------------
    story.append(Paragraph('Stage A — Data and Documentation', h1_style))
    story.append(HRFlowable(width='100%', thickness=0.8, color=c_secondary, spaceBefore=1, spaceAfter=5))
    story.append(Paragraph(
        '<b>Dataset Criteria Fulfillment:</b> The project utilizes the real Kaggle <i>HR Analytics: Job Change of Data Scientists</i> dataset containing <b>19,158 real applicant records</b> and <b>14 raw attributes</b> (exceeding the >= 2,000 records and >= 10 attributes requirement).',
        body_style
    ))
    story.append(Paragraph('<b>Four Measurement Types Present (Lecture 2):</b>', h2_style))
    story.append(Paragraph('• <b>Nominal:</b> <code>gender</code>, <code>enrolled_university</code>, <code>major_discipline</code>, <code>company_type</code> (categorical identifiers with no natural ordering).', bullet_style))
    story.append(Paragraph('• <b>Ordinal:</b> <code>education_level</code> (Primary < High School < Graduate < Masters < Phd), <code>experience</code>, <code>company_size</code>, <code>last_new_job</code> (natural hierarchy).', bullet_style))
    story.append(Paragraph('• <b>Ratio:</b> <code>training_hours</code> (numeric with an absolute, non-arbitrary zero point at 0 hours; ratio comparisons like 100 hours is twice 50 hours are meaningful).', bullet_style))
    story.append(Paragraph('• <b>Interval:</b> <code>city_development_index</code> (continuous economic prosperity scale where intervals are equal).', bullet_style))

    story.append(Paragraph('<b>Written Statement of Excluded Columns (Mandatory Rubric Component):</b>', h2_style))
    story.append(Paragraph(
        '1. <b><code>enrollee_id</code>:</b> An arbitrary primary key generated by the administrative applicant tracking database (19,158 unique IDs). It carries zero generalisable semantic signal. Including it in predictive modeling causes severe identity memorization, overfitting, and leakage. Strictly excluded from the feature space and retained only as an audit case index.<br/>'
        '2. <b><code>target</code>:</b> Ground-truth hiring outcome (Proceed to interview). At the exact moment the recruiter runs shortlisting on incoming applications, this future outcome is completely unknown. Training on it as an input would constitute catastrophic target leakage. Exclusively reserved as the training target and test evaluation label.',
        body_style
    ))

    # -------------------------------------------------------------------------
    # STAGE B: DATA QUALITY AUDIT AND REPAIR (LECTURES 2–3)
    # -------------------------------------------------------------------------
    story.append(Spacer(1, 4))
    story.append(Paragraph('Stage B — Data Quality Audit and Repair (Lectures 2–3)', h1_style))
    story.append(HRFlowable(width='100%', thickness=0.8, color=c_secondary, spaceBefore=1, spaceAfter=5))
    story.append(Paragraph(
        '<b>Six Distinct Fault Categories Detected (Lecture 2 Vocabulary):</b><br/>'
        '• <b>1. Incompleteness (Missing Values):</b> Detected in <code>gender</code> (4,508 records), <code>company_size</code> (5,938), <code>company_type</code> (6,140), <code>major_discipline</code> (2,813), <code>education_level</code> (460). Expression: <code>row[col] in [None, \'\', \'nan\', \'NaN\']</code>. Remediated via explicit <code>\'Unknown\'</code> category and median numeric imputation.<br/>'
        '• <b>2. Syntactic Inconsistency (Boundary String Encodings):</b> Detected in <code>experience</code> with raw string bounds <code>\'&lt;1\'</code> (522 records) and <code>\'&gt;20\'</code> (3,286 records). Expression: <code>row[\'experience\'] in [\'&lt;1\', \'&gt;20\']</code>. Remediated by mapping &lt;1 to 0 and &gt;20 to 21 years numeric.<br/>'
        '• <b>3. Outliers & Extreme Values:</b> Detected in <code>training_hours</code> exceeding Tukey upper fence $Q_3 + 1.5 \\times IQR$ (&gt; 185 hours, 984 records). Remediated via continuous scaling.<br/>'
        '• <b>4. Arbitrary Identifier / Leakage Risk:</b> Detected in <code>enrollee_id</code> (19,158 unique keys). Expression: <code>len(set(ids)) == len(records)</code>. Remediated by strictly excluding from model inputs.<br/>'
        '• <b>5. Delimiter Formatting Contamination:</b> Detected in <code>company_size</code> containing slash delimiters like <code>\'10/49\'</code> (1,471 records). Expression: <code>\'/\' in str(row[\'company_size\'])</code>. Remediated by standardizing to hyphenated range <code>\'10-49\'</code>.<br/>'
        '• <b>6. Categorical Redundancy & Null Conflict:</b> Detected in <code>enrolled_university</code> where degree holders had missing enrollment records (386 records). Remediated by composite tier mapping.',
        body_style
    ))

    story.append(Paragraph('<b>Provenance Tracking & Before-and-After Numeric Repair Table:</b>', h2_style))
    ba_table_data = [
        [Paragraph('<b>Field</b>', body_bold), Paragraph('<b>Fault Category</b>', body_bold), Paragraph('<b>Detection Expression</b>', body_bold), Paragraph('<b>Before</b>', body_bold), Paragraph('<b>After</b>', body_bold), Paragraph('<b>Provenance Column & Action</b>', body_bold)],
        [Paragraph('gender', code_style), Paragraph('Missing Values', body_style), Paragraph("val in ['', None, 'nan']", code_style), Paragraph('4,508', body_style), Paragraph('0', body_style), Paragraph("_prov_gender ('imputed_unknown')", body_style)],
        [Paragraph('experience', code_style), Paragraph('Boundary Strings', body_style), Paragraph("val in ['<1', '>20']", code_style), Paragraph('3,808', body_style), Paragraph('0', body_style), Paragraph("_prov_experience ('mapped_boundary')", body_style)],
        [Paragraph('company_size', code_style), Paragraph('Slash Contamination', body_style), Paragraph("'/' in str(val)", code_style), Paragraph('1,471', body_style), Paragraph('0', body_style), Paragraph("_prov_company_size ('fixed_slash_format')", body_style)],
        [Paragraph('company_size', code_style), Paragraph('Missing Values', body_style), Paragraph("val in ['', None, 'nan']", code_style), Paragraph('5,938', body_style), Paragraph('0', body_style), Paragraph("_prov_company_size ('imputed_unknown')", body_style)],
        [Paragraph('enrollee_id', code_style), Paragraph('Identifier Leakage', body_style), Paragraph("len(set(ids))==len(data)", code_style), Paragraph('19,158', body_style), Paragraph('0', body_style), Paragraph("Strictly excluded from feature matrix X", body_style)],
    ]
    t_ba = Table(ba_table_data, colWidths=[65, 95, 125, 45, 45, 165])
    t_ba.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_light]),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
    ]))
    story.append(t_ba)
    story.append(Spacer(1, 3))

    story.append(Paragraph('<b>The 10-Assertion validate() Engine:</b>', h2_style))
    story.append(Paragraph(
        'Implemented in <code>backend/data_manager.py:validate()</code>. Executes 10 integrity assertions across missing values, range boundaries, string standardizations, proxy derivations, and provenance columns. <b>Result: Passes 100% (10/10 green checkmarks) on cleaned data, and fails on raw data</b> (failing assertions 1, 2, 3, 6, 7, 8, 10).',
        body_style
    ))

    # -------------------------------------------------------------------------
    # STAGE C: PRE-PROCESSING (LECTURES 3–4)
    # -------------------------------------------------------------------------
    story.append(PageBreak())
    story.append(Paragraph('Stage C — Pre-Processing (Lectures 3–4)', h1_style))
    story.append(HRFlowable(width='100%', thickness=0.8, color=c_secondary, spaceBefore=1, spaceAfter=5))

    story.append(Paragraph('<b>1. Stated & Justified Attribute Rescaling Decision per Model Family:</b>', h2_style))
    story.append(Paragraph('• <b>Decision Tree:</b> Rescaling is <b>NOT needed</b>. Tree split selection uses greedy impurity reduction $\\Delta \\text{Gini}(S, \\theta)$ which depends solely on feature rank ordering and is invariant to monotonic transformations.', bullet_style))
    story.append(Paragraph('• <b>Naïve Bayes:</b> Continuous variables are modeled using univariate Gaussian distributions $\\mathcal{N}(\\mu_c, \\sigma_c^2)$ where variance is estimated independently per class; scaling does not distort relative likelihoods.', bullet_style))
    story.append(Paragraph('• <b>k-Nearest Neighbours (KNN):</b> Rescaling is <b>STRICTLY REQUIRED</b>. KNN computes Euclidean distance $d(x, q) = \\sqrt{\\sum (x_j - q_j)^2}$. Without standard scaling, <code>training_hours</code> (range 1-336) would completely dominate <code>city_development_index</code> (range 0.40-0.95) by orders of magnitude.', bullet_style))

    story.append(Spacer(1, 3))
    story.append(Paragraph('<b>2. Dimensionality Reduction (PCA) vs. Feature Subset Selection:</b>', h2_style))
    story.append(Paragraph(
        'Both techniques were evaluated on the exact same model (Decision Tree) and the exact same 80/20 test set to establish an empirical comparison:',
        body_style
    ))
    dim_table_data = [
        [Paragraph('<b>Technique</b>', body_bold), Paragraph('<b>Input Dims</b>', body_bold), Paragraph('<b>Accuracy</b>', body_bold), Paragraph('<b>Majority Baseline</b>', body_bold), Paragraph('<b>ROC-AUC</b>', body_bold), Paragraph('<b>Recruiter Interpretability Rating</b>', body_bold)],
        [Paragraph('All Features (Baseline)', body_style), Paragraph('48 Dims', body_style), Paragraph('79.1%', body_style), Paragraph('75.1%', body_style), Paragraph('0.791', body_style), Paragraph('High: Full feature vocabulary preserved', body_style)],
        [Paragraph('Feature Subset Selection', body_style), Paragraph('10 Dims', body_style), Paragraph('78.1%', body_style), Paragraph('75.1%', body_style), Paragraph('0.745', body_style), Paragraph('Very High: Retains top 10 original features; recommended', body_style)],
        [Paragraph('PCA Dimensionality Reduction', body_style), Paragraph('10 Dims', body_style), Paragraph('76.3%', body_style), Paragraph('75.1%', body_style), Paragraph('0.681', body_style), Paragraph('Low: Orthogonal eigenvectors destroy feature names; not recommended', body_style)],
    ]
    t_dim = Table(dim_table_data, colWidths=[130, 60, 60, 80, 55, 155])
    t_dim.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_light]),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
    ]))
    story.append(t_dim)
    story.append(Spacer(1, 3))

    story.append(Paragraph('<b>3. Discretization & Binarization Justification:</b>', h2_style))
    story.append(Paragraph('• <b>Experience into 4 Age Bands:</b> Binned into <code>0-5</code> (Entry), <code>6-10</code> (Early-Mid), <code>11-15</code> (Mid-Senior), and <code>16+</code> (Veteran) to construct an auditable proxy for candidate age without using volatile single-year categories.', bullet_style))
    story.append(Paragraph('• <b>City Development Index into 3 Tiers:</b> Binned into Low (<0.65), Medium (0.65-0.85), and High (>0.85) for regional parity analysis.', bullet_style))

    # -------------------------------------------------------------------------
    # STAGE D & E: MODELS & EVALUATION (LECTURES 5–14)
    # -------------------------------------------------------------------------
    story.append(Spacer(1, 4))
    story.append(Paragraph('Stage D & E — Models & Rigorous Evaluation (Lectures 5–14)', h1_style))
    story.append(HRFlowable(width='100%', thickness=0.8, color=c_secondary, spaceBefore=1, spaceAfter=5))

    story.append(Paragraph('<b>Multi-Model Family Benchmarking (Exact Same 80/20 Test Set):</b>', h2_style))
    story.append(Paragraph(
        'The majority-class baseline is <b>75.07%</b> (ZeroR classifier predicting all 0s). An accuracy quoted alone earns no marks under DSC306 rules. Below is the multi-model comparison table reported beside the baseline:',
        body_style
    ))

    model_eval_data = [
        [Paragraph('<b>Model Classifier</b>', body_bold), Paragraph('<b>Model Family</b>', body_bold), Paragraph('<b>Accuracy & Baseline Beside</b>', body_bold), Paragraph('<b>Precision</b>', body_bold), Paragraph('<b>Recall</b>', body_bold), Paragraph('<b>F1</b>', body_bold), Paragraph('<b>AUC</b>', body_bold), Paragraph('<b>5-Fold CV Spread</b>', body_bold)],
        [Paragraph('Decision Tree', body_bold), Paragraph('Tree-Based', body_style), Paragraph('<b>79.1%</b> (Base: 75.1%, <font color="#276749"><b>+4.0%</b></font>)', body_style), Paragraph('59.2%', body_style), Paragraph('51.6%', body_style), Paragraph('55.2%', body_style), Paragraph('0.791', body_style), Paragraph('78.2% ± 0.8%', body_style)],
        [Paragraph('Naïve Bayes', body_bold), Paragraph('Bayesian / Probabilistic', body_style), Paragraph('<b>68.7%</b> (Base: 75.1%, <font color="#9B2C2C"><b>-6.4%</b></font>)', body_style), Paragraph('41.4%', body_style), Paragraph('61.7%', body_style), Paragraph('49.6%', body_style), Paragraph('0.691', body_style), Paragraph('68.8% ± 0.8%', body_style)],
        [Paragraph('k-Nearest Neighbours', body_bold), Paragraph('Instance-Based', body_style), Paragraph('<b>74.9%</b> (Base: 75.1%, <font color="#9B2C2C"><b>-0.2%</b></font>)', body_style), Paragraph('49.5%', body_style), Paragraph('37.0%', body_style), Paragraph('42.3%', body_style), Paragraph('0.717', body_style), Paragraph('74.9% ± 0.4%', body_style)],
        [Paragraph('Logistic Regression', body_bold), Paragraph('Linear Benchmark', body_style), Paragraph('<b>76.8%</b> (Base: 75.1%, <font color="#276749"><b>+1.7%</b></font>)', body_style), Paragraph('57.4%', body_style), Paragraph('26.5%', body_style), Paragraph('36.2%', body_style), Paragraph('0.782', body_style), Paragraph('76.9% ± 0.3%', body_style)],
    ]
    t_eval = Table(model_eval_data, colWidths=[80, 80, 135, 45, 40, 40, 40, 80])
    t_eval.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_light]),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
    ]))
    story.append(t_eval)
    story.append(Spacer(1, 3))

    story.append(Paragraph('<b>Written Reason Why Precision and Recall Suit This User (Stage E):</b>', h2_style))
    story.append(Paragraph('• <b>Precision (Positive Predictive Value):</b> Recruiter interview capacity is limited. False positives waste hundreds of expensive interviewer hours screening unqualified candidates. High precision directly protects company interview bandwidth.', bullet_style))
    story.append(Paragraph('• <b>Recall (True Positive Rate / Sensitivity):</b> The opportunity cost of a false negative is severe: missing a qualified data scientist who will be hired by a competitor. High recall ensures top talent is never discarded.', bullet_style))

    story.append(Paragraph('<b>Financial Cost Matrix Analysis & Optimal Operating Threshold (θ*):</b>', h2_style))
    story.append(Paragraph('Theoretical Cost Formulation: $\\mathbb{E}[\\text{Cost}(\\theta)] = FP(\\theta) \\cdot C_{FP} + FN(\\theta) \\cdot C_{FN} - TP(\\theta) \\cdot B_{TP} + TN(\\theta) \\cdot C_{TN}$.<br/>With parameters: Cost FP = $500 (wasted interview), Cost FN = $3,500 (missed talent), Benefit TP = $5,000 (successful hire), Cost TN = $0.<br/><b>Result:</b> Rather than leaving the threshold at an arbitrary 0.50, our Cost Matrix evaluates financial outcomes across $\\theta \\in [0.05, 0.95]$ and selects the <b>Cost-Optimal Operating Threshold $\\theta^* = 0.06$ to $0.38$</b> (minimizing total hiring expenditure).', body_style))

    # -------------------------------------------------------------------------
    # STAGE F & G: EXPLANATION & SIX APPLICATION SCREENS
    # -------------------------------------------------------------------------
    story.append(PageBreak())
    story.append(Paragraph('Stage F & G — Explanation & Six Application Screens', h1_style))
    story.append(HRFlowable(width='100%', thickness=0.8, color=c_secondary, spaceBefore=1, spaceAfter=5))

    story.append(Paragraph('<b>Stage F — User-Language Explanations:</b>', h2_style))
    story.append(Paragraph(
        'Every prediction provides its reason written strictly in the recruiter\'s vocabulary, not the model\'s:<br/>'
        '• <b>Decision Path Rule:</b> <i>\'City Development Index is High (&gt; 0.85) AND Experience &gt;= 10 years AND Education is Masters degree\'</i> (rather than <i>\'node 14, gini 0.31\'</i>).<br/>'
        '• <b>Local Attribution Breakdown:</b> Features mean-centered $\\Delta \\phi_j = \\beta_j(x_{ij} - \\bar{x}_j)$ to ensure candidates receive individualized, distinct hiring criteria rather than identical generic lists.',
        body_style
    ))

    story.append(Paragraph('<b>Stage G — The Six Master Screens (Rubric Architecture):</b>', h2_style))
    screen_desc_table = [
        [Paragraph('<b>Screen</b>', body_bold), Paragraph('<b>Screen Name</b>', body_bold), Paragraph('<b>What It Does (Exact Rubric Requirements)</b>', body_bold)],
        [Paragraph('Screen 1', code_style), Paragraph('Data & Quality', body_style), Paragraph('Loads dataset (19,158 rows), audits 6 fault categories, displays Before/After table, executes 10-point validate() engine, provides Data Dictionary and download link for cleaned file with provenance.', body_style)],
        [Paragraph('Screen 2', code_style), Paragraph('Model Performance', body_style), Paragraph('Comparison table across Decision Tree, Naïve Bayes, and KNN with majority baseline beside every accuracy figure, ROC curves, confusion matrix, PCA vs feature selection comparison, and 5-fold CV spread.', body_style)],
        [Paragraph('Screen 3', code_style), Paragraph('Single Prediction', body_style), Paragraph('Interactive profile form for one candidate $\\rightarrow$ prediction verdict (PROCEED TO INTERVIEW vs HOLD), confidence percentage (e.g. 78.4%), and user-language decision path explanation.', body_style)],
        [Paragraph('Screen 4', code_style), Paragraph('Batch Scoring', body_style), Paragraph('Scores applicant pool in bulk $\\rightarrow$ ranked shortlist table with interactive probability slider, top-N quota cutoff, inline candidate criteria breakdown drawer, and CSV shortlist export.', body_style)],
        [Paragraph('Screen 5', code_style), Paragraph('Settings', body_style), Paragraph('Choose active classifier, move decision threshold slider (0.05 - 0.95), edit financial cost matrix ($C_{FP}, C_{FN}, B_{TP}$), and observe consequences update live on the Expected Cost curve.', body_style)],
        [Paragraph('Screen 6', code_style), Paragraph('Domain Screen:<br/>Fairness Audit', body_style), Paragraph('<b>Project 5 Technical Challenge:</b> Audits selection rate, recall, and precision across Gender, Age Band, and Institution. Detects EEOC 80% rule violations in RED (&lt;0.80), flags small groups ($N&lt;30$), identifies disparity drivers ($\\beta \\times \\Delta\\bar{x}$), and runs Feature Ablation Remediation.', body_style)],
    ]
    t_screens = Table(screen_desc_table, colWidths=[55, 120, 365])
    t_screens.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_light]),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
    ]))
    story.append(t_screens)

    # -------------------------------------------------------------------------
    # SECTION 8: 40 MASTER VIVA VOCE QUESTIONS & DEFENSIVE ANSWERS
    # -------------------------------------------------------------------------
    story.append(PageBreak())
    story.append(Paragraph('Master Viva Voce Questions & Definitive Answers (40 Questions)', h1_style))
    story.append(HRFlowable(width='100%', thickness=0.8, color=c_secondary, spaceBefore=1, spaceAfter=5))

    viva_qa = [
        ('Q1. What is the fundamental data mining problem formulated in this project?',
         'It is formulated as a Supervised Binary Classification task. The goal is to learn a mapping function f: X -> {0, 1} from applicant credentials X to predict whether a candidate should proceed to interview (y=1) or be held/rejected (y=0).'),

        ('Q2. Why is enrollee_id strictly excluded from the predictive feature space?',
         'enrollee_id is an arbitrary administrative primary key with 19,158 unique integer values. It possesses zero semantic generalizability. If included, tree or distance models will memorize individual candidates, resulting in severe target leakage and overfitting.'),

        ('Q3. Why is target excluded from the explanatory attributes?',
         'target represents the ground-truth hiring outcome (job transition). When a recruiter screens an incoming applicant pool, this future outcome is completely unknown. Using it as an input predictor would constitute catastrophic target leakage.'),

        ('Q4. What are the four measurement types in our dataset and why does each matter?',
         'Nominal (gender, university): unordered labels requiring one-hot encoding. Ordinal (education, experience): ranked hierarchy allowing directional splits. Ratio (training_hours): has an absolute zero point at 0 hours, validating ratio comparisons. Interval (city_development_index): continuous scaled interval where differences between values are uniform.'),

        ('Q5. Name the six fault categories audited in Stage B using Lecture 2 vocabulary.',
         '1. Incompleteness (missing categories in gender, company size). 2. Syntactic Inconsistency (boundary strings <1 and >20). 3. Outliers & Extreme Values (training hours > 185). 4. Arbitrary Identifier Leakage (enrollee_id). 5. Delimiter Formatting Contamination (slash notation 10/49 in company size). 6. Categorical Redundancy & Null Conflict (missing enrollment with valid degree).'),

        ('Q6. How does the 10-point validate() function prove data cleanliness?',
         'validate() tests 10 invariant assertions covering null values, valid intervals [0, 1], positive ratios, string boundary removal, slash normalization, proxy derivations, and provenance presence. It passes 100% on cleaned data and fails immediately on raw data.'),

        ('Q7. What is provenance tracking and why is it necessary in data engineering?',
         'Provenance records the origin and transformation history of each data cell. We create dedicated columns like _prov_gender and _prov_experience so auditors can verify whether a field is raw observed, imputed with unknown, or mapped from a boundary string.'),

        ('Q8. Explain our attribute rescaling decisions for Decision Tree, Naïve Bayes, and KNN.',
         'Decision Tree does not require rescaling because split selection depends solely on monotonic rank order. Naïve Bayes normalizes feature variance per class. KNN strictly requires standard scaling; otherwise Euclidean distance is overwhelmed by training_hours (1-336) over city index (0.4-0.95).'),

        ('Q9. What happened when we compared Feature Subset Selection against PCA on the same model?',
         'On the Decision Tree, Feature Selection (top 10 features) achieved 78.1% accuracy and 0.745 AUC while preserving full feature names and interpretability. PCA achieved 76.3% accuracy and 0.681 AUC, but its orthogonal linear combinations destroyed domain feature names, making recruiter-facing explanations impossible.'),

        ('Q10. Why did we choose Decision Tree, Naïve Bayes, and KNN as our three model families?',
         'They represent three fundamentally distinct paradigms: Tree-based (hierarchical recursive partitioning and transparent rule paths), Bayesian/Probabilistic (class priors and Gaussian likelihoods), and Instance-based (lazy learning using distance to prototype cases).'),

        ('Q11. Why did we use an 80/20 Stratified Split instead of simple random sampling?',
         'Target class distribution is imbalanced (~24.9% positive). Simple random sampling risks assigning disproportionately more positive candidates to one partition. Stratification preserves the exact 24.9% ratio across both train (15,326) and test (3,832) sets.'),

        ('Q12. What is the majority-class baseline and why must it be reported beside every accuracy?',
         'The majority class is negative (75.07%). A naive ZeroR classifier predicting all 0s achieves 75.07% accuracy with zero predictive intelligence. Quoting accuracy alone is meaningless without reporting the baseline and the positive delta earned over it.'),

        ('Q13. Why do Precision and Recall suit this recruiter better than raw accuracy?',
         'Precision protects limited recruiter interview hours by eliminating false-positive candidates. Recall guarantees that top talent is not falsely rejected and lost to rival firms. Balancing both optimizes hiring efficiency.'),

        ('Q14. How is the ROC Curve generated and how is AUC computed?',
         'The ROC curve plots True Positive Rate (Recall) vs False Positive Rate across all decision cutoffs theta in [0, 1]. Area Under the Curve (ROC-AUC) evaluates ranking discrimination independent of cutoff, computed via numerical trapezoidal integration.'),

        ('Q15. Explain how the Cost Matrix determines the optimal threshold theta*.',
         'Expected financial cost is: E[Cost] = FP * 500 + FN * 3500 - TP * 5000 + TN * 0. We evaluate expected cost across thresholds [0.05, 0.95] and pick the cutoff theta* that minimizes financial loss, rather than defaulting to arbitrary 0.50.'),

        ('Q16. What is the spread in 5-fold cross-validation and why is reporting the mean alone insufficient?',
         'Mean accuracy alone obscures fold instability. Reporting spread (mean +- std dev, min, max) proves that performance is consistent and generalisable across different validation slices (e.g. Decision Tree: 78.24% +- 0.77%).'),

        ('Q17. How does our single prediction engine generate user-language explanations?',
         'It extracts the tree decision path and translates node conditions into recruiter English: "City Development Index is High (>0.85) AND Experience >= 10 years AND Education is Masters degree", avoiding cryptic engine jargon like "node 14, gini 0.31".'),

        ('Q18. What is Demographic Parity (Statistical Parity)?',
         'Demographic Parity requires equal selection rates across protected demographic groups: P(Y_hat = 1 | A = g_a) = P(Y_hat = 1 | A = g_b), regardless of ground-truth qualification labels.'),

        ('Q19. What is Equal Opportunity in algorithmic fairness?',
         'Equal Opportunity requires that qualified applicants (ground truth Y = 1) have an equal probability of being shortlisted across groups: P(Y_hat = 1 | Y = 1, A = g_a) = P(Y_hat = 1 | Y = 1, A = g_b). Measured as Group Recall.'),

        ('Q20. What is Predictive Parity?',
         'Predictive Parity requires that shortlisted candidates have identical positive predictive value across groups: P(Y = 1 | Y_hat = 1, A = g_a) = P(Y = 1 | Y_hat = 1, A = g_b). Measured as Group Precision.'),

        ('Q21. Explain the US EEOC 80% (Four-Fifths) Adverse Impact Rule.',
         'Under US Uniform Guidelines, a selection rate for any demographic group that is less than 80% of the rate for the highest-selected group constitutes prima facie evidence of adverse impact. Our audit flags any ratio < 0.80 with a prominent red badge.'),

        ('Q22. Why do we flag protected groups with sample size N < 30 as statistically unreliable?',
         'By the Central Limit Theorem, sample sizes under 30 suffer from high sampling variance. A single hiring decision in a group of 8 swings the selection rate by 12.5%. The warning alerts recruiters against making legal or bias claims on volatile small cohorts.'),

        ('Q23. What is a Disparity Driver and how is it mathematically calculated?',
         'A disparity driver is a feature responsible for the demographic acceptance gap between favored and disadvantaged groups. Calculated as: Driver Impact_j = beta_j * (mean(x_fav, j) - mean(x_dis, j)). Multiplies model sensitivity by group mean difference.'),

        ('Q24. What happens during Feature Ablation Remediation?',
         'We ablate the offending driver feature from the feature matrix, retrain the model on the exact same fixed split, and evaluate the Before vs After tradeoff in Selection Rate Gap vs ROC-AUC.'),

        ('Q25. What is the Fairness-Accuracy Tradeoff?',
         'Models trained to maximize accuracy exploit historical correlations. Debiasing models (via ablation or threshold shifts) often slightly reduces predictive AUC in exchange for substantial reductions in demographic disparity.'),

        ('Q26. How do we prevent proxy discrimination if protected traits are omitted?',
         'Screen 1 & 2 compute the Pearson correlation matrix between all non-protected features and protected attributes (gender, age, institution) to surface hidden proxy collinearity before training.'),

        ('Q27. Why did we build a transparent pure-Python ML engine alongside scikit-learn?',
         'In secure enterprise or Windows environments with User Mode Code Integrity (UMCI / Smart App Control), compiled C-extensions are blocked. Pure-Python guarantees 100% auditability and zero-dependency execution anywhere.'),

        ('Q28. What happens if a recruiter sets the decision threshold to 0.10?',
         'Selection rate and recall surge toward 90%+. The acceptance gap narrows because nearly everyone is accepted, but recruiter screening efficiency collapses as interview volume explodes with false positives.'),

        ('Q29. What happens if a recruiter sets the threshold to 0.90?',
         'Selection rates plunge toward 0-5%. Disparate impact spikes because even slight credential differences cause disadvantaged groups to fall below the severe cutoff.'),

        ('Q30. Explain the dual-panel layout on Screen 4 and Screen 6.',
         'Places the Ranked Shortlist on the left and the Live Fairness Audit on the right, enabling recruiters to witness the real-time demographic impact of their threshold adjustments instantly.'),

        ('Q31. How are candidates ranked on Screen 4?',
         'Candidates are ranked descending by predicted probability P(interview | x). Recruiters can apply a probability cutoff or a Top-N quota.'),

        ('Q32. What is Gini Impurity in decision trees?',
         'Gini Impurity measures misclassification probability: Gini(S) = 1 - sum(p_k^2). Gini gain evaluates impurity reduction across left and right split partitions.'),

        ('Q33. What is L2 Regularization in Logistic Regression?',
         'L2 penalty (lambda / 2N) * ||w||_2^2 constrains weight magnitudes on collinear dummy features, preventing overfitting and stabilizing explainability weights.'),

        ('Q34. Why do we export shortlists to CSV?',
         'For seamless handoff into enterprise Applicant Tracking Systems (ATS) like Workday or Greenhouse, containing candidate ID, rank, score, and top selection drivers.'),

        ('Q35. How does the executive hiring narrative get generated?',
         'The engine translates top drivers and inhibitors into human-readable labels and synthesizes a plain-language summary of candidate qualifications.'),

        ('Q36. How is Age Band derived as a proxy?',
         'Chronological age is rarely available in job applicant pools. Experience years strongly correlates with career age and is discretized into 4 non-overlapping seniority bands.'),

        ('Q37. How is Institution Tier derived as a proxy?',
         'Composite mapping combining education level and university enrollment status into 3 prestige tiers (Postgraduate, Graduate, Non-Degree/School).'),

        ('Q38. Why is the Fairness Audit computed exclusively on the held-out test set?',
         'Auditing the training set measures memorized bias. Auditing the 3,832 held-out test candidates guarantees an unbiased evaluation of operational performance on unseen applicants.'),

        ('Q39. Can a marker start this project with one command without installing external servers?',
         'Yes. The application runs immediately with `python app.py` on http://127.0.0.1:5000 with zero path edits, zero database setup, and shipped data.'),

        ('Q40. In one sentence, what is the ultimate achievement of this project?',
         'It delivers an end-to-end, mathematically rigorous recruitment shortlisting console with transparent multi-model benchmarking, user-language explainability, and an actionable regulatory fairness audit.')
    ]

    for q_text, a_text in viva_qa:
        story.append(Paragraph(q_text, qa_q_style))
        story.append(Paragraph(a_text, qa_a_style))

    # -------------------------------------------------------------------------
    # BUILD DOCUMENT
    # -------------------------------------------------------------------------
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f'[SUCCESS] Generated complete Viva Voce Guide PDF: {filename}')

if __name__ == '__main__':
    build_pdf()
