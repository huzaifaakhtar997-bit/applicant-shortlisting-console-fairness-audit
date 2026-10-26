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
            self.setFont('Helvetica-Bold', 8)
            self.setFillColor(colors.HexColor('#1A365D'))
            self.drawString(40, letter[1] - 30, 'PROJECT 5: APPLICANT SHORTLISTING CONSOLE WITH FAIRNESS AUDIT')
            
            self.setFont('Helvetica', 8)
            self.setFillColor(colors.HexColor('#718096'))
            self.drawRightString(letter[0] - 40, letter[1] - 30, 'COMPREHENSIVE VIVA VOCE & TECHNICAL REPORT')
            
            self.setStrokeColor(colors.HexColor('#CBD5E0'))
            self.setLineWidth(0.6)
            self.line(40, letter[1] - 34, letter[0] - 40, letter[1] - 34)

            self.line(40, 36, letter[0] - 40, 36)
            self.setFont('Helvetica', 8)
            self.setFillColor(colors.HexColor('#718096'))
            self.drawString(40, 24, 'Data Mining Lab | Comprehensive Viva Guide (Formulas, Code & Theory)')
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
    
    c_primary = colors.HexColor('#1A365D')
    c_secondary = colors.HexColor('#2B6CB0')
    c_accent = colors.HexColor('#C53030')
    c_dark = colors.HexColor('#2D3748')
    c_light = colors.HexColor('#F7FAFC')
    c_border = colors.HexColor('#E2E8F0')
    c_code_bg = colors.HexColor('#EDF2F7')

    title_style = ParagraphStyle(
        'CoverTitle', parent=styles['Heading1'],
        fontName='Helvetica-Bold', fontSize=22, leading=26,
        textColor=c_primary, spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'CoverSubtitle', parent=styles['Normal'],
        fontName='Helvetica', fontSize=11, leading=15,
        textColor=c_secondary, spaceAfter=12
    )

    h1_style = ParagraphStyle(
        'CustomH1', parent=styles['Heading1'],
        fontName='Helvetica-Bold', fontSize=14, leading=18,
        textColor=c_primary, spaceBefore=12, spaceAfter=5, keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'CustomH2', parent=styles['Heading2'],
        fontName='Helvetica-Bold', fontSize=11, leading=15,
        textColor=c_secondary, spaceBefore=8, spaceAfter=3, keepWithNext=True
    )

    body_style = ParagraphStyle(
        'CustomBody', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8.5, leading=12,
        textColor=c_dark, spaceAfter=5
    )

    body_bold = ParagraphStyle('CustomBodyBold', parent=body_style, fontName='Helvetica-Bold')

    bullet_style = ParagraphStyle(
        'CustomBullet', parent=body_style,
        leftIndent=12, firstLineIndent=-8, spaceAfter=2.5
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

    # Title & Metadata
    story.append(Spacer(1, 6))
    story.append(Paragraph('APPLICANT SHORTLISTING CONSOLE WITH FAIRNESS AUDIT', title_style))
    story.append(Paragraph('Comprehensive Viva Voce & Technical Architecture Report | Data Mining Laboratory Project 5', subtitle_style))
    story.append(HRFlowable(width='100%', thickness=2, color=c_primary, spaceBefore=0, spaceAfter=8))

    meta_table_data = [
        [Paragraph('<b>Domain:</b> Recruitment AI & Algorithmic Fairness', body_style),
         Paragraph('<b>Intended Audience:</b> Viva Voce Examiners & Engineers', body_style)],
        [Paragraph('<b>Core Models:</b> Logistic Regression & Random Forest', body_style),
         Paragraph('<b>Dataset:</b> Kaggle HR Analytics (19,158 real records)', body_style)],
        [Paragraph('<b>Compliance Standard:</b> US EEOC 80% (Four-Fifths) Adverse Impact Rule', body_style),
         Paragraph('<b>Fairness Metrics:</b> Selection Rate, Recall (Equal Opp.), Precision', body_style)],
    ]
    meta_table = Table(meta_table_data, colWidths=[270, 270])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_code_bg),
        ('BOX', (0,0), (-1,-1), 1, c_border),
        ('INNERGRID', (0,0), (-1,-1), 0.5, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 8))

    # Section 1: Executive Summary
    story.append(Paragraph('1. Executive Overview & Recruiter Problem Statement', h1_style))
    story.append(HRFlowable(width='100%', thickness=0.8, color=c_secondary, spaceBefore=1, spaceAfter=6))
    story.append(Paragraph(
        '<b>The Problem:</b> In high-volume hiring, recruiters screen hundreds of applicants for a handful of posts. Traditional shortlisting relies on unsophisticated boolean keyword matching and subjective human intuition (\'gut feeling\'). This approach fails fundamentally in three ways: it is extremely slow, decisions are erratic and inconsistent across reviewers, and organizations possess zero audit trail to demonstrate that selections were demographically fair and non-discriminatory.',
        body_style
    ))
    story.append(Paragraph(
        '<b>The Solution:</b> This project delivers an end-to-end recruitment intelligence system. The recruiter uploads an applicant pool and instantly receives a statistically ranked shortlist. Beside each candidate, the console details the exact criteria driving their ranking. Crucially, in a live side-by-side panel, the console runs an automatic <b>Fairness Audit</b> evaluating Selection Rate, Recall (Equal Opportunity), and Precision across <b>Gender</b>, <b>Age Band</b>, and <b>Institution Tier</b>. If disparate impact appears, the console identifies the underlying driver feature and enables instant <b>Feature Ablation Remediation</b>.',
        body_style
    ))

    # Section 2: Dataset & Protected Attributes
    story.append(Spacer(1, 4))
    story.append(Paragraph('2. Dataset Architecture & Derived Protected Attributes', h1_style))
    story.append(HRFlowable(width='100%', thickness=0.8, color=c_secondary, spaceBefore=1, spaceAfter=6))
    story.append(Paragraph(
        'The application utilizes the authentic Kaggle <i>HR Analytics: Job Change of Data Scientists</i> dataset (<b>19,158 applicant records</b>). The binary column <code>target</code> serves as the proxy label for <b>\'Proceed to Interview\' (1)</b> versus <b>\'Reject / Hold\' (0)</b>.',
        body_style
    ))
    
    dataset_table = [
        [Paragraph('<b>Feature Name</b>', body_bold), Paragraph('<b>Type</b>', body_bold), Paragraph('<b>Imputation & Preprocessing Rule</b>', body_bold), Paragraph('<b>Technical Role in Audit</b>', body_bold)],
        [Paragraph('city_development_index', code_style), Paragraph('Continuous', body_style), Paragraph('Median imputed; Standardized numerical scale', body_style), Paragraph('City economic prosperity index (Primary bias driver)', body_style)],
        [Paragraph('training_hours', code_style), Paragraph('Continuous', body_style), Paragraph('Median imputed; Continuous feature', body_style), Paragraph('Measures candidate technical commitment', body_style)],
        [Paragraph('gender', code_style), Paragraph('Categorical', body_style), Paragraph('Missing imputed as \'Unknown\'; One-hot encoded', body_style), Paragraph('<b>Protected Attribute 1</b> (Direct demographic)', body_style)],
        [Paragraph('experience', code_style), Paragraph('Ordinal/Text', body_style), Paragraph('Parsed to years; mapped to 4 Age Bands', body_style), Paragraph('<b>Protected Attribute 2 (Age Proxy)</b>', body_style)],
        [Paragraph('education_level + enrolled_university', code_style), Paragraph('Categorical', body_style), Paragraph('Composite rule into 3 Institutional Tiers', body_style), Paragraph('<b>Protected Attribute 3 (Institution Proxy)</b>', body_style)],
        [Paragraph('company_size, company_type, etc.', code_style), Paragraph('Categorical', body_style), Paragraph('Missing as \'Unknown\'; One-hot encoded', body_style), Paragraph('Contextual organizational credentials', body_style)],
    ]
    t_data = Table(dataset_table, colWidths=[120, 60, 180, 180])
    t_data.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_light]),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_data)
    story.append(Spacer(1, 4))
    story.append(Paragraph('<b>Proxy Derivations:</b> (1) <i>Age Band</i>: Derived from experience: 0-5 yrs (Entry), 6-10 yrs (Early-Mid), 11-15 yrs (Mid-Senior), 16+ yrs (Veteran). (2) <i>Institution</i>: Derived from education & university enrollment: Tier 1 Premier (Masters/PhD with no enrollment), Tier 2 Accredited (Graduate degrees or Part-time enrollment), Tier 3 Unenrolled/Other (High School or Full-time university enrollment).', body_style))
    story.append(Paragraph('<b>Splitting Protocol:</b> An <b>80/20 Stratified Split</b> with fixed seed <code>42</code> is enforced, yielding 15,326 train rows and 3,832 test rows with identical positive class prevalence (~24.9%).', body_style))

    # Section 3: Mathematical Formulations
    story.append(PageBreak())
    story.append(Paragraph('3. Complete Mathematical Formulations: Theory vs. Implemented Code', h1_style))
    story.append(HRFlowable(width='100%', thickness=0.8, color=c_secondary, spaceBefore=1, spaceAfter=6))
    story.append(Paragraph(
        'Every algorithm and metric is implemented with full mathematical fidelity. Below is the direct comparison between the theoretical formulations and the exact Python implementations in our codebase.',
        body_style
    ))

    # 3.1 Proxy Correlation
    story.append(Paragraph('3.1 Proxy Correlation Matrix (Pearson r)', h2_style))
    story.append(Paragraph('<b>Theoretical Formula:</b>', body_bold))
    story.append(Paragraph('r_{xy} = \\frac{\\sum_{i=1}^n (x_i - \\bar{x})(y_i - \\bar{y})}{\\sqrt{\\sum_{i=1}^n (x_i - \\bar{x})^2} \\sqrt{\\sum_{i=1}^n (y_i - \\bar{y})^2}} = \\frac{\\text{Cov}(X, Y)}{\\sigma_X \\sigma_Y}', formula_style))
    story.append(Paragraph('<b>Implemented Python Code (backend/data_manager.py):</b>', body_bold))
    story.append(Paragraph(
        'mean_x = sum(x) / n; mean_y = sum(y) / n<br/>'
        'cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))<br/>'
        'var_x = sum((xi - mean_x)**2 for xi in x); var_y = sum((yi - mean_y)**2 for yi in y)<br/>'
        'r = cov / (math.sqrt(var_x * var_y) + 1e-12)',
        code_style
    ))

    # 3.2 Logistic Regression
    story.append(Spacer(1, 3))
    story.append(Paragraph('3.2 Logistic Regression: Hypothesis, Sigmoid, Loss, & L2 Regularization', h2_style))
    story.append(Paragraph('<b>Theoretical Formulation:</b>', body_bold))
    story.append(Paragraph(
        'Linear Hypothesis: z = w^T x + b = \\sum_{j=1}^d w_j x_j + b<br/>'
        'Sigmoid Activation: \\sigma(z) = \\frac{1}{1 + e^{-z}} = P(Y=1|X=x)<br/>'
        'Binary Cross-Entropy Loss with L2 Penalty:<br/>'
        '\\mathcal{L}(w, b) = -\\frac{1}{N} \\sum_{i=1}^N \\left[ y_i \\ln(\\hat{y}_i) + (1-y_i)\\ln(1-\\hat{y}_i) \\right] + \\frac{\\lambda}{2N} \\|w\\|_2^2<br/>'
        'Gradient Updates: w_j \\leftarrow w_j - \\eta \\left( \\frac{1}{N}\\sum (\\hat{y}_i - y_i)x_{ij} + \\frac{\\lambda}{N}w_j \\right), \\quad b \\leftarrow b - \\eta \\left( \\frac{1}{N}\\sum (\\hat{y}_i - y_i) \\right)',
        formula_style
    ))
    story.append(Paragraph('<b>Implemented Python Code (backend/ml_engine.py):</b>', body_bold))
    story.append(Paragraph(
        'z = sum(w * x for w, x in zip(weights, row)) + bias<br/>'
        'prob = 1.0 / (1.0 + math.exp(-max(min(z, 25.0), -25.0)))  # Clipped against overflow<br/>'
        'error = prob - target<br/>'
        'grad_w = (1/N) * sum(error_i * x_ij) + (C_reg / N) * w_j<br/>'
        'weights[j] -= learning_rate * grad_w',
        code_style
    ))

    # 3.3 Random Forest
    story.append(Spacer(1, 3))
    story.append(Paragraph('3.3 Random Forest: Gini Impurity, Information Gain, & Ensemble Voting', h2_style))
    story.append(Paragraph('<b>Theoretical Formulation:</b>', body_bold))
    story.append(Paragraph(
        'Gini Impurity: Gini(S) = 1 - \\sum_{k=1}^C p_k^2 = 1 - (p_0^2 + p_1^2)<br/>'
        'Split Gini Gain: \\Delta Gini(S, \\theta) = Gini(S) - \\left( \\frac{|S_L|}{|S|} Gini(S_L) + \\frac{|S_R|}{|S|} Gini(S_R) \\right)<br/>'
        'Ensemble Probability: \\hat{P}(Y=1|x) = \\frac{1}{B} \\sum_{b=1}^B P_b(Y=1|x)',
        formula_style
    ))
    story.append(Paragraph('<b>Implemented Python Code (backend/ml_engine.py):</b>', body_bold))
    story.append(Paragraph(
        'p1 = count_ones / total_samples; p0 = 1.0 - p1<br/>'
        'gini = 1.0 - (p0**2 + p1**2)<br/>'
        'gain = parent_gini - (len(left)/N * gini_left + len(right)/N * gini_right)<br/>'
        'avg_prob = sum(tree.predict_prob(x) for tree in forest) / len(forest)',
        code_style
    ))

    # 3.4 Performance Metrics & ROC-AUC
    story.append(Spacer(1, 3))
    story.append(Paragraph('3.4 Performance Metrics & Trapezoidal ROC-AUC', h2_style))
    story.append(Paragraph('<b>Theoretical Formulations:</b>', body_bold))
    story.append(Paragraph(
        '\\text{Accuracy} = \\frac{TP + TN}{TP + TN + FP + FN}, \\quad \\text{Precision} = \\frac{TP}{TP + FP}, \\quad \\text{Recall} = \\frac{TP}{TP + FN}<br/>'
        '\\text{F1-Score} = 2 \\times \\frac{\\text{Precision} \\times \\text{Recall}}{\\text{Precision} + \\text{Recall}}, \\quad \\text{FPR} = \\frac{FP}{FP + TN}<br/>'
        '\\text{ROC-AUC} = \\sum_{k=1}^{M-1} \\frac{TPR_k + TPR_{k+1}}{2} (FPR_{k+1} - FPR_k) \\quad \\text{(Numerical Trapezoidal Rule)}',
        formula_style
    ))
    story.append(Paragraph('<b>Implemented Python Code (backend/ml_engine.py):</b>', body_bold))
    story.append(Paragraph(
        'precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0<br/>'
        'recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0<br/>'
        'f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0<br/>'
        'auc = sum((tpr[k] + tpr[k+1]) / 2.0 * (fpr[k+1] - fpr[k]) for k in range(len(fpr)-1))',
        code_style
    ))

    # Section 4: Explainability & Individual Selection Criteria
    story.append(PageBreak())
    story.append(Paragraph('4. Candidate Selection Criteria & Explainability Mathematics', h1_style))
    story.append(HRFlowable(width='100%', thickness=0.8, color=c_secondary, spaceBefore=1, spaceAfter=6))
    story.append(Paragraph(
        '<b>Why Candidate Criteria Cannot Be Identical:</b> In simple uncentered models, raw feature attribution $\\phi_j = \\beta_j \\cdot x_{ij}$ causes continuous features with large positive scale (like <code>city_development_index</code> = 0.92) to dwarf all dummy variables, producing the exact same 3 features for every applicant. This ruins recruiter trust.',
        body_style
    ))
    story.append(Paragraph('<b>Our Solution: Individualized Mean-Centered Local Marginal Attribution</b>', h2_style))
    story.append(Paragraph('<b>Theoretical Formulation:</b>', body_bold))
    story.append(Paragraph(
        'For Continuous Features: \\quad \\Delta \\phi_j(x_i) = \\beta_j \\times (x_{i,j} - \\bar{x}_j)<br/>'
        'For Categorical Dummies: \\quad \\phi_j(x_i) = \\begin{cases} \\beta_j \\times 1 & \\text{if } x_{i,j} = 1 \\text{ (Candidate holds this credential)} \\\\ 0 & \\text{if } x_{i,j} = 0 \\text{ (Excluded; not an individual driver)} \\end{cases}',
        formula_style
    ))
    story.append(Paragraph('<b>Implemented Python Code (backend/explainability.py):</b>', body_bold))
    story.append(Paragraph(
        'if feat in continuous_cols:<br/>'
        '    diff = val - feature_means.get(feat, 0.0)<br/>'
        '    impact = beta * diff  # Deviation from average candidate<br/>'
        'elif val == 1:<br/>'
        '    impact = beta * 1.0   # Only actual credentials held by candidate<br/>'
        '# Categorized into top positive drivers (advancing) and negative inhibitors (holding back)',
        code_style
    ))
    story.append(Paragraph(
        '<b>Executive Hiring Reasoning Narrative:</b> The system combines top drivers into plain-language executive summaries. Example: <i>\'Candidate #14598 prioritized with 84.2% match probability, driven primarily by Tier 1 Premier Institution pedigree (+0.81) and 16+ years experience (+0.54), surpassing the 0.50 cutoff despite training hours below pool median (-0.08).\'</i>',
        body_style
    ))

    # Section 5: Fairness Audit Mathematics
    story.append(Spacer(1, 4))
    story.append(Paragraph('5. Algorithmic Fairness Audit & EEOC 80% Rule', h1_style))
    story.append(HRFlowable(width='100%', thickness=0.8, color=c_secondary, spaceBefore=1, spaceAfter=6))
    story.append(Paragraph(
        'Audits are performed strictly on the held-out test set (3,832 records) across groups $g \\in G$ for Gender, Age Band, and Institution.',
        body_style
    ))

    fairness_table = [
        [Paragraph('<b>Fairness Metric</b>', body_bold), Paragraph('<b>Theoretical Formulation</b>', body_bold), Paragraph('<b>Code Formulation & Legal Standard</b>', body_bold)],
        [
            Paragraph('Selection Rate<br/>(Demographic Parity)', body_style),
            Paragraph('SR(g) = \\frac{|\\{i \\in g : \\hat{y}_i = 1\\}|}{|g|}', formula_style),
            Paragraph('<code>sel_rate = sum(shortlisted_g) / len(g)</code><br/>Goal: Equal proportion of candidates selected across groups.', body_style)
        ],
        [
            Paragraph('Group Recall<br/>(Equal Opportunity)', body_style),
            Paragraph('Recall(g) = \\frac{TP(g)}{TP(g) + FN(g)}', formula_style),
            Paragraph('<code>recall_g = tp / (tp + fn)</code><br/>Goal: Qualified applicants have equal chance of being shortlisted.', body_style)
        ],
        [
            Paragraph('Group Precision<br/>(Predictive Parity)', body_style),
            Paragraph('Precision(g) = \\frac{TP(g)}{TP(g) + FP(g)}', formula_style),
            Paragraph('<code>prec_g = tp / (tp + fp)</code><br/>Goal: Selected applicants have identical probability of true qualification.', body_style)
        ],
        [
            Paragraph('Disparity Gap', body_style),
            Paragraph('\\text{Gap} = \\max_{g} SR(g) - \\min_{g} SR(g)', formula_style),
            Paragraph('<code>gap = max(rates.values()) - min(rates.values())</code><br/>Absolute spread between most and least favored group.', body_style)
        ],
        [
            Paragraph('EEOC 80% Rule<br/>(Adverse Impact)', body_style),
            Paragraph('\\text{Ratio}(g) = \\frac{SR(g)}{\\max_k SR(k)}', formula_style),
            Paragraph('<code>ratio = sel_rate / max_rate</code><br/><b>Violated (Flagged RED) if ratio &lt; 0.80 (80%).</b> EEOC standard.', body_style)
        ],
        [
            Paragraph('Small Sample Check', body_style),
            Paragraph('N(g) &lt; 30', formula_style),
            Paragraph('<code>flagged_unreliable = (len(g) &lt; 30)</code><br/>Alerts recruiter against making claims on volatile subgroup sizes.', body_style)
        ],
    ]
    t_fair = Table(fairness_table, colWidths=[110, 205, 225])
    t_fair.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_light]),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_fair)

    # Section 6: Disparity Drivers & Feature Ablation
    story.append(PageBreak())
    story.append(Paragraph('6. Disparity Driver Identification & Feature Ablation Remediation', h1_style))
    story.append(HRFlowable(width='100%', thickness=0.8, color=c_secondary, spaceBefore=1, spaceAfter=6))
    story.append(Paragraph(
        '<b>6.1 Disparity Driver Mathematical Formulation:</b> When an adverse impact ratio falls below 0.80 between favored group $g_{\\text{fav}}$ and disadvantaged group $g_{\\text{dis}}$, the system calculates the <b>Weight-Shifted Differential Mean Impact</b> for every feature $j$:',
        body_style
    ))
    story.append(Paragraph(
        '\\text{Disparity Impact}_j = \\beta_j \\times \\left( \\bar{x}_{j, g_{\\text{fav}}} - \\bar{x}_{j, g_{\\text{dis}}} \\right)',
        formula_style
    ))
    story.append(Paragraph('<b>Implemented Python Code (backend/fairness_audit.py):</b>', body_bold))
    story.append(Paragraph(
        'mean_fav = sum(applicant[feat] for applicant in group_fav) / len(group_fav)<br/>'
        'mean_dis = sum(applicant[feat] for applicant in group_dis) / len(group_dis)<br/>'
        'diff = mean_fav - mean_dis<br/>'
        'impact = beta_j * diff  # Combines model sensitivity with demographic difference<br/>'
        '# Sorted descending; top positive feature is the primary driver of the disparity gap',
        code_style
    ))
    story.append(Paragraph(
        '<b>6.2 Feature Ablation Remediation Workflow:</b> (1) Recruiter selects offending driver feature. (2) Column is ablated: $X_{\\text{ablated}} = X \\setminus \\{x_{\\text{driver}}\\}$. (3) Model retrained from scratch. (4) System displays side-by-side Before-vs-After delta in Fairness Gap vs ROC-AUC tradeoff, giving recruiters quantifiable proof of debiasing.',
        body_style
    ))

    # Section 7: 6-Screen Architecture
    story.append(Spacer(1, 4))
    story.append(Paragraph('7. Six-Screen End-to-End Application Architecture', h1_style))
    story.append(HRFlowable(width='100%', thickness=0.8, color=c_secondary, spaceBefore=1, spaceAfter=6))
    
    screen_table = [
        [Paragraph('<b>Screen</b>', body_bold), Paragraph('<b>Screen Name</b>', body_bold), Paragraph('<b>Recruiter Workflow & Technical Capabilities</b>', body_bold)],
        [Paragraph('Screen 1', code_style), Paragraph('Dataset Profiling', body_style), Paragraph('Uploads CSV (19,158 rows). Inspects summary statistics, missing values, and demographic distributions.', body_style)],
        [Paragraph('Screen 2', code_style), Paragraph('Proxy Discovery', body_style), Paragraph('Pearson correlation matrix uncovering hidden proxies between candidate features and protected attributes.', body_style)],
        [Paragraph('Screen 3', code_style), Paragraph('Model Training', body_style), Paragraph('Trains Logistic Regression vs Random Forest on 80/20 split; Confusion Matrix, ROC-AUC, Precision, Recall, F1.', body_style)],
        [Paragraph('Screen 4', code_style), Paragraph('Shortlisting & Live Audit<br/><b>(Dual-Panel Console)</b>', body_style), Paragraph('<b>Left:</b> Ranked shortlist with threshold slider and criteria drawers.<br/><b>Right:</b> Live beside-it fairness audit updating Selection Rate, Recall, Precision & EEOC violations instantly.', body_style)],
        [Paragraph('Screen 5', code_style), Paragraph('Disparity Drivers', body_style), Paragraph('Ranks features by $\\beta_j(\\bar{x}_{\\text{fav}} - \\bar{x}_{\\text{dis}})$, pinpointing the exact cause of demographic acceptance gaps.', body_style)],
        [Paragraph('Screen 6', code_style), Paragraph('Remediation & Ablation', body_style), Paragraph('Actionable debiasing: Retrains model without driver feature, displaying live Before-vs-After tradeoff.', body_style)],
    ]
    t_screens = Table(screen_table, colWidths=[60, 160, 320])
    t_screens.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_light]),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_screens)

    # Section 8: Viva Voce Questions & Answers
    story.append(PageBreak())
    story.append(Paragraph('8. Master Viva Voce Questions & Definitive Answers (35 Questions)', h1_style))
    story.append(HRFlowable(width='100%', thickness=0.8, color=c_secondary, spaceBefore=1, spaceAfter=6))
    story.append(Paragraph(
        'The following 35 questions represent the most rigorous theoretical, mathematical, and practical questions asked by examiners during data mining project evaluations.',
        body_style
    ))

    qa_list = [
        ('Q1. What is the fundamental data mining problem formulated in this project?',
         'It is formulated as a Supervised Binary Classification task. The goal is to learn a mapping function f: X -> {0, 1} from applicant features X (experience, education, training hours, city economic index) to determine whether an applicant should be shortlisted to Proceed to Interview (y=1) or Reject/Hold (y=0).'),

        ('Q2. Why did we choose Logistic Regression and Random Forest specifically?',
         'We chose them to contrast parametric linear interpretability against non-parametric non-linear flexibility. Logistic Regression provides closed-form transparent weight coefficients beta_j representing log-odds ratios, which directly feed our explainability and disparity driver math. Random Forest builds an ensemble of decorrelated decision trees using bootstrap aggregation (bagging) and random subspace feature sampling, capturing complex non-linear interactions without strong distributional assumptions.'),

        ('Q3. What is the difference between Gini Impurity and Entropy in decision trees?',
         'Gini Impurity measures the probability of misclassifying a randomly chosen element from the set if it were randomly labeled according to the class distribution: Gini = 1 - sum(p_k^2). Entropy measures information disorder: Entropy = -sum(p_k * log2(p_k)). Gini is computationally more efficient because it avoids expensive logarithmic operations, making it standard for high-throughput decision trees.'),

        ('Q4. Why did we use an 80/20 Stratified Split instead of simple random sampling?',
         'In recruitment datasets, target class distribution is typically imbalanced (here ~24.9% positive). Simple random sampling risks assigning disproportionately more positive candidates to one split. Stratification preserves the exact 24.9% ratio across both train and test partitions, ensuring the test set reflects true generalization performance.'),

        ('Q5. How did we handle missing values, and why not just drop incomplete rows?',
         'Dropping incomplete rows would discard thousands of real records, causing massive survivorship bias and reducing statistical power. We used domain-guided median imputation for continuous variables (robust to outliers unlike mean) and created an explicit Unknown category for categorical variables so the model can learn whether missingness itself carries predictive information.'),

        ('Q6. What is the Sigmoid activation function and why do we clip its exponent?',
         'Sigmoid maps any real-valued number z in (-inf, +inf) into a valid probability in (0, 1): sigma(z) = 1 / (1 + exp(-z)). In numerical computation, when z < -709 or z > 709, exp(-z) causes floating-point overflow. We implemented clipping: z_clipped = max(min(z, 25.0), -25.0), ensuring numerical stability without distorting probabilities.'),

        ('Q7. Explain L2 Regularization (Ridge penalty) in our Logistic Regression.',
         'L2 regularization adds a penalty proportional to the sum of squared weights (lambda / 2N) * ||w||_2^2 to the loss function. This prevents weights from growing arbitrarily large on collinear features, constrains model complexity, prevents overfitting, and stabilizes the coefficient values used in explainability.'),

        ('Q8. How is the ROC Curve generated and how is AUC computed?',
         'The ROC curve plots the True Positive Rate (Recall) on the y-axis against the False Positive Rate on the x-axis across all decision thresholds theta in [0, 1]. The Area Under the Curve (ROC-AUC) evaluates ranking capability independent of threshold. We compute it via numerical trapezoidal integration summing areas of adjacent trapezoids: AUC = sum( (TPR_k + TPR_{k+1}) / 2 * (FPR_{k+1} - FPR_k) ).'),

        ('Q9. What is F1-Score and why is it preferred over Accuracy for imbalanced datasets?',
         'Accuracy can be deceptively high: if 95% of candidates are rejected, a dumb model predicting all 0s has 95% accuracy but 0% recall. F1-Score is the harmonic mean of Precision and Recall: 2 * (P * R) / (P + R). The harmonic mean penalizes extreme imbalances, ensuring a high score is achieved only when both precision and recall are strong.'),

        ('Q10. What is Demographic Parity (Statistical Parity)?',
         'Demographic Parity requires that the probability of shortlisting is identical across all protected groups: P(Y_hat = 1 | A = g_a) = P(Y_hat = 1 | A = g_b). It focuses purely on selection rates regardless of ground-truth qualification labels.'),

        ('Q11. What is Equal Opportunity (Equality of Odds)?',
         'Equal Opportunity requires that qualified candidates (ground truth Y = 1) have an equal probability of being shortlisted across all groups: P(Y_hat = 1 | Y = 1, A = g_a) = P(Y_hat = 1 | Y = 1, A = g_b). In our audit, this is measured directly as the Group Recall.'),

        ('Q12. What is Predictive Parity?',
         'Predictive Parity requires that a positive shortlisting decision has the same positive predictive value across groups: P(Y = 1 | Y_hat = 1, A = g_a) = P(Y = 1 | Y_hat = 1, A = g_b). In our audit, this is measured as Group Precision.'),

        ('Q13. What is the EEOC 80% (Four-Fifths) Adverse Impact Rule?',
         'The US Equal Employment Opportunity Commission (EEOC) Uniform Guidelines state that a selection rate for any demographic group which is less than 80% (4/5ths) of the rate for the highest-selected group is considered prima facie evidence of adverse disparate impact. Our system flags any group ratio < 0.80 with a prominent red badge.'),

        ('Q14. Why is the Fairness Audit computed exclusively on the held-out test set?',
         'Computing fairness on the training set measures memorized patterns rather than real-world operational impact. Auditing the held-out test set guarantees an unbiased assessment of how the model will treat unseen, future applicants.'),

        ('Q15. Why do we flag groups with sample size N < 30?',
         'In statistical sampling theory (Central Limit Theorem), sample sizes under 30 exhibit high variance and volatile rates. One single hiring decision in a group of 5 can swing the selection rate by 20%. Flagging N < 30 alerts recruiters not to draw definitive conclusions from statistically insignificant subgroups.'),

        ('Q16. How does our system calculate candidate-specific selection criteria?',
         'We use individualized mean-centered marginal feature attribution. For continuous features, we calculate Delta phi_j = beta_j * (x_ij - mean(x_j)), evaluating how far above or below the population average the candidate sits. For one-hot categorical features, we only evaluate credentials the applicant actually holds (x_ij = 1). This yields distinct, accurate positive drivers and negative inhibitors for every applicant.'),

        ('Q17. Why do some systems produce identical criteria for all candidates?',
         'Because they calculate raw attribution beta_j * x_ij without mean-centering. Continuous features like city_development_index have values around 0.90, producing huge positive numbers that drown out categorical features across all applicants. Mean-centering centers population baseline effect at zero.'),

        ('Q18. How does the interactive decision threshold slider work?',
         'The slider adjusts the classification cutoff theta between 0.10 and 0.90 (default 0.50). An applicant is shortlisted if P(interview | x) >= theta. Lowering theta increases recall (more candidates invited), while raising theta increases precision (stricter screening). Crucially, changing theta dynamically recomputes all selection rates and EEOC ratios in real time on the adjacent audit panel.'),

        ('Q19. What is a Disparity Driver and how is it mathematically calculated?',
         'A disparity driver is a feature responsible for the selection rate gap between the favored group and a disadvantaged group. It is calculated as: Impact_j = beta_j * (mean(x_fav, j) - mean(x_dis, j)). It multiplies the model sensitivity (beta_j) by the demographic discrepancy in feature possession.'),

        ('Q20. What is Feature Ablation and what happens during it?',
         'Feature Ablation is an empirical debiasing technique. We remove the identified disparity driver column from the dataset, retrain the model from scratch, and evaluate the change in disparity gap versus the change in predictive ROC-AUC. It reveals whether fairness can be restored with minimal loss in model accuracy.'),

        ('Q21. What is the Fairness-Accuracy Tradeoff?',
         'In machine learning, models trained to maximize predictive accuracy inherently exploit historical correlations present in training data. If historical data contains systemic inequities, an accuracy-maximizing model will replicate them. Mitigating bias (e.g. via ablation or threshold adjustment) often slightly reduces accuracy/ROC-AUC in exchange for substantial reductions in demographic disparity.'),

        ('Q22. Explain the dual-panel layout on Screen 4.',
         'Screen 4 places the Ranked Shortlist on the left and the Live Beside-It Fairness Audit on the right. Recruiters can view who is being invited and examine their individual criteria drawer, while simultaneously witnessing the real-time demographic impact of their threshold decisions across Gender, Age Band, and Institution.'),

        ('Q23. Why did we build a transparent pure-Python ML engine alongside scikit-learn?',
         'In high-security enterprise environments or Windows systems with strict User Mode Code Integrity (UMCI / Smart App Control / WDAC), compiled C-extensions (like numpy _umath_linalg.pyd) are blocked. Our pure-Python engine guarantees complete operational independence, full auditability of every mathematical step, and zero-dependency execution anywhere.'),

        ('Q24. How do we test and verify this system?',
         'We implemented an automated test suite (tests/test_fairness_engine.py) covering: (1) Ingestion integrity, (2) Stratified split ratios, (3) Model convergence, (4) Audit metrics calculation, and (5) End-to-end API verification (verify_spec.py) querying live Flask endpoints.'),

        ('Q25. How do you defend this system if an examiner asks about proxy discrimination?',
         'We show Screen 2 Proxy Correlation Matrix! Even if protected attributes like gender or race are omitted from training, non-protected features (like university tier or location) can act as mathematical surrogates. Our system explicitly measures correlation r_xy between all features and protected attributes to detect and surface proxy bias before training.'),

        ('Q26. What is the difference between Disparate Treatment and Disparate Impact?',
         'Disparate Treatment is intentional discrimination where decisions are made explicitly based on a protected trait (e.g. rejecting someone because they are female). Disparate Impact is unintentional discrimination where a neutral practice or algorithm disproportionately harms a protected group in practice. Our tool audits and mitigates Disparate Impact.'),

        ('Q27. Can a model be both fair and accurate?',
         'Yes, up to a Pareto frontier. Often, features driving disparity contribute only marginal predictive power. Through feature ablation and threshold calibration, we can dramatically close disparity gaps with negligible drops in ROC-AUC.'),

        ('Q28. Why is Pearson correlation sufficient for proxy detection?',
         'Pearson r measures linear bivariate association. While non-linear mutual information can also be used, Pearson r is intuitive, computationally fast (-1 to +1 scale), easily understood by HR professionals, and effectively flags high collinearity between credentials and demographics.'),

        ('Q29. What is One-Hot Encoding and why is it necessary?',
         'Machine learning models require numerical matrices. Categorical variables with no natural ordering (e.g., university enrollment type) cannot be assigned arbitrary integers like 1, 2, 3 because the model would infer false numeric distance. One-hot encoding creates binary dummy columns (0 or 1) for each category.'),

        ('Q30. What happens if a recruiter sets the threshold to 0.10?',
         'Almost all applicants are shortlisted (very high selection rate and recall, low precision). The selection gap between groups narrows because nearly everyone is accepted, but recruiter screening efficiency collapses as interview volume explodes.'),

        ('Q31. What happens if a recruiter sets the threshold to 0.90?',
         'Only exceptionally high-scoring candidates are shortlisted. Selection rates plunge toward 0-5%. Disparate impact frequently spikes because even tiny differences in top credential scores cause disadvantaged groups to fall below the severe cutoff.'),

        ('Q32. How does the executive hiring reasoning string get constructed?',
         'The system parses top positive drivers and top negative inhibitors, matches them to human-readable labels, and populates an executive template summarizing candidate match probability, key credential drivers, and mitigating factors.'),

        ('Q33. What is the role of the Confusion Matrix in the audit?',
         'The Confusion Matrix partitions predictions into True Positives (correctly interviewed), False Positives (unnecessarily interviewed), True Negatives (correctly rejected), and False Negatives (missed talent). Computing this matrix per demographic group reveals whether errors are distributed symmetrically.'),

        ('Q34. Why do we export shortlists to CSV?',
         'Recruiters need to import ranked shortlists into enterprise Applicant Tracking Systems (ATS) like Workday or Greenhouse. Our CSV export contains applicant ID, match probability, shortlisted status, and top selection drivers for direct enterprise handoff.'),

        ('Q35. In one sentence, what is the ultimate achievement of this project?',
         'It transforms recruitment from an unverified, subjective black box into a mathematically rigorous, explainable, and provably fair talent shortlisting system with built-in regulatory compliance and remediation.')
    ]

    for q_text, a_text in qa_list:
        story.append(Paragraph(q_text, qa_q_style))
        story.append(Paragraph(a_text, qa_a_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f'[SUCCESS] Generated complete Viva Voce Guide PDF: {filename}')

if __name__ == '__main__':
    build_pdf()
