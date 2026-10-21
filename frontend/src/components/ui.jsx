export function PageHeader({ kicker, title, lede, actions }) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div className="max-w-2xl">
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-hint">{kicker}</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-paper">{title}</h1>
        {lede ? <p className="mt-2 text-sm leading-relaxed text-mute">{lede}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}

export function ErrorBanner({ message }) {
  if (!message) return null;
  return (
    <div role="alert" className="mb-4 rounded-lg border border-break/40 bg-break/10 px-4 py-3 text-sm text-[#f3c1c7]">
      {message}
    </div>
  );
}

export function LoadingLine({ label }) {
  return (
    <p className="flex items-center gap-2 font-mono text-xs text-mute" role="status">
      <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-hint" />
      {label}
    </p>
  );
}

export const btn =
  "inline-flex items-center justify-center gap-2 rounded-lg bg-hint px-4 py-2 text-sm font-semibold text-ink transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40";

export const btnDanger =
  "inline-flex items-center justify-center gap-2 rounded-lg bg-break px-4 py-2 text-sm font-semibold text-ink transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40";

export const btnGhost =
  "inline-flex items-center justify-center gap-2 rounded-lg border border-line bg-panel px-4 py-2 text-sm font-medium text-mute transition hover:border-faint hover:text-paper disabled:cursor-not-allowed disabled:opacity-40";

export const field =
  "w-full rounded-lg border border-line bg-ink px-3 py-2.5 text-sm text-paper outline-none placeholder:text-faint focus:border-hint";

export function ConfirmDialog({ open, title, body, confirmLabel, onConfirm, onClose, busy, danger }) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-40 grid place-items-center bg-ink/70 px-4"
      onClick={busy ? undefined : onClose}
      role="presentation"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        className="w-full max-w-md rounded-xl border border-line bg-panel p-5"
        onClick={(event) => event.stopPropagation()}
        onKeyDown={(event) => {
          if (event.key === "Escape" && !busy) onClose();
        }}
      >
        <h2 id="confirm-title" className="text-lg font-semibold text-paper">
          {title}
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-mute">{body}</p>
        <div className="mt-5 flex justify-end gap-2">
          <button type="button" className={btnGhost} onClick={onClose} disabled={busy} autoFocus>
            Cancel
          </button>
          <button type="button" className={danger ? btnDanger : btn} onClick={onConfirm} disabled={busy}>
            {busy ? "Working…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
