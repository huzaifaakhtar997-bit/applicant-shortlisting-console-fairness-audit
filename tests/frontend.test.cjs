const { test, before } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const { JSDOM, VirtualConsole } = require("jsdom");
const axe = require("axe-core");
let fixtures;
before(() => {
  const local =
    process.platform === "win32"
      ? ".venv/Scripts/python.exe"
      : ".venv/bin/python";
  const python =
    process.env.PYTHON || (fs.existsSync(local) ? local : "python");
  const r = spawnSync(python, ["tests/frontend_fixtures.py"], {
    encoding: "utf8",
    timeout: 60000,
  });
  assert.equal(r.status, 0, r.stderr);
  fixtures = JSON.parse(r.stdout);
});
async function mount(hash = "overview", override = {}) {
  const errors = [];
  const virtualConsole = new VirtualConsole();
  virtualConsole.on("jsdomError", (error) => errors.push(error.message));
  const dom = new JSDOM(fs.readFileSync("templates/index.html", "utf8"), {
    url: "http://localhost/#" + hash,
    runScripts: "outside-only",
    pretendToBeVisual: true,
    virtualConsole,
  });
  const w = dom.window;
  w.fetch = async (url) => {
    const data = override[url] ?? fixtures[url];
    if (!data) throw new Error("Unexpected API request: " + url);
    return { ok: true, json: async () => structuredClone(data) };
  };
  w.HTMLElement.prototype.scrollIntoView = function () {};
  w.HTMLDialogElement.prototype.showModal = function () {
    this.open = true;
  };
  w.HTMLDialogElement.prototype.close = function () {
    this.open = false;
  };
  w.eval(fs.readFileSync("static/js/app.js", "utf8"));
  await new Promise((resolve) =>
    w.addEventListener("load", resolve, { once: true }),
  );
  for (
    let i = 0;
    i < 100 &&
    w.document.getElementById("page-content").getAttribute("aria-busy") ===
      "true";
    i++
  )
    await new Promise((resolve) => setTimeout(resolve, 5));
  assert.equal(
    w.document.getElementById("page-content").getAttribute("aria-busy"),
    "false",
  );
  assert.deepEqual(errors, []);
  return dom;
}
test("fairness page consumes actual nested API groups and all three gaps", async () => {
  const dom = await mount("fairness");
  const d = dom.window.document;
  assert.equal(
    d.querySelectorAll("#fairness-table tbody tr").length,
    fixtures["/api/fairness/audit?scope=validation&intersectional=false"].audit
      .gender.groups.length,
  );
  assert.equal(d.querySelectorAll(".gap-card").length, 3);
  assert.match(d.body.textContent, /Selection-rate gap/);
  assert.match(d.body.textContent, /Recall gap/);
  assert.match(d.body.textContent, /Precision gap/);
  assert.doesNotMatch(
    d.body.textContent,
    /All Subgroups Comply|This view could not load/,
  );
  dom.window.close();
});
test("zero selections never display a compliance claim or NaN", async () => {
  const data = structuredClone(
    fixtures["/api/fairness/audit?scope=validation&intersectional=false"],
  );
  const a = data.audit.gender;
  a.status = "no_selections";
  a.adverse_impact_detected = null;
  a.min_four_fifths_ratio = null;
  a.recall_gap = null;
  a.precision_gap = null;
  for (const g of a.groups) {
    g.selected_count = 0;
    g.selection_rate = 0;
    g.precision = null;
    g.recall = null;
    g.four_fifths_ratio = null;
    g.violates_80_rule = null;
  }
  const dom = await mount("fairness", {
    "/api/fairness/audit?scope=validation&intersectional=false": data,
  });
  assert.match(
    dom.window.document.body.textContent,
    /No selections to compare/,
  );
  assert.doesNotMatch(
    dom.window.document.body.textContent,
    /NaN|undefined|All Subgroups Comply/,
  );
  dom.window.close();
});
test("uploaded fields are escaped when actual API data are rendered", async () => {
  const data = structuredClone(
    fixtures["/api/fairness/audit?scope=validation&intersectional=false"],
  );
  data.audit.gender.groups[0].group = '<img src=x onerror="alert(1)">';
  const dom = await mount("fairness", {
    "/api/fairness/audit?scope=validation&intersectional=false": data,
  });
  assert.equal(
    dom.window.document.querySelectorAll("#fairness-table img").length,
    0,
  );
  assert.match(
    dom.window.document.querySelector("#fairness-table").textContent,
    /<img src=x/,
  );
  dom.window.close();
});
test("all six real page consumers render without contract errors", async () => {
  for (const page of [
    "overview",
    "applicants",
    "fairness",
    "models",
    "data",
    "settings",
  ]) {
    const dom = await mount(page);
    assert.doesNotMatch(
      dom.window.document.body.textContent,
      /This view could not load|NaN|undefined/,
    );
    dom.window.close();
  }
});
test("candidate evidence contains actual paths and measured effects", async () => {
  const dom = await mount("applicants");
  const html = dom.window.FairRecruit.explanationHtml(fixtures.explanation);
  assert.match(html, /Actual tree decision path/);
  assert.match(html, /Measured attribute sensitivity/);
  assert.doesNotMatch(html, /confidence_pct|Senior Veteran|guarantee/);
  dom.window.close();
});
test("ablation submit renders all tradeoffs and a separate apply action", async () => {
  const dom = await mount("fairness", {
    "/api/fairness/ablate": fixtures.experiment,
  });
  const w = dom.window;
  w.document
    .getElementById("ablation-form")
    .dispatchEvent(new w.Event("submit", { bubbles: true, cancelable: true }));
  for (let i = 0; i < 100 && !w.document.getElementById("ablation-result"); i++)
    await new Promise((resolve) => setTimeout(resolve, 5));
  const result = w.document.getElementById("ablation-result");
  assert.ok(result);
  for (const text of [
    "Selection-rate gap",
    "Recall gap",
    "Precision gap",
    "Scope accuracy",
    "ROC-AUC",
  ])
    assert.match(result.textContent, new RegExp(text));
  assert.equal(
    result.querySelector('[data-action="apply-ablation"]').dataset.run,
    fixtures.experiment.run_id,
  );
  assert.match(result.textContent, /before-and-after rates/);
  dom.window.close();
});
test("scope, tabs, input labels and landmarks pass automated accessibility checks", async () => {
  for (const page of [
    "overview",
    "applicants",
    "fairness",
    "models",
    "data",
    "settings",
  ]) {
    const dom = await mount(page);
    dom.window.eval(axe.source);
    const result = await dom.window.axe.run(dom.window.document, {
      rules: { "color-contrast": { enabled: false } },
    });
    assert.equal(
      result.violations.length,
      0,
      JSON.stringify({
        page,
        violations: result.violations.map((v) => ({
          id: v.id,
          nodes: v.nodes.map((n) => n.target),
        })),
      }),
    );
    dom.window.close();
  }
});
