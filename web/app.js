const state = {
  initialRun: null,
  rippleRun: null,
  activeRun: null,
  selectedFindingId: null,
  hasRun: false,
  rippleApplied: false,
  dataLoadFailed: false,
  isRunning: false,
  runError: "",
  runMessage: "",
  runJobId: "",
  activeStageNumber: null,
  activeScriptStepNumber: null,
  completedStageNumbers: new Set(),
  handoffNotice: "",
  demoTimers: [],
  userRiskOrder: [],
  remediationDecisions: {},
  rejectDraft: null,
};

const stages = [
  {
    number: 1,
    verb: "Ingest",
    agentLabel: "Data Ingestion & Detective Agent",
    agentNeedle: "Data Ingestion",
    description: "Read the files and create source memory.",
    script: [
      "Open the warehouse files and profile every column.",
      "Promote risky rows into evidence-backed findings.",
      "Write sources, schema, candidates, findings, and trace cards.",
    ],
    demoReads: 1,
    demoWrites: 8,
  },
  {
    number: 2,
    verb: "Rank",
    agentLabel: "Classification & Risk Prioritizer Agent",
    agentNeedle: "Classification",
    description: "Recall source memory and rank audit risk.",
    script: [
      "Recall Agent 1 findings, sources, and schema.",
      "Score each issue by audit-blocker probability.",
      "Write the ranked baseline and updated finding cards.",
    ],
    demoReads: 1,
    demoWrites: 7,
  },
  {
    number: 3,
    verb: "Resolve",
    agentLabel: "Reconciliation & Remediation Agent",
    agentNeedle: "Reconciliation",
    description: "Choose fix, review, or escalation.",
    script: [
      "Read ranked findings and prior baselines.",
      "Choose fix, review, or escalation with reasons.",
      "Write remediation decisions for downstream review.",
    ],
    demoReads: 1,
    demoWrites: 12,
  },
  {
    number: 4,
    verb: "Narrate",
    agentLabel: "Narrative & Audit Report Agent",
    agentNeedle: "Narrative",
    description: "Write the executive audit brief.",
    script: [
      "Recall resolved evidence and remediation decisions.",
      "Draft the compliance-readable audit story.",
      "Write the final executive summary and open risks.",
    ],
    demoReads: 1,
    demoWrites: 4,
  },
  {
    number: 5,
    verb: "Present",
    agentLabel: "UI Demo & Feedback Agent",
    agentNeedle: "UI Demo",
    description: "Show evidence and capture feedback.",
    script: [
      "Read all outcomes and report cards.",
      "Package the handoff, risk table, and evidence drill-down.",
      "Capture explicit feedback as governed semantic memory.",
    ],
    demoReads: 1,
    demoWrites: 1,
  },
];

function $(id) {
  return document.getElementById(id);
}

async function loadData() {
  async function getJson(path) {
    const res = await fetch(path);
    if (!res.ok) throw new Error(`${path} returned ${res.status}`);
    return res.json();
  }
  const [initial, ripple] = await Promise.all([getJson("./data/audit_run.json"), getJson("./data/audit_ripple.json")]);
  state.initialRun = initial;
  state.rippleRun = ripple;
  state.dataLoadFailed = false;
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

function severityTone(severity) {
  if (severity === "Critical" || severity === "High") return "critical";
  if (severity === "Medium") return "watch";
  return "stable";
}

function plainAction(action) {
  const labels = {
    Escalate: "Escalate now",
    "Manual Review Required": "Needs review",
    "Suggested Fix": "Can fix",
    "Safe Auto-Fix": "Safe to fix",
    "Pending triage": "Needs triage",
  };
  return labels[action] || action || "Review";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function shortIssueText(finding) {
  if (finding.audit_risk) return finding.audit_risk;
  return finding.why_broken || "This record may cause trouble during audit review.";
}

function whereText(finding) {
  if (finding.affected_entity) return finding.affected_entity;
  const evidence = finding.evidence || [];
  if (!evidence.length) return "No row pointer available";
  const source = evidence[0].source_file || "Source file";
  const fields = [...new Set(evidence.map((item) => item.field_name).filter(Boolean))];
  const rows = evidence.map((item) => item.row_number).filter(Boolean).slice(0, 4);
  const rowText = rows.length ? `rows ${rows.join(", ")}${evidence.length > rows.length ? ", ..." : ""}` : "row pointers";
  return `${source} · ${fields.join(", ") || "field"} · ${rowText}`;
}

const categoryRules = [
  {
    id: "chronology",
    label: "Chronology breach",
    tone: "crisis",
    description: "Shipping or transaction timing conflicts with production chronology, so cutoff and traceability assertions need source-of-truth proof.",
    keywords: ["ship date", "chronology", "production_date", "ship_date"],
  },
  {
    id: "negative-quantity",
    label: "Negative quantity",
    tone: "crisis",
    description: "Inventory or production quantities are below zero without transaction semantics proving a return, scrap, or reversal.",
    keywords: ["negative quantities", "negative quantity", "positive quantity", "returns/scrap"],
  },
  {
    id: "conflicting-values",
    label: "Conflicting values",
    tone: "watch",
    description: "The same auditable entity carries different values, so an authoritative version rule must be chosen before reporting.",
    keywords: ["conflicting quantities", "conflicting numeric", "authoritative version", "versioning"],
  },
  {
    id: "master-data-gap",
    label: "Master data gap",
    tone: "watch",
    description: "Transaction records reference master records that do not exist, leaving the evidence chain incomplete.",
    keywords: ["customer master", "missing from the customer", "master-data", "customer_id"],
  },
  {
    id: "duplicate-signature",
    label: "Duplicate signature",
    tone: "stable",
    description: "Rows appear repeated or near-repeated; confirm true double counting before deleting or merging records.",
    keywords: ["duplicate row", "duplicate signature", "double-count"],
  },
  {
    id: "unit-semantics",
    label: "Unit semantics",
    tone: "stable",
    description: "Quantity fields are mixed with measurement units, so reporting logic needs a clear business definition.",
    keywords: ["physical measurement units", "unit", "mm", "count vs measurement"],
  },
];

function categoryForFinding(finding) {
  const idOverrides = {
    "F-DC-001": "master-data-gap",
    "F-DC-002": "chronology",
    "F-DC-003": "negative-quantity",
    "F-DC-004": "unit-semantics",
    "F-DC-005": "conflicting-values",
    "F-DC-006": "duplicate-signature",
  };
  const override = categoryRules.find((category) => category.id === idOverrides[finding.finding_id]);
  if (override) return override;
  const evidenceText = (finding.evidence || [])
    .map((item) => `${item.field_name} ${item.observed_value} ${item.expected_or_conflicting_value} ${item.explanation}`)
    .join(" ");
  const haystack = [
    finding.finding_id,
    finding.ranking_reason,
    finding.action_rationale,
    finding.audit_risk,
    finding.why_broken,
    evidenceText,
  ]
    .join(" ")
    .toLowerCase();
  return (
    categoryRules.find((category) => category.keywords.some((keyword) => haystack.includes(keyword.toLowerCase()))) || {
      id: "other",
      label: "Other audit issue",
      tone: "watch",
      description: "The issue needs human review because it can weaken audit readiness.",
    }
  );
}

function groupedFindings(findings) {
  const groups = new Map();
  findings.forEach((finding) => {
    const category = categoryForFinding(finding);
    if (!groups.has(category.id)) groups.set(category.id, { ...category, findings: [] });
    groups.get(category.id).findings.push(finding);
  });
  return [...groups.values()].sort((a, b) => {
    const maxA = Math.max(...a.findings.map((finding) => finding.risk_score));
    const maxB = Math.max(...b.findings.map((finding) => finding.risk_score));
    return maxB - maxA;
  });
}

function decisionKey(findingId, evidence) {
  return `${findingId}::${evidence.row_number}::${evidence.field_name}`;
}

function ensureUserState(run) {
  const findings = run?.findings || [];
  const ids = findings.map((finding) => finding.finding_id);
  state.userRiskOrder = state.userRiskOrder.filter((id) => ids.includes(id));
  ids.forEach((id) => {
    if (!state.userRiskOrder.includes(id)) state.userRiskOrder.push(id);
  });
}

function orderedFindings(run) {
  const findings = run?.findings || [];
  ensureUserState(run);
  const byId = new Map(findings.map((finding) => [finding.finding_id, finding]));
  return state.userRiskOrder.map((id) => byId.get(id)).filter(Boolean);
}

function recommendedRepairText(finding, evidence) {
  const category = categoryForFinding(finding);
  const target = `${evidence.field_name}=${evidence.observed_value}`;
  if (category.id === "chronology") return `Verify ${target} against ERP/WMS/BOL source dates, then correct the shipment date lineage or quarantine the row.`;
  if (category.id === "negative-quantity") return `Map ${target} to an approved return/scrap/reversal transaction type before using it in inventory valuation.`;
  if (category.id === "conflicting-values") return `Select the authoritative quantity for row ${evidence.row_number} using revision timestamp, status, or source-system priority.`;
  if (category.id === "master-data-gap") return `Reconcile ${target} to the customer master; attach the approved master record or hold the transaction.`;
  if (category.id === "duplicate-signature") return `Confirm whether row ${evidence.row_number} is a true duplicate before merge/delete; keep evidence if it is a legitimate repeat.`;
  if (category.id === "unit-semantics") return `Define whether ${target} is a count or measurement and route it to the correct reporting field.`;
  return finding.action_rationale || "Review the evidence and document the chosen remediation.";
}

function decisionStats(run, findingId = null) {
  const findings = run?.findings || [];
  let total = 0;
  let accepted = 0;
  let rejected = 0;
  findings.forEach((finding) => {
    if (findingId && finding.finding_id !== findingId) return;
    (finding.evidence || []).forEach((evidence) => {
      total += 1;
      const decision = state.remediationDecisions[decisionKey(finding.finding_id, evidence)];
      if (decision?.status === "accepted") accepted += 1;
      if (decision?.status === "rejected") rejected += 1;
    });
  });
  return {
    total,
    accepted,
    rejected,
    decided: accepted + rejected,
    pending: Math.max(0, total - accepted - rejected),
  };
}

function finalDecisionRows(run) {
  const rows = [];
  (run?.findings || []).forEach((finding) => {
    (finding.evidence || []).forEach((evidence) => {
      const key = decisionKey(finding.finding_id, evidence);
      const decision = state.remediationDecisions[key];
      if (!decision) return;
      rows.push({
        finding,
        evidence,
        decision,
        category: categoryForFinding(finding),
      });
    });
  });
  return rows;
}

function resetUserReviewState() {
  state.userRiskOrder = [];
  state.remediationDecisions = {};
  state.rejectDraft = null;
}

function outcomeForStage(run, stage) {
  return (run?.outcomes || []).find((outcome) => outcome.agent.includes(stage.agentNeedle));
}

function traceForStage(run, stage) {
  return (run?.prompt_traces || []).find((trace) => trace.agent.includes(stage.agentNeedle));
}

function shortTraceSummary(trace) {
  const summary = String(trace?.input_summary || "");
  if (!summary) return "";
  return summary.length > 132 ? `${summary.slice(0, 132)}...` : summary;
}

function clearDemoTimers() {
  state.demoTimers.forEach((timer) => clearTimeout(timer));
  state.demoTimers = [];
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
      : `Confidence range ${formatProbability(m.readinessLow)}-${formatProbability(m.readinessHigh)}`;
  $("criticalMetric").textContent = m.critical;
  $("findingsMetric").textContent = m.findings;
  $("readyMetric").textContent = m.ready;
  $("patchMetric").textContent = m.patches;
  $("runId").textContent = run?.report?.readiness_reason || (run ? "Agent run complete" : "Waiting for agent handoff");
  $("executiveSummary").textContent =
    state.runError ||
    (state.isRunning ? "Demo handoff running. Watch the map below to see control move between agents." : "") ||
    run?.report?.executive_summary ||
    "Start the demo to find the risky records, prove why they matter, and generate the next action.";
  if (run?.data_sources?.length) {
    const source = run.data_sources.find((item) => item.source_id.includes("data_rescue")) || run.data_sources[0];
    $("sourceMeta").textContent = `${source.row_count.toLocaleString()} records checked`;
  }
}

function renderStages(run) {
  $("stageGrid").innerHTML = stages
    .map((stage) => {
      const outcome = outcomeForStage(run, stage);
      const ready = Boolean(outcome) || state.completedStageNumbers.has(stage.number);
      const active = state.activeStageNumber === stage.number;
      const statusLabel = active ? "Running" : ready ? "Done" : "Armed";
      const reads = outcome?.memory_reads ?? (ready || active ? stage.demoReads : 0);
      const writes = outcome?.memory_writes ?? (ready || active ? stage.demoWrites : 0);
      return `
        <article class="pstep ${ready ? "is-done" : "is-pending"} ${active ? "is-active" : ""}">
          <div class="pstep-n">0${stage.number} · ${outcome?.agent || stage.agentLabel}</div>
          <div class="pstep-name">${stage.verb}</div>
          <div class="pstep-copy">${stage.description}</div>
          <div class="pstep-status">${statusLabel} · Read ${reads} / Write ${writes}</div>
          <div class="pstep-script">
            <div class="script-label">Script</div>
            ${stage.script
              .map(
                (line, index) => `
                  <div class="script-line ${active && state.activeScriptStepNumber === index + 1 ? "is-current" : ""}">
                    <span>${index + 1}</span>
                    <p>${line}</p>
                  </div>
                `,
              )
              .join("")}
          </div>
        </article>
      `;
    })
    .join("");
}

function renderPassports(run) {
  const findings = orderedFindings(run);
  if (state.isRunning) {
    $("passportList").innerHTML = `<div class="empty-state">${state.runMessage || "Running live multi-agent pipeline..."}</div>`;
    return;
  }
  if (state.runError) {
    $("passportList").innerHTML = `<div class="empty-state">${state.runError}</div>`;
    return;
  }
  if (state.dataLoadFailed) {
    $("passportList").innerHTML = `<div class="empty-state">Demo data is not ready yet. Check web/data/audit_run.json.</div>`;
    return;
  }
  if (!findings.length) {
    $("passportList").innerHTML = `<div class="empty-state">Start the demo to see the risk list.</div>`;
    return;
  }
  if (!state.selectedFindingId || !findings.some((finding) => finding.finding_id === state.selectedFindingId)) {
    state.selectedFindingId = findings[0].finding_id;
  }
  const rows = findings
    .map((finding) => {
      const tone = severityTone(finding.severity);
      const category = categoryForFinding(finding);
      const reviewed = Object.entries(state.remediationDecisions).filter(([key]) => key.startsWith(`${finding.finding_id}::`)).length;
      return `
        <article
          class="risk-card ${finding.finding_id === state.selectedFindingId ? "is-selected" : ""}"
          data-finding-id="${finding.finding_id}"
          draggable="true"
          tabindex="0"
          role="button"
        >
          <div class="rank-tools">
            <div class="drag-grip" aria-hidden="true">::</div>
            <button class="rank-btn move-risk-up" type="button" data-move-id="${finding.finding_id}" aria-label="Move ${finding.finding_id} up">Up</button>
            <button class="rank-btn move-risk-down" type="button" data-move-id="${finding.finding_id}" aria-label="Move ${finding.finding_id} down">Dn</button>
          </div>
          <div class="risk-main">
            <div class="risk-topline">
              <span class="sev sev-${tone}">${plainSeverity(finding.severity)}</span>
              <span class="category-pill tone-${category.tone}">${category.label}</span>
              <span class="mono">${finding.finding_id}</span>
            </div>
            <h3>${category.label}</h3>
            <p>${category.description}</p>
            <div class="risk-foot">
              <span>${plainAction(finding.suggested_action)}</span>
              <span>${reviewed}/${(finding.evidence || []).length} records decided</span>
            </div>
          </div>
          <div class="risk-score">
            <strong>${finding.risk_score}</strong>
            <span>${formatProbability(finding.audit_blocker_probability)}</span>
          </div>
        </article>
      `;
    })
    .join("");
  $("passportList").innerHTML = `
    <div class="risk-list" aria-label="User sortable risk list">${rows}</div>
  `;
  document.querySelectorAll("[data-finding-id]").forEach((row) => {
    const select = () => {
      state.selectedFindingId = row.dataset.findingId;
      render();
      location.hash = "#detail";
    };
    row.addEventListener("click", select);
    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        select();
      }
    });
    row.addEventListener("dragstart", (event) => {
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", row.dataset.findingId);
      row.classList.add("is-dragging");
    });
    row.addEventListener("dragend", () => row.classList.remove("is-dragging"));
    row.addEventListener("dragover", (event) => {
      event.preventDefault();
      row.classList.add("is-drop-target");
    });
    row.addEventListener("dragleave", () => row.classList.remove("is-drop-target"));
    row.addEventListener("drop", (event) => {
      event.preventDefault();
      row.classList.remove("is-drop-target");
      const draggedId = event.dataTransfer.getData("text/plain");
      const targetId = row.dataset.findingId;
      if (!draggedId || draggedId === targetId) return;
      const next = state.userRiskOrder.filter((id) => id !== draggedId);
      const targetIndex = next.indexOf(targetId);
      next.splice(targetIndex, 0, draggedId);
      state.userRiskOrder = next;
      render();
    });
  });
  document.querySelectorAll(".move-risk-up, .move-risk-down").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      const id = button.dataset.moveId;
      const currentIndex = state.userRiskOrder.indexOf(id);
      const direction = button.classList.contains("move-risk-up") ? -1 : 1;
      const nextIndex = currentIndex + direction;
      if (currentIndex < 0 || nextIndex < 0 || nextIndex >= state.userRiskOrder.length) return;
      const nextOrder = [...state.userRiskOrder];
      [nextOrder[currentIndex], nextOrder[nextIndex]] = [nextOrder[nextIndex], nextOrder[currentIndex]];
      state.userRiskOrder = nextOrder;
      render();
    });
  });
}

function renderDetail(run) {
  const finding = (run?.findings || []).find((item) => item.finding_id === state.selectedFindingId);
  if (!finding) {
    $("detailTitle").textContent = "Nothing selected yet";
    $("passportDetail").innerHTML = "Pick an issue from the list after starting the demo.";
    $("actionSummary").innerHTML = `<div class="empty-state">Pick a risk row after starting the demo.</div>`;
    return;
  }
  $("detailTitle").textContent = `${finding.finding_id} · ${finding.type}`;
  const category = categoryForFinding(finding);
  const evidenceItems = finding.evidence || [];
  const selectedStats = decisionStats(run, finding.finding_id);
  const overallStats = decisionStats(run);
  $("actionSummary").innerHTML = `
    <div class="action">
      <span class="a-idx">1</span>
      <div>
        <div class="a-title">${category.label}</div>
        <div class="a-meta">${finding.severity} risk · user rank ${state.userRiskOrder.indexOf(finding.finding_id) + 1}</div>
      </div>
    </div>
    <div class="action">
      <span class="a-idx">2</span>
      <div>
        <div class="a-title">${selectedStats.decided}/${selectedStats.total} selected records decided</div>
        <div class="a-meta">${selectedStats.accepted} adopted · ${selectedStats.rejected} custom · ${selectedStats.pending} pending</div>
      </div>
    </div>
    <div class="action">
      <span class="a-idx">3</span>
      <div>
        <div class="a-title">${overallStats.decided}/${overallStats.total} total record decisions captured</div>
        <div class="a-meta">This is the user-owned remediation handoff.</div>
      </div>
    </div>
  `;
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
        <strong>${whereText(finding)}</strong>
      </div>
    </div>
    <div class="detail-block">
      <h3>Why it matters</h3>
      <p>${shortIssueText(finding)}</p>
      <p>${category.description}</p>
      <p>${finding.action_rationale || "A person should confirm the final change before sign-off."}</p>
      ${finding.ripple_note ? `<p class="update-note">${finding.ripple_note}</p>` : ""}
      <div class="confidence-note">Blocker chance ${formatProbability(finding.audit_blocker_probability)} · ${finding.uncertainty_level || "unscored"} uncertainty</div>
    </div>
    <div class="detail-block evidence-preview">
      <h3>Records needing a decision</h3>
      <div class="evidence-grid">
        ${evidenceItems
          .map(
            (evidence) => {
              const key = decisionKey(finding.finding_id, evidence);
              const decision = state.remediationDecisions[key];
              const recommended = recommendedRepairText(finding, evidence);
              return `
            <div class="evidence-row">
              <div class="evidence-text">
                <strong>Row ${evidence.row_number}</strong>
                <span>${evidence.field_name}: ${evidence.observed_value}</span>
                <small>Recommended: ${recommended}</small>
                ${
                  decision
                    ? `<em class="decision-note ${decision.status === "accepted" ? "is-accepted" : "is-rejected"}">${
                        decision.status === "accepted" ? "Accepted" : "Rejected"
                      }: ${escapeHtml(decision.plan)}</em>`
                    : ""
                }
              </div>
              <div class="decision-controls">
                <button class="mini-btn accept-fix" type="button" data-decision-key="${escapeHtml(key)}">Adopt</button>
                <button class="mini-btn reject-fix" type="button" data-reject-key="${escapeHtml(key)}">Reject</button>
              </div>
            </div>
          `;
            },
          )
          .join("")}
      </div>
    </div>
  `;
  document.querySelectorAll(".accept-fix").forEach((button) => {
    button.addEventListener("click", () => {
      const key = button.dataset.decisionKey;
      const evidence = evidenceItems.find((item) => decisionKey(finding.finding_id, item) === key);
      if (!evidence) return;
      state.remediationDecisions[key] = {
        status: "accepted",
        plan: recommendedRepairText(finding, evidence),
      };
      render();
    });
  });
  document.querySelectorAll(".reject-fix").forEach((button) => {
    button.addEventListener("click", () => {
      const key = button.dataset.rejectKey;
      const evidence = evidenceItems.find((item) => decisionKey(finding.finding_id, item) === key);
      if (!evidence) return;
      state.rejectDraft = {
        key,
        findingId: finding.finding_id,
        rowNumber: evidence.row_number,
        fieldName: evidence.field_name,
        recommendation: recommendedRepairText(finding, evidence),
        plan: state.remediationDecisions[key]?.status === "rejected" ? state.remediationDecisions[key].plan : "",
      };
      renderRejectDialog();
    });
  });
}

function renderQualityAlerts(run) {
  const findings = run?.findings || [];
  if (!findings.length) {
    $("qualityAlerts").innerHTML = `
      <div class="qalert is-watch">
        <span class="q-ic">?</span>
        <div>
          <div class="q-t">Awaiting triage</div>
          <div class="q-d">Start the demo to generate audit findings.</div>
        </div>
      </div>
    `;
    return;
  }
  const groups = groupedFindings(findings);
  $("qualityAlerts").innerHTML = groups
    .map((group) => {
      const maxRisk = Math.max(...group.findings.map((finding) => finding.risk_score));
      return `
      <div class="qalert is-${group.tone}">
        <span class="q-ic">${group.findings.length}</span>
        <div>
          <div class="q-t">${group.label}</div>
          <div class="q-d">${group.description}</div>
          <div class="q-meta">Top risk ${maxRisk} · ${group.findings.map((finding) => finding.finding_id).join(", ")}</div>
        </div>
      </div>
    `;
    })
    .join("");
}

function renderRejectDialog() {
  const dialog = $("rejectDialog");
  if (!dialog) return;
  if (!state.rejectDraft) {
    dialog.classList.remove("is-open");
    dialog.setAttribute("aria-hidden", "true");
    dialog.innerHTML = "";
    return;
  }
  const draft = state.rejectDraft;
  dialog.classList.add("is-open");
  dialog.setAttribute("aria-hidden", "false");
  dialog.innerHTML = `
    <div class="dialog-backdrop" data-close-dialog="true"></div>
    <section class="dialog-panel" role="dialog" aria-modal="true" aria-labelledby="rejectTitle">
      <div class="dialog-hd">
        <div>
          <p class="label">Custom repair plan</p>
          <h2 id="rejectTitle">Reject recommendation for row ${escapeHtml(draft.rowNumber)}</h2>
        </div>
        <button class="icon-btn" type="button" data-close-dialog="true" aria-label="Close">×</button>
      </div>
      <div class="dialog-bd">
        <p class="dialog-copy">Original recommendation: ${escapeHtml(draft.recommendation)}</p>
        <label class="repair-label" for="customRepair">Final repair plan</label>
        <textarea id="customRepair" rows="5" placeholder="Describe the fix the team will actually apply...">${escapeHtml(draft.plan)}</textarea>
      </div>
      <div class="dialog-ft">
        <button class="btn btn-ghost" type="button" data-close-dialog="true">Cancel</button>
        <button class="btn btn-crisis" type="button" id="saveRejectPlan">Save custom plan</button>
      </div>
    </section>
  `;
  dialog.querySelectorAll("[data-close-dialog]").forEach((item) => {
    item.addEventListener("click", () => {
      state.rejectDraft = null;
      renderRejectDialog();
    });
  });
  $("saveRejectPlan").addEventListener("click", () => {
    const plan = $("customRepair").value.trim();
    if (!plan) {
      $("customRepair").focus();
      return;
    }
    state.remediationDecisions[draft.key] = { status: "rejected", plan };
    state.rejectDraft = null;
    render();
  });
  $("customRepair").focus();
}

function renderFinalRepairPlan(run) {
  const stats = decisionStats(run);
  const rows = finalDecisionRows(run);
  const patch = (run?.patches || []).at(-1);
  $("finalSummary").innerHTML = `
    <div>
      <span>Decided</span>
      <strong>${stats.decided} / ${stats.total} records</strong>
    </div>
    <div>
      <span>Adopted</span>
      <strong>${stats.accepted} recommendations</strong>
    </div>
    <div>
      <span>Custom</span>
      <strong>${stats.rejected} repair plans</strong>
    </div>
  `;
  if (!run?.findings?.length) {
    $("rippleSummary").textContent = "Run the agents to create findings, then capture record-level repair decisions.";
    $("diffCard").innerHTML = `<div class="empty-state">Final choices will appear here.</div>`;
    return;
  }
  if (!stats.decided) {
    $("rippleSummary").textContent =
      "No final repair choices have been captured yet. Adopt recommended fixes or reject them with a custom plan.";
    $("diffCard").innerHTML = patch
      ? `
        <div class="diff-grid">
          <div class="diff-box">
            <div>
              <div class="diff-label">Evidence before</div>
              <h3>Risk ${patch.before.risk_score}</h3>
            </div>
            <strong>${plainAction(patch.before.action)}</strong>
          </div>
          <div class="diff-box after">
            <div>
              <div class="diff-label">Evidence after</div>
              <h3>Risk ${patch.after.risk_score}</h3>
            </div>
            <strong>${plainAction(patch.after.action)}</strong>
          </div>
        </div>
      `
      : `<div class="empty-state">Final choices will appear here.</div>`;
    return;
  }
  $("rippleSummary").textContent =
    `${stats.decided} of ${stats.total} record-level decisions are ready for handoff: ${stats.accepted} adopted recommendations, ${stats.rejected} custom repair plans, and ${stats.pending} still pending.`;
  $("diffCard").innerHTML = `
    <div class="decision-rollup">
      ${rows
        .slice(0, 5)
        .map(
          ({ finding, evidence, decision, category }) => `
            <div class="plan-row">
              <div>
                <strong>${finding.finding_id} · Row ${evidence.row_number}</strong>
                <span>${category.label} · ${evidence.field_name}</span>
              </div>
              <em class="${decision.status === "accepted" ? "is-accepted" : "is-rejected"}">${
                decision.status === "accepted" ? "Adopted" : "Custom"
              }</em>
              <p>${escapeHtml(decision.plan)}</p>
            </div>
          `,
        )
        .join("")}
      ${rows.length > 5 ? `<div class="rollup-more">+${rows.length - 5} more decisions captured</div>` : ""}
    </div>
  `;
}

function render() {
  const run = state.activeRun;
  if (run?.findings?.length) ensureUserState(run);
  renderMetrics(run);
  renderStages(run);
  renderPassports(run);
  renderDetail(run);
  renderQualityAlerts(run);
  renderFinalRepairPlan(run);
  $("runAgentsBtn").disabled = state.isRunning;
  $("runAgentsBtn").textContent = state.isRunning ? "Running agents..." : "▶ Start demo";
  $("rippleBtn").disabled = state.isRunning || !state.hasRun || !state.rippleRun || state.rippleApplied;
  $("downloadReportBtn").disabled = state.isRunning || !state.hasRun;
  renderRejectDialog();
}

function startHandoffDemo() {
  clearDemoTimers();
  state.isRunning = true;
  state.runError = "";
  state.runMessage = "Demo handoff running: agents are passing control through inspectable memory.";
  state.runJobId = "";
  state.dataLoadFailed = false;
  state.activeRun = null;
  state.hasRun = false;
  state.rippleApplied = false;
  state.selectedFindingId = null;
  state.activeStageNumber = null;
  state.activeScriptStepNumber = null;
  state.completedStageNumbers = new Set();
  state.handoffNotice = "";
  resetUserReviewState();
  render();

  const flow = [
    [1, "Ingest"],
    [2, "Rank"],
    [3, "Resolve"],
    [4, "Narrate"],
    [3, "Resolve"],
    [4, "Narrate"],
    [5, "Present"],
  ];
  const scriptTicks = flow.flatMap(([stageNumber, label]) =>
    [1, 2, 3].map((scriptStep) => [stageNumber, label, scriptStep]),
  );

  scriptTicks.forEach(([stageNumber, label, scriptStep], index) => {
    const timer = setTimeout(() => {
      if (state.activeStageNumber && state.activeStageNumber !== stageNumber) {
        state.completedStageNumbers.add(state.activeStageNumber);
      }
      state.activeStageNumber = stageNumber;
      state.activeScriptStepNumber = scriptStep;
      state.handoffNotice = "";
      state.runMessage = `${label} agent running script step ${scriptStep} of 3.`;
      render();
    }, index * 520);
    state.demoTimers.push(timer);
  });

  const finishTimer = setTimeout(() => {
    state.completedStageNumbers = new Set(stages.map((stage) => stage.number));
    state.activeStageNumber = null;
    state.activeScriptStepNumber = null;
    state.handoffNotice = "";
    state.activeRun = structuredClone(state.initialRun);
    state.hasRun = true;
    state.runMessage = "";
    state.selectedFindingId = state.activeRun?.findings?.[0]?.finding_id || null;
    state.isRunning = false;
    ensureUserState(state.activeRun);
    window.scrollTo({ top: 0, behavior: "smooth" });
    render();
  }, scriptTicks.length * 520 + 450);
  state.demoTimers.push(finishTimer);
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
    state.dataLoadFailed = true;
    $("passportList").innerHTML = `<div class="empty-state">Demo data is not ready yet.</div>`;
    console.error(error);
  }
  render();

  $("runAgentsBtn").addEventListener("click", startHandoffDemo);

  $("rippleBtn").addEventListener("click", () => {
    if (!state.rippleRun) return;
    state.activeRun = structuredClone(state.rippleRun);
    state.rippleApplied = true;
    resetUserReviewState();
    const target = state.activeRun?.patches?.at(-1)?.affected_findings?.[0];
    if (target) state.selectedFindingId = target;
    ensureUserState(state.activeRun);
    render();
    location.hash = "#detail";
  });

  $("downloadReportBtn").addEventListener("click", downloadReportBrief);
}

init();
