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
    verb: "Find",
    agentNeedle: "Data Ingestion",
    description: "Profiles Kaggle data and writes source, schema, and finding memory cards.",
  },
  {
    number: 2,
    verb: "Rank",
    agentNeedle: "Classification",
    description: "Recalls Agent 1 output and writes the risk baseline plus ranked findings.",
  },
  {
    number: 3,
    verb: "Act",
    agentNeedle: "Reconciliation",
    description: "Chooses fix, flag, manual review, or escalation and creates Memory Patches.",
  },
  {
    number: 4,
    verb: "Explain",
    agentNeedle: "Narrative",
    description: "Recalls the full evidence chain and generates a compliance-readable report.",
  },
  {
    number: 5,
    verb: "Show",
    agentNeedle: "UI Demo",
    description: "Displays the memory trail and records explicit compliance feedback.",
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

function outcomeForStage(run, stage) {
  return (run?.outcomes || []).find((outcome) => outcome.agent.includes(stage.agentNeedle));
}

function metrics(run) {
  const findings = run?.findings || [];
  return {
    readiness: run?.report?.readiness_score ?? "--",
    critical: findings.filter((finding) => finding.severity === "Critical").length,
    findings: findings.length,
    ready: findings.filter((finding) => ["Safe Auto-Fix", "Suggested Fix"].includes(finding.suggested_action)).length,
    patches: (run?.patches || []).length,
  };
}

function renderMetrics(run) {
  const m = metrics(run);
  $("scoreRing").textContent = m.readiness === "--" ? "--" : `${m.readiness}`;
  $("criticalMetric").textContent = m.critical;
  $("findingsMetric").textContent = m.findings;
  $("readyMetric").textContent = m.ready;
  $("patchMetric").textContent = m.patches;
  $("runId").textContent = run ? run.run_id : "Run not started";
  if (run?.data_sources?.length) {
    const source = run.data_sources.find((item) => item.source_id.includes("data_rescue")) || run.data_sources[0];
    $("sourceMeta").textContent = `${source.row_count.toLocaleString()} rows · ${source.columns.length} columns · hash ${source.content_hash}`;
  }
}

function renderStages(run) {
  $("stageGrid").innerHTML = stages
    .map((stage) => {
      const outcome = outcomeForStage(run, stage);
      const ready = Boolean(outcome);
      return `
        <article class="stage-card ${ready ? "ready" : "waiting"}">
          <div>
            <div class="chip-row">
              <span class="chip">Agent ${stage.number}</span>
              <span class="chip">${ready ? "Ready" : "Waiting"}</span>
            </div>
            <h3>${stage.verb}</h3>
            <p>${stage.description}</p>
          </div>
          <div class="memory-count">
            <span>Reads ${outcome?.memory_reads ?? 0}</span>
            <span>Writes ${outcome?.memory_writes ?? 0}</span>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderPassports(run) {
  const findings = run?.findings || [];
  if (!findings.length) {
    $("passportList").innerHTML = `<div class="empty-state">Run the agents to generate evidence-backed passports.</div>`;
    return;
  }
  if (!state.selectedFindingId || !findings.some((finding) => finding.finding_id === state.selectedFindingId)) {
    state.selectedFindingId = findings[0].finding_id;
  }
  $("passportList").innerHTML = findings
    .map(
      (finding) => `
      <button class="passport-item ${finding.finding_id === state.selectedFindingId ? "active" : ""}" data-finding-id="${finding.finding_id}">
        <div class="passport-top">
          <span class="chip">${finding.finding_id}</span>
          <span class="${severityClass(finding.severity)}">${finding.severity} · ${finding.risk_score}</span>
        </div>
        <strong>${finding.type}</strong>
        <small>${finding.affected_entity}</small>
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
    $("detailTitle").textContent = "No passport selected";
    $("passportDetail").innerHTML = "Select a passport after running the agents.";
    return;
  }
  $("detailTitle").textContent = `${finding.finding_id} · ${finding.type}`;
  $("passportDetail").innerHTML = `
    <div class="detail-block">
      <strong class="${severityClass(finding.severity)}">${finding.severity} risk · ${finding.risk_score}</strong>
      <p>${finding.why_broken}</p>
      <p><strong>Ranking reason:</strong> ${finding.ranking_reason || "Pending ranking"}</p>
      <p><strong>Recommended action:</strong> ${finding.suggested_action}</p>
      <p><strong>Action rationale:</strong> ${finding.action_rationale || "Pending remediation"}</p>
      ${finding.ripple_note ? `<p><strong>Ripple update:</strong> ${finding.ripple_note}</p>` : ""}
    </div>
    <div class="detail-block">
      <strong>Evidence pointers</strong>
      <div class="evidence-grid">
        ${(finding.evidence || [])
          .map(
            (evidence) => `
            <div class="evidence-row">
              <strong>${evidence.source_file} · row ${evidence.row_number}</strong><br>
              ${evidence.field_name}: ${evidence.observed_value}<br>
              <small>${evidence.explanation}</small>
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
      "Click New evidence found after the first run to apply a Memory Patch and refresh risk, action, and report language.";
    $("diffCard").innerHTML = `<span>Before / after appears here</span>`;
    return;
  }
  $("rippleSummary").textContent = `${patch.patch_id}: ${patch.change_summary} ${patch.reason}`;
  $("diffCard").innerHTML = `
    <div class="diff-grid">
      <div class="diff-box">
        <div class="diff-label">Before</div>
        <h3>Risk ${patch.before.risk_score}</h3>
        <strong>${patch.before.action}</strong>
        <p>${patch.before.interpretation}</p>
      </div>
      <div class="diff-box after">
        <div class="diff-label">After</div>
        <h3>Risk ${patch.after.risk_score}</h3>
        <strong>${patch.after.action}</strong>
        <p>${patch.after.interpretation}</p>
      </div>
    </div>
  `;
}

function renderTimeline(run) {
  const events = (run?.memory_events || []).slice(-18).reverse();
  if (!events.length) {
    $("memoryTimeline").innerHTML = `<div class="empty-state">No memory events yet.</div>`;
    return;
  }
  $("memoryTimeline").innerHTML = events
    .map(
      (event) => `
      <div class="timeline-event">
        <strong>${event.agent || "Agent"}</strong>
        <span>${event.event_type || "memory"}</span>
        <small>${event.dataset || ""} · ${event.summary || event.status || ""}</small>
      </div>
    `,
    )
    .join("");
}

function render() {
  const run = state.activeRun;
  renderMetrics(run);
  renderStages(run);
  renderPassports(run);
  renderDetail(run);
  renderRipple(run);
  renderTimeline(run);
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
    $("passportList").innerHTML = `<div class="empty-state">Could not load web/data/audit_run.json. Run python -m src.audit_passport.export_web_data first.</div>`;
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
