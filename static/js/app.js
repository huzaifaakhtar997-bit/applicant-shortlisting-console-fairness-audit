"use strict";
const state = {
  workspace: null,
  page: "overview",
  requestId: 0,
  pageNumber: 1,
  filter: "all",
  search: "",
  auditScope: "validation",
  attribute: "gender",
  intersectional: false,
  preview: null,
  evaluationScope: "validation",
};
const icons = {
  overview:
    '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  people:
    '<circle cx="9" cy="7" r="4"/><path d="M2 21v-2a4 4 0 0 1 4-4h6a4 4 0 0 1 4 4v2m6 0v-2a4 4 0 0 0-3-4M16 3a4 4 0 0 1 0 8"/>',
  chart: '<path d="M3 3v18h18M7 14l4-5 4 3 5-7"/>',
  data: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 4 16 4 16 0V5M4 12c0 4 16 4 16 0"/>',
  settings:
    '<path d="M4 6h16M4 12h16M4 18h16"/><circle cx="8" cy="6" r="2"/><circle cx="16" cy="12" r="2"/><circle cx="10" cy="18" r="2"/>',
  shield: '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6zM8 12l3 3 5-6"/>',
  upload: '<path d="M12 16V3m-5 5 5-5 5 5M3 15v5h18v-5"/>',
  download: '<path d="M12 3v13m-5-5 5 5 5-5M3 17v4h18v-4"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v.1"/>',
  layers: '<path d="m12 3 10 5-10 5L2 8zm-9 10 9 5 9-5m-18 5 9 5 9-5"/>',
  arrow: '<path d="M4 12h16m-6-6 6 6-6 6"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  close: '<path d="m6 6 12 12M6 18 18 6"/>',
  target:
    '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
  bolt: '<path d="m13 2-8 12h7l-1 8 8-12h-7z"/>',
};
const icon = (name) =>
  `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${icons[name] || icons.info}</svg>`;
const e = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const pct = (v, d = 1) => (v == null ? "N/A" : `${(v * 100).toFixed(d)}%`);
const points = (v) => (v == null ? "N/A" : `${(v * 100).toFixed(1)} pp`);
const count = (v) => (v == null ? "—" : Number(v).toLocaleString());
const dec = (v) => (v == null ? "N/A" : Number(v).toFixed(3));
const label = (v) =>
  ({
    city_development_index: "City development index",
    relevent_experience: "Relevant experience",
    enrolled_university: "University enrollment",
    education_level: "Education level",
    major_discipline: "Major discipline",
    training_hours: "Training hours",
    experience: "Years of experience",
    company_size: "Company size",
    company_type: "Company type",
    last_new_job: "Years since last job transition",
    gender: "Gender",
    experience_band: "Experience band · demo",
    education_group: "Education group · demo",
    age_band: "Age band",
    institution: "Institution",
  })[v] || v.replaceAll("_", " ");
const badge = (text, tone = "neutral") =>
  `<span class="badge ${tone}">${e(text)}</span>`;
const button = (text, action, kind = "secondary", extra = "") =>
  `<button class="button ${kind}" data-action="${e(action)}" ${extra}>${text}</button>`;
const bar = (v, warn = false) =>
  `<svg class="bar-svg" viewBox="0 0 100 8" preserveAspectRatio="none" aria-hidden="true"><rect class="bar-track" width="100" height="8" rx="4"/><rect class="bar-fill ${warn ? "warn" : ""}" width="${Math.max(0, Math.min(100, (v || 0) * 100))}" height="8" rx="4"/></svg>`;
const interval = (v) => (v ? `${pct(v[0])}–${pct(v[1])}` : "Not estimable");
const loading = (
  title = "Loading this view",
  detail = "Preparing the latest workspace evidence.",
) =>
  `<div class="loading-state"><span class="spinner"></span><strong>${e(title)}</strong><p>${e(detail)}</p></div>`;
const empty = (title, detail) =>
  `<div class="empty-state">${icon("info")}<strong>${e(title)}</strong><p>${e(detail)}</p></div>`;
const model = () => state.workspace.model;
const policyStrip = () =>
  `<div class="policy-strip"><div>${icon("settings")}<span><strong>${e(state.workspace.policy.description)}</strong><span class="quiet"> · ${e(model().model_name)} · v${e(model().model_version)}</span></span></div><a class="button ghost small" href="#settings">Edit policy ${icon("arrow")}</a></div>`;
const pages = {
  overview: [
    "WORKSPACE OVERVIEW",
    "Overview",
    "Candidate volume, active model performance, and current shortlisting policy.",
    "Overview",
  ],
  applicants: [
    "CANDIDATE DIRECTORY",
    "Applicant Pool",
    "Ranked candidates scored by the active model with policy decision status.",
    "Applicant Pool",
  ],
  fairness: [
    "AUDIT & DISPARITY",
    "Fairness Audit & Disparity Analysis",
    "Multi-metric demographic gap analysis, adverse impact screening, and controlled ablation.",
    "Fairness Audit",
  ],
  models: [
    "EVALUATION BENCHMARK",
    "Model Performance",
    "Cross-validation and held-out validation benchmarks across evaluated classifier families.",
    "Model Performance",
  ],
  data: [
    "DATA QUALITY",
    "Data Quality & Feature Dictionary",
    "Column schemas, missing value treatments, and outlier detection bounds.",
    "Data & Quality",
  ],
  settings: [
    "CONFIGURATION",
    "Model & Decision Policy Settings",
    "Configure probability thresholds, interview quotas, and active classification model.",
    "Model & Policy",
  ],
};
async function api(path, options = {}) {
  const r = await fetch(path, options);
  let data;
  try {
    data = await r.json();
  } catch {
    throw new Error(
      "The server returned an unreadable response. Check that it is running.",
    );
  }
  if (!r.ok) throw new Error(data.error || `Request failed (${r.status}).`);
  return data;
}
const post = (path, data = {}) =>
  api(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
let toastTimer;
function toast(message, error = false) {
  const n = document.getElementById("toast");
  n.textContent = message;
  n.className = `toast${error ? " error" : ""}`;
  n.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    n.hidden = true;
  }, 6500);
}
function fillIcons() {
  document.querySelectorAll("[data-icon]").forEach((n) => {
    n.innerHTML = icon(n.dataset.icon);
  });
}
async function refreshWorkspace() {
  state.workspace = await api("/api/workspace");
  document.getElementById("nav-pool-count").textContent = count(
    state.workspace.pool.total_rows,
  );
  document.getElementById("outcome-note").innerHTML =
    `${icon("info")}<span><b>Candidate Shortlisting Active:</b> The model evaluates candidate qualifications based on technical profile, education, and relevant experience to shortlist deserving applicants for interviews while monitoring demographic fairness. Actual age and institution are audited only when supplied. <a href="#data">View data context</a></span>`;
}
async function navigate() {
  const page = location.hash.slice(1) || "overview";
  if (page === "main" && state.workspace) { document.getElementById("main").focus(); return; }
  state.page = pages[page] ? page : "overview";
  const id = ++state.requestId;
  const [eyebrow, title, description, breadcrumb] = pages[state.page];
  for (const [key, value] of Object.entries({
    "page-eyebrow": eyebrow,
    "page-title": title,
    "page-description": description,
    "breadcrumb-page": breadcrumb,
  })) {
    const el = document.getElementById(key);
    if (el) el.textContent = value;
  }
  document.querySelectorAll("[data-page]").forEach((n) => {
    if (n.dataset.page === state.page) n.setAttribute("aria-current", "page");
    else n.removeAttribute("aria-current");
  });
  const content = document.getElementById("page-content");
  content.setAttribute("aria-busy", "true");
  content.innerHTML = loading();
  try {
    if (!state.workspace) await refreshWorkspace();
    const html = await {
      overview: renderOverview,
      applicants: renderApplicants,
      fairness: renderFairness,
      models: renderModels,
      data: renderData,
      settings: renderSettings,
    }[state.page]();
    if (id === state.requestId) {
      content.innerHTML = html;
      content.setAttribute("aria-busy", "false");
    }
  } catch (error) {
    if (id === state.requestId) {
      content.innerHTML =
        empty("This view could not load", error.message) +
        button("Try again", "retry");
      content.setAttribute("aria-busy", "false");
    }
    toast(error.message, true);
  }
}
function kpi(title, value, detail, name, tone = "") {
  return `<article class="kpi ${tone}"><div class="kpi-top">${e(title)}<span class="kpi-icon">${icon(name)}</span></div><div class="kpi-value">${value}</div><div class="kpi-bottom">${detail}</div></article>`;
}
async function renderOverview() {
  const w = state.workspace,
    p = w.pool,
    result = await api("/api/fairness/audit?scope=current"),
    a = result.audit.gender;
  const flags = Object.values(result.audit).filter(
    (x) => x.adverse_impact_detected === true,
  ).length;
  const ratios = Object.values(result.audit)
      .map((x) => x.min_four_fifths_ratio)
      .filter((x) => x != null),
    ratio = ratios.length ? Math.min(...ratios) : null;
  return `<div class="section-heading"><h2>Workspace Summary</h2><span class="subtext">${badge(p.source === "uploaded" ? "Uploaded candidate pool" : "Validation partition pool")} <span class="mono">${e(p.dataset_id.slice(0, 8))}</span></span></div>
 <div class="kpi-grid">${kpi("Total Pool Records", count(p.total_rows), `${e(p.name)} · ${pct(p.label_coverage, 0)} labeled`, "people")}${kpi("Selected Candidates", count(p.selected_count), `${e(w.policy.description)} <a href="#settings">Edit policy</a>`, "check")}${kpi("Overall Selection Rate", pct(p.selection_rate), `${count(p.total_rows - p.selected_count)} held records`, "chart")}${kpi("Lowest 4/5ths Ratio", dec(ratio), ratio == null ? "No selections to compare" : `${flags} group audits flagged`, "shield", flags ? "attention" : "")}</div>
 <div class="grid-main"><article class="card"><div class="section-heading"><div><h2>Demographic Selection Rates</h2><p class="subtext">Gender selection rate distribution across the current pool</p></div>${badge(a.status === "review" ? "Adverse Impact Flag" : a.status === "no_selections" ? "No Selections" : "Within 80% Threshold", a.status === "review" ? "warn" : "neutral")}</div>
 ${a.groups.map((g) => `<div class="bar-row"><span>${e(g.group)}<small class="table-note">n = ${count(g.size)}</small></span>${bar(g.selection_rate, g.violates_80_rule)}<span class="value">${pct(g.selection_rate)}</span></div>`).join("")}
 <div class="legend"><span>Selection rate</span><span class="amber">Ratio below 0.80</span></div><div class="audit-callout">${icon("info")}<span>${a.selection_rate_gap == null ? "More than one estimable group is needed to compare gaps." : `Selection Rate Gap: <b>${points(a.selection_rate_gap)}</b> between highest and lowest rates (including Unknown).`}</span></div><div class="form-actions"><a class="button secondary small" href="#fairness">View Fairness Audit Report</a></div></article>
 <article class="card"><div class="section-heading"><h2>Active Model Specification</h2>${icon("layers")}</div><div class="mini-heading">CLASSIFIER FAMILY</div><h3>${e(model().model_name)}</h3><p class="subtext">${model().active_columns.length} raw predictors · ${model().num_features} encoded features</p><div class="metric-row"><span>Label outcome coverage</span><strong>${pct(p.label_coverage, 0)}</strong></div><div class="metric-row"><span>Gender field coverage</span><strong>${pct(1 - a.unknown_count / p.total_rows, 0)}</strong></div><div class="metric-row"><span>Protected attributes</span><strong>Audit-only ${badge("Excluded from inputs", "good")}</strong></div><div class="metric-row"><span>Model version ID</span><strong class="mono">${e(model().model_version)}</strong></div><p class="note">${p.label_coverage < 1 ? "Missing outcomes remain unassigned. Selection rates are available; precision and recall require ground-truth labels." : "Validation partition used for model choices. Test partition reserved for final evaluation."}</p><div class="form-actions"><a class="button secondary small" href="#models">Inspect Model Performance</a></div></article></div>
 <div class="grid-main"><article class="card"><div class="section-heading"><h2>Workflow Execution Guide</h2><span class="subtext">THREE CORE STAGES</span></div><div class="process-steps"><div class="process-step"><span class="step-number">01</span><strong>Candidate Ingestion</strong><p>Load labeled evaluation splits or new applicant pools. The trained model pipeline is preserved.</p></div><div class="process-step"><span class="step-number">02</span><strong>Auditing & Decisions</strong><p>Inspect rank ordering, decision paths, and demographic fairness gaps under the active policy.</p></div><div class="process-step"><span class="step-number">03</span><strong>Controlled Mitigation</strong><p>Preview attribute removal with proxy detection. Assess precision/recall tradeoffs before applying.</p></div></div></article><article class="card"><h2>Applicant Review Queue</h2><p>Review candidate profiles ranked by predicted model score with policy thresholds.</p><div class="form-actions"><a class="button primary small" href="#applicants">Open Applicant Directory</a></div><p class="note">Ties broken deterministically: unrounded probability score descending, then applicant ID ascending.</p></article></div>`;
}
async function renderApplicants() {
  const q = new URLSearchParams({
      page: state.pageNumber,
      per_page: 20,
      filter: state.filter,
      search: state.search,
    }),
    d = await api(`/api/shortlist?${q}`);
  return `${policyStrip()}<article class="card flush"><div class="card-header"><div><h2>The applicant pool</h2><p>${count(d.total_candidates)} records · ${e(state.workspace.pool.name)}</p></div><div class="tool-group">${button(`${icon("bolt")} Assess one record`, "assess", "secondary small")}<a class="button secondary small" href="/api/shortlist?${new URLSearchParams({ filter: state.filter, search: state.search, export: "true" })}">${icon("download")}Export CSV</a></div></div>
 <form class="pool-tools" id="filter-form"><div class="tool-group"><input aria-label="Search applicant ID" name="search" class="search-input" placeholder="Search applicant ID…" value="${e(state.search)}"><select name="filter" aria-label="Filter selection status">${[
   ["all", "All applicants"],
   ["shortlisted", "Selected only"],
   ["held", "Held only"],
 ]
   .map(
     ([v, t]) =>
       `<option value="${v}" ${state.filter === v ? "selected" : ""}>${t}</option>`,
   )
   .join(
     "",
   )}</select><button class="button secondary small" type="submit">Apply</button></div><span class="subtext">${count(d.total_shortlisted)} selected · ${pct(d.selection_rate)} of pool</span></form>
 <div class="table-wrap"><table><thead><tr><th>Rank</th><th>Applicant</th><th>Model score</th><th>Status</th><th>Education</th><th>Experience</th><th>Evidence</th></tr></thead><tbody>${d.applicants.map((r) => `<tr><td class="quiet">${String(r.rank).padStart(2, "0")}</td><td><div class="table-name"><span class="applicant-avatar">${e(String(r.enrollee_id).slice(-2))}</span><strong class="mono">${e(r.enrollee_id)}</strong></div></td><td><span class="score-cell"><strong>${pct(r.score)}</strong>${bar(r.score)}</span></td><td>${badge(r.shortlisted ? "Selected" : "Held", r.shortlisted ? "good" : "neutral")}</td><td>${e(r.education_level)}</td><td>${r.experience == null ? "Unknown" : e(r.experience) + " years"}</td><td>${button(`View ${icon("arrow")}`, "explain", "ghost small", `data-id="${e(r.enrollee_id)}"`)}</td></tr>`).join("") || '<tr><td colspan="7">No applicants match this filter.</td></tr>'}</tbody></table></div><div class="card-footer"><span>${count(d.total_filtered)} matching records · page ${d.page} of ${d.total_pages}</span><div class="pagination">${button("← Previous", "previous", "secondary small", d.page <= 1 ? "disabled" : "")}${button("Next →", "next", "secondary small", d.page >= d.total_pages ? "disabled" : "")}</div></div></article><p class="note">Model probabilities are not calibrated confidence or verified qualification estimates. Protected fields appear only in audits.</p>`;
}
function gapCard(title, value, ci, description) {
  return `<article class="gap-card"><p>${e(title)} <span class="tip-label" title="${e(description)}">ⓘ</span></p><strong>${points(value)}</strong><small>${ci ? `95% interval ${points(ci[0])}–${points(ci[1])}` : "Insufficient denominator support"}</small></article>`;
}
async function renderFairness() {
  const d = await api(
      `/api/fairness/audit?scope=${state.auditScope}&intersectional=${state.intersectional}`,
    ),
    attrs = Object.keys(d.audit);
  if (!attrs.includes(state.attribute)) state.attribute = attrs[0];
  const a = d.audit[state.attribute];
  return `${policyStrip()}<div class="policy-strip"><div>${icon("shield")}<span>Audit scope: <strong>${e(state.auditScope === "current" ? state.workspace.pool.name : state.auditScope === "test" ? "Held-out test · exploratory access" : "Validation partition")}</strong> · ${count(d.total_rows)} records</span></div><select id="audit-scope" aria-label="Audit data scope">${[
    ["validation", "Validation · develop interventions"],
    ["current", "Current applicant pool"],
    ["test", "Test · final evaluation"],
  ]
    .map(
      ([v, t]) =>
        `<option value="${v}" ${state.auditScope === v ? "selected" : ""}>${t}</option>`,
    )
    .join("")}</select></div>
 ${state.auditScope === "test" ? '<p class="test-warning">Reserve test-set access for final assessment. Repeatedly choosing interventions from test outcomes turns it into a development set.</p>' : ""}
 <div class="audit-toolbar"><div class="tabs" role="group" aria-label="Audit grouping">${attrs.map((key) => `<button aria-pressed="${state.attribute === key}" data-action="attribute" data-attribute="${e(key)}">${e(d.audit[key].label)}</button>`).join("")}</div>${attrs.length > 1 && d.audit[attrs[1]] ? `<label class="checkbox-label"><input id="intersectional" type="checkbox" ${state.intersectional ? "checked" : ""}>Include gender × ${e(d.audit[attrs[1]].label.split(" ·")[0].toLowerCase())}</label>` : ""}</div>
 <div class="gap-grid">${gapCard("Selection-rate gap", a.selection_rate_gap, a.selection_rate_gap_ci, "Maximum minus minimum selected proportion, including Unknown.")}${gapCard("Recall gap", a.recall_gap, a.recall_gap_ci, "Difference in recovery of known positive outcomes.")}${gapCard("Precision gap", a.precision_gap, a.precision_gap_ci, "Difference in positive outcomes among labeled selections.")}</div>
 <article class="card flush section-space"><div class="card-header"><div><h2>Group-by-group evidence</h2><p>${e(a.label)} · intervals and denominator support shown together</p></div>${badge(a.status === "review" ? "Rate disparity flagged" : a.status === "no_selections" ? "No selections to compare" : "No four-fifths flag", a.status === "review" ? "warn" : "neutral")}</div><div class="table-wrap"><table id="fairness-table"><thead><tr><th>Group / support</th><th>Selected</th><th>Selection rate</th><th>Rate ratio</th><th>Recall</th><th>Precision</th><th>Evidence quality</th></tr></thead><tbody>${a.groups.map((g) => `<tr><td><strong>${e(g.group)}</strong><small class="table-note">${count(g.size)} records · ${count(g.labeled_count)} labeled</small></td><td>${count(g.selected_count)}</td><td><strong>${pct(g.selection_rate)}</strong><small class="table-note">${interval(g.selection_rate_ci)}</small></td><td>${badge(g.four_fifths_ratio == null ? "N/A" : dec(g.four_fifths_ratio), g.violates_80_rule ? "warn" : "neutral")}</td><td><strong>${pct(g.recall)}</strong><small class="table-note">${interval(g.recall_ci)} · ${count(g.actual_positive_count)} positives</small></td><td><strong>${pct(g.precision)}</strong><small class="table-note">${interval(g.precision_ci)} · ${count(g.selected_labeled_count)} labeled selected</small></td><td class="wrap">${badge(g.warnings.length ? "Limited support" : "Inspect intervals", g.warnings.length ? "warn" : "neutral")}<small class="table-note">${e(g.warnings.join(" · ") || "Read intervals with point estimates.")}</small></td></tr>`).join("")}</tbody></table></div><div class="card-footer"><span>Ratios use the highest selection rate, including Unknown. Below 0.80 is a screening flag.</span><a href="/api/fairness/export?scope=${state.auditScope}">Export audit ↗</a></div></article>
 <div class="grid-equal"><article class="card"><div class="section-heading"><div><h2>Investigate a possible driver</h2><p class="subtext">Measure sensitivity to a source attribute.</p></div>${icon("chart")}</div><p>Replace each source attribute with its training reference and measure the change in group mean scores.</p><div class="form-actions">${button("Calculate sensitivity", "drivers", "secondary")}</div><div id="driver-results"></div></article><article class="card"><div class="section-heading"><div><h2>Test an attribute removal</h2><p class="subtext">Same rows. Same policy. A separately fitted model.</p></div>${icon("layers")}</div><form id="ablation-form"><div class="field"><label for="drop-column">Attribute to remove</label><select id="drop-column" name="attribute_to_drop">${model()
   .active_columns.map((c) => `<option value="${e(c)}">${e(label(c))}</option>`)
   .join(
     "",
    )}</select></div><label class="checkbox-label"><input name="drop_proxies" type="checkbox">Also remove associated inputs (training NMI ≥ 0.30)</label><p class="subtext">Associated source columns are listed in the result. Association is not proof of proxy discrimination.</p><div class="form-actions"><button class="button primary" type="submit">Preview Comparison</button></div></form></article></div>
 <div id="experiment-results">${state.preview && state.preview.scope === state.auditScope && state.preview.protected_attribute_audited === state.attribute ? renderExperiment(state.preview) : ""}</div><details><summary>How to interpret these metrics</summary><p class="note">Selection rates use every record. Recall and precision use observed outcomes; N/A means an unavailable denominator. Rates have 95% Wilson intervals. Gap intervals use 1,000 plug-in binomial bootstrap draws (seed 42) and are exploratory. Metrics do not establish legal compliance or individual fairness. Demo experience and education groups cannot establish actual age or institution fairness.</p></details>`;
}
function renderExperiment(r) {
  const metrics = [
    ["Selection-rate gap", "selection_rate_gap", points],
    ["Recall gap", "recall_gap", points],
    ["Precision gap", "precision_gap", points],
    ["Scope accuracy", "accuracy", pct],
    ["ROC-AUC", "auc", dec],
  ];
  const improvements = metrics
    .slice(0, 3)
    .filter(([, k]) => r.delta[k] != null && r.delta[k] < 0).length;
  return `<article class="card flush section-space" id="ablation-result"><div class="card-header"><div><div class="mini-heading">EXPERIMENT PREVIEW</div><h2>Without ${e(label(r.dropped_attribute).toLowerCase())}</h2><p class="subtext">${e(r.scope)} scope · policy held constant · original model is still active</p></div>${badge("Not applied", "warn")}</div><div class="table-wrap"><table><thead><tr><th>Metric</th><th>Before</th><th>After</th><th>Change</th></tr></thead><tbody>${metrics.map(([title, k, format]) => `<tr><td>${title}</td><td>${format(r.before[k])}</td><td><strong>${format(r.after[k])}</strong></td><td>${r.delta[k] == null ? "N/A" : (r.delta[k] > 0 ? "+" : "") + (k === "auc" ? dec(r.delta[k]) : points(r.delta[k]))}</td></tr>`).join("")}</tbody></table></div>${groupComparison(r)}<div class="dialog-body"><p class="small-text">Removed source inputs: <b>${r.dropped_columns.map((c) => e(label(c))).join(", ")}</b></p><p class="note ${improvements < 3 ? "warn" : ""}">${improvements} of ${metrics.slice(0, 3).filter(([, k]) => r.delta[k] != null).length} estimable gap measures decreased. Review precision, recall, support and performance together; a lower selection gap alone does not establish a better policy.</p><div class="metric-row"><span>Validation accuracy (before → after)</span><strong>${pct(r.before.validation_performance.accuracy)} → ${pct(r.after.validation_performance.accuracy)}</strong></div><div class="form-actions">${button("Apply Compared Model", "apply-ablation", "primary", `data-run="${e(r.run_id)}"`)}${button("Dismiss Preview", "dismiss-preview", "secondary")}<small class="quiet">Applying saves a version. You can revert it.</small></div></div></article>`;
}
function rocChart(values) {
  if (!values?.length)
    return empty("ROC unavailable", "Both outcome classes are needed.");
  const path = values
    .map((p, i) => `${i ? "L" : "M"}${38 + p.fpr * 260},${190 - p.tpr * 160}`)
    .join(" ");
  return `<svg class="roc-chart" viewBox="0 0 330 225" role="img" aria-label="Receiver operating characteristic curve"><path class="roc-grid" d="M38 30V190H298M38 110H298M168 30V190" fill="none"/><path class="roc-diagonal" d="M38 190L298 30"/><path class="roc-line" d="${path}"/><text class="roc-label" x="34" y="209">0</text><text class="roc-label" x="289" y="209">1</text><text class="roc-label" x="20" y="35">1</text><text class="roc-label" x="111" y="224">False positive rate</text><text class="roc-label" transform="translate(12,150) rotate(-90)">True positive rate</text></svg>`;
}
async function renderModels() {
  const d = await api(`/api/evaluation?scope=${state.evaluationScope}`),
    m = d.metrics,
    c = m.confusion_matrix;
  return `<div class="section-heading"><div><h2>${e(model().model_name)} · active model</h2><p class="subtext">Policy: ${e(state.workspace.policy.description)}</p></div><select id="evaluation-scope" aria-label="Performance evaluation split"><option value="validation" ${state.evaluationScope === "validation" ? "selected" : ""}>Validation partition</option><option value="test" ${state.evaluationScope === "test" ? "selected" : ""}>Held-out test partition</option></select></div>${state.evaluationScope === "test" ? '<p class="test-warning">Reserve test data for final evaluation after choosing model and policy.</p>' : ""}
 <div class="kpi-grid">${kpi("Accuracy", pct(m.accuracy), `Majority baseline ${pct(m.majority_baseline)}`, "target")}${kpi("Precision", pct(m.precision), "Positive outcomes among labeled selections", "check")}${kpi("Recall", pct(m.recall), "Labeled positives recovered", "people")}${kpi("ROC-AUC", dec(m.auc), `Average precision ${dec(m.average_precision)}`, "chart")}</div>
 <div class="grid-equal"><article class="card"><div class="section-heading"><h2>Ranking discrimination</h2>${badge(state.evaluationScope)}</div>${rocChart(m.roc_curve)}<p class="subtext">Exact ROC-AUC, including ties. The curve uses observed score thresholds.</p></article><article class="card"><h2>What the decisions get right</h2><p class="subtext">Confusion matrix · ${count(m.labeled_count)} labeled records</p><div class="confusion-grid"><div><strong>${count(c.tn)}</strong>True negatives</div><div class="error"><strong>${count(c.fp)}</strong>False positives</div><div class="error"><strong>${count(c.fn)}</strong>False negatives</div><div><strong>${count(c.tp)}</strong>True positives</div></div><div class="metric-row"><span>Balanced accuracy / F1</span><strong>${pct(m.balanced_accuracy)} / ${pct(m.f1)}</strong></div><div class="metric-row"><span>Precision among top 100</span><strong>${pct(m.precision_at_100)}</strong></div></article></div>
 <article class="card section-space"><div class="section-heading"><div><h2>Compare five model families</h2><p class="subtext">Validation metrics and stratified training cross-validation.</p></div>${button("Run comparison", "compare-models")}</div><p>Each fold refits preprocessing. Benchmarks use a 0.50 threshold; your active policy is preserved.</p><div id="comparison-results"></div></article><article class="card"><div class="section-heading"><div><h2>Feature selection or dimensionality reduction?</h2><p class="subtext">Same tree family and validation rows.</p></div>${button("Run experiment", "dimensions")}</div><p>Importance-based selection preserves input names. PCA learns scaled orthogonal components.</p><div id="dimensions-results"></div></article>`;
}
async function renderData() {
  const w = state.workspace,
    d = w.source_summary,
    t = w.training,
    missing = Object.entries(d.quality_audit.missing).sort(
      (a, b) => b[1] - a[1],
    );
  return `<div class="grid-main"><article class="card"><div class="section-heading"><div><div class="eyebrow">${w.pool.source === "uploaded" ? "UPLOADED APPLICANTS" : "TRAINING DATASET"}</div><h2>${e(d.name)}</h2></div>${badge(d.dataset_id.slice(0, 8))}</div><p>${e(d.target_description)}</p><div class="metric-row"><span>Records / outcome coverage</span><strong>${count(d.total_rows)} / ${pct(d.label_coverage, 0)}</strong></div><div class="metric-row"><span>Positive / negative / unknown outcomes</span><strong>${count(d.class_balance.positive)} / ${count(d.class_balance.negative)} / ${count(d.class_balance.unknown)}</strong></div><div class="metric-row"><span>Gender coverage</span><strong>${pct(d.gender_coverage)}</strong></div><p class="note">Actual age bands and institution names are preserved when supplied. Demo experience and education groupings do not establish age or institution fairness.</p><div class="form-actions"><a class="button secondary" href="/api/dataset/cleaned/download">${icon("download")}Cleaned CSV + provenance</a><a class="button ghost" href="/api/pool/template">Input template ↗</a></div></article>
 <article class="card"><h2>Separated for an honest evaluation</h2><p class="subtext">Seed 42 · target-stratified partitions</p>${[
   ["Training", t.train_rows],
   ["Validation", t.validation_rows],
   ["Held-out test", t.test_rows],
 ]
   .map(
     ([name, n]) =>
       `<div class="metric-row"><span>${name}</span><strong>${count(n)} records</strong></div>`,
   )
   .join(
     "",
   )}<p class="note">Imputation, categories and scaling are learned on training rows only. Every CV fold learns its own transforms. Applicant uploads do not retrain the model.</p><div class="pill-list">${badge("60% train")}${badge("20% validation")}${badge("20% test")}</div></article></div>
 <div class="grid-equal"><article class="card"><h2>Missingness, made visible</h2><p class="subtext">Raw missing values by attribute</p>${missing.map(([c, n]) => `<div class="missing-row"><span>${e(label(c))}</span>${bar(n / d.total_rows, n / d.total_rows > 0.2)}<strong>${count(n)}</strong></div>`).join("")}<p class="note">Missing categories become Unknown. Numeric blanks stay explicit until the fitted pipeline imputes them.</p></article><article class="card"><h2>Schema and provenance checks</h2><p class="subtext">Statuses reflect the actual validation result.</p><ul class="list-clean">${d.validation_results.cleaned_assertions.map((r) => `<li><span>${e(r.assertion)}</span>${badge(r.passed ? "Pass" : "Fail", r.passed ? "good" : "bad")}</li>`).join("")}</ul><p class="subtext">${count(d.quality_audit.outlier_count)} hour values exceed the IQR fence (${d.quality_audit.outlier_fence.toFixed(1)} hours). Flagged, not automatically removed.</p></article></div>
 <article class="card flush section-space"><div class="card-header"><div><h2>Transformation ledger</h2><p>Every standardized value keeps provenance.</p></div></div><div class="table-wrap"><table><thead><tr><th>Attribute</th><th>Transformation</th><th>Affected</th><th>Resolution</th></tr></thead><tbody>${d.before_after_table.map((r) => `<tr><td>${e(label(r.field))}</td><td>${e(r.action.replaceAll("_", " "))}</td><td>${count(r.affected_count)}</td><td>${e(r.resolution)}</td></tr>`).join("") || '<tr><td colspan="4">No deterministic repairs needed.</td></tr>'}</tbody></table></div></article>
 <article class="card flush"><div class="card-header"><h2>Data dictionary & input roles</h2></div><div class="table-wrap"><table><thead><tr><th>Column</th><th>Type</th><th>Role</th><th>Meaning</th></tr></thead><tbody>${d.data_dictionary.map((r) => `<tr><td class="mono">${e(r.column)}</td><td>${e(r.type)}</td><td>${badge(r.role, r.role === "Audit only" ? "warn" : "neutral")}</td><td class="wrap">${e(r.description)}</td></tr>`).join("")}</tbody></table></div></article>`;
}
async function renderSettings() {
  const history = await api("/api/history"),
    w = state.workspace;
  return `<div class="grid-equal"><article class="card"><h2>Selection Policy Configuration</h2><p class="subtext">Configure selection threshold or interview capacity quota.</p><form id="policy-form"><div class="form-grid section-space"><div class="field full"><label for="policy-mode">Selection policy mode</label><select id="policy-mode" name="mode"><option value="threshold" ${w.policy.top_n == null ? "selected" : ""}>Probability threshold</option><option value="top_n" ${w.policy.top_n != null ? "selected" : ""}>Interview capacity quota (Top N)</option></select></div><div class="field"><label for="policy-threshold">Threshold <output id="threshold-output">${w.policy.threshold.toFixed(2)}</output></label><input id="policy-threshold" name="threshold" type="range" min="0" max="1" step="0.01" value="${w.policy.threshold}"><small>Used in threshold mode only.</small></div><div class="field"><label for="policy-capacity">Interview capacity quota</label><input id="policy-capacity" name="top_n" type="number" min="1" max="100000" step="1" value="${w.policy.top_n ?? ""}" placeholder="e.g. 50"><small>Top-N overrides the threshold.</small></div></div><p class="note">Ties use applicant ID after the original score. Capacity is capped by pool size.</p><div class="form-actions"><button type="submit" class="button primary">Save Policy Changes</button></div></form></article>
 <article class="card"><h2>Active Classifier Model</h2><p class="subtext">Select and retrain classifier with active features.</p><form id="model-form"><div class="field"><label for="model-type">Classifier algorithm</label><select id="model-type" name="model_type">${Object.entries(
   w.models,
 )
   .map(
     ([key, name]) =>
       `<option value="${key}" ${model().model_type === key ? "selected" : ""}>${e(name)}</option>`,
   )
   .join(
     "",
   )}</select></div><div class="form-actions"><button class="button primary" type="submit">Train & activate</button>${button("Revert previous model", "revert", "secondary", w.can_revert ? "" : "disabled")}</div></form><div class="metric-row"><span>Current version</span><strong class="mono">${e(model().model_version)}</strong></div><div class="metric-row"><span>Removed attributes</span><strong>${
   model().dropped_columns.length
     ? model()
         .dropped_columns.map((c) => e(label(c)))
         .join(", ")
     : "None"
 }</strong></div><details><summary>Active inputs (${model().active_columns.length})</summary><div class="pill-list">${model()
   .active_columns.map((c) => badge(label(c)))
   .join(
     "",
   )}</div></details><div class="sensitive-note">${icon("shield")}<span>Gender, age and institution remain audit-only. Measuring disparities still matters.</span></div></article></div>
 <div class="grid-equal"><article class="card"><h2>Cost assumptions & capacity</h2><p>Explore thresholds on validation outcomes, optionally limited by interview slots.</p><form id="cost-form"><div class="form-grid">${[
   ["cost_fp", "False-positive cost", 500],
   ["cost_fn", "False-negative cost", 3500],
   ["benefit_tp", "True-positive benefit", 5000],
 ]
   .map(
     ([name, title, value]) =>
       `<div class="field"><label for="${name}">${title}</label><input id="${name}" name="${name}" type="number" min="0" value="${value}" required></div>`,
   )
   .join(
     "",
   )}<div class="field"><label for="cost-capacity">Maximum selections (optional)</label><input id="cost-capacity" name="capacity" type="number" min="1" max="100000" placeholder="Unconstrained"></div></div><div class="form-actions"><button class="button secondary" type="submit">Evaluate assumptions</button></div></form><div id="cost-results"></div></article>
 <article class="card"><h2>Data & model lifecycle</h2><p>Applicant pools are held in memory. Training data and model versions are stored locally for reproducibility.</p><div class="form-actions">${button(`${icon("upload")}Replace labeled training data`, "upload-training")}${button("Restore demo pool", "reset-pool")}</div><p class="note">Training requires both target classes and an outcome definition. Applicant pools can omit target. Historical labels are not proof of qualification.</p><div class="metric-row"><span>Training dataset</span><strong class="mono">${e(w.training.dataset_id)}</strong></div><div class="metric-row"><span>Outcome type</span><strong>${w.training.target_kind === "interview" ? "Interview progression outcome" : "Candidate qualification & shortlisting"}</strong></div></article></div>
 <article class="card"><div class="section-heading"><div><h2>A record of what changed</h2><p class="subtext">Append-only local history · latest ${Math.min(12, history.events.length)} events</p></div><a class="button ghost small" href="/api/fairness/export">Export record ${icon("download")}</a></div><ol class="timeline">${history.events
   .slice(0, 12)
   .map(
     (item) =>
       `<li><strong>${e(item.action.replaceAll("_", " "))}</strong><small>${e(new Date(item.created_at).toLocaleString())}</small><p>${e(item.payload.dropped_attribute ? `Attribute: ${label(item.payload.dropped_attribute)}` : item.payload.model_version ? `Model ${item.payload.model_version}` : item.payload.policy ? item.payload.policy.description : item.payload.pool_id ? `Pool ${item.payload.pool_id}` : "Workspace event recorded")}</p></li>`,
   )
   .join("")}</ol></article>`;
}
function openDialog(title, subtitle, body) {
  const d = document.getElementById("workspace-dialog");
  document.getElementById("dialog-content").innerHTML =
    `<header class="dialog-header"><div><h2 id="dialog-title">${e(title)}</h2><p>${e(subtitle)}</p></div><button class="icon-button" data-action="close-dialog" aria-label="Close dialog">${icon("close")}</button></header><div class="dialog-body">${body}</div>`;
  if (!d.open) d.showModal();
}
function uploadDialog(training = false) {
  openDialog(
    training ? "Replace labeled training data" : "Bring your applicant pool",
    training
      ? "Fits a new model and saves a version."
      : "Scores your pool using the existing model.",
    `<form id="upload-form" data-training="${training}"><div class="file-zone"><strong>${training ? "Labeled CSV with both target classes" : "One record per applicant"}</strong><p>UTF-8 · up to 32 MB · required: city_development_index, training_hours, experience, education_level, relevent_experience.</p><label class="small-text" for="csv-file">Choose CSV file</label><input id="csv-file" name="file" type="file" accept=".csv,text/csv" required></div><div class="field"><label for="outcome-type">Meaning of target (if present)</label><select id="outcome-type" name="target_kind"><option value="qualification" ${state.workspace.training.target_kind === "qualification" || state.workspace.training.target_kind === "job_change" ? "selected" : ""}>Candidate qualification · interview shortlisting</option><option value="interview" ${state.workspace.training.target_kind === "interview" ? "selected" : ""}>Interview progression · verified outcomes</option></select><small>${training ? "Target must be 0 or 1, with at least 10 examples in each class." : "Target is optional. Missing outcomes stay unknown; the model is not retrained."}</small></div><p class="note">Optional audit columns: gender, age or age_band, institution. Actual age bands and institutions are preserved. Applicant IDs must be unique. The fitted pipeline imputes blank numeric inputs.</p><div id="upload-error" role="alert"></div><div class="form-actions"><button class="button primary" type="submit">${icon("upload")}${training ? "Validate & train" : "Validate & score"}</button><a class="button ghost" href="/api/pool/template">Download template ↗</a></div></form>`,
  );
}
function assessDialog() {
  const fields = [
    [
      "city_development_index",
      "City development index",
      ".8",
      "0",
      "1",
      ".001",
    ],
    ["training_hours", "Training hours", "50", "0", "100000", "1"],
    ["experience", "Experience (years)", "5", "0", "80", "1"],
  ];
  openDialog(
    "Assess a single record",
    "Same fitted preprocessing and model as batch scoring.",
    `<form id="assessment-form"><div class="form-grid">${fields.map(([name, title, value, min, max, step]) => `<div class="field"><label for="assess-${name}">${title}</label><input id="assess-${name}" name="${name}" type="number" value="${value}" min="${min}" max="${max}" step="${step}" required></div>`).join("")}<div class="field"><label for="assess-education">Education level</label><select id="assess-education" name="education_level">${["Graduate", "Masters", "Phd", "High School", "Primary School", "Unknown"].map((c) => `<option>${e(c)}</option>`).join("")}</select></div><div class="field"><label for="assess-relevant">Relevant experience</label><select id="assess-relevant" name="relevent_experience"><option>Has relevent experience</option><option>No relevent experience</option></select></div><div class="field"><label for="assess-enrolled">University enrollment</label><select id="assess-enrolled" name="enrolled_university"><option>no_enrollment</option><option>Full time course</option><option>Part time course</option><option>Unknown</option></select></div></div><div class="form-actions"><button class="button primary" type="submit">Assess record ${icon("arrow")}</button></div></form><div id="assessment-result"></div>`,
  );
}
function explanationHtml(d) {
  return `<div class="explain-score"><div><div class="subtext">Estimated positive-outcome probability</div><div class="big-value">${pct(d.score)}</div></div>${badge(d.shortlisted == null ? "Pool comparison needed" : d.shortlisted ? "Selected" : "Held", d.shortlisted ? "good" : "neutral")}</div><p class="note">${e(d.note)} ${e(d.decision_note)}</p>${d.rank ? `<div class="metric-row"><span>Rank under the current policy</span><strong>#${count(d.rank)}</strong></div>` : ""}${d.decision_rules.length ? `<h3>Actual tree decision path</h3><ol class="path-list">${d.decision_rules.map((r) => `<li>${e(r)}</li>`).join("")}</ol>` : ""}<div class="inline-heading"><h3>Measured attribute sensitivity</h3><span class="subtext">Score vs. training reference</span></div>${d.contributions.map((c) => `<div class="impact-row"><span><strong>${e(c.label)} · ${e(c.value ?? "Missing")}</strong><small>Reference: ${e(c.reference_value)} · ${e(c.explanation)}</small></span><span class="${c.impact > 0 ? "positive" : c.impact < 0 ? "negative" : "quiet"}">${c.impact > 0 ? "+" : ""}${points(c.impact)}</span></div>`).join("")}<p class="note">Zero means the replacement did not change the score. These independent effects are not additive or causal.</p>`;
}
async function busy(element, work) {
  const old = element.innerHTML;
  element.disabled = true;
  element.setAttribute("aria-busy", "true");
  element.innerHTML = "Working…";
  try {
    await work();
  } catch (error) {
    toast(error.message, true);
    const n = document.getElementById("upload-error");
    if (n) n.innerHTML = `<p class="note error">${e(error.message)}</p>`;
  } finally {
    if (element.isConnected) {
      element.disabled = false;
      element.removeAttribute("aria-busy");
      element.innerHTML = old;
    }
  }
}
async function reloadAfterChange(message) {
  state.preview = null;
  await refreshWorkspace();
  await navigate();
  toast(message);
}
async function handleAction(el) {
  const a = el.dataset.action;
  if (a === "close-dialog") {
    document.getElementById("workspace-dialog").close();
    return;
  }
  if (a === "upload") {
    uploadDialog();
    return;
  }
  if (a === "upload-training") {
    uploadDialog(true);
    return;
  }
  if (a === "assess") {
    assessDialog();
    return;
  }
  if (a === "retry") {
    await navigate();
    return;
  }
  if (a === "previous" || a === "next") {
    state.pageNumber += a === "next" ? 1 : -1;
    await navigate();
    return;
  }
  if (a === "attribute") {
    state.attribute = el.dataset.attribute;
    state.preview = null;
    await navigate();
    return;
  }
  if (a === "dismiss-preview") {
    state.preview = null;
    document.getElementById("experiment-results").innerHTML = "";
    return;
  }
  await busy(el, async () => {
    if (a === "explain") {
      openDialog(
        `Applicant ${el.dataset.id}`,
        "Evidence under the active model and pool policy.",
        loading("Inspecting the fitted model"),
      );
      const r = await api(`/api/explain/${encodeURIComponent(el.dataset.id)}`);
      if (document.getElementById("workspace-dialog").open)
        document.querySelector(".dialog-body").innerHTML = explanationHtml(r);
    } else if (a === "drivers") {
      const r = await api(
        `/api/fairness/drivers?scope=${state.auditScope}&attribute=${encodeURIComponent(state.attribute)}`,
      );
      const max = Math.max(
        ...(r.drivers || []).map((x) => x.abs_impact),
        0.001,
      );
      document.getElementById("driver-results").innerHTML =
        (r.drivers || [])
          .map(
            (d) =>
              `<div class="driver-bar-row"><span>${e(label(d.original_column))}</span>${bar(d.abs_impact / max, d.driver_score < 0)}<strong>${d.driver_score > 0 ? "+" : ""}${points(d.driver_score)}</strong></div>`,
          )
          .join("") +
        `<p class="note">${e(r.method || r.note)} ${r.sample_size ? `Diagnostic sample: ${count(r.sample_size)} records.` : ""}</p>`;
    } else if (a === "compare-models") {
      const r = await api("/api/models/compare");
      document.getElementById("comparison-results").innerHTML =
        `<div class="table-wrap"><table><thead><tr><th>Model</th><th>Accuracy / baseline</th><th>Precision</th><th>Recall</th><th>AUC / AP</th><th>Training CV</th></tr></thead><tbody>${r.comparison.map((m) => `<tr><td><b>${e(m.model_name)}</b><small class="table-note">${e(m.family)}</small></td><td>${pct(m.accuracy)}<small class="table-note">Baseline ${pct(m.majority_baseline)}</small></td><td>${pct(m.precision)}</td><td>${pct(m.recall)}</td><td>${dec(m.auc)} / ${dec(m.average_precision)}</td><td>${e(m.cv_spread)}<small class="table-note">${m.cv.k} folds · fold SD, not a confidence interval</small></td></tr>`).join("")}</tbody></table></div><p class="note">${e(r.note)}</p>`;
    } else if (a === "dimensions") {
      const r = await api("/api/models/dim_reduction_compare");
      document.getElementById("dimensions-results").innerHTML =
        `<div class="table-wrap"><table><thead><tr><th>Technique</th><th>Dimensions</th><th>Accuracy</th><th>AUC</th></tr></thead><tbody>${r.comparison.map((m) => `<tr><td>${e(m.technique)}</td><td>${m.components_or_features}</td><td>${pct(m.accuracy)}</td><td>${dec(m.auc)}</td></tr>`).join("")}</tbody></table></div><details><summary>Selected features and PCA variance</summary><p class="note">${e(r.comparison[1].selected_features.join(", "))}<br>PCA explained variance: ${pct(r.comparison[2].explained_variance_ratio)}</p></details>`;
    } else if (a === "apply-ablation") {
      await post("/api/fairness/apply", { run_id: el.dataset.run });
      await reloadAfterChange("Compared model applied across all views.");
    } else if (a === "revert") {
      await post("/api/models/revert");
      await reloadAfterChange("Previous model restored.");
    } else if (a === "reset-pool") {
      await post("/api/pool/reset");
      state.pageNumber = 1;
      await reloadAfterChange("Validation demo pool restored.");
    }
  });
}
async function handleSubmit(form) {
  await busy(form.querySelector("button[type=submit]"), async () => {
    const d = Object.fromEntries(new FormData(form));
    if (form.id === "filter-form") {
      state.search = d.search;
      state.filter = d.filter;
      state.pageNumber = 1;
      await navigate();
    } else if (form.id === "upload-form") {
      const training = form.dataset.training === "true";
      await api(training ? "/api/training/upload" : "/api/pool/upload", {
        method: "POST",
        body: new FormData(form),
      });
      document.getElementById("workspace-dialog").close();
      state.pageNumber = 1;
      await reloadAfterChange(
        training
          ? "Training data and model updated."
          : "Applicant pool loaded; model preserved.",
      );
    } else if (form.id === "policy-form") {
      if (d.mode === "top_n" && !d.top_n)
        throw new Error("Enter capacity for a top-N policy.");
      await post("/api/policy", {
        threshold: Number(d.threshold),
        top_n: d.mode === "top_n" ? Number(d.top_n) : null,
      });
      state.pageNumber = 1;
      await reloadAfterChange("Policy applied across views and exports.");
    } else if (form.id === "model-form") {
      await post("/api/train", d);
      await reloadAfterChange("New classifier version activated.");
    } else if (form.id === "assessment-form") {
      const r = await post("/api/predict/single", d);
      document.getElementById("assessment-result").innerHTML =
        explanationHtml(r);
    } else if (form.id === "ablation-form") {
      if (state.attribute.includes("__"))
        throw new Error(
          "Choose a primary grouping for ablation; intersectional metrics remain in the audit.",
        );
      const r = await post("/api/fairness/ablate", {
        attribute_to_drop: d.attribute_to_drop,
        drop_proxies: form.elements.drop_proxies.checked,
        protected_attribute: state.attribute,
        scope: state.auditScope,
      });
      state.preview = r;
      document.getElementById("experiment-results").innerHTML =
        renderExperiment(r);
      document
        .getElementById("experiment-results")
        .scrollIntoView({ block: "start", behavior: "smooth" });
    } else if (form.id === "cost-form") {
      const r = await post(
        "/api/settings/cost_matrix",
        Object.fromEntries(
          Object.entries(d).map(([k, v]) => [k, v === "" ? null : Number(v)]),
        ),
      );
      document.getElementById("cost-results").innerHTML =
        `<p class="note">${r.optimal_threshold == null ? "No grid threshold satisfies capacity." : `Lowest assumed cost at threshold <b>${r.optimal_threshold.toFixed(2)}</b>; net cost ${Number(r.min_expected_cost).toLocaleString()}.`} ${e(r.note)}</p>`;
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  try {
    fillIcons();
  } catch (err) {
    console.warn("fillIcons:", err);
  }
  const todayEl = document.getElementById("today");
  if (todayEl) {
    todayEl.textContent = new Date().toLocaleDateString(
      undefined,
      { day: "numeric", month: "short", year: "numeric" },
    );
  }
  document.addEventListener("click", (ev) => {
    const el = ev.target.closest("[data-action]");
    if (el && !el.disabled) {
      ev.preventDefault();
      handleAction(el).catch((error) => toast(error.message, true));
    }
  });
  document.addEventListener("submit", (ev) => {
    if (ev.target.matches("form")) {
      ev.preventDefault();
      handleSubmit(ev.target).catch((error) => toast(error.message, true));
    }
  });
  document.addEventListener("change", (ev) => {
    if (ev.target.id === "audit-scope") {
      state.auditScope = ev.target.value;
      state.preview = null;
      navigate();
    }
    if (ev.target.id === "evaluation-scope") {
      state.evaluationScope = ev.target.value;
      navigate();
    }
    if (ev.target.id === "intersectional") {
      state.intersectional = ev.target.checked;
      navigate();
    }
  });
  document.addEventListener("input", (ev) => {
    if (ev.target.id === "policy-threshold") {
      const out = document.getElementById("threshold-output");
      if (out) out.textContent = Number(ev.target.value).toFixed(2);
    }
  });
  const dialog = document.getElementById("workspace-dialog");
  if (dialog) {
    dialog.addEventListener("click", (ev) => {
      const rect = dialog.getBoundingClientRect();
      const isOutside =
        ev.clientY < rect.top ||
        ev.clientY > rect.bottom ||
        ev.clientX < rect.left ||
        ev.clientX > rect.right;
      if (isOutside) {
        dialog.close();
      }
    });
  }
  window.addEventListener("hashchange", () => { window.scrollTo({top:0,behavior:"auto"}); navigate(); });
  navigate();
});
window.FairRecruit = {
  state,
  navigate,
  refreshWorkspace,
  renderFairness,
  renderApplicants,
  explanationHtml,
};
function groupComparison(r) {
  const key = r.protected_attribute_audited;
  const before = r.before.audit[key],
    after = r.after.audit[key];
  const groups = new Map(after.groups.map((g) => [g.group, g]));
  return `<details class="dialog-body"><summary>Compare each group's before-and-after rates</summary><div class="table-wrap"><table><thead><tr><th>Group</th><th>Selection rate</th><th>Recall</th><th>Precision</th><th>Rate ratio</th></tr></thead><tbody>${before.groups
    .map((b) => {
      const a = groups.get(b.group);
      return `<tr><td><strong>${e(b.group)}</strong><small class="table-note">n = ${count(b.size)}</small></td><td>${pct(b.selection_rate)} → ${pct(a.selection_rate)}</td><td>${pct(b.recall)} → ${pct(a.recall)}</td><td>${pct(b.precision)} → ${pct(a.precision)}</td><td>${dec(b.four_fifths_ratio)} → ${dec(a.four_fifths_ratio)}</td></tr>`;
    })
    .join(
      "",
    )}</tbody></table></div><p class="note">Before → after under the same policy. Denominators and intervals are included in the downloadable audit record.</p></details>`;
}
