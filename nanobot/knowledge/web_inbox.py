"""Local web inbox for browser-based knowledge capture."""

from __future__ import annotations

import asyncio
import io
import json
import os
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import quote

from python_multipart import parse_form


def build_capture_icon_markup() -> str:
    """Return the shared Nanobot Capture icon."""
    return """
<svg class="capture-mark" viewBox="0 0 64 64" fill="none" aria-hidden="true">
  <rect x="4" y="4" width="56" height="56" rx="18" fill="#C92F2F"/>
  <path d="M21 16.5h16.5L46 25v22.5A4.5 4.5 0 0 1 41.5 52h-20A4.5 4.5 0 0 1 17 47.5V21a4.5 4.5 0 0 1 4.5-4.5Z" fill="#FFF7F3"/>
  <path d="M37.5 16.5V24a2 2 0 0 0 2 2H46" fill="#FFD9D2"/>
  <path d="M24 31h15" stroke="#C92F2F" stroke-width="3" stroke-linecap="round"/>
  <path d="M24 38h15" stroke="#C92F2F" stroke-width="3" stroke-linecap="round" opacity="0.82"/>
  <path d="M24 45h10" stroke="#C92F2F" stroke-width="3" stroke-linecap="round" opacity="0.66"/>
</svg>
""".strip()


def build_capture_icon_data_uri() -> str:
    """Return the shared icon as an SVG data URI for favicon use."""
    icon_svg = build_capture_icon_markup().replace(' class="capture-mark"', "")
    return f"data:image/svg+xml,{quote(icon_svg)}"


def build_job_status_payload(job) -> dict[str, object]:
    """Build a JSON-safe view of a queued capture job."""
    if job.project_memory_paths:
        primary_path = str(job.project_memory_paths[0])
    elif job.canonical_paths:
        primary_path = str(job.canonical_paths[0])
    elif job.archive_paths:
        primary_path = str(job.archive_paths[0])
    else:
        primary_path = str(job.inbox_item_path)
    return {
        "capture_id": job.capture_id,
        "status": job.status,
        "source_channel": job.source_channel,
        "capture_type": job.capture_type,
        "inbox_item_path": str(job.inbox_item_path),
        "primary_path": primary_path,
        "canonical_paths": [str(path) for path in job.canonical_paths],
        "archive_paths": [str(path) for path in job.archive_paths],
        "project_memory_paths": [str(path) for path in job.project_memory_paths],
        "follow_up": job.follow_up or None,
        "error": job.error or None,
        "queued_at": job.queued_at.isoformat() if job.queued_at else None,
    }


def build_inbox_page() -> str:
    """Build the desktop-aligned browser UI for local capture."""
    icon = build_capture_icon_markup()
    favicon = build_capture_icon_data_uri()
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Nanobot Capture</title>
  <meta name="application-name" content="Nanobot Capture">
  <link rel="icon" href="{favicon}">
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f3ee;
      --panel: rgba(255,255,255,0.76);
      --panel-strong: #ffffff;
      --line: rgba(32, 24, 20, 0.12);
      --ink: #1f1b18;
      --muted: #726861;
      --accent: #c92f2f;
      --accent-dark: #9f2323;
      --accent-soft: rgba(201,47,47,0.1);
      --surface: #f8f5ef;
      --shadow: 0 20px 60px rgba(30, 24, 20, 0.12);
      --radius: 26px;
    }}
    * {{ box-sizing: border-box; }}
    html, body {{ height: 100%; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at top left, rgba(201,47,47,0.16), transparent 28%),
        radial-gradient(circle at bottom right, rgba(201,47,47,0.08), transparent 22%),
        linear-gradient(180deg, #f5efe7 0%, var(--bg) 100%);
      color: var(--ink);
      font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", sans-serif;
      padding: 24px;
    }}
    .capture-shell {{
      width: min(1240px, 100%);
      min-height: calc(100vh - 48px);
      margin: 0 auto;
      display: grid;
      grid-template-rows: auto 1fr auto;
      background: color-mix(in srgb, var(--panel) 86%, white);
      border: 1px solid var(--line);
      border-radius: 28px;
      box-shadow: var(--shadow);
      overflow: hidden;
      backdrop-filter: blur(18px);
    }}
    .capture-header {{
      padding: 28px 30px 24px;
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 16px;
      align-items: start;
      background: linear-gradient(180deg, rgba(255,255,255,0.82), rgba(255,255,255,0.56));
    }}
    .capture-mark {{
      width: 54px;
      height: 54px;
      flex: 0 0 auto;
      display: block;
      filter: drop-shadow(0 10px 18px rgba(201,47,47,0.18));
    }}
    .capture-brand {{
      display: grid;
      gap: 8px;
    }}
    .capture-title {{
      margin: 0;
      font-size: clamp(2rem, 4vw, 3rem);
      line-height: 0.95;
      letter-spacing: -0.04em;
      font-weight: 750;
    }}
    .capture-copy {{
      margin: 0;
      color: var(--muted);
      max-width: 72ch;
      font-size: 1.03rem;
      line-height: 1.55;
    }}
    .capture-composer {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 360px;
      gap: 24px;
      padding: 24px 30px;
      overflow: auto;
    }}
    .capture-column {{
      display: grid;
      gap: 22px;
      align-content: start;
    }}
    .capture-section-title {{
      margin: 0 0 10px;
      font-size: 1.02rem;
      font-weight: 720;
    }}
    .capture-field-label {{
      margin: 0 0 10px;
      font-size: 0.88rem;
      letter-spacing: 0.02em;
      text-transform: uppercase;
      color: var(--muted);
      font-weight: 650;
    }}
    .capture-context,
    .capture-hint,
    .capture-card,
    .attachment-dropzone,
    .attachment-item {{
      border: 1px solid var(--line);
      border-radius: 20px;
      background: color-mix(in srgb, var(--panel-strong) 74%, var(--surface));
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.5);
    }}
    .capture-context {{
      min-height: 240px;
      width: 100%;
      border-radius: 22px;
      padding: 18px 18px 20px;
      resize: vertical;
      color: var(--ink);
      font: inherit;
      line-height: 1.55;
    }}
    .capture-hint {{
      width: 100%;
      padding: 14px 16px;
      color: var(--ink);
      font: inherit;
    }}
    .attachment-dropzone {{
      position: relative;
      min-height: 196px;
      padding: 22px 20px;
      display: grid;
      place-items: center;
      text-align: center;
      border-style: dashed;
      border-width: 2px;
      color: var(--muted);
      background:
        linear-gradient(180deg, rgba(255,255,255,0.82), rgba(248,245,239,0.92));
    }}
    .attachment-dropzone.dragover {{
      border-color: var(--accent);
      background: linear-gradient(180deg, rgba(201,47,47,0.08), rgba(201,47,47,0.04));
    }}
    .attachment-dropzone strong {{
      display: block;
      font-size: 1.45rem;
      color: var(--ink);
      margin-top: 10px;
      margin-bottom: 8px;
    }}
    .attachment-toolbar {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 14px;
    }}
    .capture-button,
    .capture-button-secondary,
    .capture-button-danger {{
      border: 0;
      border-radius: 999px;
      cursor: pointer;
      font: inherit;
      font-weight: 680;
      letter-spacing: 0.01em;
      transition: transform 120ms ease, box-shadow 120ms ease, opacity 120ms ease;
    }}
    .capture-button {{
      background: linear-gradient(135deg, var(--accent), var(--accent-dark));
      color: white;
      padding: 13px 22px;
      box-shadow: 0 14px 26px rgba(201,47,47,0.24);
    }}
    .capture-button-secondary,
    .capture-button-danger {{
      padding: 10px 14px;
      background: rgba(32,24,20,0.07);
      color: var(--ink);
    }}
    .capture-button-danger {{
      background: rgba(201,47,47,0.1);
      color: var(--accent-dark);
    }}
    .capture-button:hover,
    .capture-button-secondary:hover,
    .capture-button-danger:hover {{
      transform: translateY(-1px);
    }}
    .capture-button:disabled,
    .capture-button-secondary:disabled,
    .capture-button-danger:disabled {{
      opacity: 0.55;
      cursor: default;
      transform: none;
      box-shadow: none;
    }}
    .capture-card {{
      padding: 18px;
    }}
    .capture-card p {{
      margin: 0;
      line-height: 1.55;
    }}
    .capture-card pre {{
      margin: 0;
      padding: 0;
      white-space: pre-wrap;
      word-break: break-word;
      font: inherit;
      line-height: 1.55;
    }}
    .capture-card.result-card {{
      display: none;
      gap: 10px;
    }}
    .capture-card.result-card.visible {{
      display: grid;
    }}
    .capture-card.result-card code {{
      display: block;
      margin-top: 10px;
      font-size: 0.9rem;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      line-height: 1.5;
      white-space: pre-wrap;
      word-break: break-word;
    }}
    .status-pill {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      align-self: start;
      border-radius: 999px;
      padding: 7px 12px;
      background: rgba(32,24,20,0.06);
      color: var(--muted);
      font-size: 0.82rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      font-weight: 700;
    }}
    .status-pill.busy::before {{
      content: "";
      width: 10px;
      height: 10px;
      border-radius: 999px;
      border: 2px solid rgba(114,104,97,0.28);
      border-top-color: var(--accent);
      animation: capture-spin 800ms linear infinite;
    }}
    .attachment-list,
    .recent-captures {{
      display: grid;
      gap: 12px;
    }}
    .attachment-item {{
      padding: 14px;
      display: grid;
      gap: 12px;
    }}
    .attachment-thumb {{
      width: 100%;
      aspect-ratio: 16 / 10;
      border-radius: 16px;
      overflow: hidden;
      background: color-mix(in srgb, var(--surface) 80%, white);
      display: grid;
      place-items: center;
      border: 1px solid rgba(32,24,20,0.08);
    }}
    .attachment-thumb img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }}
    .attachment-meta {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: start;
    }}
    .attachment-name {{
      font-weight: 650;
      line-height: 1.35;
      word-break: break-word;
    }}
    .attachment-kind {{
      color: var(--muted);
      font-size: 0.92rem;
    }}
    .recent-capture-card {{
      padding: 14px;
      display: grid;
      gap: 10px;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: color-mix(in srgb, var(--panel-strong) 76%, var(--surface));
    }}
    .recent-header,
    .recent-actions {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      flex-wrap: wrap;
    }}
    .recent-id {{
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 0.82rem;
      color: var(--muted);
    }}
    .recent-badge {{
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 4px 8px;
      background: var(--accent-soft);
      color: var(--accent-dark);
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .recent-path {{
      font-size: 0.96rem;
      line-height: 1.5;
      word-break: break-word;
    }}
    .recent-meta {{
      color: var(--muted);
      font-size: 0.88rem;
    }}
    .capture-footer {{
      border-top: 1px solid var(--line);
      padding: 16px 20px;
      background: rgba(248,245,239,0.96);
      display: flex;
      gap: 14px;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
    }}
    .capture-footer-copy {{
      display: grid;
      gap: 4px;
      min-width: 0;
    }}
    .capture-footer-status {{
      color: var(--muted);
      line-height: 1.4;
      min-height: 1.4em;
    }}
    .visually-hidden {{
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      white-space: nowrap;
      border: 0;
    }}
    @keyframes capture-spin {{
      from {{ transform: rotate(0deg); }}
      to {{ transform: rotate(360deg); }}
    }}
    @media (max-width: 1024px) {{
      .capture-composer {{
        grid-template-columns: 1fr;
      }}
    }}
    @media (max-width: 720px) {{
      body {{ padding: 12px; }}
      .capture-shell {{ min-height: calc(100vh - 24px); }}
      .capture-header,
      .capture-composer {{
        padding-left: 18px;
        padding-right: 18px;
      }}
      .capture-footer {{
        padding-left: 18px;
        padding-right: 18px;
      }}
      .capture-title {{ font-size: 2rem; }}
    }}
  </style>
</head>
<body>
  <main class="capture-shell">
    <header class="capture-header" id="captureHeader">
      {icon}
      <div class="capture-brand">
        <h1 class="capture-title">Nanobot Capture</h1>
        <p class="capture-copy">Drop in a note, a screenshot, a receipt, or a PDF. Nanobot Capture queues the raw material first, then updates your organized memory in Mehr and preserves archive evidence only when it matters.</p>
      </div>
    </header>

    <form action="/capture" method="post" enctype="multipart/form-data" id="captureForm">
    <section class="capture-composer" id="capture-composer">
      <div class="capture-column">
        <section>
          <h2 class="capture-section-title">Context</h2>
          <label class="visually-hidden" for="captureContext">Context</label>
          <textarea
            class="capture-context"
            id="captureContext"
            name="content_text"
            placeholder="Drop in the context, or just paste the raw thing. Example: this is my regular bike service centre and this invoice is for the 10,000 km service."
          ></textarea>
        </section>

        <section>
          <h2 class="capture-section-title">Hint</h2>
          <label class="visually-hidden" for="captureHint">Hint</label>
          <input class="capture-hint" id="captureHint" type="text" name="user_hint" placeholder="bike, house, expense, subscription, nanobot">
        </section>

        <section class="capture-card result-card" id="captureResultCard">
          <div class="status-pill" id="captureResultStatus">Queued</div>
          <div>
            <h2 class="capture-section-title">Result</h2>
            <pre id="captureResultText"></pre>
            <code id="capturePrimaryPath"></code>
          </div>
        </section>

        <section>
          <div class="recent-header">
            <h2 class="capture-section-title">Recent Captures</h2>
            <button class="capture-button-secondary" type="button" id="captureRefreshButton">Refresh</button>
          </div>
          <div class="recent-captures" id="captureRecentList"></div>
        </section>
      </div>

      <aside class="capture-column">
        <section>
          <div class="recent-header">
            <h2 class="capture-section-title">Attachments</h2>
            <span class="recent-meta" id="captureAttachmentCount">0 items</span>
          </div>
          <div class="attachment-dropzone" id="attachment-dropzone">
            <div>
              {icon}
              <strong>Drop more files here</strong>
              <div>Paste screenshots, drag files, or attach receipts and PDFs. Images stay inline as attachment cards.</div>
            </div>
          </div>
          <div class="attachment-toolbar">
            <button class="capture-button-secondary" type="button" id="captureChooseFiles">Choose Files</button>
            <button class="capture-button-secondary" type="button" id="capturePasteClipboard">Paste Clipboard</button>
            <button class="capture-button-danger" type="button" id="captureClearAttachments">Clear</button>
          </div>
          <input class="visually-hidden" id="captureFileInput" type="file" name="file" multiple>
          <div class="attachment-list" id="captureAttachmentList"></div>
        </section>
      </aside>
    </section>

    <footer class="capture-footer" id="capture-footer">
      <div class="capture-footer-copy">
        <div class="status-pill" id="captureStatus">Ready</div>
        <div class="capture-footer-status" id="captureFooterMessage">Paste context, drag files, or capture a clipboard screenshot. Results here show the final memory destination in Mehr.</div>
      </div>
      <button class="capture-button" type="button" id="captureSubmit">Capture to Nanobot</button>
    </footer>
    </form>
  </main>

  <script>
    const captureState = {{
      attachments: [],
      activeCaptureId: null,
      pollHandle: null,
    }};

    const contextField = document.getElementById("captureContext");
    const hintField = document.getElementById("captureHint");
    const fileInput = document.getElementById("captureFileInput");
    const attachmentList = document.getElementById("captureAttachmentList");
    const attachmentCount = document.getElementById("captureAttachmentCount");
    const dropzone = document.getElementById("attachment-dropzone");
    const statusPill = document.getElementById("captureStatus");
    const footerMessage = document.getElementById("captureFooterMessage");
    const submitButton = document.getElementById("captureSubmit");
    const resultCard = document.getElementById("captureResultCard");
    const resultStatus = document.getElementById("captureResultStatus");
    const resultText = document.getElementById("captureResultText");
    const resultPath = document.getElementById("capturePrimaryPath");
    const recentList = document.getElementById("captureRecentList");

    function setStatus(label, message, busy = false) {{
      statusPill.textContent = label;
      statusPill.classList.toggle("busy", busy);
      footerMessage.textContent = message;
      submitButton.disabled = busy;
      submitButton.textContent = busy ? "Capturing..." : "Capture to Nanobot";
    }}

    function escapeHtml(value) {{
      return value
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    }}

    function syncInputFiles() {{
      const transfer = new DataTransfer();
      for (const attachment of captureState.attachments) {{
        if (attachment.file instanceof File) {{
          transfer.items.add(attachment.file);
        }}
      }}
      fileInput.files = transfer.files;
    }}

    function renderAttachments() {{
      attachmentList.innerHTML = "";
      attachmentCount.textContent = `${{captureState.attachments.length}} item${{captureState.attachments.length === 1 ? "" : "s"}}`;
      for (const attachment of captureState.attachments) {{
        const article = document.createElement("article");
        article.className = "attachment-item";
        const preview = attachment.preview
          ? `<div class="attachment-thumb"><img src="${{attachment.preview}}" alt=""></div>`
          : `<div class="attachment-thumb"><div class="recent-meta">${{escapeHtml(attachment.kindLabel)}}</div></div>`;
        article.innerHTML = `
          ${{preview}}
          <div class="attachment-meta">
            <div>
              <div class="attachment-name">${{escapeHtml(attachment.name)}}</div>
              <div class="attachment-kind">${{escapeHtml(attachment.kindLabel)}}</div>
            </div>
            <button class="capture-button-danger" type="button">Remove</button>
          </div>
        `;
        article.querySelector("button").addEventListener("click", () => {{
          captureState.attachments = captureState.attachments.filter((item) => item.id !== attachment.id);
          syncInputFiles();
          renderAttachments();
        }});
        attachmentList.appendChild(article);
      }}
    }}

    function makeAttachment(file) {{
      const imagePreview = file.type.startsWith("image/") ? URL.createObjectURL(file) : "";
      return {{
        id: crypto.randomUUID(),
        file,
        name: file.name || "clipboard-item",
        preview: imagePreview,
        kindLabel: file.type.startsWith("image/") ? "Image attachment" : "File attachment",
      }};
    }}

    function appendFiles(files) {{
      for (const file of files) {{
        captureState.attachments.push(makeAttachment(file));
      }}
      syncInputFiles();
      renderAttachments();
      if (files.length) {{
        setStatus("Ready", `${{files.length}} attachment${{files.length === 1 ? "" : "s"}} added. Capture to Nanobot when ready.`);
      }}
    }}

    function clearAttachments() {{
      for (const attachment of captureState.attachments) {{
        if (attachment.preview) {{
          URL.revokeObjectURL(attachment.preview);
        }}
      }}
      captureState.attachments = [];
      syncInputFiles();
      renderAttachments();
      setStatus("Ready", "Attachments cleared.");
    }}

    async function pasteClipboard() {{
      try {{
        if (navigator.clipboard && navigator.clipboard.read) {{
          const clipboardItems = await navigator.clipboard.read();
          const files = [];
          for (const item of clipboardItems) {{
            for (const type of item.types) {{
              if (type.startsWith("image/")) {{
                const blob = await item.getType(type);
                const extension = type.split("/")[1] || "png";
                files.push(new File([blob], `clipboard-${{crypto.randomUUID()}}.${{extension}}`, {{ type }}));
              }}
            }}
          }}
          if (files.length) {{
            appendFiles(files);
            setStatus("Ready", "Clipboard screenshot added.");
            return;
          }}
        }}
        const text = await navigator.clipboard.readText();
        if (text) {{
          if (contextField.value) {{
            contextField.value += "\\n";
          }}
          contextField.value += text;
          setStatus("Ready", "Clipboard text pasted into context.");
          return;
        }}
        setStatus("Ready", "Clipboard did not contain a supported image or text item.");
      }} catch (error) {{
        setStatus("Ready", "Browser clipboard access failed. Use drag and drop or Choose Files.");
      }}
    }}

    async function submitCapture() {{
      const hasContext = contextField.value.trim().length > 0;
      const hasFiles = captureState.attachments.length > 0;
      if (!hasContext && !hasFiles) {{
        setStatus("Ready", "Add context or at least one attachment before capturing.");
        return;
      }}

      const payload = new FormData();
      payload.set("content_text", contextField.value);
      payload.set("user_hint", hintField.value);
      for (const attachment of captureState.attachments) {{
        payload.append("file", attachment.file, attachment.name);
      }}

      try {{
        setStatus("Queued", "Submitting capture to the queue...", true);
        const response = await fetch("/capture", {{
          method: "POST",
          body: payload,
          headers: {{
            "Accept": "application/json"
          }}
        }});
        const result = await response.json();
        if (!response.ok) {{
          throw new Error(result.error || "capture_failed");
        }}
        captureState.activeCaptureId = result.capture_id;
        resultCard.classList.add("visible");
        resultStatus.textContent = result.status.replaceAll("_", " ");
        resultText.textContent = `Capture queued successfully.\\nSource: web-inbox\\nActions: ${{(result.actions || []).join(", ") || "queued"}}`;
        resultPath.textContent = result.inbox_item_path || "";
        setStatus("Queued", `Capture ${{result.capture_id}} queued. Waiting for processing...`, true);
        await refreshRecentCaptures();
        startPolling(result.capture_id);
      }} catch (error) {{
        resultCard.classList.add("visible");
        resultStatus.textContent = "failed";
        resultText.textContent = `Capture failed: ${{error.message}}`;
        resultPath.textContent = "";
        setStatus("Failed", `Capture failed: ${{error.message}}`);
      }}
    }}

    async function fetchCaptureStatus(captureId) {{
      const response = await fetch(`/captures/${{captureId}}`);
      if (!response.ok) {{
        throw new Error("status_unavailable");
      }}
      return response.json();
    }}

    function renderRecentCapture(capture) {{
      const card = document.createElement("article");
      card.className = "recent-capture-card";
      const actions = [];
      if (capture.status === "failed") {{
        actions.push(`<button class="capture-button-secondary" type="button" data-action="retry">Retry</button>`);
      }}
      if (["completed", "needs_input", "failed", "retracted"].includes(capture.status)) {{
        actions.push(`<button class="capture-button-danger" type="button" data-action="retract">Retract</button>`);
      }}
      const projectBadge = (capture.project_memory_paths || []).length
        ? `<span class="recent-badge">Project Memory</span>`
        : "";
      card.innerHTML = `
        <div class="recent-header">
          <div class="recent-id">${{escapeHtml(capture.capture_id)}}</div>
          <div class="status-pill">${{escapeHtml(capture.status.replaceAll("_", " "))}}</div>
        </div>
        ${{projectBadge}}
        <div class="recent-path">${{escapeHtml(capture.primary_path || capture.inbox_item_path || "")}}</div>
        <div class="recent-meta">Source: ${{escapeHtml(capture.source_channel || "web-inbox")}}</div>
        <div class="recent-actions">${{actions.join("")}}</div>
      `;
      for (const button of card.querySelectorAll("button")) {{
        button.addEventListener("click", async () => {{
          const endpoint = button.dataset.action === "retry"
            ? `/captures/${{capture.capture_id}}/retry`
            : `/captures/${{capture.capture_id}}/retract`;
          const response = await fetch(endpoint, {{ method: "POST" }});
          if (response.ok) {{
            await refreshRecentCaptures();
            if (capture.capture_id === captureState.activeCaptureId) {{
              await updateResultFromCapture(capture.capture_id);
            }}
          }}
        }});
      }}
      return card;
    }}

    async function refreshRecentCaptures() {{
      try {{
        const response = await fetch("/captures/recent");
        if (!response.ok) {{
          throw new Error("recent_unavailable");
        }}
        const payload = await response.json();
        recentList.innerHTML = "";
        const captures = payload.captures || [];
        if (!captures.length) {{
          recentList.innerHTML = `<div class="capture-card"><p>No recent captures yet.</p></div>`;
          return;
        }}
        for (const capture of captures) {{
          recentList.appendChild(renderRecentCapture(capture));
        }}
      }} catch (_error) {{
        recentList.innerHTML = `<div class="capture-card"><p>Recent captures are temporarily unavailable.</p></div>`;
      }}
    }}

    async function updateResultFromCapture(captureId) {{
      const capture = await fetchCaptureStatus(captureId);
      resultCard.classList.add("visible");
      resultStatus.textContent = capture.status.replaceAll("_", " ");
      const lines = [];
      if (capture.status === "completed") {{
        lines.push("Captured successfully.");
      }} else if (capture.status === "processing") {{
        lines.push("Capture is processing.");
      }} else if (capture.status === "queued") {{
        lines.push("Capture is queued.");
      }} else if (capture.status === "needs_input") {{
        lines.push("Capture needs follow-up input.");
      }} else if (capture.status === "failed") {{
        lines.push(`Capture failed: ${{capture.error || "unknown error"}}`);
      }} else if (capture.status === "retracted") {{
        lines.push("Capture was retracted.");
      }}
      if (capture.follow_up) {{
        lines.push(`Follow-up: ${{capture.follow_up}}`);
      }}
      if ((capture.project_memory_paths || []).length) {{
        lines.push(`Project Memory: ${{capture.project_memory_paths[0]}}`);
      }}
      resultText.textContent = lines.join("\\n");
      resultPath.textContent = capture.primary_path || "";
      if (["queued", "processing"].includes(capture.status)) {{
        setStatus(capture.status.replaceAll("_", " "), "Capture is moving through the queue...", true);
      }} else if (capture.status === "completed") {{
        setStatus("Completed", "Capture saved into organized memory.");
      }} else if (capture.status === "needs_input") {{
        setStatus("Needs Input", capture.follow_up || "Capture requires a follow-up answer.");
      }} else if (capture.status === "failed") {{
        setStatus("Failed", capture.error || "Capture failed.");
      }} else if (capture.status === "retracted") {{
        setStatus("Retracted", "Capture was retracted from active memory.");
      }}
      return capture;
    }}

    function stopPolling() {{
      if (captureState.pollHandle) {{
        clearInterval(captureState.pollHandle);
        captureState.pollHandle = null;
      }}
    }}

    function startPolling(captureId) {{
      stopPolling();
      captureState.pollHandle = window.setInterval(async () => {{
        try {{
          const capture = await updateResultFromCapture(captureId);
          await refreshRecentCaptures();
          if (!["queued", "processing"].includes(capture.status)) {{
            stopPolling();
          }}
        }} catch (_error) {{
          stopPolling();
          setStatus("Failed", "Status polling failed.");
        }}
      }}, 1500);
    }}

    document.getElementById("captureChooseFiles").addEventListener("click", () => fileInput.click());
    document.getElementById("capturePasteClipboard").addEventListener("click", pasteClipboard);
    document.getElementById("captureClearAttachments").addEventListener("click", clearAttachments);
    document.getElementById("captureSubmit").addEventListener("click", submitCapture);
    document.getElementById("captureRefreshButton").addEventListener("click", refreshRecentCaptures);

    fileInput.addEventListener("change", () => {{
      appendFiles(Array.from(fileInput.files || []));
    }});

    dropzone.addEventListener("dragover", (event) => {{
      event.preventDefault();
      dropzone.classList.add("dragover");
    }});
    dropzone.addEventListener("dragleave", () => {{
      dropzone.classList.remove("dragover");
    }});
    dropzone.addEventListener("drop", (event) => {{
      event.preventDefault();
      dropzone.classList.remove("dragover");
      const files = Array.from(event.dataTransfer?.files || []);
      appendFiles(files);
    }});

    document.addEventListener("paste", async (event) => {{
      const files = [];
      for (const item of Array.from(event.clipboardData?.items || [])) {{
        if (item.kind === "file") {{
          const file = item.getAsFile();
          if (file) {{
            files.push(file);
          }}
        }}
      }}
      if (files.length) {{
        event.preventDefault();
        appendFiles(files);
        setStatus("Ready", "Clipboard screenshot added.");
      }}
    }});

    refreshRecentCaptures();
  </script>
</body>
</html>"""


def build_result_page(
    *,
    entities: list[str],
    actions: list[str],
    follow_up: str | None,
) -> str:
    """Build a human-facing result page for non-JS clients."""
    entity_html = "".join(f"<li>{entity}</li>" for entity in entities) or "<li>unclassified</li>"
    action_html = "".join(f"<li>{action}</li>" for action in actions) or "<li>saved</li>"
    follow_up_html = (
        f'<section class="panel accent"><h2>Follow-up</h2><p>{follow_up}</p></section>'
        if follow_up
        else ""
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Nanobot Capture</title>
  <style>
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      padding: 24px;
      background: linear-gradient(180deg, #f5efe7, #f6f3ee);
      color: #1f1b18;
      font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", sans-serif;
    }}
    .shell {{
      width: min(720px, 100%);
      background: white;
      border: 1px solid rgba(32,24,20,0.12);
      border-radius: 24px;
      padding: 28px;
      box-shadow: 0 20px 60px rgba(30,24,20,0.12);
    }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    .panel {{
      border: 1px solid rgba(32,24,20,0.12);
      border-radius: 18px;
      padding: 16px 18px;
      background: rgba(255,255,255,0.86);
    }}
    .accent {{ border-color: rgba(201,47,47,0.28); background: rgba(201,47,47,0.07); }}
    h1 {{ margin: 0 0 16px; font-size: 2.2rem; }}
    h2 {{ margin: 0 0 10px; font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.08em; color: #726861; }}
    ul {{ margin: 0; padding-left: 18px; }}
    a {{
      display: inline-block;
      margin-top: 18px;
      color: white;
      background: #c92f2f;
      padding: 12px 18px;
      border-radius: 999px;
      text-decoration: none;
    }}
  </style>
</head>
<body>
  <main class="shell">
    <h1>Nanobot Capture</h1>
    <div class="grid">
      <section class="panel">
        <h2>Entities</h2>
        <ul>{entity_html}</ul>
      </section>
      <section class="panel">
        <h2>Actions</h2>
        <ul>{action_html}</ul>
      </section>
    </div>
    {follow_up_html}
    <a href="/">Capture another item</a>
  </main>
</body>
</html>"""


def build_capture_response(
    *,
    capture_id: str,
    status: str,
    inbox_item_path: Path,
    entities: list[str],
    actions: list[str],
    project_memory_paths: list[Path],
    follow_up: str | None,
) -> str:
    """Build the JSON response payload for a capture request."""
    return json.dumps(
        {
            "capture_id": capture_id,
            "status": status,
            "inbox_item_path": str(inbox_item_path),
            "entities": entities,
            "actions": actions,
            "project_memory_paths": [str(path) for path in project_memory_paths],
            "follow_up": follow_up,
        }
    )


class LocalWebInboxServer:
    """A small local inbox server for browser and JSON capture."""

    def __init__(
        self,
        *,
        bind: str,
        port: int,
        intake_service: Any,
        auth_token: str = "",
    ) -> None:
        self.bind = bind
        self.port = port
        self.intake_service = intake_service
        self.auth_token = auth_token
        self._server = ThreadingHTTPServer((bind, port), self._make_handler())
        self._thread: threading.Thread | None = None

    def _make_handler(self):
        intake_service = self.intake_service
        auth_token = self.auth_token

        class Handler(BaseHTTPRequestHandler):
            def _send(self, status: int, body: str, content_type: str = "application/json") -> None:
                data = body.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _require_auth(self) -> bool:
                if not auth_token:
                    return True
                provided = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
                if provided != auth_token:
                    self._send(401, json.dumps({"error": "unauthorized"}))
                    return False
                return True

            def do_GET(self) -> None:  # noqa: N802
                if self.path == "/":
                    self._send(200, build_inbox_page(), "text/html; charset=utf-8")
                    return
                if not self._require_auth():
                    return
                if self.path == "/captures/recent":
                    jobs = intake_service.store.list_recent_jobs()
                    self._send(200, json.dumps({"captures": [build_job_status_payload(job) for job in jobs]}))
                    return
                if self.path.startswith("/captures/"):
                    capture_id = self.path.removeprefix("/captures/").strip("/")
                    try:
                        job = intake_service.store.load_job(capture_id)
                    except FileNotFoundError:
                        self._send(404, json.dumps({"error": "not_found"}))
                        return
                    self._send(200, json.dumps(build_job_status_payload(job)))
                    return
                self._send(404, "not found", "text/plain; charset=utf-8")

            def do_POST(self) -> None:  # noqa: N802
                if self.path == "/capture":
                    if not self._require_auth():
                        return
                    try:
                        length = int(self.headers.get("Content-Length", "0"))
                        content_type = self.headers.get("Content-Type", "")
                        body = self.rfile.read(length)
                        accept = self.headers.get("Accept", "")
                        if "multipart/form-data" in content_type:
                            results = self._handle_multipart_capture(body, content_type)
                            if "application/json" in accept:
                                primary = results[0]
                                self._send(
                                    202,
                                    build_capture_response(
                                        capture_id=primary.capture_id,
                                        status=primary.status,
                                        inbox_item_path=primary.inbox_item_path,
                                        entities=sorted({entity for result in results for entity in result.entities}),
                                        actions=[action for result in results for action in result.actions],
                                        project_memory_paths=[
                                            path for result in results for path in result.project_memory_paths
                                        ],
                                        follow_up=next(
                                            (
                                                result.follow_up.question
                                                for result in results
                                                if result.follow_up is not None
                                            ),
                                            None,
                                        ),
                                    ),
                                )
                                return
                            entities = sorted({entity for result in results for entity in result.entities})
                            actions = [action for result in results for action in result.actions]
                            follow_up = next(
                                (result.follow_up.question for result in results if result.follow_up is not None),
                                None,
                            )
                            self._send(
                                200,
                                build_result_page(
                                    entities=entities,
                                    actions=actions,
                                    follow_up=follow_up,
                                ),
                                "text/html; charset=utf-8",
                            )
                            return
                        result = self._handle_json_capture(body)
                        self._send(
                            202,
                            build_capture_response(
                                capture_id=result.capture_id,
                                status=result.status,
                                inbox_item_path=result.inbox_item_path,
                                entities=result.entities,
                                actions=result.actions,
                                project_memory_paths=result.project_memory_paths,
                                follow_up=result.follow_up.question if result.follow_up else None,
                            ),
                        )
                    except Exception as exc:  # pragma: no cover - defensive server path
                        self._send(500, json.dumps({"error": str(exc)}))
                    return
                if not self._require_auth():
                    return
                if self.path.endswith("/retract") and self.path.startswith("/captures/"):
                    capture_id = self.path.removeprefix("/captures/").removesuffix("/retract")
                    try:
                        intake_service.retract_capture(capture_id)
                        job = intake_service.store.load_job(capture_id)
                    except FileNotFoundError:
                        self._send(404, json.dumps({"error": "not_found"}))
                        return
                    self._send(200, json.dumps(build_job_status_payload(job)))
                    return
                if self.path.endswith("/retry") and self.path.startswith("/captures/"):
                    capture_id = self.path.removeprefix("/captures/").removesuffix("/retry")
                    try:
                        intake_service.store.retry_job(capture_id)
                        job = intake_service.store.load_job(capture_id)
                    except FileNotFoundError:
                        self._send(404, json.dumps({"error": "not_found"}))
                        return
                    self._send(200, json.dumps(build_job_status_payload(job)))
                    return
                self._send(404, json.dumps({"error": "not_found"}))

            def _handle_json_capture(self, body: bytes):
                payload = json.loads(body or b"{}")
                content_text = str(payload.get("content_text", "")).strip()
                user_hint = str(payload.get("user_hint", "")).strip()
                if not content_text:
                    raise ValueError("content_text_required")
                return asyncio.run(
                    intake_service.capture_text(
                        content_text,
                        user_hint=user_hint,
                        source="web-inbox",
                    )
                )

            def _handle_multipart_capture(self, body: bytes, content_type: str):
                fields: dict[str, str] = {}
                uploaded: list[tuple[str, str]] = []

                def on_field(field) -> None:
                    name = field.field_name.decode() if isinstance(field.field_name, bytes) else str(field.field_name)
                    value = field.value.decode() if isinstance(field.value, bytes) else str(field.value)
                    fields[name] = value

                def on_file(file) -> None:
                    filename = file.file_name.decode() if isinstance(file.file_name, bytes) else str(file.file_name)
                    suffix = Path(filename).suffix
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
                        file.file_object.seek(0)
                        handle.write(file.file_object.read())
                        uploaded.append((handle.name, filename))

                parse_form(
                    {
                        "Content-Type": content_type.encode(),
                        "Content-Length": str(len(body)).encode(),
                    },
                    io.BytesIO(body),
                    on_field,
                    on_file,
                )
                content_text = fields.get("content_text", "").strip()
                user_hint = fields.get("user_hint", "").strip()
                if uploaded:
                    results = []
                    try:
                        for temp_path, _filename in uploaded:
                            path = Path(temp_path)
                            results.append(
                                asyncio.run(
                                    intake_service.capture_file(
                                        path,
                                        user_hint=user_hint,
                                        source="web-inbox",
                                        content_text=content_text,
                                    )
                                )
                            )
                        return results
                    finally:
                        for temp_path, _filename in uploaded:
                            path = Path(temp_path)
                            if path.exists():
                                os.unlink(path)
                if not content_text:
                    raise ValueError("content_text_required")
                return [
                    asyncio.run(
                        intake_service.capture_text(
                            content_text,
                            user_hint=user_hint,
                            source="web-inbox",
                        )
                    )
                ]

            def log_message(self, format: str, *args) -> None:  # noqa: A003
                return

        return Handler

    def start(self) -> None:
        """Start the inbox server on a background thread."""
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the inbox server and wait briefly for shutdown."""
        self._server.shutdown()
        self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=1)
            self._thread = None
