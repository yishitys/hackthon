const state = {
  initialRun: null,
  rippleRun: null,
  activeRun: null,
  selectedFindingId: null,
  hasRun: false,
  rippleApplied: false,
};

const stages = [
  {
    number: 1,
    verb: "Check file",
    agentNeedle: "Data Ingestion",
    description: "Read the records and spot obvious problems.",
  },
  {
    number: 2,
    verb: "Sort risks",
    agentNeedle: "Classification",
    description: "Put the biggest audit risks first.",
  },
  {
    number: 3,
    verb: "Choose action",
    agentNeedle: "Reconciliation",
    description: "Decide whether to fix, review, or escalate.",
  },
  {
    number: 4,
    verb: "Write brief",
    agentNeedle: "Narrative",
    description: "Turn the result into a plain audit summary.",
  },
  {
    number: 5,
    verb: "Show proof",
    agentNeedle: "UI Demo",
    description: "Show the issue and the next step.",
  },
];

function $(id) {
  return document.getElementById(id);
}

async function loadData() {
  const [initial, ripple] = await Promise.all([
    fetch("./data/audit_run.json").then((res) => res.json()),
    fetch("./data/audit_ripple.json").then((res) => res.json()),
  ]);
  state.initialRun = initial;
  state.rippleRun = ripple;
}

function severityClass(severity) {
  return `severity-${String(severity || "").toLowerCase()}`;
}

function uncertaintyClass(finding) {
  return `uncertainty-${finding?.uncertainty_level || "unscored"}`;
}

function formatProbability(value) {
  if (typeof value !== "number" || Number.isNaN(value)) return "--";
  return `${Math.round(value * 100)}%`;
}

function formatInterval(finding) {
  if (typeof finding?.credible_interval_low !== "number" || typeof finding?.credible_interval_high !== "number") {
    return "--";
  }
  return `${formatProbability(finding.credible_interval_low)}-${formatProbability(finding.credible_interval_high)}`;
}

function plainSeverity(severity) {
  const labels = {
    Critical: "Urgent",
    High: "High",
    Medium: "Medium",
    Low: "Low",
  };
  return labels[severity] || severity || "Unknown";
}

function plainAction(action) {
  const labels = {
    Escalate: "Escalate now",
    "Manual Review Required": "Needs review",
    "Suggested Fix": "Can fix",
    "Safe Auto-Fix": "Safe to fix",
  };
  return labels[action] || action || "Review";
}

function shortIssueText(finding) {
  if (finding.audit_risk) return finding.audit_risk;
  return finding.why_broken || "This record may cause trouble during audit review.";
}

function outcomeForStage(run, stage) {
  return (run?.outcomes || []).find((outcome) => outcome.agent.includes(stage.agentNeedle));
}

function metrics(run) {
  const findings = run?.findings || [];
  return {
    readiness: run?.report?.readiness_score ?? "--",
    readinessProbability: run?.report?.readiness_probability ?? null,
    readinessLow: run?.report?.readiness_interval_low ?? null,
    readinessHigh: run?.report?.readiness_interval_high ?? null,
    readinessUncertainty: run?.report?.readiness_uncertainty ?? "unscored",
    critical: findings.filter((finding) => finding.severity === "Critical").length,
    findings: findings.length,
    ready: findings.filter((finding) => ["Safe Auto-Fix", "Suggested Fix"].includes(finding.suggested_action)).length,
    patches: (run?.patches || []).length,
  };
}

function renderMetrics(run) {
  const m = metrics(run);
  $("scoreRing").textContent = m.readinessProbability === null ? "--" : formatProbability(m.readinessProbability);
  $("scoreRing").className = `score-ring readiness-${m.readinessUncertainty}`;
  $("readyInterval").textContent =
    m.readinessProbability === null
      ? "Run not started"
      : `90% CI ${formatProbability(m.readinessLow)}-${formatProbability(m.readinessHigh)} · ${m.readinessUncertainty} uncertainty`;
  $("criticalMetric").textContent = m.critical;
  $("findingsMetric").textContent = m.findings;
  $("readyMetric").textContent = m.ready;
  $("patchMetric").textContent = m.patches;
  $("runId").textContent = run?.report?.readiness_reason || (run ? run.run_id : "No posterior yet");
  if (run?.data_sources?.length) {
    const source = run.data_sources.find((item) => item.source_id.includes("data_rescue")) || run.data_sources[0];
    $("sourceMeta").textContent = `${source.row_count.toLocaleString()} records checked`;
  }
}

function renderStages(run) {
  $("stageGrid").innerHTML = stages
    .map((stage) => {
      const outcome = outcomeForStage(run, stage);
      const ready = Boolean(outcome);
      return `
        <article class="stage-card ${ready ? "ready" : "waiting"}">
          <span class="step-number">${stage.number}</span>
          <h3>${stage.verb}</h3>
          <p>${stage.description}</p>
          <strong>${ready ? "Done" : "Waiting"}</strong>
        </article>
      `;
    })
    .join("");
}

function renderPassports(run) {
  const findings = run?.findings || [];
  if (!findings.length) {
    $("passportList").innerHTML = `<div class="empty-state">Start the demo to see the risk list.</div>`;
    return;
  }
  if (!state.selectedFindingId || !findings.some((finding) => finding.finding_id === state.selectedFindingId)) {
    state.selectedFindingId = findings[0].finding_id;
  }
  $("passportList").innerHTML = findings
    .map(
      (finding) => `
      <button class="passport-item ${finding.finding_id === state.selectedFindingId ? "active" : ""} ${uncertaintyClass(finding)}" data-finding-id="${finding.finding_id}">
        <div class="passport-top">
          <span class="${severityClass(finding.severity)}">${plainSeverity(finding.severity)}</span>
          <span class="risk-pill">Risk ${finding.risk_score}</span>
        </div>
        <strong>${finding.type}</strong>
        <span class="action-line">${plainAction(finding.suggested_action)}</span>
      </button>
    `,
    )
    .join("");
  document.querySelectorAll("[data-finding-id]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedFindingId = button.dataset.findingId;
      render();
      location.hash = "#detail";
    });
  });
}

function renderDetail(run) {
  const finding = (run?.findings || []).find((item) => item.finding_id === state.selectedFindingId);
  if (!finding) {
    $("detailTitle").textContent = "Nothing selected yet";
    $("passportDetail").innerHTML = "Pick an issue from the list after starting the demo.";
    return;
  }
  $("detailTitle").textContent = finding.type;
  $("passportDetail").innerHTML = `
    <div class="detail-summary">
      <div>
        <span>Risk</span>
        <strong class="${severityClass(finding.severity)}">${plainSeverity(finding.severity)} · ${finding.risk_score}</strong>
      </div>
      <div>
        <span>Next step</span>
        <strong>${plainAction(finding.suggested_action)}</strong>
      </div>
      <div>
        <span>Where</span>
        <strong>${finding.affected_entity}</strong>
      </div>
    </div>
    <div class="detail-block">
      <h3>Why it matters</h3>
      <p>${shortIssueText(finding)}</p>
      <p>${finding.action_rationale || "A person should confirm the final change before sign-off."}</p>
      ${finding.ripple_note ? `<p class="update-note">${finding.ripple_note}</p>` : ""}
    </div>
    <div class="detail-block evidence-preview">
      <h3>Sample records</h3>
      <div class="evidence-grid">
        ${(finding.evidence || [])
          .slice(0, 2)
          .map(
            (evidence) => `
            <div class="evidence-row">
              <strong>Row ${evidence.row_number}</strong>
              <span>${evidence.field_name}: ${evidence.observed_value}</span>
            </div>
          `,
          )
          .join("")}
      </div>
    </div>
  `;
}

function renderRipple(run) {
  const patch = (run?.patches || []).at(-1);
  if (!patch) {
    $("rippleSummary").textContent =
      "After the first run, add new evidence to see one issue become less risky.";
    $("diffCard").innerHTML = `<span>Before and after will appear here.</span>`;
    return;
  }
  $("rippleSummary").textContent = "A supplier file explains part of the problem, so the system lowers the risk and updates the action.";
  $("diffCard").innerHTML = `
    <div class="diff-grid">
      <div class="diff-box">
        <div class="diff-label">Before</div>
        <h3>Risk ${patch.before.risk_score}</h3>
        <strong>${plainAction(patch.before.action)}</strong>
      </div>
      <div class="diff-box after">
        <div class="diff-label">After</div>
        <h3>Risk ${patch.after.risk_score}</h3>
        <strong>${plainAction(patch.after.action)}</strong>
      </div>
    </div>
  `;
}

function render() {
  const run = state.activeRun;
  renderMetrics(run);
  renderStages(run);
  renderPassports(run);
  renderDetail(run);
  renderRipple(run);
  $("rippleBtn").disabled = !state.hasRun || state.rippleApplied;
  $("downloadReportBtn").disabled = !state.hasRun;
}

function downloadReportBrief() {
  const anchor = document.createElement("a");
  anchor.href = "./data/audit_passport_summary.pdf";
  anchor.download = "audit_passport_summary.pdf";
  anchor.click();
}

async function init() {
  try {
    await loadData();
  } catch (error) {
    $("passportList").innerHTML = `<div class="empty-state">Demo data is not ready yet.</div>`;
    console.error(error);
  }
  render();

  $("runAgentsBtn").addEventListener("click", () => {
    state.activeRun = structuredClone(state.initialRun);
    state.hasRun = true;
    state.rippleApplied = false;
    state.selectedFindingId = state.activeRun?.findings?.[0]?.finding_id || null;
    render();
    location.hash = "#handoff";
  });

  $("rippleBtn").addEventListener("click", () => {
    state.activeRun = structuredClone(state.rippleRun);
    state.rippleApplied = true;
    const target = state.activeRun?.patches?.at(-1)?.affected_findings?.[0];
    if (target) state.selectedFindingId = target;
    render();
    location.hash = "#detail";
  });

  $("downloadReportBtn").addEventListener("click", downloadReportBrief);
}

init();
