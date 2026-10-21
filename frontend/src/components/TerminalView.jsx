import { useEffect, useRef } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import "@xterm/xterm/css/xterm.css";

function paint(term, text, stderr) {
  term.reset();
  const out = text || "";
  const err = stderr || "";
  if (!out && !err) {
    term.write("\x1b[2mOutput from Run appears here. This pane does not take keyboard input.\x1b[0m");
    return;
  }
  if (out) term.write(out.endsWith("\n") ? out : `${out}\n`);
  if (err) term.write(`\x1b[31m${err.endsWith("\n") ? err : `${err}\n`}\x1b[0m`);
}

export function TerminalView({ text, stderr }) {
  const hostRef = useRef(null);
  const termRef = useRef(null);
  const fitRef = useRef(null);
  const outputRef = useRef({ text, stderr });
  outputRef.current = { text, stderr };

  useEffect(() => {
    const term = new Terminal({
      convertEol: true,
      disableStdin: true,
      cursorBlink: false,
      cursorStyle: "bar",
      fontFamily: '"JetBrains Mono", ui-monospace, monospace',
      fontSize: 13,
      theme: {
        background: "#0c1016",
        foreground: "#e8eaee",
        cursor: "#0c1016",
        selectionBackground: "#243044",
      },
    });
    const fit = new FitAddon();
    term.loadAddon(fit);
    term.open(hostRef.current);
    fit.fit();
    paint(term, outputRef.current.text, outputRef.current.stderr);
    termRef.current = term;
    fitRef.current = fit;

    const observer = new ResizeObserver(() => fit.fit());
    observer.observe(hostRef.current);
    return () => {
      observer.disconnect();
      term.dispose();
      termRef.current = null;
      fitRef.current = null;
    };
  }, []);

  useEffect(() => {
    const term = termRef.current;
    if (!term) return;
    paint(term, text, stderr);
    fitRef.current?.fit();
  }, [text, stderr]);

  return (
    <div className="overflow-hidden rounded-lg border border-line bg-ink">
      <div className="flex items-center justify-between border-b border-line px-3 py-1.5">
        <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-faint">terminal</span>
        <span className="font-mono text-[11px] text-faint">stdout / stderr · output only</span>
      </div>
      <div ref={hostRef} className="h-32" />
    </div>
  );
}
