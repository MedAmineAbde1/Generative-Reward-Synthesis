/* ============================================================
   GZ Migrator — Frontend JavaScript
   ============================================================ */

"use strict";

// ---- Monaco Editor setup ----
let pasteEditor = null;
let outputEditor = null;
let diffEditor = null;
let originalXml = "";
let migratedXml = "";
let outputFilename = "migrated.sdf";

require.config({ paths: { vs: "https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs" } });

require(["vs/editor/editor.main"], function () {
  // Paste / input editor
  pasteEditor = monaco.editor.create(document.getElementById("paste-editor"), {
    value: "",
    language: "xml",
    theme: "vs-dark",
    fontSize: 13,
    minimap: { enabled: false },
    lineNumbers: "on",
    wordWrap: "on",
    scrollBeyondLastLine: false,
    automaticLayout: true,
    placeholder: "<!-- Paste your Gazebo Classic .world XML here -->",
  });

  // Output editor (read-only)
  outputEditor = monaco.editor.create(document.getElementById("output-editor"), {
    value: "",
    language: "xml",
    theme: "vs-dark",
    fontSize: 13,
    minimap: { enabled: false },
    readOnly: true,
    wordWrap: "on",
    scrollBeyondLastLine: false,
    automaticLayout: true,
  });
});

// ---- Drag & Drop ----
const dropZone = document.getElementById("drop-zone");
const fileInput = document.getElementById("file-input");

dropZone.addEventListener("click", () => fileInput.click());
dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("drag-over");
});
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("drag-over");
  const file = e.dataTransfer.files[0];
  if (file) handleFile(file);
});
fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) handleFile(fileInput.files[0]);
});

function handleFile(file) {
  const reader = new FileReader();
  reader.onload = (e) => {
    const xml = e.target.result;
    if (pasteEditor) pasteEditor.setValue(xml);
    runMigration(xml, file.name);
  };
  reader.readAsText(file);
}

// ---- Paste migration ----
document.getElementById("migrate-paste-btn").addEventListener("click", () => {
  const xml = pasteEditor ? pasteEditor.getValue() : "";
  if (!xml.trim()) {
    showError("Please paste XML content or upload a file first.");
    return;
  }
  runMigration(xml, "pasted_world.world");
});

document.getElementById("clear-paste-btn").addEventListener("click", () => {
  if (pasteEditor) pasteEditor.setValue("");
});

// ---- Core migration call ----
async function runMigration(xml, filename) {
  hideError();
  showLoading(true);
  hideResults();

  try {
    const resp = await fetch("/migrate_text", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ xml }),
    });

    const data = await resp.json();

    if (!resp.ok || data.error) {
      showError(data.error || "Unknown server error");
      showLoading(false);
      return;
    }

    originalXml = xml;
    migratedXml = data.output_sdf;
    outputFilename = filename.replace(/\.(world|sdf|xml)$/i, "_harmonic.sdf");

    renderResults(data.report);
    showLoading(false);
    showResults();

  } catch (err) {
    showError("Network error: " + err.message);
    showLoading(false);
  }
}

// ---- Render results ----
function renderResults(report) {
  // Stats
  document.getElementById("stat-changes").textContent = report.changes.length;
  document.getElementById("stat-warnings").textContent = report.warnings.length;
  document.getElementById("stat-errors").textContent = report.errors.length;

  // Output editor
  if (outputEditor) {
    outputEditor.setValue(migratedXml);
  }

  // Report lists
  renderList("changes-list", report.changes, "changes-count");
  renderList("warnings-list", report.warnings, "warnings-count");
  renderList("errors-list", report.errors, "errors-count");

  if (report.errors.length > 0) {
    document.getElementById("report-errors-section").style.display = "block";
  }

  // Diff editor (lazy init)
  initDiffEditor();
}

function renderList(listId, items, countId) {
  const list = document.getElementById(listId);
  const count = document.getElementById(countId);
  list.innerHTML = "";
  items.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    list.appendChild(li);
  });
  if (count) count.textContent = items.length;
}

function initDiffEditor() {
  if (diffEditor) {
    diffEditor.getModel().original.setValue(originalXml);
    diffEditor.getModel().modified.setValue(migratedXml);
    return;
  }

  require(["vs/editor/editor.main"], function () {
    const originalModel = monaco.editor.createModel(originalXml, "xml");
    const modifiedModel = monaco.editor.createModel(migratedXml, "xml");

    diffEditor = monaco.editor.createDiffEditor(document.getElementById("diff-editor"), {
      theme: "vs-dark",
      fontSize: 12,
      readOnly: true,
      automaticLayout: true,
      renderSideBySide: true,
      minimap: { enabled: false },
      wordWrap: "on",
    });

    diffEditor.setModel({ original: originalModel, modified: modifiedModel });
  });
}

// ---- Tabs ----
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    const target = tab.dataset.tab;
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById("tab-" + target).classList.add("active");

    // Trigger layout update for editors
    if (target === "output" && outputEditor) outputEditor.layout();
    if (target === "diff" && diffEditor) diffEditor.layout();
  });
});

// ---- Copy button ----
document.getElementById("copy-btn").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(migratedXml);
    const btn = document.getElementById("copy-btn");
    const orig = btn.innerHTML;
    btn.innerHTML = "✓ Copied!";
    btn.style.color = "var(--green)";
    setTimeout(() => { btn.innerHTML = orig; btn.style.color = ""; }, 2000);
  } catch {
    // fallback
    const ta = document.createElement("textarea");
    ta.value = migratedXml;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    document.body.removeChild(ta);
  }
});

// ---- Download button ----
document.getElementById("download-btn").addEventListener("click", async () => {
  try {
    const resp = await fetch("/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ xml: migratedXml, filename: outputFilename }),
    });
    if (!resp.ok) { showError("Download failed"); return; }
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = outputFilename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (err) {
    showError("Download error: " + err.message);
  }
});

// ---- Reset button ----
document.getElementById("reset-btn").addEventListener("click", () => {
  hideResults();
  if (pasteEditor) pasteEditor.setValue("");
  if (outputEditor) outputEditor.setValue("");
  originalXml = "";
  migratedXml = "";
  fileInput.value = "";
  document.getElementById("upload-section").scrollIntoView({ behavior: "smooth" });
});

// ---- UI helpers ----
function showLoading(show) {
  document.getElementById("loading").style.display = show ? "block" : "none";
}
function showResults() {
  document.getElementById("results-section").style.display = "block";
  document.getElementById("results-section").scrollIntoView({ behavior: "smooth" });
}
function hideResults() {
  document.getElementById("results-section").style.display = "none";
}
function showError(msg) {
  document.getElementById("error-box").style.display = "block";
  document.getElementById("error-msg").textContent = msg;
}
function hideError() {
  document.getElementById("error-box").style.display = "none";
}
