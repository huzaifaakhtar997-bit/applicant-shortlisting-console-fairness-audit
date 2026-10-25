/**
 * FairRecruit Console - Frontend Application Logic
 * Implements interactive controllers for all 6 screens,
 * Chart.js visualizations, and asynchronous API communication.
 */

// Global Application State
const state = {
    threshold: 0.50,
    modelType: 'logistic_regression',
    currentPage: 1,
    perPage: 25,
    topN: null,
    filterStatus: 'all',
    activeProtectedAttr: 'gender',
    charts: {}
};

// DOM Content Loaded Handler
document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    loadScreen1Data();
    loadScreen2Data();
    loadScreen3Metrics();
    loadScreen4Shortlist();
    loadScreen6FairnessAudit();
});

// Event Listeners Initialization
function initEventListeners() {
    // Screen 3: Retrain Button & Slider
    const s3Slider = document.getElementById('s3-thresh-slider');
    const s3ThreshVal = document.getElementById('s3-thresh-val');
    s3Slider.addEventListener('input', (e) => {
        state.threshold = parseFloat(e.target.value);
        s3ThreshVal.textContent = state.threshold.toFixed(2);
        syncGlobalThreshold();
    });

    document.getElementById('s3-btn-train').addEventListener('click', () => {
        state.modelType = document.getElementById('s3-model-select').value;
        trainModel();
    });

    // Screen 4: Shortlist Controls
    const s4Slider = document.getElementById('s4-thresh-slider');
    const s4ThreshDisplay = document.getElementById('s4-thresh-display');
    s4Slider.addEventListener('input', (e) => {
        state.threshold = parseFloat(e.target.value);
        s4ThreshDisplay.textContent = state.threshold.toFixed(2);
        syncGlobalThreshold();
    });

    document.getElementById('s4-btn-apply').addEventListener('click', () => {
        const topNVal = document.getElementById('s4-topn-input').value;
        state.topN = topNVal ? parseInt(topNVal) : null;
        state.filterStatus = document.getElementById('s4-filter-select').value;
        state.currentPage = 1;
        loadScreen4Shortlist();
    });

    document.getElementById('s4-btn-prev').addEventListener('click', () => {
        if (state.currentPage > 1) {
            state.currentPage--;
            loadScreen4Shortlist();
        }
    });

    document.getElementById('s4-btn-next').addEventListener('click', () => {
        state.currentPage++;
        loadScreen4Shortlist();
    });

    document.getElementById('s4-btn-export').addEventListener('click', () => {
        const filter = document.getElementById('s4-filter-select').value;
        window.location.href = `/api/shortlist?threshold=${state.threshold}&filter=${filter}&export=true`;
    });

    // Screen 4: Close Criteria Drawer
    const s4DrawerClose = document.getElementById('s4-drawer-close');
    if (s4DrawerClose) {
        s4DrawerClose.addEventListener('click', () => {
            document.getElementById('s4-criteria-drawer').classList.add('d-none');
        });
    }

    // Screen 5: Explainability
    document.getElementById('s5-btn-explain').addEventListener('click', () => {
        const id = document.getElementById('s5-applicant-input').value.trim();
        if (id) explainCandidate(id);
    });

    // Screen 6: Protected Attribute Selector
    document.querySelectorAll('#fairnessAttrPills button').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('#fairnessAttrPills button').forEach(b => b.classList.remove('active'));
            e.currentTarget.classList.add('active');
            state.activeProtectedAttr = e.currentTarget.getAttribute('data-attr');
            loadScreen6FairnessAudit();
        });
    });

    // Screen 6: Ablation Simulator
    document.getElementById('s6-btn-run-ablation').addEventListener('click', () => {
        runAblationSimulation();
    });

    // CSV Upload Handler
    document.getElementById('btnUploadSubmit').addEventListener('click', uploadCsvDataset);
}

// Synchronize Threshold Across UI
function syncGlobalThreshold() {
    document.getElementById('global-thresh-badge').textContent = `Threshold: ${state.threshold.toFixed(2)}`;
    document.getElementById('s3-thresh-slider').value = state.threshold;
    document.getElementById('s3-thresh-val').textContent = state.threshold.toFixed(2);
    document.getElementById('s4-thresh-slider').value = state.threshold;
    document.getElementById('s4-thresh-display').textContent = state.threshold.toFixed(2);
}

// ==========================================
// SCREEN 1: DATA INGESTION CONTROLLER
// ==========================================
async function loadScreen1Data() {
    try {
        const res = await fetch('/api/dataset');
        const data = await res.json();

        // Update KPIs
        document.getElementById('s1-total-rows').textContent = data.total_rows.toLocaleString();
        document.getElementById('s1-positive-count').textContent = `${data.class_balance.positive.toLocaleString()} (${data.class_balance.positive_pct}%)`;
        document.getElementById('s1-split-ratio').textContent = `${data.train_rows.toLocaleString()} / ${data.test_rows.toLocaleString()}`;
        document.getElementById('s1-feature-count').textContent = data.num_features;
        document.getElementById('global-pool-badge').textContent = `Pool: ${data.total_rows.toLocaleString()} Applicants`;

        // Render Demographic Charts
        renderGenderChart(data.gender_dist);
        renderAgeChart(data.age_band_dist);
        renderInstitutionChart(data.institution_dist);

        // Render Preview Table
        const tbody = document.querySelector('#s1-preview-table tbody');
        tbody.innerHTML = '';
        data.preview.forEach(row => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${row.enrollee_id}</strong></td>
                <td><span class="badge bg-secondary-subtle text-secondary">${row.gender}</span></td>
                <td><span class="badge bg-info-subtle text-info">${row.age_band}</span></td>
                <td><span class="badge bg-warning-subtle text-warning-emphasis">${row.institution}</span></td>
                <td>${row.education_level || 'N/A'}</td>
                <td>${row.experience || 'N/A'} yrs</td>
                <td>${row.city_development_index}</td>
                <td>${row.company_size || 'Unknown'}</td>
                <td>${row.target === 1 ? '<span class="badge bg-success">1 (Interview)</span>' : '<span class="badge bg-light text-dark border">0 (Reject)</span>'}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error('Failed to load dataset summary:', err);
    }
}

function renderGenderChart(dist) {
    const ctx = document.getElementById('chart-gender').getContext('2d');
    if (state.charts.gender) state.charts.gender.destroy();
    state.charts.gender = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(dist),
            datasets: [{
                data: Object.values(dist),
                backgroundColor: ['#0d6efd', '#6c757d', '#d63384', '#fd7e14']
            }]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });
}

function renderAgeChart(dist) {
    const ctx = document.getElementById('chart-age').getContext('2d');
    if (state.charts.age) state.charts.age.destroy();
    state.charts.age = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: Object.keys(dist),
            datasets: [{
                label: 'Applicants',
                data: Object.values(dist),
                backgroundColor: '#0dcaf0'
            }]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
    });
}

function renderInstitutionChart(dist) {
    const ctx = document.getElementById('chart-institution').getContext('2d');
    if (state.charts.institution) state.charts.institution.destroy();
    state.charts.institution = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: Object.keys(dist).map(k => k.length > 18 ? k.substring(0, 16) + '..' : k),
            datasets: [{
                label: 'Applicants',
                data: Object.values(dist),
                backgroundColor: '#ffc107'
            }]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
    });
}

// ==========================================
// SCREEN 2: PREPROCESSING & PROXIES
// ==========================================
async function loadScreen2Data() {
    try {
        const res = await fetch('/api/preprocess');
        const data = await res.json();

        // Medians
        if (data.medians) {
            document.getElementById('s2-cdi-median').textContent = data.medians.city_development_index;
            document.getElementById('s2-th-median').textContent = `${data.medians.training_hours} hrs`;
        }

        // Categorical encoding badges
        const badgesContainer = document.getElementById('s2-encoding-badges');
        badgesContainer.innerHTML = '';
        for (const [col, vals] of Object.entries(data.categories_map)) {
            const badge = document.createElement('span');
            badge.className = 'badge bg-light text-dark border p-2';
            badge.innerHTML = `<strong>${col}</strong>: ${vals.length} categories`;
            badgesContainer.appendChild(badge);
        }

        // Proxy detection table
        const tbody = document.querySelector('#s2-proxy-table tbody');
        tbody.innerHTML = '';
        data.correlations.forEach(row => {
            const tr = document.createElement('tr');
            if (row.is_high_risk_proxy) tr.className = 'table-warning';
            tr.innerHTML = `
                <td><code>${row.feature}</code></td>
                <td><span class="badge bg-secondary-subtle text-secondary">${row.original_column}</span></td>
                <td>${row.corr_gender.toFixed(3)}</td>
                <td>${row.corr_age_band.toFixed(3)}</td>
                <td>${row.corr_institution.toFixed(3)}</td>
                <td><strong>${row.max_correlation.toFixed(3)}</strong></td>
                <td><span class="small">${row.highest_proxy_group}</span></td>
                <td>${row.is_high_risk_proxy 
                    ? '<span class="badge bg-danger">High Proxy Risk (&ge;0.25)</span>' 
                    : '<span class="badge bg-success-subtle text-success">Low Risk</span>'}
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error('Failed to load preprocessing data:', err);
    }
}

// ==========================================
// SCREEN 3: CLASSIFICATION CONTROLLER
// ==========================================
async function trainModel() {
    try {
        const res = await fetch('/api/train', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model_type: state.modelType, threshold: state.threshold })
        });
        const metrics = await res.json();
        updateScreen3Metrics(metrics);
        // Refresh dependent screens
        loadScreen4Shortlist();
        loadScreen6FairnessAudit();
    } catch (err) {
        console.error('Model training error:', err);
    }
}

async function loadScreen3Metrics() {
    await trainModel();
}

function updateScreen3Metrics(m) {
    document.getElementById('s3-metric-acc').textContent = (m.accuracy * 100).toFixed(1) + '%';
    document.getElementById('s3-metric-prec').textContent = (m.precision * 100).toFixed(1) + '%';
    document.getElementById('s3-metric-recall').textContent = (m.recall * 100).toFixed(1) + '%';
    document.getElementById('s3-metric-f1').textContent = m.f1.toFixed(3);
    document.getElementById('s3-metric-auc').textContent = m.auc.toFixed(3);

    // Confusion Matrix
    if (m.confusion_matrix) {
        document.getElementById('cm-tn').textContent = m.confusion_matrix.tn.toLocaleString();
        document.getElementById('cm-fp').textContent = m.confusion_matrix.fp.toLocaleString();
        document.getElementById('cm-fn').textContent = m.confusion_matrix.fn.toLocaleString();
        document.getElementById('cm-tp').textContent = m.confusion_matrix.tp.toLocaleString();
    }

    // Global badge
    const modelName = m.model_type === 'random_forest' ? 'Random Forest' : 'Logistic Regression';
    document.getElementById('global-model-badge').textContent = `Model: ${modelName}`;

    // ROC Curve
    if (m.roc_curve) renderRocCurve(m.roc_curve, m.auc);
}

function renderRocCurve(points, auc) {
    const ctx = document.getElementById('chart-roc').getContext('2d');
    if (state.charts.roc) state.charts.roc.destroy();

    const dataPoints = points.map(p => ({ x: p.fpr, y: p.tpr }));
    state.charts.roc = new Chart(ctx, {
        type: 'line',
        data: {
            datasets: [
                {
                    label: `Model ROC (AUC = ${auc.toFixed(3)})`,
                    data: dataPoints,
                    borderColor: '#0d6efd',
                    backgroundColor: 'rgba(13, 110, 253, 0.1)',
                    fill: true,
                    tension: 0.1
                },
                {
                    label: 'Random Guess Reference',
                    data: [{ x: 0, y: 0 }, { x: 1, y: 1 }],
                    borderColor: '#adb5bd',
                    borderDash: [5, 5],
                    fill: false,
                    pointRadius: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { type: 'linear', min: 0, max: 1, title: { display: true, text: 'False Positive Rate (FPR)' } },
                y: { min: 0, max: 1, title: { display: true, text: 'True Positive Rate (TPR / Recall)' } }
            }
        }
    });
}

// ==============================================================
// SCREEN 4: RANKED SHORTLIST & BESIDE-IT FAIRNESS AUDIT
// ==============================================================
async function loadScreen4Shortlist() {
    try {
        let url = `/api/shortlist?threshold=${state.threshold}&page=${state.currentPage}&per_page=${state.perPage}&filter=${state.filterStatus}`;
        if (state.topN) url += `&top_n=${state.topN}`;

        const res = await fetch(url);
        const data = await res.json();

        // KPIs
        document.getElementById('s4-total-applicants').textContent = data.total_candidates.toLocaleString();
        document.getElementById('s4-shortlisted-count').textContent = data.total_shortlisted.toLocaleString();
        document.getElementById('s4-selection-rate').textContent = (data.selection_rate * 100).toFixed(1) + '%';
        document.getElementById('s4-page-info').textContent = `Page ${data.page} of ${data.total_pages || 1}`;

        // Populate Ranked Table
        const tbody = document.querySelector('#s4-shortlist-table tbody');
        tbody.innerHTML = '';
        data.applicants.forEach(app => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>#${app.rank}</strong></td>
                <td><code>${app.enrollee_id}</code></td>
                <td>
                    <div class="d-flex align-items-center gap-1">
                        <div class="progress flex-grow-1" style="height: 6px; min-width: 45px;">
                            <div class="progress-bar ${app.shortlisted ? 'bg-success' : 'bg-secondary'}" style="width: ${app.score * 100}%"></div>
                        </div>
                        <span class="small fw-bold">${(app.score * 100).toFixed(1)}%</span>
                    </div>
                </td>
                <td>${app.shortlisted 
                    ? '<span class="badge bg-success py-1 px-2"><i class="bi bi-check-circle me-1"></i>YES</span>' 
                    : '<span class="badge bg-light text-muted border py-1 px-2">NO</span>'}
                </td>
                <td><span class="badge bg-secondary-subtle text-secondary">${app.gender}</span></td>
                <td><span class="badge bg-info-subtle text-info">${app.age_band}</span></td>
                <td><span class="small text-truncate" style="max-width: 110px; display: inline-block;">${app.institution}</span></td>
                <td>
                    <button class="btn btn-sm btn-outline-info py-0 px-2" onclick="showInlineCriteria('${app.enrollee_id}', ${app.score}, ${app.shortlisted})" title="See criteria behind this ranking">
                        <i class="bi bi-lightbulb"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        // Populate Beside-It Fairness Audit (Gender, Age Band, Institution)
        if (data.audit_summary) {
            renderBesideAudit(data.audit_summary);
        }

    } catch (err) {
        console.error('Failed to load shortlist:', err);
    }
}

// Show criteria behind each ranking right on Screen 4
async function showInlineCriteria(enrolleeId, score, shortlisted) {
    const drawer = document.getElementById('s4-criteria-drawer');
    drawer.classList.remove('d-none');
    document.getElementById('s4-drawer-id').textContent = enrolleeId;
    document.getElementById('s4-drawer-score').textContent = `${(score * 100).toFixed(1)}%`;
    const statusBadge = document.getElementById('s4-drawer-status');
    statusBadge.className = shortlisted ? 'badge bg-success ms-2' : 'badge bg-secondary ms-2';
    statusBadge.textContent = shortlisted ? 'SHORTLISTED' : 'NOT SHORTLISTED';

    const posContainer = document.getElementById('s4-drawer-pos-factors');
    const negContainer = document.getElementById('s4-drawer-neg-factors');
    posContainer.innerHTML = '<span class="text-muted small">Loading factors...</span>';
    negContainer.innerHTML = '<span class="text-muted small">Loading factors...</span>';

    try {
        const res = await fetch(`/api/explain/${enrolleeId}`);
        const data = await res.json();
        posContainer.innerHTML = '';
        negContainer.innerHTML = '';

        // Display Detailed Executive Reasoning Narrative
        if (data.executive_reasoning) {
            document.getElementById('s4-drawer-narrative').textContent = data.executive_reasoning.detailed_narrative;
        }

        if (data.positive_drivers && data.positive_drivers.length > 0) {
            data.positive_drivers.slice(0, 4).forEach(d => {
                const badge = document.createElement('span');
                badge.className = 'badge bg-success-subtle text-success border border-success-subtle p-1';
                badge.innerHTML = `+${d.contribution.toFixed(3)}: <strong>${d.label || d.feature}</strong>`;
                posContainer.appendChild(badge);
            });
        } else {
            posContainer.innerHTML = '<span class="text-muted small">No strong positive drivers</span>';
        }

        if (data.negative_drivers && data.negative_drivers.length > 0) {
            data.negative_drivers.slice(0, 4).forEach(d => {
                const badge = document.createElement('span');
                badge.className = 'badge bg-danger-subtle text-danger border border-danger-subtle p-1';
                badge.innerHTML = `${d.contribution.toFixed(3)}: <strong>${d.label || d.feature}</strong>`;
                negContainer.appendChild(badge);
            });
        } else {
            negContainer.innerHTML = '<span class="text-muted small">No strong negative drivers</span>';
        }

    } catch (e) {
        posContainer.innerHTML = '<span class="text-danger small">Error loading criteria</span>';
        negContainer.innerHTML = '';
    }
}

// Render the Beside-It Fairness Audit Panel
function renderBesideAudit(auditSummary) {
    const hasDisparity = auditSummary.gender.adverse_impact || auditSummary.age_band.adverse_impact || auditSummary.institution.adverse_impact;
    
    // Overall badge
    const overallBadge = document.getElementById('s4-audit-overall-badge');
    if (hasDisparity) {
        overallBadge.className = 'badge bg-danger';
        overallBadge.innerHTML = '<i class="bi bi-exclamation-triangle-fill me-1"></i> Disparity Detected (<0.80)';
    } else {
        overallBadge.className = 'badge bg-success';
        overallBadge.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i> Selection Parity Compliant';
    }

    // Diagnostic message banner
    const bannerEl = document.getElementById('s4-disparity-banner');
    const bannerMsg = document.getElementById('s4-disparity-msg');
    if (hasDisparity) {
        bannerEl.className = 'alert alert-danger border-danger mt-3 mb-0 p-2 small';
        bannerMsg.innerHTML = '<strong>Warning:</strong> Selection rate differs across demographic groups. Adjust threshold or see Screen 6 for attribute ablation.';
    } else {
        bannerEl.className = 'alert alert-success border-success mt-3 mb-0 p-2 small';
        bannerMsg.innerHTML = '<strong>Compliant:</strong> Selection rate does not violate the 80% rule across groups with &ge;30 samples.';
    }

    // Render Dimension 1: Gender
    renderAuditDimension('gender', auditSummary.gender);

    // Render Dimension 2: Age Band
    renderAuditDimension('age', auditSummary.age_band);

    // Render Dimension 3: Institution
    renderAuditDimension('inst', auditSummary.institution);
}

function renderAuditDimension(prefix, dimData) {
    // Gap badge
    document.getElementById(`s4-${prefix}-gap-badge`).textContent = `Gap: ${(dimData.selection_rate_gap * 100).toFixed(1)}%`;

    // Progress bars container
    const barsContainer = document.getElementById(`s4-${prefix}-bars`);
    barsContainer.innerHTML = '';

    dimData.groups.forEach(g => {
        const ratePct = (g.selection_rate * 100).toFixed(1);
        const barDiv = document.createElement('div');
        barDiv.className = 'mb-2';
        barDiv.innerHTML = `
            <div class="d-flex justify-content-between small mb-1">
                <span><strong>${g.group}</strong> <span class="text-muted">(${g.selected}/${g.total})</span></span>
                <span class="${g.violates_80_rule ? 'text-danger fw-bold' : 'text-dark'}">${ratePct}% (Ratio: ${g.four_fifths_ratio.toFixed(2)})</span>
            </div>
            <div class="progress" style="height: 8px;">
                <div class="progress-bar ${g.violates_80_rule ? 'bg-danger' : 'bg-primary'}" style="width: ${Math.min(100, Math.max(g.selection_rate * 250, 4))}%"></div>
            </div>
        `;
        barsContainer.appendChild(barDiv);
    });

    // Mini Table
    const tbody = document.querySelector(`#s4-${prefix}-table tbody`);
    tbody.innerHTML = '';
    dimData.groups.forEach(g => {
        const tr = document.createElement('tr');
        if (g.violates_80_rule) tr.className = 'table-danger';
        tr.innerHTML = `
            <td><strong>${g.group}</strong></td>
            <td>${g.total.toLocaleString()}</td>
            <td>${g.selected.toLocaleString()}</td>
            <td><strong>${(g.selection_rate * 100).toFixed(1)}%</strong></td>
            <td>
                <span class="${g.violates_80_rule ? 'badge bg-danger' : 'text-success fw-bold'}">
                    ${g.four_fifths_ratio.toFixed(2)} ${g.violates_80_rule ? '<i class="bi bi-exclamation-circle"></i>' : ''}
                </span>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function inspectApplicant(enrolleeId) {
    // Switch to Screen 5 tab
    const tabEl = document.getElementById('tab-screen5');
    const tab = new bootstrap.Tab(tabEl);
    tab.show();
    document.getElementById('s5-applicant-input').value = enrolleeId;
    explainCandidate(enrolleeId);
}

// ==========================================
// SCREEN 5: EXPLAINABILITY BREAKDOWN
// ==========================================
async function explainCandidate(applicantId) {
    try {
        const res = await fetch(`/api/explain/${applicantId}`);
        const data = await res.json();
        if (data.error) {
            alert(data.error);
            return;
        }

        // Profile updates
        document.getElementById('s5-profile-id').textContent = `Enrollee #${data.applicant_id}`;
        document.getElementById('s5-profile-score').textContent = `${(data.score * 100).toFixed(1)}%`;
        const statusEl = document.getElementById('s5-profile-status');
        if (data.shortlisted) {
            statusEl.className = 'badge bg-success mt-1';
            statusEl.textContent = 'SHORTLISTED FOR INTERVIEW';
        } else {
            statusEl.className = 'badge bg-secondary mt-1';
            statusEl.textContent = 'NOT SHORTLISTED';
        }

        document.getElementById('s5-profile-gender').textContent = data.demographics.gender;
        document.getElementById('s5-profile-age').textContent = data.demographics.age_band;
        document.getElementById('s5-profile-inst').textContent = data.demographics.institution;
        document.getElementById('s5-profile-edu').textContent = data.profile.education_level || 'Unknown';
        document.getElementById('s5-profile-cdi').textContent = data.profile.city_development_index;
        document.getElementById('s5-profile-th').textContent = `${data.profile.training_hours} hrs`;

        // Render Executive Reasoning Dossier Card
        if (data.executive_reasoning) {
            const er = data.executive_reasoning;
            const verdictEl = document.getElementById('s5-reasoning-verdict');
            verdictEl.className = data.shortlisted ? 'badge bg-success' : 'badge bg-secondary';
            verdictEl.textContent = er.verdict;

            document.getElementById('s5-reasoning-headline').textContent = er.headline;
            document.getElementById('s5-reasoning-narrative').textContent = er.detailed_narrative;

            const strengthsList = document.getElementById('s5-reasoning-strengths');
            strengthsList.innerHTML = '';
            er.key_strengths.forEach(s => {
                const li = document.createElement('li');
                li.className = 'mb-1';
                li.textContent = s;
                strengthsList.appendChild(li);
            });

            const risksList = document.getElementById('s5-reasoning-risks');
            risksList.innerHTML = '';
            er.key_risks.forEach(r => {
                const li = document.createElement('li');
                li.className = 'mb-1';
                li.textContent = r;
                risksList.appendChild(li);
            });
        }

        // Render Waterfall Chart
        renderExplainChart(data.top_contributions);

        // Populate Table
        const tbody = document.querySelector('#s5-explain-table tbody');
        tbody.innerHTML = '';
        data.top_contributions.forEach(c => {
            const tr = document.createElement('tr');
            const isPos = c.contribution > 0;
            tr.innerHTML = `
                <td>
                    <strong>${c.label || c.feature}</strong>
                    <code class="d-block text-muted small">${c.feature}</code>
                </td>
                <td><span class="badge bg-light text-dark border">${c.original_column}</span></td>
                <td>${c.value}</td>
                <td>${c.weight.toFixed(4)}</td>
                <td class="${isPos ? 'text-success fw-bold' : 'text-danger fw-bold'}">
                    ${isPos ? '+' : ''}${c.contribution.toFixed(4)}
                </td>
                <td>
                    <span class="badge ${isPos ? 'bg-success' : 'bg-danger'}">${c.direction}</span>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error('Explainability error:', err);
    }
}

function renderExplainChart(contributions) {
    const ctx = document.getElementById('chart-explain').getContext('2d');
    if (state.charts.explain) state.charts.explain.destroy();

    const labels = contributions.map(c => c.label || c.feature);
    const values = contributions.map(c => c.contribution);
    const colors = values.map(v => v >= 0 ? '#198754' : '#dc3545');

    state.charts.explain = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Score Contribution (β * x)',
                data: values,
                backgroundColor: colors
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { title: { display: true, text: 'Net Attribution Impact' } }
            }
        }
    });
}

// ==========================================
// SCREEN 6: FAIRNESS AUDIT (MAIN CHALLENGE)
// ==========================================
async function loadScreen6FairnessAudit() {
    try {
        const res = await fetch(`/api/fairness/audit?attribute=${state.activeProtectedAttr}&threshold=${state.threshold}`);
        const data = await res.json();
        const audit = data.audit[state.activeProtectedAttr];

        // Audit KPIs
        const minRatio = audit.min_four_fifths_ratio;
        const ratioEl = document.getElementById('s6-min-80-ratio');
        const badgeEl = document.getElementById('s6-80-status-badge');
        ratioEl.textContent = minRatio.toFixed(3);

        if (audit.adverse_impact_detected) {
            ratioEl.className = 'fw-bold mt-1 text-danger';
            badgeEl.className = 'badge bg-danger';
            badgeEl.textContent = '80% Rule Violation (Adverse Impact)';
        } else {
            ratioEl.className = 'fw-bold mt-1 text-success';
            badgeEl.className = 'badge bg-success';
            badgeEl.textContent = 'Compliant with 80% Rule';
        }

        document.getElementById('s6-sr-gap').textContent = (audit.selection_rate_gap * 100).toFixed(1) + '%';
        document.getElementById('s6-recall-gap').textContent = (audit.recall_gap * 100).toFixed(1) + '%';
        document.getElementById('s6-prec-gap').textContent = (audit.precision_gap * 100).toFixed(1) + '%';

        // Populate Group Table
        const tbody = document.querySelector('#s6-group-table tbody');
        tbody.innerHTML = '';
        audit.groups.forEach(g => {
            const tr = document.createElement('tr');
            if (g.violates_80_rule) tr.className = 'row-violation';

            tr.innerHTML = `
                <td>
                    <strong>${g.group}</strong>
                    ${g.is_small_group ? '<span class="badge bg-warning text-dark ms-2"><i class="bi bi-exclamation-triangle"></i> Small Group (< 30) - Unreliable</span>' : ''}
                </td>
                <td>${g.size.toLocaleString()}</td>
                <td>${g.selected_count.toLocaleString()}</td>
                <td><strong>${(g.selection_rate * 100).toFixed(1)}%</strong></td>
                <td>${(g.recall * 100).toFixed(1)}%</td>
                <td>${(g.precision * 100).toFixed(1)}%</td>
                <td>
                    <span class="fw-bold ${g.violates_80_rule ? 'text-danger fs-6' : 'text-success'}">
                        ${g.four_fifths_ratio.toFixed(3)}
                    </span>
                </td>
                <td>
                    ${g.violates_80_rule 
                        ? '<span class="badge badge-violation"><i class="bi bi-x-circle me-1"></i>Adverse Impact (< 0.8)</span>' 
                        : '<span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>Pass</span>'}
                </td>
            `;
            tbody.appendChild(tr);
        });

        // Disparity Driver Panel
        if (data.drivers) {
            document.getElementById('s6-fav-dis-badge').textContent = 
                `Favoured: ${data.drivers.favoured_group} vs Disadvantaged: ${data.drivers.disadvantaged_group}`;
            renderDriverChart(data.drivers.drivers);
            renderDriverTable(data.drivers.drivers);
        }
    } catch (err) {
        console.error('Fairness audit load error:', err);
    }
}

function renderDriverChart(drivers) {
    const ctx = document.getElementById('chart-drivers').getContext('2d');
    if (state.charts.drivers) state.charts.drivers.destroy();

    const labels = drivers.map(d => d.feature);
    const values = drivers.map(d => d.driver_score);
    const colors = values.map(v => v >= 0 ? '#0d6efd' : '#fd7e14');

    state.charts.drivers = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Disparity Driver Score: β * (Mean_fav - Mean_dis)',
                data: values,
                backgroundColor: colors
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { title: { display: true, text: 'Disparity Driver Contribution' } }
            }
        }
    });
}

function renderDriverTable(drivers) {
    const tbody = document.querySelector('#s6-driver-table tbody');
    tbody.innerHTML = '';
    drivers.forEach(d => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><code>${d.feature}</code></td>
            <td>${d.coefficient.toFixed(3)}</td>
            <td>${d.diff.toFixed(3)}</td>
            <td class="fw-bold ${d.driver_score > 0 ? 'text-primary' : 'text-warning-emphasis'}">
                ${d.driver_score.toFixed(4)}
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// ==========================================
// SCREEN 6: FEATURE ABLATION SANDBOX
// ==========================================
async function runAblationSimulation() {
    const attrToDrop = document.getElementById('s6-ablate-select').value;
    const dropProxies = document.getElementById('s6-drop-proxies-check').checked;

    try {
        const res = await fetch('/api/fairness/ablate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                attribute_to_drop: attrToDrop,
                drop_proxies: dropProxies,
                protected_attribute: state.activeProtectedAttr
            })
        });
        const data = await res.json();
        if (data.error) {
            alert(data.error);
            return;
        }

        // Populate Before vs After Table
        document.getElementById('abl-before-ratio').textContent = data.before.four_fifths_ratio.toFixed(3);
        document.getElementById('abl-after-ratio').textContent = data.after.four_fifths_ratio.toFixed(3);
        formatDeltaCell('abl-delta-ratio', data.delta.four_fifths_ratio, true);
        document.getElementById('abl-interp-ratio').textContent = data.delta.four_fifths_ratio >= 0 ? 'Fairness Improved/Maintained' : 'Fairness Degraded';

        document.getElementById('abl-before-srgap').textContent = (data.before.selection_rate_gap * 100).toFixed(1) + '%';
        document.getElementById('abl-after-srgap').textContent = (data.after.selection_rate_gap * 100).toFixed(1) + '%';
        formatDeltaCell('abl-delta-srgap', data.delta.selection_rate_gap, false);
        document.getElementById('abl-interp-srgap').textContent = data.delta.selection_rate_gap <= 0 ? 'Selection Gap Narrowed' : 'Selection Gap Widened';

        document.getElementById('abl-before-recallgap').textContent = (data.before.recall_gap * 100).toFixed(1) + '%';
        document.getElementById('abl-after-recallgap').textContent = (data.after.recall_gap * 100).toFixed(1) + '%';
        formatDeltaCell('abl-delta-recallgap', data.delta.recall_gap, false);
        document.getElementById('abl-interp-recallgap').textContent = data.delta.recall_gap <= 0 ? 'Recall Gap Narrowed' : 'Recall Gap Widened';

        document.getElementById('abl-before-acc').textContent = (data.before.accuracy * 100).toFixed(1) + '%';
        document.getElementById('abl-after-acc').textContent = (data.after.accuracy * 100).toFixed(1) + '%';
        formatDeltaCell('abl-delta-acc', data.delta.accuracy, true);
        document.getElementById('abl-interp-acc').textContent = `${(data.after.accuracy * 100).toFixed(1)}% Accuracy Retained`;

        document.getElementById('abl-before-auc').textContent = data.before.auc.toFixed(3);
        document.getElementById('abl-after-auc').textContent = data.after.auc.toFixed(3);
        formatDeltaCell('abl-delta-auc', data.delta.auc, true);
        document.getElementById('abl-interp-auc').textContent = `${data.after.auc.toFixed(3)} AUC`;

        // Note
        document.getElementById('s6-ablation-note').textContent = data.explanation_note;
    } catch (err) {
        console.error('Ablation error:', err);
    }
}

function formatDeltaCell(elemId, val, higherIsBetter) {
    const el = document.getElementById(elemId);
    const sign = val > 0 ? '+' : '';
    el.textContent = `${sign}${val.toFixed(3)}`;
    if (val === 0) {
        el.className = 'text-muted';
    } else if ((higherIsBetter && val > 0) || (!higherIsBetter && val < 0)) {
        el.className = 'delta-pos';
    } else {
        el.className = 'delta-neg';
    }
}

// Upload CSV Dataset
async function uploadCsvDataset() {
    const fileInput = document.getElementById('csvFileInput');
    if (!fileInput.files || fileInput.files.length === 0) {
        alert('Please select a CSV file.');
        return;
    }
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    const statusEl = document.getElementById('uploadStatus');
    statusEl.innerHTML = '<div class="spinner-border spinner-border-sm text-primary" role="status"></div> Processing dataset...';

    try {
        const res = await fetch('/api/dataset', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.error) {
            statusEl.innerHTML = `<span class="text-danger">${data.error}</span>`;
            return;
        }
        statusEl.innerHTML = '<span class="text-success"><i class="bi bi-check-circle"></i> Loaded successfully!</span>';
        setTimeout(() => {
            const modalEl = document.getElementById('uploadModal');
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
            // Reload all screens
            loadScreen1Data();
            loadScreen2Data();
            loadScreen3Metrics();
            loadScreen4Shortlist();
            loadScreen6FairnessAudit();
        }, 800);
    } catch (err) {
        statusEl.innerHTML = `<span class="text-danger">Upload failed: ${err.message}</span>`;
    }
}
