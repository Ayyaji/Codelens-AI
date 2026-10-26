import { useEffect, useMemo, useState } from "react";
import {
  approveKb,
  approveKbUpload,
  bulkReviewKb,
  createKb,
  deleteKb,
  discardKbUpload,
  listKbUploads,
  rejectKb,
  searchKb,
  updateKb,
  uploadKbFile,
} from "../api/client";
import { MarkdownView } from "../components/MarkdownView";
import { ConfirmDialog, ErrorBanner, LoadingLine, PageHeader, btn, btnDanger, btnGhost, field } from "../components/ui";
import { formatWhen } from "../lib/format";
import { KB_DIFFICULTIES, KB_SOURCES, KB_TYPES, labelFor } from "../lib/kbModel";

const PAGE_SIZE = 8;
const ACCEPT = ".pdf,.docx,.txt,.md,.markdown,application/pdf,text/plain,text/markdown";
const TABS = [
  { id: "pending", label: "Pending" },
  { id: "approved", label: "Approved" },
  { id: "rejected", label: "Rejected" },
];

const emptyDraft = {
  title: "",
  content: "",
  topic: "",
  tags: "",
  difficulty: "medium",
  source: "teacher",
  type: "concept",
  approve: true,
};

function draftFrom(item) {
  return {
    title: item.title || "",
    content: item.content || "",
    topic: item.topic || "",
    tags: (item.tags || []).join(", "),
    difficulty: item.difficulty || "",
    source: item.source || "teacher",
    type: item.type || "concept",
    approve: false,
  };
}

function payloadFrom(draft) {
  return {
    title: draft.title.trim(),
    content: draft.content.trim(),
    topic: draft.topic.trim(),
    tags: draft.tags.split(",").map((tag) => tag.trim()).filter(Boolean),
    difficulty: draft.difficulty || null,
    source: draft.source,
    type: draft.type,
    approve: Boolean(draft.approve),
  };
}

function statusClass(status) {
  if (status === "approved") return "border-ok/40 text-ok";
  if (status === "rejected") return "border-break/40 text-break";
  return "border-full/40 text-full";
}

export function KbPage() {
  const [status, setStatus] = useState("pending");
  const [qInput, setQInput] = useState("");
  const [q, setQ] = useState("");
  const [topic, setTopic] = useState("");
  const [tag, setTag] = useState("");
  const [type, setType] = useState("");
  const [source, setSource] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [page, setPage] = useState(1);
  const [result, setResult] = useState(null);
  const [selectedId, setSelectedId] = useState("");
  const [checked, setChecked] = useState([]);
  const [mode, setMode] = useState("view");
  const [draft, setDraft] = useState(emptyDraft);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [rejectFor, setRejectFor] = useState(null);
  const [rejectReason, setRejectReason] = useState("");
  const [deleteId, setDeleteId] = useState("");
  const [confirmApprove, setConfirmApprove] = useState(false);
  const [uploads, setUploads] = useState([]);
  const [uploadEpoch, setUploadEpoch] = useState(0);
  const [dragOver, setDragOver] = useState(false);
  const [chunkPicks, setChunkPicks] = useState({});
  const [uploadTopics, setUploadTopics] = useState({});

  useEffect(() => {
    const timer = setTimeout(() => {
      setQ(qInput.trim());
      setPage(1);
    }, 250);
    return () => clearTimeout(timer);
  }, [qInput]);

  useEffect(() => {
    let cancel = false;
    setLoading(true);
    searchKb({ q, status, topic, tag, type, source, from, to, page, page_size: PAGE_SIZE })
      .then((data) => {
        if (cancel) return;
        setResult(data);
        if (data.page !== page) setPage(data.page);
        setSelectedId((current) => {
          if (mode !== "view") return current;
          if (data.items.some((item) => item.id === current)) return current;
          return data.items[0]?.id || "";
        });
      })
      .catch((err) => {
        if (!cancel) setError(err.message || "Could not load the knowledge base.");
      })
      .finally(() => {
        if (!cancel) setLoading(false);
      });
    return () => {
      cancel = true;
    };
  }, [q, status, topic, tag, type, source, from, to, page, mode]);

  useEffect(() => {
    let cancel = false;
    let timer = 0;
    async function tick() {
      try {
        const rows = await listKbUploads();
        if (cancel) return;
        setUploads((current) => {
          const local = current.filter((row) => String(row.id).startsWith("local_"));
          return [...rows, ...local];
        });
        if (rows.some((row) => row.status === "processing")) timer = setTimeout(tick, 400);
      } catch (err) {
        if (!cancel) setError(err.message || "Could not load uploads.");
      }
    }
    tick();
    return () => {
      cancel = true;
      clearTimeout(timer);
    };
  }, [uploadEpoch]);

  useEffect(() => {
    if (!uploads.some((row) => row.status === "processing")) return undefined;
    const timer = setInterval(() => {
      setUploads((current) =>
        current.map((row) =>
          row.status === "processing" ? { ...row, progress: Math.min(90, (row.progress || 30) + 8) } : row,
        ),
      );
    }, 200);
    return () => clearInterval(timer);
  }, [uploads]);

  const items = result?.items || [];
  const selected = items.find((item) => item.id === selectedId) || null;
  const counts = result?.counts || { pending: 0, approved: 0, rejected: 0 };
  const facets = result?.facets || { topics: [], tags: [], types: [], sources: [] };
  const pages = Math.max(1, Math.ceil((result?.total || 0) / PAGE_SIZE));
  const preview = mode === "view" ? selected?.content || "" : draft.content;

  const filterSummary = useMemo(() => {
    const parts = [];
    if (q) parts.push(`“${q}”`);
    if (topic) parts.push(topic);
    if (tag) parts.push(`#${tag}`);
    if (type) parts.push(labelFor(KB_TYPES, type));
    if (source) parts.push(labelFor(KB_SOURCES, source));
    if (from || to) parts.push(`${from || "…"} – ${to || "…"}`);
    return parts.join(" · ");
  }, [q, topic, tag, type, source, from, to]);

  function resetFilters() {
    setQInput("");
    setQ("");
    setTopic("");
    setTag("");
    setType("");
    setSource("");
    setFrom("");
    setTo("");
    setPage(1);
  }

  function chooseTab(next) {
    setStatus(next);
    setPage(1);
    setChecked([]);
    setMode("view");
  }

  async function reload(nextPage = page) {
    const data = await searchKb({ q, status, topic, tag, type, source, from, to, page: nextPage, page_size: PAGE_SIZE });
    setResult(data);
    return data;
  }

  function openCreate() {
    setMode("create");
    setDraft(emptyDraft);
    setSelectedId("");
    setError("");
  }

  function openEdit(item) {
    setMode("edit");
    setDraft(draftFrom(item));
    setSelectedId(item.id);
    setError("");
  }

  async function onSave(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const body = payloadFrom(draft);
      if (mode === "create") {
        const created = await createKb(body);
        setNote(created.status === "approved" ? "Saved and approved." : "Saved to the pending queue.");
        setMode("view");
        setStatus(created.status);
        setPage(1);
        setSelectedId(created.id);
      } else if (selected) {
        const updated = await updateKb(selected.id, body);
        setNote("Edits saved.");
        setMode("view");
        setSelectedId(updated.id);
        await reload();
      }
    } catch (err) {
      setError(err.message || "Could not save that note.");
    } finally {
      setBusy(false);
    }
  }

  async function onApprove(item) {
    setBusy(true);
    setError("");
    try {
      if (mode === "edit" && draft.content.trim() && draft.content.trim() !== item.content) {
        await updateKb(item.id, payloadFrom(draft));
      }
      await approveKb(item.id);
      setNote("Approved.");
      setMode("view");
      setChecked((current) => current.filter((id) => id !== item.id));
      const data = await reload();
      setSelectedId(data.items[0]?.id || "");
    } catch (err) {
      setError(err.message || "Could not approve that note.");
    } finally {
      setBusy(false);
    }
  }

  async function submitReject() {
    const reason = rejectReason.trim();
    if (!reason) {
      setError("A reject reason is required.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      if (rejectFor === "bulk") {
        const response = await bulkReviewKb({ ids: checked, action: "reject", reason });
        setNote(`Rejected ${response.updated.length}.`);
        if (response.failed.length) setError(`${response.failed.length} could not be rejected.`);
        setChecked([]);
      } else {
        await rejectKb(rejectFor, reason);
        setNote("Rejected.");
        setChecked((current) => current.filter((id) => id !== rejectFor));
      }
      setRejectFor(null);
      setRejectReason("");
      setMode("view");
      const data = await reload();
      setSelectedId(data.items[0]?.id || "");
    } catch (err) {
      setError(err.message || "Could not reject.");
    } finally {
      setBusy(false);
    }
  }

  async function onBulkApprove() {
    setBusy(true);
    setError("");
    try {
      const response = await bulkReviewKb({ ids: checked, action: "approve" });
      setNote(`Approved ${response.updated.length}.`);
      if (response.failed.length) setError(`${response.failed.length} could not be approved.`);
      setChecked([]);
      setConfirmApprove(false);
      const data = await reload();
      setSelectedId(data.items[0]?.id || "");
    } catch (err) {
      setError(err.message || "Could not approve the selection.");
    } finally {
      setBusy(false);
    }
  }

  async function onDelete() {
    setBusy(true);
    setError("");
    try {
      await deleteKb(deleteId);
      setNote("Deleted.");
      setDeleteId("");
      setMode("view");
      const data = await reload();
      setSelectedId(data.items[0]?.id || "");
    } catch (err) {
      setError(err.message || "Could not delete that note.");
    } finally {
      setBusy(false);
    }
  }

  async function takeFiles(fileList) {
    const files = [...fileList];
    setError("");
    for (const file of files) {
      const lower = file.name.toLowerCase();
      const allowed = [".pdf", ".docx", ".txt", ".md", ".markdown"].some((ext) => lower.endsWith(ext));
      if (!allowed || file.size > 5_000_000) {
        setUploads((current) => [
          {
            id: `local_${file.name}_${file.size}_${Date.now()}`,
            filename: file.name,
            size: file.size,
            status: "failed",
            progress: 100,
            error: !allowed ? "Upload a PDF, DOCX, TXT, or MD file." : "That file is larger than 5 MB.",
            chunks: [],
          },
          ...current,
        ]);
        continue;
      }
      try {
        const created = await uploadKbFile(file, (progress) => {
          setUploads((current) => current.map((row) => (row.filename === file.name && row.status === "processing" ? { ...row, progress } : row)));
        });
        setUploads((current) => [created, ...current.filter((row) => row.id !== created.id)]);
        setUploadEpoch((value) => value + 1);
      } catch (err) {
        setUploads((current) => [
          {
            id: `local_${file.name}_${Date.now()}`,
            filename: file.name,
            size: file.size,
            status: "failed",
            progress: 100,
            error: err.message || "Upload failed.",
            chunks: [],
          },
          ...current,
        ]);
      }
    }
  }

  async function onApproveUpload(upload) {
    const picks = chunkPicks[upload.id] || upload.chunks.map((chunk) => chunk.index);
    setBusy(true);
    setError("");
    try {
      await approveKbUpload(upload.id, {
        chunk_indexes: picks,
        topic: (uploadTopics[upload.id] || "Upload").trim() || "Upload",
        tags: ["upload"],
      });
      setNote("Chunks added to the approved library.");
      setUploadEpoch((value) => value + 1);
      if (status === "approved") await reload();
    } catch (err) {
      setError(err.message || "Could not approve those chunks.");
    } finally {
      setBusy(false);
    }
  }

  async function onDiscardUpload(upload) {
    setBusy(true);
    setError("");
    try {
      if (String(upload.id).startsWith("local_")) {
        setUploads((current) => current.filter((row) => row.id !== upload.id));
      } else {
        await discardKbUpload(upload.id);
        setUploadEpoch((value) => value + 1);
      }
    } catch (err) {
      setError(err.message || "Could not discard that upload.");
    } finally {
      setBusy(false);
    }
  }

  function toggleChunk(upload, index) {
    setChunkPicks((current) => {
      const existing = current[upload.id] || upload.chunks.map((chunk) => chunk.index);
      const next = existing.includes(index) ? existing.filter((value) => value !== index) : [...existing, index];
      return { ...current, [upload.id]: next };
    });
  }

  return (
    <div>
      <PageHeader
        kicker="Knowledge"
        title="Library and review"
        lede="Teacher notes can go straight into the library. Student and AI proposals stay pending until you approve them. Uploads stay as chunks until you accept them."
        actions={
          <button type="button" className={btn} onClick={openCreate}>
            New note
          </button>
        }
      />
      <ErrorBanner message={error} />
      {note ? (
        <p className="mb-4 text-sm text-ok" role="status">
          {note}
        </p>
      ) : null}

      <div className="mb-4 flex flex-wrap gap-2" role="tablist" aria-label="Review status">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={status === tab.id}
            className={`rounded-lg border px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.14em] ${
              status === tab.id ? "border-hint bg-hint/10 text-paper" : "border-line text-faint hover:text-paper"
            }`}
            onClick={() => chooseTab(tab.id)}
          >
            {tab.label} {counts[tab.id] ?? 0}
          </button>
        ))}
      </div>

      <div className="mb-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-6">
        <label className="text-xs text-mute lg:col-span-2">
          Search
          <input className={`${field} mt-1`} value={qInput} onChange={(event) => setQInput(event.target.value)} placeholder="Title, topic, or text" />
        </label>
        <label className="text-xs text-mute">
          Topic
          <select className={`${field} mt-1`} value={topic} onChange={(event) => { setTopic(event.target.value); setPage(1); }}>
            <option value="">All topics</option>
            {facets.topics.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </label>
        <label className="text-xs text-mute">
          Type
          <select className={`${field} mt-1`} value={type} onChange={(event) => { setType(event.target.value); setPage(1); }}>
            <option value="">All types</option>
            {KB_TYPES.map((item) => (
              <option key={item.value} value={item.value}>{item.label}</option>
            ))}
          </select>
        </label>
        <label className="text-xs text-mute">
          Source
          <select className={`${field} mt-1`} value={source} onChange={(event) => { setSource(event.target.value); setPage(1); }}>
            <option value="">All sources</option>
            {KB_SOURCES.map((item) => (
              <option key={item.value} value={item.value}>{item.label}</option>
            ))}
          </select>
        </label>
        <div className="grid grid-cols-2 gap-2">
          <label className="text-xs text-mute">
            From
            <input type="date" className={`${field} mt-1`} value={from} onChange={(event) => { setFrom(event.target.value); setPage(1); }} />
          </label>
          <label className="text-xs text-mute">
            To
            <input type="date" className={`${field} mt-1`} value={to} onChange={(event) => { setTo(event.target.value); setPage(1); }} />
          </label>
        </div>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        {facets.tags.map((item) => (
          <button
            key={item}
            type="button"
            className={`rounded-full border px-2.5 py-1 font-mono text-[11px] ${
              tag === item ? "border-hint bg-hint/15 text-paper" : "border-line text-faint hover:text-paper"
            }`}
            onClick={() => {
              setTag((current) => (current === item ? "" : item));
              setPage(1);
            }}
          >
            {item}
          </button>
        ))}
        {filterSummary ? (
          <button type="button" className="text-xs text-mute underline decoration-line underline-offset-2" onClick={resetFilters}>
            Clear filters
          </button>
        ) : null}
      </div>

      <section className="mb-6 rounded-xl border border-line bg-panel p-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="font-mono text-[11px] uppercase tracking-[0.16em] text-faint">Upload into the library</h2>
          <p className="text-xs text-faint">PDF, DOCX, TXT, or MD. 5 MB max.</p>
        </div>
        <label
          className={`mt-3 block cursor-pointer rounded-lg border border-dashed px-4 py-6 text-center text-sm ${
            dragOver ? "border-hint bg-hint/10 text-paper" : "border-line text-mute"
          }`}
          onDragOver={(event) => {
            event.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragOver(false);
            takeFiles(event.dataTransfer.files);
          }}
        >
          Drop files here, or browse
          <input
            className="sr-only"
            type="file"
            accept={ACCEPT}
            multiple
            onChange={(event) => {
              takeFiles(event.target.files);
              event.target.value = "";
            }}
          />
        </label>
        <ul className="mt-3 space-y-3">
          {uploads.map((upload) => {
            const picks = chunkPicks[upload.id] || upload.chunks.map((chunk) => chunk.index);
            return (
              <li key={upload.id} className="rounded-lg border border-line bg-ink px-3 py-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm text-paper">{upload.filename}</p>
                  <p className={`font-mono text-[10px] uppercase tracking-[0.14em] ${upload.status === "failed" ? "text-break" : upload.status === "chunked" ? "text-ok" : "text-hint"}`}>
                    {upload.status}
                  </p>
                </div>
                <div className="mt-2 h-1 overflow-hidden rounded bg-panel">
                  <div className={`h-1 ${upload.status === "failed" ? "bg-break" : "bg-hint"}`} style={{ width: `${upload.progress || (upload.status === "chunked" ? 100 : 20)}%` }} />
                </div>
                {upload.error ? <p className="mt-2 text-xs text-break">{upload.error}</p> : null}
                {upload.kb_item_id ? <p className="mt-2 text-xs text-ok">Added to the library.</p> : null}
                {upload.status === "chunked" && !upload.kb_item_id ? (
                  <div className="mt-3 space-y-2">
                    {upload.chunks.map((chunk) => (
                      <label key={chunk.index} className="block rounded-md border border-line p-2 text-xs text-mute">
                        <span className="flex items-center gap-2 text-paper">
                          <input
                            type="checkbox"
                            checked={picks.includes(chunk.index)}
                            onChange={() => toggleChunk(upload, chunk.index)}
                          />
                          {chunk.title}
                        </span>
                        <span className="mt-1 block max-h-24 overflow-auto whitespace-pre-wrap font-mono text-[11px] text-faint">{chunk.content}</span>
                      </label>
                    ))}
                    <div className="flex flex-wrap items-end gap-2">
                      <label className="text-xs text-mute">
                        Topic
                        <input
                          className={`${field} mt-1`}
                          value={uploadTopics[upload.id] ?? "Upload"}
                          onChange={(event) => setUploadTopics((current) => ({ ...current, [upload.id]: event.target.value }))}
                        />
                      </label>
                      <button type="button" className={btn} disabled={busy || !picks.length} onClick={() => onApproveUpload(upload)}>
                        Approve chunks
                      </button>
                      <button type="button" className={btnGhost} disabled={busy} onClick={() => onDiscardUpload(upload)}>
                        Discard
                      </button>
                    </div>
                  </div>
                ) : null}
                {upload.status === "failed" ? (
                  <button type="button" className={`${btnGhost} mt-2`} disabled={busy} onClick={() => onDiscardUpload(upload)}>
                    Dismiss
                  </button>
                ) : null}
              </li>
            );
          })}
        </ul>
      </section>

      <div className="grid items-start gap-4 lg:grid-cols-5">
        <section className="lg:col-span-2">
          <div className="mb-2 flex items-center justify-between gap-2">
            <p className="text-xs text-faint">
              {loading ? "Loading…" : `${result?.total || 0} in this view`}
              {filterSummary ? ` · ${filterSummary}` : ""}
            </p>
            {status === "pending" && items.length ? (
              <label className="flex items-center gap-2 text-xs text-mute">
                <input
                  type="checkbox"
                  checked={items.length > 0 && items.every((item) => checked.includes(item.id))}
                  onChange={(event) => {
                    const ids = items.map((item) => item.id);
                    setChecked((current) =>
                      event.target.checked ? [...new Set([...current, ...ids])] : current.filter((id) => !ids.includes(id)),
                    );
                  }}
                />
                Page
              </label>
            ) : null}
          </div>
          {loading ? <LoadingLine label="Loading notes…" /> : null}
          {!loading && !items.length ? (
            <p className="rounded-xl border border-dashed border-line px-4 py-10 text-center text-sm text-faint">
              {status === "pending" ? "Nothing is waiting for review." : `No ${status} notes match.`}
            </p>
          ) : null}
          <ul className="space-y-2">
            {items.map((item) => (
              <li key={item.id}>
                <div
                  className={`rounded-xl border px-3 py-3 ${
                    item.id === selectedId && mode !== "create" ? "border-hint bg-hint/5" : "border-line bg-panel"
                  }`}
                >
                  <div className="flex items-start gap-2">
                    {status === "pending" ? (
                      <input
                        type="checkbox"
                        className="mt-1"
                        checked={checked.includes(item.id)}
                        aria-label={`Select ${item.title}`}
                        onChange={() => setChecked((current) => (current.includes(item.id) ? current.filter((id) => id !== item.id) : [...current, item.id]))}
                      />
                    ) : null}
                    <button
                      type="button"
                      className="min-w-0 flex-1 text-left"
                      onClick={() => {
                        setSelectedId(item.id);
                        setMode("view");
                      }}
                    >
                      <span className="block truncate text-sm font-medium text-paper">{item.title}</span>
                      <span className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-faint">
                        <span className={`rounded border px-1.5 py-0.5 font-mono uppercase tracking-[0.12em] ${statusClass(item.status)}`}>{item.status}</span>
                        <span>{item.topic || "No topic"}</span>
                        <span>{formatWhen(item.created_at)}</span>
                      </span>
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
          {status === "pending" && checked.length ? (
            <div className="mt-3 flex flex-wrap gap-2 rounded-xl border border-line bg-panel p-3">
              <p className="w-full text-xs text-mute">{checked.length} selected</p>
              <button type="button" className={btn} disabled={busy} onClick={() => setConfirmApprove(true)}>
                Approve selected
              </button>
              <button
                type="button"
                className={btnDanger}
                disabled={busy}
                onClick={() => {
                  setRejectFor("bulk");
                  setRejectReason("");
                }}
              >
                Reject selected
              </button>
            </div>
          ) : null}
          {pages > 1 ? (
            <div className="mt-3 flex items-center justify-between text-xs text-mute">
              <button type="button" className={btnGhost} disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>
                Previous
              </button>
              <span>
                Page {page} of {pages}
              </span>
              <button type="button" className={btnGhost} disabled={page >= pages} onClick={() => setPage((value) => value + 1)}>
                Next
              </button>
            </div>
          ) : null}
        </section>

        <section className="rounded-xl border border-line bg-panel p-4 lg:col-span-3">
          {mode === "view" && !selected ? (
            <p className="text-sm text-faint">Select a note to preview it.</p>
          ) : null}
          {mode === "view" && selected ? (
            <div className="grid gap-4 xl:grid-cols-2">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`rounded border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.12em] ${statusClass(selected.status)}`}>
                    {selected.status}
                  </span>
                  <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-faint">{labelFor(KB_TYPES, selected.type)}</span>
                  <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-faint">{labelFor(KB_SOURCES, selected.source)}</span>
                  {selected.difficulty ? (
                    <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-faint">{selected.difficulty}</span>
                  ) : null}
                </div>
                <h2 className="mt-2 text-lg font-semibold text-paper">{selected.title}</h2>
                <p className="mt-1 text-sm text-mute">{selected.topic}</p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {selected.tags.map((item) => (
                    <button key={item} type="button" className="rounded-full border border-line px-2 py-0.5 font-mono text-[10px] text-faint" onClick={() => { setTag(item); setPage(1); }}>
                      {item}
                    </button>
                  ))}
                </div>
                <dl className="mt-4 space-y-1 text-xs text-faint">
                  <div>Proposed by {selected.proposer_name || selected.proposed_by || "unknown"}{selected.proposer_role ? ` · ${selected.proposer_role}` : ""}</div>
                  <div>Created {formatWhen(selected.created_at)}</div>
                  {selected.updated_at ? <div>Updated {formatWhen(selected.updated_at)}</div> : null}
                  {selected.reviewed_at ? <div>Reviewed {formatWhen(selected.reviewed_at)}</div> : null}
                </dl>
                {selected.reject_reason ? (
                  <p className="mt-3 rounded-lg border border-break/30 bg-break/10 px-3 py-2 text-sm text-[#f3c1c7]">
                    {selected.reject_reason}
                  </p>
                ) : null}
                <div className="mt-4 flex flex-wrap gap-2">
                  <button type="button" className={btnGhost} disabled={busy} onClick={() => openEdit(selected)}>
                    Edit
                  </button>
                  {selected.status === "pending" ? (
                    <>
                      <button type="button" className={btnDanger} disabled={busy} onClick={() => { setRejectFor(selected.id); setRejectReason(""); }}>
                        Reject
                      </button>
                      <button type="button" className={btn} disabled={busy} onClick={() => onApprove(selected)}>
                        Approve
                      </button>
                    </>
                  ) : null}
                  <button type="button" className={btnDanger} disabled={busy} onClick={() => setDeleteId(selected.id)}>
                    Delete
                  </button>
                </div>
              </div>
              <div className="rounded-lg border border-line bg-ink p-3">
                <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.14em] text-faint">Preview</p>
                <MarkdownView text={selected.content} />
              </div>
            </div>
          ) : null}
          {mode !== "view" ? (
            <form onSubmit={onSave} className="grid gap-4 xl:grid-cols-2">
              <div className="space-y-3">
                <h2 className="text-lg font-semibold text-paper">{mode === "create" ? "New note" : "Edit note"}</h2>
                <label className="block text-xs text-mute">
                  Title
                  <input className={`${field} mt-1`} value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} required />
                </label>
                <label className="block text-xs text-mute">
                  Topic
                  <input className={`${field} mt-1`} value={draft.topic} onChange={(event) => setDraft({ ...draft, topic: event.target.value })} list="kb-topics" required />
                  <datalist id="kb-topics">
                    {facets.topics.map((item) => (
                      <option key={item} value={item} />
                    ))}
                  </datalist>
                </label>
                <label className="block text-xs text-mute">
                  Tags
                  <input className={`${field} mt-1`} value={draft.tags} onChange={(event) => setDraft({ ...draft, tags: event.target.value })} placeholder="arrays, dsa" />
                </label>
                <div className="grid grid-cols-3 gap-2">
                  <label className="text-xs text-mute">
                    Difficulty
                    <select className={`${field} mt-1`} value={draft.difficulty} onChange={(event) => setDraft({ ...draft, difficulty: event.target.value })}>
                      <option value="">Unset</option>
                      {KB_DIFFICULTIES.map((item) => (
                        <option key={item.value} value={item.value}>{item.label}</option>
                      ))}
                    </select>
                  </label>
                  <label className="text-xs text-mute">
                    Source
                    <select className={`${field} mt-1`} value={draft.source} onChange={(event) => setDraft({ ...draft, source: event.target.value })}>
                      {KB_SOURCES.map((item) => (
                        <option key={item.value} value={item.value}>{item.label}</option>
                      ))}
                    </select>
                  </label>
                  <label className="text-xs text-mute">
                    Type
                    <select className={`${field} mt-1`} value={draft.type} onChange={(event) => setDraft({ ...draft, type: event.target.value })}>
                      {KB_TYPES.map((item) => (
                        <option key={item.value} value={item.value}>{item.label}</option>
                      ))}
                    </select>
                  </label>
                </div>
                <label className="block text-xs text-mute">
                  Markdown
                  <textarea className={`${field} mt-1 min-h-40 font-mono text-[13px]`} value={draft.content} onChange={(event) => setDraft({ ...draft, content: event.target.value })} required />
                </label>
                {mode === "create" ? (
                  <label className="flex items-center gap-2 text-sm text-mute">
                    <input type="checkbox" checked={draft.approve} onChange={(event) => setDraft({ ...draft, approve: event.target.checked })} />
                    Approve immediately
                  </label>
                ) : null}
                <div className="flex flex-wrap gap-2">
                  <button type="submit" className={btn} disabled={busy}>
                    {busy ? "Working…" : mode === "create" ? "Create" : "Save edits"}
                  </button>
                  <button type="button" className={btnGhost} disabled={busy} onClick={() => setMode("view")}>
                    Cancel
                  </button>
                </div>
              </div>
              <div className="rounded-lg border border-line bg-ink p-3">
                <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.14em] text-faint">Preview</p>
                <MarkdownView text={preview} />
              </div>
            </form>
          ) : null}
        </section>
      </div>

      {rejectFor ? (
        <div className="fixed inset-0 z-40 grid place-items-center bg-ink/70 px-4" role="presentation" onClick={() => !busy && setRejectFor(null)}>
          <div role="dialog" aria-modal="true" aria-labelledby="reject-title" className="w-full max-w-md rounded-xl border border-line bg-panel p-5" onClick={(event) => event.stopPropagation()}>
            <h2 id="reject-title" className="text-lg font-semibold text-paper">Reject with a reason</h2>
            <p className="mt-2 text-sm text-mute">The reason stays on the note so the next reviewer can see why it was refused.</p>
            <textarea className={`${field} mt-3 min-h-24`} value={rejectReason} onChange={(event) => setRejectReason(event.target.value)} placeholder="What is wrong or missing?" />
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" className={btnGhost} disabled={busy} onClick={() => setRejectFor(null)}>Cancel</button>
              <button type="button" className={btnDanger} disabled={busy || !rejectReason.trim()} onClick={submitReject}>
                {busy ? "Working…" : "Reject"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <ConfirmDialog
        open={confirmApprove}
        title="Approve selected notes?"
        body={`${checked.length} pending note${checked.length === 1 ? "" : "s"} will be marked approved.`}
        confirmLabel="Approve"
        busy={busy}
        onClose={() => setConfirmApprove(false)}
        onConfirm={onBulkApprove}
      />
      <ConfirmDialog
        open={Boolean(deleteId)}
        title="Delete this note?"
        body="This removes it from the library. The action cannot be undone in the demo."
        confirmLabel="Delete"
        danger
        busy={busy}
        onClose={() => setDeleteId("")}
        onConfirm={onDelete}
      />
    </div>
  );
}
