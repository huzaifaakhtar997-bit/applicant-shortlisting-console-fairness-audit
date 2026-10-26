/**
 * FairRecruit Console - Frontend Application Logic
 * DSC306 Data Mining Master Specification Implementation (Screens 1 through 6)
 */

const state = {
    threshold: 0.50,
    modelType: 'decision_tree',
    currentPage: 1,
    perPage: 25,
    topN: null,
    filterStatus: 'all',
    activeProtectedAttr: 'gender',
    charts: {}
};

document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    loadScreen1Data();
    loadScreen2Models();
    loadScreen4Shortlist();
    loadScreen5CostMatrix();
    loadScreen6FairnessAudit();
});

function initEventListeners() {
    // Screen 2: Refresh Models
    const btnRefresh = document.getElementById('btn-refresh-models');
    if (btnRefresh) {
        btnRefresh.addEventListener('click', loadScreen2Models);
    }

    // Screen 3: Single Prediction
    const btnSinglePred = document.getElementById('btn-run-single-pred');
    if (btnSinglePred) {
        btnSinglePred.addEventListener('click', runSinglePrediction);
    }

    // Screen 4: Shortlist Controls
    const s4Slider = document.getElementById('s4-thresh-slider');
    const s4ThreshVal = document.getElementById('s4-thresh-val');
    if (s4Slider) {
        s4Slider.addEventListener('input', (e) => {
            state.threshold = parseFloat(e.target.value);
            s4ThreshVal.textContent = state.threshold.toFixed(2);
            syncGlobalThreshold();
        });
    }

    const s4Apply = document.getElementById('s4-btn-apply');
    if (s4Apply) {
        s4Apply.addEventListener('click', () => {
            const topNVal = document.getElementById('s4-topn-input').value;
            state.topN = topNVal ? parseInt(topNVal) : null;
            state.filterStatus = document.getElementById('s4-filter-select').value;
            state.currentPage = 1;
            loadScreen4Shortlist();
        });
    }

    const s4Prev = document.getElementById('s4-btn-prev');
    if (s4Prev) {
        s4Prev.addEventListener('click', () => {
            if (state.currentPage > 1) {
                state.currentPage--;
                loadScreen4Shortlist();
            }
        });
    }

    const s4Next = document.getElementById('s4-btn-next');
    if (s4Next) {
        s4Next.addEventListener('click', () => {
            state.currentPage++;
            loadScreen4Shortlist();
        });
    }

    const s4Export = document.getElementById('s4-btn-export');
    if (s4Export) {
        s4Export.addEventListener('click', () => {
            const filter = document.getElementById('s4-filter-select').value;
            window.location.href = `/api/shortlist?threshold=${state.threshold}&filter=${filter}&export=true`;
        });
    }

    const drawerClose = document.getElementById('drawer-close-btn');
    if (drawerClose) {
        drawerClose.addEventListener('click', () => {
            document.getElementById('s4-criteria-drawer').classList.add('d-none');
        });
    }

    // Screen 5: Settings & Cost Matrix
    const s5Slider = document.getElementById('s5-thresh-slider');
    const s5Badge = document.getElementById('s5-thresh-badge');
    if (s5Slider) {
        s5Slider.addEventListener('input', (e) => {
            state.threshold = parseFloat(e.target.value);
            s5Badge.textContent = state.threshold.toFixed(2);
            syncGlobalThreshold();
            loadScreen5CostMatrix();
        });
    }

    const s5ModelSelect = document.getElementById('s5-model-select');
    if (s5ModelSelect) {
        s5ModelSelect.addEventListener('change', (e) => {
            state.modelType = e.target.value;
            fetch('/api/train', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_type: state.modelType, threshold: state.threshold })
            }).then(() => {
                syncGlobalModelBadge();
                loadScreen2Models();
                loadScreen4Shortlist();
                loadScreen5CostMatrix();
                loadScreen6FairnessAudit();
            });
        });
    }

    const btnUpdateCost = document.getElementById('btn-update-cost-matrix');
    if (btnUpdateCost) {
        btnUpdateCost.addEventListener('click', loadScreen5CostMatrix);
    }

    // Screen 6: Protected Attribute Selector
    document.querySelectorAll('#fairnessAttrPills button').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('#fairnessAttrPills button').forEach(b => b.classList.remove('active'));
            e.currentTarget.classList.add('active');
            state.activeProtectedAttr = e.currentTarget.getAttribute('data-attr');
            loadScreen6FairnessAudit();
        });
    });

    // Screen 6: Feature Ablation Button
    const btnAblate = document.getElementById('btn-run-ablation');
    if (btnAblate) {
        btnAblate.addEventListener('click', runFeatureAblation);
    }

    // Upload Form
    const uploadForm = document.getElementById('upload-csv-form');
    if (uploadForm) {
        uploadForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const formData = new FormData(uploadForm);
            fetch('/api/dataset', { method: 'POST', body: formData })
                .then(res => res.json())
                .then(data => {
                    const modalEl = document.getElementById('uploadModal');
                    const modal = bootstrap.Modal.getInstance(modalEl);
                    if (modal) modal.hide();
                    alert("Custom applicant pool uploaded and audited successfully!");
                    loadScreen1Data();
                    loadScreen2Models();
                    loadScreen4Shortlist();
                    loadScreen6FairnessAudit();
                }).catch(err => alert("Upload error: " + err));
        });
    }
}

function syncGlobalThreshold() {
    document.getElementById('global-thresh-badge').textContent = `Threshold: ${state.threshold.toFixed(2)}`;
    const s4Slider = document.getElementById('s4-thresh-slider');
    const s4Val = document.getElementById('s4-thresh-val');
    if (s4Slider) s4Slider.value = state.threshold;
    if (s4Val) s4Val.textContent = state.threshold.toFixed(2);

    const s5Slider = document.getElementById('s5-thresh-slider');
    const s5Badge = document.getElementById('s5-thresh-badge');
    if (s5Slider) s5Slider.value = state.threshold;
    if (s5Badge) s5Badge.textContent = state.threshold.toFixed(2);
}

function syncGlobalModelBadge() {
    const formatted = state.modelType.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
    document.getElementById('global-model-badge').textContent = `Model: ${formatted}`;
    const s5Select = document.getElementById('s5-model-select');
    if (s5Select) s5Select.value = state.modelType;
}


// ==============================================================================
// SCREEN 1: DATA & QUALITY (Stage A & B)
// ==============================================================================

function loadScreen1Data() {
    fetch('/api/dataset')
        .then(res => res.json())
        .then(data => {
            document.getElementById('s1-total-rows').textContent = (data.total_rows || 0).toLocaleString();
            if (data.class_balance) {
                document.getElementById('s1-target-split').textContent =
                    `${data.class_balance.positive_pct}% / ${data.class_balance.negative_pct}%`;
            }
            if (data.majority_baseline_accuracy) {
                const basePct = (data.majority_baseline_accuracy * 100).toFixed(2);
                document.getElementById('s1-baseline-acc').textContent = `${basePct}%`;
                document.getElementById('global-base-badge').textContent = `Baseline Acc: ${basePct}%`;
            }
            document.getElementById('s1-total-features').textContent = data.num_features || 34;

            // Populate Faults Table
            const faultsTbody = document.getElementById('faults-tbody');
            faultsTbody.innerHTML = '';
            if (data.quality_audit && data.quality_audit.faults) {
                data.quality_audit.faults.forEach(f => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td><span class="badge bg-light text-dark border fw-semibold">${f.category}</span></td>
                        <td><code>${f.attribute}</code></td>
                        <td><code class="text-danger" style="font-size: 0.75rem;">${f.expression}</code></td>
                        <td><span class="badge bg-warning text-dark">${f.affected_count.toLocaleString()}</span></td>
                        <td class="small text-muted">${f.remediation}</td>
                    `;
                    faultsTbody.appendChild(tr);
                });
            }

            // Populate 10 Assertions Validate List
            const validateList = document.getElementById('validate-list');
            validateList.innerHTML = '';
            if (data.validation_results && data.validation_results.cleaned_assertions) {
                data.validation_results.cleaned_assertions.forEach((item, idx) => {
                    const li = document.createElement('li');
                    li.className = 'list-group-item d-flex justify-content-between align-items-center py-2';
                    li.innerHTML = `
                        <span><b>${idx + 1}.</b> ${item.assertion}</span>
                        <span class="badge bg-success"><i class="bi bi-check-circle me-1"></i> PASS</span>
                    `;
                    validateList.appendChild(li);
                });
            }

            // Populate Before & After Repair Table
            const baTbody = document.getElementById('before-after-tbody');
            baTbody.innerHTML = '';
            if (data.before_after_table) {
                data.before_after_table.forEach(row => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td><code>${row.field}</code></td>
                        <td><span class="badge bg-secondary">${row.fault}</span></td>
                        <td><code style="font-size: 0.75rem;">${row.expression}</code></td>
                        <td><span class="badge bg-danger">${row.before_count.toLocaleString()}</span></td>
                        <td><span class="badge bg-success">${row.after_count}</span></td>
                        <td class="small text-muted">${row.action_taken}</td>
                    `;
                    baTbody.appendChild(tr);
                });
            }

            // Populate Data Dictionary
            const dictTbody = document.getElementById('data-dictionary-tbody');
            dictTbody.innerHTML = '';
            if (data.data_dictionary) {
                data.data_dictionary.forEach(col => {
                    const tr = document.createElement('tr');
                    const roleBadge = col.role.includes('MUST NOT') ? 'bg-danger' : (col.role.includes('Protected') ? 'bg-warning text-dark' : 'bg-primary');
                    tr.innerHTML = `
                        <td><b><code>${col.column}</code></b></td>
                        <td><span class="badge bg-light text-dark border">${col.type}</span></td>
                        <td><small>${col.plausible_range}</small></td>
                        <td><span class="badge ${roleBadge}">${col.role}</span></td>
                        <td><small class="text-muted">${col.description}</small></td>
                    `;
                    dictTbody.appendChild(tr);
                });
            }
        });
}


// ==============================================================================
// SCREEN 2: MODEL PERFORMANCE (Stage C, D, E)
// ==============================================================================

function loadScreen2Models() {
    // 1. Load multi-model comparison
    fetch('/api/models/compare')
        .then(res => res.json())
        .then(data => {
            const tbody = document.getElementById('model-comparison-tbody');
            tbody.innerHTML = '';
            const baseAcc = data.majority_baseline_accuracy || 0.751;
            const basePct = (baseAcc * 100).toFixed(1);

            let firstRoc = null;

            data.comparison.forEach(m => {
                const accPct = (m.accuracy * 100).toFixed(1);
                const delta = (m.baseline_delta * 100).toFixed(1);
                const deltaBadge = m.baseline_delta >= 0 ?
                    `<span class="badge bg-success ms-1">+${delta}%</span>` :
                    `<span class="badge bg-danger ms-1">${delta}%</span>`;

                if (!firstRoc && m.roc_curve) firstRoc = m.roc_curve;

                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><b>${m.model_name}</b></td>
                    <td><span class="badge bg-light text-dark border">${m.family}</span></td>
                    <td>
                        <span class="fw-bold">${accPct}%</span>
                        <small class="text-muted d-block" style="font-size: 0.75rem;">(Baseline: ${basePct}%) ${deltaBadge}</small>
                    </td>
                    <td>${(m.precision * 100).toFixed(1)}%</td>
                    <td>${(m.recall * 100).toFixed(1)}%</td>
                    <td>${(m.f1 * 100).toFixed(1)}%</td>
                    <td><span class="badge bg-info text-dark">${m.auc.toFixed(3)}</span></td>
                    <td><small class="text-muted">${m.cv_spread || 'N/A'}</small></td>
                    <td><small>${m.explanation_type}</small></td>
                `;
                tbody.appendChild(tr);
            });

            if (firstRoc) renderRocChart('s2-roc-chart', firstRoc);

            // Update confusion matrix for active model
            if (data.comparison.length > 0) {
                const active = data.comparison.find(x => x.model_id === state.modelType) || data.comparison[0];
                if (active.confusion_matrix) {
                    document.getElementById('s2-cm-tn').textContent = active.confusion_matrix.tn.toLocaleString();
                    document.getElementById('s2-cm-fp').textContent = active.confusion_matrix.fp.toLocaleString();
                    document.getElementById('s2-cm-fn').textContent = active.confusion_matrix.fn.toLocaleString();
                    document.getElementById('s2-cm-tp').textContent = active.confusion_matrix.tp.toLocaleString();
                }
            }
        });

    // 2. Load Feature Selection vs PCA comparison
    fetch('/api/models/dim_reduction_compare')
        .then(res => res.json())
        .then(data => {
            const tbody = document.getElementById('pca-comparison-tbody');
            tbody.innerHTML = '';
            data.comparison.forEach(row => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><b>${row.technique}</b></td>
                    <td><span class="badge bg-secondary">${row.components_or_features} Dimensions</span></td>
                    <td><b>${(row.accuracy * 100).toFixed(1)}%</b></td>
                    <td>${(row.majority_baseline * 100).toFixed(1)}%</td>
                    <td><span class="badge bg-primary">${row.auc.toFixed(3)}</span></td>
                    <td>${(row.precision * 100).toFixed(1)}%</td>
                    <td>${(row.recall * 100).toFixed(1)}%</td>
                    <td><small class="text-muted">${row.interpretability}</small></td>
                `;
                tbody.appendChild(tr);
            });
        });
}

function renderRocChart(canvasId, rocPoints) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    if (state.charts[canvasId]) state.charts[canvasId].destroy();

    const dataPoints = rocPoints.map(p => ({ x: p.fpr, y: p.tpr }));

    state.charts[canvasId] = new Chart(ctx, {
        type: 'line',
        data: {
            datasets: [
                {
                    label: 'ROC Curve (AUC Evaluated)',
                    data: dataPoints,
                    borderColor: '#2B6CB0',
                    backgroundColor: 'rgba(43, 108, 176, 0.1)',
                    fill: true,
                    tension: 0.2,
                    pointRadius: 2
                },
                {
                    label: 'Chance Diagonal (Zero Discrimination)',
                    data: [{ x: 0, y: 0 }, { x: 1, y: 1 }],
                    borderColor: '#CBD5E0',
                    borderDash: [5, 5],
                    pointRadius: 0,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { type: 'linear', min: 0, max: 1, title: { display: true, text: 'False Positive Rate (FPR)' } },
                y: { type: 'linear', min: 0, max: 1, title: { display: true, text: 'True Positive Rate (Recall / TPR)' } }
            }
        }
    });
}


// ==============================================================================
// SCREEN 3: SINGLE PREDICTION (Stage F)
// ==============================================================================

function runSinglePrediction() {
    const payload = {
        city_development_index: parseFloat(document.getElementById('sp-cdi').value),
        experience: document.getElementById('sp-experience').value,
        education_level: document.getElementById('sp-education').value,
        enrolled_university: document.getElementById('sp-enrollment').value,
        training_hours: parseFloat(document.getElementById('sp-training-hours').value),
        company_size: document.getElementById('sp-company-size').value,
        gender: document.getElementById('sp-gender').value,
        relevent_experience: document.getElementById('sp-relevent-exp').value
    };

    fetch('/api/predict/single', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        const container = document.getElementById('sp-result-container');
        const isShort = data.shortlisted;
        const verdictBadge = isShort ?
            `<span class="badge bg-success fs-5 px-3 py-2"><i class="bi bi-check-circle-fill me-2"></i>PROCEED TO INTERVIEW</span>` :
            `<span class="badge bg-danger fs-5 px-3 py-2"><i class="bi bi-x-circle-fill me-2"></i>HOLD / REJECT</span>`;

        let rulesHtml = '';
        if (data.decision_rules && data.decision_rules.length > 0) {
            rulesHtml = data.decision_rules.map(r => `<li class="list-group-item small py-2"><i class="bi bi-arrow-right-short text-primary"></i> ${r}</li>`).join('');
        }

        container.innerHTML = `
            <div class="text-center mb-4">
                <span class="text-muted small text-uppercase fw-semibold d-block mb-1">Recommendation Verdict</span>
                ${verdictBadge}
                <div class="mt-3">
                    <span class="fs-4 fw-bold text-dark">${data.confidence_pct}% Match Confidence</span>
                    <div class="progress mt-2" style="height: 10px;">
                        <div class="progress-bar ${isShort ? 'bg-success' : 'bg-danger'}" style="width: ${data.confidence_pct}%;"></div>
                    </div>
                    <small class="text-muted">Threshold cutoff: ${data.threshold.toFixed(2)} | Model: ${data.model_type}</small>
                </div>
            </div>

            <div class="mb-3">
                <h6 class="fw-bold mb-2"><i class="bi bi-diagram-3-fill text-primary me-1"></i>Decision Path & Rule Set (Stage F):</h6>
                <ul class="list-group list-group-flush border rounded">
                    ${rulesHtml}
                </ul>
            </div>

            <div class="alert alert-light border small mb-0">
                <h6 class="fw-bold text-primary mb-1"><i class="bi bi-chat-quote-fill me-1"></i>Executive Recruiter Explanation:</h6>
                <p class="mb-0 text-muted">${data.executive_narrative}</p>
            </div>
        `;
    });
}


// ==============================================================================
// SCREEN 4: BATCH SCORING
// ==============================================================================

function loadScreen4Shortlist() {
    const url = `/api/shortlist?threshold=${state.threshold}&page=${state.currentPage}&per_page=${state.perPage}&filter=${state.filterStatus}${state.topN ? '&top_n=' + state.topN : ''}`;
    fetch(url)
        .then(res => res.json())
        .then(data => {
            document.getElementById('s4-count-badge').textContent =
                `Shortlisted: ${data.total_shortlisted.toLocaleString()} / ${data.total_candidates.toLocaleString()} (${(data.selection_rate * 100).toFixed(1)}%)`;

            document.getElementById('s4-page-info').textContent =
                `Showing page ${data.page} of ${data.total_pages || 1} (${data.total_candidates.toLocaleString()} candidates)`;

            const tbody = document.getElementById('shortlist-tbody');
            tbody.innerHTML = '';

            data.applicants.forEach(app => {
                const tr = document.createElement('tr');
                const isShort = app.shortlisted;
                tr.innerHTML = `
                    <td><b>#${app.rank}</b></td>
                    <td><code>${app.enrollee_id}</code></td>
                    <td>
                        <div class="d-flex align-items-center gap-2">
                            <span class="fw-bold">${(app.score * 100).toFixed(1)}%</span>
                            <div class="progress flex-grow-1" style="height: 6px; width: 60px;">
                                <div class="progress-bar ${isShort ? 'bg-success' : 'bg-secondary'}" style="width: ${(app.score * 100)}%;"></div>
                            </div>
                        </div>
                    </td>
                    <td>
                        <span class="badge ${isShort ? 'bg-success' : 'bg-secondary'}">
                            ${isShort ? 'SHORTLISTED' : 'HELD'}
                        </span>
                    </td>
                    <td>${app.gender}</td>
                    <td><span class="badge bg-light text-dark border">${app.age_band}</span></td>
                    <td><small>${app.institution}</small></td>
                    <td><small>${app.education_level}</small></td>
                    <td>${app.experience} yrs</td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary py-0" onclick="explainCandidate('${app.enrollee_id}')">
                            <i class="bi bi-search"></i> Criteria
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        });
}

function explainCandidate(applicantId) {
    const drawer = document.getElementById('s4-criteria-drawer');
    const title = document.getElementById('drawer-title');
    const body = document.getElementById('drawer-body');

    if (!drawer || !title || !body) return;

    // Show loading state immediately so recruiter gets instant feedback
    drawer.classList.remove('d-none');
    title.innerHTML = `<i class="bi bi-hourglass-split me-2"></i>Analyzing Selection Criteria for Candidate #${applicantId}...`;
    body.innerHTML = `
        <div class="text-center py-4 text-primary">
            <div class="spinner-border text-primary mb-2" role="status"></div>
            <p class="small text-muted mb-0">Computing individualized criteria breakdown and model feature attribution...</p>
        </div>
    `;
    drawer.scrollIntoView({ behavior: 'smooth' });

    fetch(`/api/explain/${applicantId}`)
        .then(res => {
            if (!res.ok) throw new Error(`HTTP Error ${res.status}: Failed to load candidate criteria`);
            return res.json();
        })
        .then(data => {
            if (data.error) {
                body.innerHTML = `<div class="alert alert-danger py-2"><i class="bi bi-exclamation-triangle-fill me-2"></i>${data.error}</div>`;
                return;
            }

            const matchScore = (data.match_score !== undefined) ? data.match_score : (data.score * 100).toFixed(1);
            const threshScore = ((data.threshold || 0.5) * 100).toFixed(1);
            const isShort = data.shortlisted;
            const badgeClass = isShort ? 'bg-success' : 'bg-secondary';
            const verdictText = data.verdict || (isShort ? 'SHORTLISTED FOR INTERVIEW' : 'NOT SHORTLISTED');

            title.innerHTML = `
                <div class="d-flex align-items-center justify-content-between flex-wrap gap-2 w-100">
                    <div>
                        <i class="bi bi-person-badge me-2"></i>Candidate #${data.applicant_id} — Selection Criteria Breakdown
                    </div>
                    <div class="d-flex align-items-center gap-2">
                        <span class="badge ${badgeClass} fs-6">${verdictText}</span>
                        <span class="badge bg-light text-dark fs-6">${matchScore}% Match <small class="text-muted">(Cutoff: ${threshScore}%)</small></span>
                    </div>
                </div>
            `;

            // Candidate profile pills
            const prof = data.profile || {};
            const demo = data.demographics || {};
            const profilePills = `
                <div class="d-flex flex-wrap gap-2 align-items-center p-2 mb-3 bg-light rounded border">
                    <span class="badge bg-white text-dark border"><i class="bi bi-briefcase me-1 text-primary"></i>Experience: <strong>${prof.experience || 'N/A'} yrs</strong></span>
                    <span class="badge bg-white text-dark border"><i class="bi bi-mortarboard me-1 text-primary"></i>Education: <strong>${prof.education_level || 'Graduate'}</strong></span>
                    <span class="badge bg-white text-dark border"><i class="bi bi-book me-1 text-primary"></i>Major: <strong>${prof.major_discipline || 'STEM'}</strong></span>
                    <span class="badge bg-white text-dark border"><i class="bi bi-geo-alt me-1 text-primary"></i>City Dev Index: <strong>${prof.city_development_index !== undefined ? prof.city_development_index : '0.82'}</strong></span>
                    <span class="badge bg-white text-dark border"><i class="bi bi-clock-history me-1 text-primary"></i>Training: <strong>${prof.training_hours !== undefined ? prof.training_hours : '50'} hrs</strong></span>
                    <span class="badge bg-white text-dark border"><i class="bi bi-building me-1 text-primary"></i>Company Scale: <strong>${prof.company_size || 'N/A'}</strong></span>
                    <span class="badge bg-white text-dark border"><i class="bi bi-arrow-repeat me-1 text-primary"></i>Tenure: <strong>${prof.last_new_job || '1'} yrs</strong></span>
                </div>
            `;

            const posList = (data.top_positive_drivers || data.positive_drivers || []);
            let posDrivers = posList.map(d => `
                <li class="list-group-item py-2">
                    <div class="d-flex justify-content-between align-items-start">
                        <span class="fw-semibold text-success"><i class="bi bi-plus-circle-fill me-1"></i> ${d.display_name || d.label || d.feature}</span>
                        <span class="badge bg-success-subtle text-success border border-success-subtle">+${Math.abs(d.impact || d.contribution || 0).toFixed(3)}</span>
                    </div>
                    <p class="small text-muted mb-0 mt-1">${d.explanation || 'Credential elevates candidate qualification score.'}</p>
                </li>
            `).join('');

            const negList = (data.top_negative_inhibitors || data.negative_drivers || []);
            let negInhibitors = negList.map(d => `
                <li class="list-group-item py-2">
                    <div class="d-flex justify-content-between align-items-start">
                        <span class="fw-semibold text-danger"><i class="bi bi-dash-circle-fill me-1"></i> ${d.display_name || d.label || d.feature}</span>
                        <span class="badge bg-danger-subtle text-danger border border-danger-subtle">${(d.impact || d.contribution || 0) < 0 ? (d.impact || d.contribution).toFixed(3) : '-' + (d.impact || d.contribution || 0).toFixed(3)}</span>
                    </div>
                    <p class="small text-muted mb-0 mt-1">${d.explanation || 'Credential falls below competitive pool median.'}</p>
                </li>
            `).join('');

            body.innerHTML = `
                ${profilePills}
                <div class="alert alert-light border border-primary-subtle shadow-sm mb-3">
                    <h6 class="fw-bold text-dark mb-2"><i class="bi bi-chat-left-quote-fill text-primary me-2"></i>Executive Hiring Reasoning:</h6>
                    <p class="mb-0 text-secondary lh-base">${data.hiring_reasoning || (data.executive_reasoning ? data.executive_reasoning.detailed_narrative : 'Evaluation completed.')}</p>
                </div>
                <div class="row g-3">
                    <div class="col-md-6">
                        <h6 class="fw-bold text-success mb-2"><i class="bi bi-arrow-up-circle me-1"></i>Top Positive Drivers (Advancing Shortlist)</h6>
                        <ul class="list-group list-group-flush border rounded small">
                            ${posDrivers || '<li class="list-group-item text-muted">Baseline credentials aligned with pool benchmark.</li>'}
                        </ul>
                    </div>
                    <div class="col-md-6">
                        <h6 class="fw-bold text-danger mb-2"><i class="bi bi-arrow-down-circle me-1"></i>Top Negative Inhibitors (Areas for Interview Review)</h6>
                        <ul class="list-group list-group-flush border rounded small">
                            ${negInhibitors || '<li class="list-group-item text-muted">No negative inhibitors detected.</li>'}
                        </ul>
                    </div>
                </div>
                <div class="mt-3 pt-2 border-top text-muted small d-flex justify-content-between align-items-center flex-wrap gap-2">
                    <span><i class="bi bi-shield-check text-success me-1"></i><strong>Fair Hiring Compliance:</strong> Demographic attributes (Gender: <em>${demo.gender || 'Unknown'}</em>, Age Band: <em>${demo.age_band || 'N/A'}</em>, Institution: <em>${demo.institution || 'N/A'}</em>) are audited under the 80% Four-Fifths Adverse Impact rule.</span>
                    <button class="btn btn-sm btn-outline-secondary" onclick="document.getElementById('s4-criteria-drawer').classList.add('d-none')"><i class="bi bi-x-lg me-1"></i>Close Breakdown</button>
                </div>
            `;
            drawer.scrollIntoView({ behavior: 'smooth' });
        })
        .catch(err => {
            console.error('Error in explainCandidate:', err);
            body.innerHTML = `
                <div class="alert alert-danger py-2">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i><strong>Error loading criteria:</strong> ${err.message}. Please verify the backend server is running.
                </div>
            `;
        });
}



// ==============================================================================
// SCREEN 5: SETTINGS & COST MATRIX (Stage E)
// ==============================================================================

function loadScreen5CostMatrix() {
    const costFp = document.getElementById('cm-cost-fp').value || 500;
    const costFn = document.getElementById('cm-cost-fn').value || 3500;
    const benTp = document.getElementById('cm-benefit-tp').value || 5000;
    const costTn = document.getElementById('cm-cost-tn').value || 0;

    fetch(`/api/settings/cost_matrix?cost_fp=${costFp}&cost_fn=${costFn}&benefit_tp=${benTp}&cost_tn=${costTn}`)
        .then(res => res.json())
        .then(data => {
            const optimalThresh = data.optimal_threshold;
            document.getElementById('s5-optimal-thresh-badge').textContent = `Cost-Optimal θ*: ${optimalThresh.toFixed(2)}`;

            // Render Cost Curve Chart
            const ctx = document.getElementById('s5-cost-chart');
            if (ctx && data.cost_curve) {
                if (state.charts['s5-cost-chart']) state.charts['s5-cost-chart'].destroy();

                const pts = data.cost_curve.map(c => ({ x: c.threshold, y: c.expected_cost }));
                state.charts['s5-cost-chart'] = new Chart(ctx, {
                    type: 'line',
                    data: {
                        datasets: [{
                            label: 'Expected Net Financial Cost ($)',
                            data: pts,
                            borderColor: '#C53030',
                            backgroundColor: 'rgba(197, 48, 48, 0.1)',
                            fill: true,
                            tension: 0.2,
                            pointRadius: 2
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            x: { type: 'linear', title: { display: true, text: 'Decision Threshold (θ)' } },
                            y: { title: { display: true, text: 'Expected Financial Cost ($)' } }
                        }
                    }
                });
            }

            // Update stats at current threshold
            const currentItem = data.cost_curve.find(c => Math.abs(c.threshold - state.threshold) < 0.02) || data.cost_curve[0];
            if (currentItem) {
                document.getElementById('s5-stat-thresh').textContent = currentItem.threshold.toFixed(2);
                document.getElementById('s5-stat-cost').textContent = `$${Math.round(currentItem.expected_cost).toLocaleString()}`;
                document.getElementById('s5-stat-shortlisted').textContent = currentItem.shortlisted_count.toLocaleString();
                const prec = currentItem.tp / (currentItem.tp + currentItem.fp || 1);
                document.getElementById('s5-stat-prec').textContent = `${(prec * 100).toFixed(1)}%`;
            }
        });
}


// ==============================================================================
// SCREEN 6: DOMAIN SCREEN — FAIRNESS AUDIT (PROJECT 5 CHALLENGE)
// ==============================================================================

function loadScreen6FairnessAudit() {
    fetch(`/api/fairness/audit?threshold=${state.threshold}&attribute=${state.activeProtectedAttr}`)
        .then(res => res.json())
        .then(data => {
            const auditData = data.audit;
            const driverData = data.drivers;

            // Update Adverse Impact badge
            const adverseBadge = document.getElementById('s6-adverse-badge');
            if (auditData.adverse_impact_flagged) {
                adverseBadge.className = 'badge bg-danger';
                adverseBadge.innerHTML = '<i class="bi bi-shield-x me-1"></i> EEOC 80% Rule Violation Detected';
            } else {
                adverseBadge.className = 'badge bg-success';
                adverseBadge.innerHTML = '<i class="bi bi-shield-check me-1"></i> All Subgroups Comply with 80% Rule';
            }

            // Populate Demographic Table
            const tbody = document.getElementById('s6-audit-tbody');
            tbody.innerHTML = '';

            auditData.groups.forEach(g => {
                const tr = document.createElement('tr');
                const ratioPct = (g.four_fifths_ratio * 100).toFixed(1);
                const isViolated = g.violates_80_rule;
                const ratioBadge = isViolated ?
                    `<span class="badge bg-danger fs-6">${ratioPct}% (VIOLATION)</span>` :
                    `<span class="badge bg-success">${ratioPct}%</span>`;

                const smallSampleBadge = g.small_sample_warning ?
                    `<span class="badge bg-warning text-dark"><i class="bi bi-exclamation-triangle"></i> N &lt; 30 (Volatile)</span>` :
                    `<span class="badge bg-light text-dark border">Reliable (N &ge; 30)</span>`;

                tr.innerHTML = `
                    <td><b>${g.group}</b></td>
                    <td>${g.count.toLocaleString()}</td>
                    <td>${g.shortlisted.toLocaleString()}</td>
                    <td><b>${(g.selection_rate * 100).toFixed(1)}%</b></td>
                    <td>${ratioBadge}</td>
                    <td>${(g.recall * 100).toFixed(1)}%</td>
                    <td>${(g.precision * 100).toFixed(1)}%</td>
                    <td>${smallSampleBadge}</td>
                `;
                tbody.appendChild(tr);
            });

            // Render Disparity Drivers Chart
            renderDriversChart(driverData);
        });
}

function renderDriversChart(driverData) {
    const ctx = document.getElementById('s6-drivers-chart');
    if (!ctx || !driverData || !driverData.drivers) return;
    if (state.charts['s6-drivers-chart']) state.charts['s6-drivers-chart'].destroy();

    const topDrivers = driverData.drivers.slice(0, 6);
    const labels = topDrivers.map(d => d.feature);
    const impacts = topDrivers.map(d => d.disparity_impact);

    state.charts['s6-drivers-chart'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Disparity Impact (β × Δx̄)',
                data: impacts,
                backgroundColor: impacts.map(v => v >= 0 ? '#C53030' : '#2B6CB0')
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

function runFeatureAblation() {
    const featureToDrop = document.getElementById('ablate-feature-select').value;
    const dropProxies = document.getElementById('ablate-drop-proxies').checked;

    fetch('/api/fairness/ablate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            attribute_to_drop: featureToDrop,
            drop_proxies: dropProxies,
            protected_attribute: state.activeProtectedAttr
        })
    })
    .then(res => res.json())
    .then(data => {
        const container = document.getElementById('ablation-results-container');
        const gapBefore = (data.gap_before * 100).toFixed(1);
        const gapAfter = (data.gap_after * 100).toFixed(1);
        const gapDelta = (data.gap_delta * 100).toFixed(1);

        const aucBefore = data.auc_before.toFixed(3);
        const aucAfter = data.auc_after.toFixed(3);
        const aucDelta = data.auc_delta.toFixed(3);

        container.innerHTML = `
            <div class="card bg-light border mt-3">
                <div class="card-body p-3">
                    <h6 class="fw-bold mb-2 text-dark"><i class="bi bi-sliders2 me-1"></i>Before vs. After Ablation Tradeoff:</h6>
                    <table class="table table-sm table-bordered mb-2">
                        <thead class="table-light">
                            <tr>
                                <th>Fairness & Performance Metric</th>
                                <th>Before Ablation</th>
                                <th>After Ablation</th>
                                <th>Remediation Delta</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td><b>Selection Rate Gap</b> (Demographic Parity)</td>
                                <td>${gapBefore}%</td>
                                <td><b>${gapAfter}%</b></td>
                                <td><span class="badge ${data.gap_delta <= 0 ? 'bg-success' : 'bg-danger'}">${gapDelta}%</span></td>
                            </tr>
                            <tr>
                                <td><b>ROC-AUC Performance</b></td>
                                <td>${aucBefore}</td>
                                <td><b>${aucAfter}</b></td>
                                <td><span class="badge bg-secondary">${aucDelta}</span></td>
                            </tr>
                        </tbody>
                    </table>
                    <small class="text-muted d-block">
                        <b>Audit Finding:</b> Ablating <code>${data.dropped_attribute}</code> ${data.gap_delta < 0 ? 'successfully reduced demographic disparity' : 'modified decision parity'} with an acceptable ${Math.abs(data.auc_delta * 100).toFixed(1)}% shift in ROC-AUC.
                    </small>
                </div>
            </div>
        `;
    });
}
