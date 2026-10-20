import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { uploadJd } from "../api/client";
import { ErrorBanner, PageHeader, btn, field } from "../components/ui";
import { useSession } from "../session";

const MAX_BYTES = 2_000_000;
const ACCEPT = ".pdf,.txt,.md,.text,text/plain,application/pdf";

function allowed(file) {
  const name = file.name.toLowerCase();
  return name.endsWith(".pdf") || name.endsWith(".txt") || name.endsWith(".md") || name.endsWith(".text") || file.type === "application/pdf" || file.type.startsWith("text/");
}

export function UploadPage() {
  const { setUpload } = useSession();
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [text, setText] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function takeFile(next) {
    if (!next) return;
    if (!allowed(next)) {
      setError("Choose a PDF or a text file.");
      setFile(null);
      return;
    }
    if (next.size > MAX_BYTES) {
      setError("That file is larger than 2 MB.");
      setFile(null);
      return;
    }
    setError("");
    setFile(next);
  }

  async function onSubmit(event) {
    event.preventDefault();
    if (!file && !text.trim()) {
      setError("Paste a job description or choose a file.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const result = await uploadJd(file ? { file } : { text: text.trim() });
      setUpload({
        jdId: result.jd_id,
        sourceLabel: file ? file.name : "Pasted text",
      });
      navigate("/analysis");
    } catch (err) {
      setError(err.message || "Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit}>
      <PageHeader
        kicker="01  Job description"
        title="Upload the posting"
        lede="Drop a PDF or text file, or paste the posting. A file is sent when both are filled. Analysis starts from the id the API returns."
      />
      <ErrorBanner message={error} />
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="flex flex-col gap-2">
        <label
          className={`flex min-h-64 cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed px-6 text-center transition ${
            dragOver ? "border-hint bg-hint/5" : "border-line bg-panel"
          }`}
          onDragOver={(event) => {
            event.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragOver(false);
            takeFile(event.dataTransfer.files?.[0]);
          }}
        >
          <input
            type="file"
            accept={ACCEPT}
            className="sr-only"
            onChange={(event) => takeFile(event.target.files?.[0])}
          />
          <span className="font-mono text-[11px] uppercase tracking-[0.16em] text-hint">PDF or text</span>
          <p className="mt-3 text-sm text-paper">{file ? file.name : "Drag a file here, or click to browse"}</p>
          <p className="mt-2 text-xs text-faint">.pdf, .txt, .md · up to 2 MB</p>
        </label>
        {file ? (
          <button type="button" className="self-start text-xs text-mute underline decoration-line underline-offset-2" onClick={() => setFile(null)}>
            Remove {file.name}
          </button>
        ) : null}
        </div>
        <div className="flex flex-col rounded-xl border border-line bg-panel p-4">
          <label htmlFor="jd-text" className="font-mono text-[11px] uppercase tracking-[0.16em] text-faint">
            Or paste
          </label>
          <textarea
            id="jd-text"
            className={`${field} mt-3 min-h-48 flex-1 resize-y font-mono text-[13px] leading-relaxed`}
            placeholder="We are hiring a junior backend engineer. You will write Python services, query PostgreSQL, and cover changes with tests."
            value={text}
            onChange={(event) => setText(event.target.value)}
          />
        </div>
      </div>
      <div className="mt-4 flex items-center justify-between gap-3">
        <p className="text-xs text-faint">{file ? "The file will be uploaded. The paste box is kept locally." : "Plain text is sent as JSON."}</p>
        <button type="submit" className={btn} disabled={busy}>
          {busy ? "Uploading…" : "Analyse posting"}
        </button>
      </div>
    </form>
  );
}
