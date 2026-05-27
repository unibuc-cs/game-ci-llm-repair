"""Generate a self-contained HTML dashboard for the repair demo report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Governed Repair Dashboard</title>
  <style>
    :root {
      --bg: #f6f4ef;
      --panel: #ffffff;
      --panel-soft: #fbfaf7;
      --ink: #1b1d1f;
      --muted: #686f77;
      --line: #d9d4ca;
      --green: #1f7a4d;
      --green-soft: #e6f2eb;
      --amber: #a15c00;
      --amber-soft: #fff1d8;
      --red: #a83434;
      --red-soft: #f9e3e3;
      --violet: #6646a3;
      --violet-soft: #eee8fb;
      --teal: #0f6c78;
      --teal-soft: #e3f2f4;
      --shadow: 0 10px 28px rgba(27, 29, 31, 0.08);
      font-family: Inter, Segoe UI, Roboto, Arial, sans-serif;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-size: 14px;
      line-height: 1.45;
    }

    button,
    select {
      font: inherit;
    }

    .app {
      min-height: 100vh;
      display: grid;
      grid-template-rows: auto auto 1fr;
    }

    header {
      background: #2f3533;
      color: #fff;
      border-bottom: 4px solid #d6a33d;
    }

    .header-inner {
      max-width: 1440px;
      margin: 0 auto;
      padding: 18px 24px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
    }

    .mark {
      width: 42px;
      height: 42px;
      border-radius: 8px;
      background: linear-gradient(135deg, #d6a33d, #2aa198 55%, #6646a3);
      display: grid;
      place-items: center;
      color: #fff;
      font-weight: 800;
      flex: 0 0 auto;
      box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.3);
    }

    h1 {
      margin: 0;
      font-size: 22px;
      line-height: 1.2;
      font-weight: 750;
      letter-spacing: 0;
    }

    .subtitle {
      margin-top: 3px;
      color: #d7ddd9;
      font-size: 13px;
    }

    .run-meta {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
      color: #f7f3e9;
      font-size: 13px;
    }

    .pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      min-height: 26px;
      padding: 3px 9px;
      border-radius: 999px;
      border: 1px solid rgba(255, 255, 255, 0.24);
      white-space: nowrap;
    }

    .toolbar {
      background: #ebe7dc;
      border-bottom: 1px solid var(--line);
    }

    .toolbar-inner {
      max-width: 1440px;
      margin: 0 auto;
      padding: 12px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      flex-wrap: wrap;
    }

    .segmented {
      display: inline-grid;
      grid-auto-flow: column;
      grid-auto-columns: minmax(78px, max-content);
      border: 1px solid #c9c2b5;
      border-radius: 8px;
      overflow: hidden;
      background: #fff;
    }

    .segmented button {
      border: 0;
      border-right: 1px solid #c9c2b5;
      padding: 8px 12px;
      background: transparent;
      color: var(--ink);
      cursor: pointer;
      min-height: 36px;
    }

    .segmented button:last-child {
      border-right: 0;
    }

    .segmented button.active {
      background: #2f3533;
      color: #fff;
    }

    .selector {
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--muted);
    }

    select {
      min-height: 36px;
      border: 1px solid #c9c2b5;
      border-radius: 8px;
      background: #fff;
      padding: 0 34px 0 10px;
      color: var(--ink);
      max-width: min(70vw, 420px);
    }

    main {
      max-width: 1440px;
      width: 100%;
      margin: 0 auto;
      padding: 18px 24px 28px;
      display: grid;
      grid-template-columns: minmax(270px, 0.76fr) minmax(0, 1.8fr);
      gap: 18px;
      min-height: 0;
    }

    .left,
    .right {
      min-width: 0;
    }

    .metric-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }

    .metric {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      box-shadow: var(--shadow);
      min-height: 78px;
    }

    .metric span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }

    .metric strong {
      display: block;
      margin-top: 5px;
      font-size: 26px;
      line-height: 1;
    }

    .case-list {
      display: grid;
      gap: 10px;
    }

    .case-row {
      width: 100%;
      text-align: left;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      padding: 12px;
      cursor: pointer;
      box-shadow: var(--shadow);
    }

    .case-row.active {
      outline: 3px solid rgba(47, 53, 51, 0.16);
      border-color: #2f3533;
    }

    .case-head {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      align-items: start;
      min-width: 0;
    }

    .case-title {
      font-weight: 740;
      overflow-wrap: anywhere;
    }

    .case-desc {
      margin: 7px 0 9px;
      color: var(--muted);
      overflow-wrap: anywhere;
    }

    .chips {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      align-items: center;
    }

    .chip {
      border-radius: 999px;
      padding: 3px 8px;
      font-size: 12px;
      border: 1px solid var(--line);
      background: var(--panel-soft);
      color: var(--ink);
      white-space: nowrap;
    }

    .status-accepted {
      background: var(--green-soft);
      color: var(--green);
      border-color: #b9dac7;
    }

    .status-partial {
      background: var(--amber-soft);
      color: var(--amber);
      border-color: #efd19c;
    }

    .status-failed {
      background: var(--red-soft);
      color: var(--red);
      border-color: #edb7b7;
    }

    .level-chip {
      background: var(--violet-soft);
      color: var(--violet);
      border-color: #d5c7ef;
    }

    .mode-chip {
      background: var(--teal-soft);
      color: var(--teal);
      border-color: #b9dce1;
    }

    .detail {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      min-width: 0;
      overflow: hidden;
    }

    .detail-header {
      padding: 16px 18px;
      border-bottom: 1px solid var(--line);
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 14px;
      align-items: start;
      background: #fffdf8;
    }

    .detail-title h2 {
      margin: 0;
      font-size: 20px;
      line-height: 1.25;
      letter-spacing: 0;
      overflow-wrap: anywhere;
    }

    .detail-title p {
      margin: 6px 0 0;
      color: var(--muted);
      overflow-wrap: anywhere;
    }

    .detail-body {
      padding: 16px 18px 18px;
      display: grid;
      gap: 18px;
    }

    .section {
      min-width: 0;
    }

    .section h3 {
      margin: 0 0 9px;
      font-size: 14px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: #3c413f;
    }

    .route {
      display: grid;
      grid-template-columns: repeat(4, minmax(56px, 1fr));
      gap: 8px;
      margin-bottom: 10px;
    }

    .route-step {
      min-height: 54px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel-soft);
      padding: 8px;
    }

    .route-step strong {
      display: block;
      font-size: 15px;
    }

    .route-step span {
      color: var(--muted);
      font-size: 12px;
    }

    .route-step.active {
      border-color: #6646a3;
      background: var(--violet-soft);
    }

    .reason-list {
      margin: 0;
      padding-left: 18px;
      color: var(--muted);
    }

    .gate-timeline {
      display: grid;
      gap: 10px;
    }

    .attempt {
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      background: var(--panel-soft);
    }

    .attempt-head {
      padding: 9px 11px;
      display: flex;
      justify-content: space-between;
      gap: 10px;
      border-bottom: 1px solid var(--line);
      background: #f2efe7;
      font-weight: 700;
      overflow-wrap: anywhere;
    }

    .gates {
      display: grid;
      grid-template-columns: repeat(5, minmax(72px, 1fr));
      gap: 8px;
      padding: 10px;
    }

    .gate {
      min-height: 74px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      padding: 8px;
      min-width: 0;
    }

    .gate.ok {
      border-color: #b9dac7;
      background: var(--green-soft);
    }

    .gate.fail {
      border-color: #edb7b7;
      background: var(--red-soft);
    }

    .gate-name {
      font-weight: 750;
      text-transform: capitalize;
    }

    .gate-message {
      margin-top: 5px;
      color: var(--muted);
      font-size: 12px;
      overflow-wrap: anywhere;
    }

    .split {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 14px;
    }

    .kv {
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }

    .kv-row {
      display: grid;
      grid-template-columns: minmax(110px, 0.5fr) minmax(0, 1fr);
      border-bottom: 1px solid var(--line);
      min-height: 38px;
    }

    .kv-row:last-child {
      border-bottom: 0;
    }

    .kv-key {
      background: #f2efe7;
      padding: 9px 10px;
      color: #444947;
      font-weight: 700;
      overflow-wrap: anywhere;
    }

    .kv-value {
      padding: 9px 10px;
      overflow-wrap: anywhere;
    }

    .bar-list {
      display: grid;
      gap: 9px;
    }

    .bar-row {
      display: grid;
      grid-template-columns: minmax(130px, 0.72fr) minmax(0, 1fr) 70px;
      gap: 9px;
      align-items: center;
    }

    .bar-label {
      color: var(--muted);
      overflow-wrap: anywhere;
    }

    .bar-track {
      height: 10px;
      border-radius: 999px;
      background: #e5dfd3;
      overflow: hidden;
    }

    .bar-fill {
      height: 100%;
      width: 0;
      border-radius: 999px;
      background: #2aa198;
    }

    .bar-value {
      text-align: right;
      font-variant-numeric: tabular-nums;
    }

    details {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel-soft);
      overflow: hidden;
    }

    summary {
      cursor: pointer;
      padding: 10px 12px;
      font-weight: 750;
      background: #f2efe7;
      border-bottom: 1px solid var(--line);
    }

    details:not([open]) summary {
      border-bottom: 0;
    }

    pre {
      margin: 0;
      padding: 12px;
      max-height: 360px;
      overflow: auto;
      background: #202522;
      color: #eef3ec;
      font-size: 12px;
      line-height: 1.5;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }

    .empty {
      padding: 18px;
      border: 1px dashed #bbb2a5;
      border-radius: 8px;
      color: var(--muted);
      background: rgba(255, 255, 255, 0.55);
    }

    @media (max-width: 960px) {
      .header-inner,
      .toolbar-inner {
        padding-left: 14px;
        padding-right: 14px;
      }

      main {
        grid-template-columns: 1fr;
        padding: 14px;
      }

      .detail-header,
      .split {
        grid-template-columns: 1fr;
      }

      .gates {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
    }

    @media (max-width: 560px) {
      .header-inner {
        align-items: flex-start;
        flex-direction: column;
      }

      .run-meta {
        justify-content: flex-start;
      }

      .metric-grid,
      .route,
      .gates {
        grid-template-columns: 1fr;
      }

      .segmented {
        width: 100%;
        grid-auto-columns: 1fr;
      }

      .toolbar-inner {
        align-items: stretch;
      }

      .selector {
        width: 100%;
        justify-content: space-between;
      }

      select {
        max-width: 100%;
        min-width: 0;
      }

      .bar-row,
      .kv-row {
        grid-template-columns: 1fr;
      }

      .bar-value {
        text-align: left;
      }
    }
  </style>
</head>
<body>
  <div class="app">
    <header>
      <div class="header-inner">
        <div class="brand">
          <div class="mark" aria-hidden="true">D0</div>
          <div>
            <h1>Governed Repair Dashboard</h1>
            <div class="subtitle">D0 routing, policy levels, prompts, and CI gates</div>
          </div>
        </div>
        <div class="run-meta" id="run-meta"></div>
      </div>
    </header>

    <div class="toolbar">
      <div class="toolbar-inner">
        <div class="segmented" id="status-filter" aria-label="Status filter">
          <button type="button" class="active" data-status="all">All</button>
          <button type="button" data-status="accepted">Accepted</button>
          <button type="button" data-status="partial">Partial</button>
          <button type="button" data-status="failed">Failed</button>
        </div>
        <label class="selector">
          <span>Case</span>
          <select id="case-select"></select>
        </label>
      </div>
    </div>

    <main>
      <section class="left" aria-label="Run overview">
        <div class="metric-grid" id="metrics"></div>
        <div class="case-list" id="case-list"></div>
      </section>
      <section class="right" aria-label="Case detail">
        <div class="detail" id="detail"></div>
      </section>
    </main>
  </div>

  <script id="report-data" type="application/json">__REPORT_JSON__</script>
  <script>
    const report = JSON.parse(document.getElementById("report-data").textContent);
    const results = report.results || [];
    const summary = report.summary || {};
    const state = { status: "all", selected: results[0] ? results[0].case_id : null };

    const statusFilter = document.getElementById("status-filter");
    const caseSelect = document.getElementById("case-select");
    const caseList = document.getElementById("case-list");
    const metrics = document.getElementById("metrics");
    const detail = document.getElementById("detail");
    const runMeta = document.getElementById("run-meta");

    function cssStatus(status) {
      return status === "accepted" ? "status-accepted" :
        status === "partial" ? "status-partial" : "status-failed";
    }

    function escapeHtml(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    function filteredResults() {
      if (state.status === "all") {
        return results;
      }
      return results.filter(item => item.status === state.status);
    }

    function ensureSelection(items) {
      if (!items.length) {
        state.selected = null;
        return;
      }
      if (!items.some(item => item.case_id === state.selected)) {
        state.selected = items[0].case_id;
      }
    }

    function selectedCase() {
      return results.find(item => item.case_id === state.selected) || null;
    }

    function renderHeader() {
      runMeta.innerHTML = [
        `<span class="pill">Cases ${summary.cases ?? results.length}</span>`,
        `<span class="pill">Accepted ${summary.accepted ?? 0}</span>`,
        `<span class="pill">Partial ${summary.partial ?? 0}</span>`,
        `<span class="pill">CI ${summary.ci_runs ?? 0}</span>`,
        `<span class="pill">Patch ${escapeHtml(summary.patch_provider ?? "synthetic")}</span>`,
        `<span class="pill">Gates ${escapeHtml(summary.gate_runner ?? "synthetic")}</span>`
      ].join("");
    }

    function renderMetrics() {
      const total = summary.cases ?? results.length;
      const accepted = summary.accepted ?? results.filter(item => item.status === "accepted").length;
      const partial = summary.partial ?? results.filter(item => item.status === "partial").length;
      const ci = summary.ci_runs ?? results.reduce((acc, item) => acc + Number(item.ci_runs || 0), 0);
      metrics.innerHTML = [
        ["Cases", total],
        ["Accepted", accepted],
        ["Partial", partial],
        ["CI runs", ci]
      ].map(([label, value]) => `
        <div class="metric">
          <span>${escapeHtml(label)}</span>
          <strong>${escapeHtml(value)}</strong>
        </div>
      `).join("");
    }

    function renderCaseControls(items) {
      caseSelect.innerHTML = items.map(item => `
        <option value="${escapeHtml(item.case_id)}"${item.case_id === state.selected ? " selected" : ""}>
          ${escapeHtml(item.case_id)}
        </option>
      `).join("");
      caseSelect.disabled = !items.length;
    }

    function renderCaseList(items) {
      if (!items.length) {
        caseList.innerHTML = `<div class="empty">No cases in this status.</div>`;
        return;
      }
      caseList.innerHTML = items.map(item => `
        <button type="button" class="case-row${item.case_id === state.selected ? " active" : ""}" data-case="${escapeHtml(item.case_id)}">
          <div class="case-head">
            <div class="case-title">${escapeHtml(item.case_id)}</div>
            <span class="chip ${cssStatus(item.status)}">${escapeHtml(item.status)}</span>
          </div>
          <div class="case-desc">${escapeHtml(item.description)}</div>
          <div class="chips">
            <span class="chip level-chip">${escapeHtml(item.diagnosis.start_level)}</span>
            <span class="chip mode-chip">${escapeHtml(item.diagnosis.mode)}</span>
            <span class="chip">${escapeHtml(item.attempts)} attempts</span>
            <span class="chip">${escapeHtml(item.ci_runs)} CI</span>
          </div>
        </button>
      `).join("");

      caseList.querySelectorAll("[data-case]").forEach(button => {
        button.addEventListener("click", () => {
          state.selected = button.dataset.case;
          render();
        });
      });
    }

    function renderRoute(item) {
      const activeIndex = ["T0", "T1", "T2", "T3"].indexOf(item.diagnosis.start_level);
      return `
        <div class="route">
          ${["T0", "T1", "T2", "T3"].map((level, index) => `
            <div class="route-step${index === activeIndex ? " active" : ""}">
              <strong>${level}</strong>
              <span>${index < activeIndex ? "skipped" : index === activeIndex ? "entry" : "available"}</span>
            </div>
          `).join("")}
        </div>
        <ul class="reason-list">
          ${(item.diagnosis.reasons || []).map(reason => `<li>${escapeHtml(reason)}</li>`).join("")}
        </ul>
      `;
    }

    function renderGates(item) {
      const history = item.gate_history || [];
      if (!history.length) {
        return `<div class="empty">No gate history captured.</div>`;
      }
      return `<div class="gate-timeline">
        ${history.map(entry => `
          <div class="attempt">
            <div class="attempt-head">
              <span>${escapeHtml(entry.level)} / ${escapeHtml(entry.patch_id)}</span>
              <span>${entry.failing_gate ? "failed at " + escapeHtml(entry.failing_gate) : "accepted"}</span>
            </div>
            <div class="gates">
              ${(entry.gates || []).map(gate => `
                <div class="gate ${gate.ok ? "ok" : "fail"}">
                  <div class="gate-name">${escapeHtml(gate.gate)}</div>
                  <div class="gate-message">${escapeHtml(gate.message)}</div>
                </div>
              `).join("")}
            </div>
          </div>
        `).join("")}
      </div>`;
    }

    function flattenMetrics(item) {
      const symptom = item.final_symptom_card || {};
      const perf = symptom.perf || {};
      const invariants = symptom.invariants || [];
      const metrics = [];
      Object.entries(perf).forEach(([key, value]) => {
        if (typeof value === "number") {
          metrics.push({ key, value });
        }
      });
      invariants.forEach(entry => {
        metrics.push({ key: entry.name, value: Number(entry.violations || 0) });
      });
      return metrics;
    }

    function renderMetricBars(item) {
      const values = flattenMetrics(item);
      if (!values.length) {
        return `<div class="empty">No runtime metrics captured.</div>`;
      }
      const max = Math.max(1, ...values.map(metric => Math.abs(metric.value)));
      return `<div class="bar-list">
        ${values.map(metric => {
          const width = Math.max(3, Math.min(100, Math.abs(metric.value) / max * 100));
          return `
            <div class="bar-row">
              <div class="bar-label">${escapeHtml(metric.key)}</div>
              <div class="bar-track"><div class="bar-fill" style="width:${width}%"></div></div>
              <div class="bar-value">${escapeHtml(metric.value)}</div>
            </div>
          `;
        }).join("")}
      </div>`;
    }

    function renderFacts(item) {
      const patch = item.accepted_patch || item.best_patch || "-";
      const lastGate = item.last_failing_gate || "-";
      return `
        <div class="kv">
          <div class="kv-row"><div class="kv-key">Status</div><div class="kv-value">${escapeHtml(item.status)}</div></div>
          <div class="kv-row"><div class="kv-key">Patch</div><div class="kv-value">${escapeHtml(patch)}</div></div>
          <div class="kv-row"><div class="kv-key">Last gate</div><div class="kv-value">${escapeHtml(lastGate)}</div></div>
          <div class="kv-row"><div class="kv-key">Approval</div><div class="kv-value">${item.diagnosis.approval_required ? "required" : "not required"}</div></div>
        </div>
      `;
    }

    function renderPrompts(item) {
      const prompts = item.prompts || [];
      if (!prompts.length) {
        return `<div class="empty">No prompt text captured.</div>`;
      }
      return prompts.map((prompt, index) => `
        <details${index === 0 ? " open" : ""}>
          <summary>${escapeHtml(prompt.level)} attempt ${escapeHtml(prompt.attempt)}</summary>
          <pre>${escapeHtml(prompt.text)}</pre>
        </details>
      `).join("");
    }

    function renderDetail() {
      const item = selectedCase();
      if (!item) {
        detail.innerHTML = `<div class="empty">No case selected.</div>`;
        return;
      }

      detail.innerHTML = `
        <div class="detail-header">
          <div class="detail-title">
            <h2>${escapeHtml(item.case_id)}</h2>
            <p>${escapeHtml(item.description)}</p>
          </div>
          <div class="chips">
            <span class="chip ${cssStatus(item.status)}">${escapeHtml(item.status)}</span>
            <span class="chip level-chip">${escapeHtml(item.diagnosis.start_level)}</span>
          </div>
        </div>
        <div class="detail-body">
          <div class="section">
            <h3>D0 Route</h3>
            ${renderRoute(item)}
          </div>

          <div class="section">
            <h3>CI Gates</h3>
            ${renderGates(item)}
          </div>

          <div class="split">
            <div class="section">
              <h3>Run Facts</h3>
              ${renderFacts(item)}
            </div>
            <div class="section">
              <h3>Runtime Evidence</h3>
              ${renderMetricBars(item)}
            </div>
          </div>

          <div class="section">
            <h3>Prompt Snapshots</h3>
            ${renderPrompts(item)}
          </div>

          <div class="section">
            <h3>Final Symptom Card</h3>
            <details>
              <summary>${escapeHtml(item.case_id)} JSON</summary>
              <pre>${escapeHtml(JSON.stringify(item.final_symptom_card || {}, null, 2))}</pre>
            </details>
          </div>
        </div>
      `;
    }

    function render() {
      const items = filteredResults();
      ensureSelection(items);
      renderHeader();
      renderMetrics();
      renderCaseControls(items);
      renderCaseList(items);
      renderDetail();
    }

    statusFilter.querySelectorAll("button").forEach(button => {
      button.addEventListener("click", () => {
        state.status = button.dataset.status;
        statusFilter.querySelectorAll("button").forEach(item => item.classList.toggle("active", item === button));
        render();
      });
    });

    caseSelect.addEventListener("change", () => {
      state.selected = caseSelect.value;
      render();
    });

    render();
  </script>
</body>
</html>
"""


def load_report(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def build_html(report: dict[str, Any]) -> str:
    report_json = json.dumps(report, sort_keys=True)
    report_json = (
        report_json.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    return HTML_TEMPLATE.replace("__REPORT_JSON__", report_json)


def write_dashboard(report_path: Path, out_path: Path) -> None:
    report = load_report(report_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(build_html(report), encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", default="outputs/demo_report.json", help="Path to the JSON run report.")
    parser.add_argument("--out", default="outputs/dashboard.html", help="Path for the generated dashboard.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    write_dashboard(Path(args.report), Path(args.out))
    print(f"Wrote dashboard: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
