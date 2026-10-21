import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatScore, formatWhen, parseMistake } from "../lib/format";

const tooltipStyle = {
  contentStyle: { background: "#131922", border: "1px solid #242c38", borderRadius: 8, color: "#e8eaee" },
  cursor: { fill: "rgba(77, 157, 224, 0.08)" },
};

export function PersonaPanel({ persona, showNotes = false }) {
  const weak = persona?.weak_topics || [];
  const mistakes = persona?.mistake_patterns || [];
  const scores = persona?.scores || [];
  const notes = persona?.learning_notes || [];
  const chart = scores.map((entry, index) => ({
    label: String(index + 1),
    score: Number(entry.score) || 0,
  }));

  return (
    <section className="rounded-xl border border-line bg-panel p-5">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="font-mono text-[11px] uppercase tracking-[0.16em] text-faint">Persona</h2>
        {persona?.updated_at ? <p className="text-xs text-faint">Updated {formatWhen(persona.updated_at)}</p> : null}
      </div>
      {!weak.length && !mistakes.length && !scores.length ? (
        <p className="mt-4 text-sm text-mute">No persona yet. A test or a guidance chat will start one.</p>
      ) : null}
      <div className="mt-4">
        <h3 className="text-xs font-medium text-mute">Weak topics</h3>
        {weak.length ? (
          <ul className="mt-2 flex flex-wrap gap-2">
            {weak.map((topic) => (
              <li key={topic} className="rounded-md border border-full/30 bg-full/10 px-2 py-1 font-mono text-[11px] text-full">
                {topic}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-sm text-faint">None recorded.</p>
        )}
      </div>
      <div className="mt-4">
        <h3 className="text-xs font-medium text-mute">Mistake patterns</h3>
        {mistakes.length ? (
          <ul className="mt-2 space-y-2">
            {mistakes.map((pattern) => {
              const parsed = parseMistake(pattern);
              return (
                <li key={pattern} className="flex items-baseline justify-between gap-3 text-sm">
                  <span className="capitalize text-paper">{parsed.kind}</span>
                  {parsed.skill ? <span className="font-mono text-[11px] text-faint">{parsed.skill}</span> : null}
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="mt-2 text-sm text-faint">None recorded.</p>
        )}
      </div>
      <div className="mt-4">
        <h3 className="text-xs font-medium text-mute">Scores</h3>
        {scores.length ? (
          <>
            <p className="mt-2 font-mono text-3xl tabular-nums text-paper">{formatScore(scores[scores.length - 1].score)}</p>
            <p className="text-xs text-faint">latest of {scores.length}</p>
            {chart.length > 1 ? (
              <div className="mt-3 h-36">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chart} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                    <CartesianGrid stroke="#242c38" vertical={false} />
                    <XAxis dataKey="label" stroke="#8d96a6" tick={{ fill: "#5d6676", fontSize: 11 }} axisLine={false} tickLine={false} />
                    <YAxis domain={[0, 100]} stroke="#8d96a6" tick={{ fill: "#5d6676", fontSize: 11 }} axisLine={false} tickLine={false} width={28} />
                    <Tooltip {...tooltipStyle} formatter={(value) => [value, "score"]} />
                    <Bar dataKey="score" fill="#4d9de0" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : null}
            <ul className="mt-3 space-y-1 text-xs text-mute">
              {scores.map((entry) => (
                <li key={entry.test_id} className="flex justify-between gap-3">
                  <span>{formatWhen(entry.created_at)}</span>
                  <span className="font-mono text-paper">{formatScore(entry.score)}</span>
                </li>
              ))}
            </ul>
          </>
        ) : (
          <p className="mt-2 text-sm text-faint">No scored attempts yet.</p>
        )}
      </div>
      {showNotes ? (
        <div className="mt-4">
          <h3 className="text-xs font-medium text-mute">Learning notes</h3>
          {notes.length ? (
            <ul className="mt-2 space-y-2 text-sm text-mute">
              {notes.map((note, index) => (
                <li key={`${index}-${note}`} className="border-l-2 border-line pl-3">
                  {note}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-faint">No notes yet.</p>
          )}
        </div>
      ) : null}
    </section>
  );
}
