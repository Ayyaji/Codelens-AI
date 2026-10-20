import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { DirectiveBadge } from "../components/DirectiveBadge";
import { PageHeader, btn } from "../components/ui";
import { formatScore, parseMistake, weakTopicChart } from "../lib/format";
import { useSession } from "../session";

export function ResultsPage() {
  const { session } = useSession();
  const result = session.result;

  if (!result) {
    return (
      <div>
        <PageHeader
          kicker="04  Results"
          title="No attempt yet"
          lede="Submit a test and the score, weak topics, and mistake list will show up here."
        />
        <Link to={session.questions.length ? "/test" : "/analysis"} className={btn}>
          {session.questions.length ? "Go to the test" : "Start from analysis"}
        </Link>
      </div>
    );
  }

  const chart = weakTopicChart(result.weak_topics);
  const guidance = result.guidance || {};
  const mistakes = guidance.mistake_patterns || [];
  const score = Number(result.score);
  const tone = score < 50 ? "#e15b6a" : score < 75 ? "#e8a33d" : "#3cbe8c";

  return (
    <div>
      <PageHeader
        kicker="04  Results"
        title="How this attempt landed"
        lede="MCQs are compared in code. Coding answers are checked in the sandbox. The next step follows the same full / hint / gentle / break judgment as the guidance chat."
      />
      <div className="grid gap-4 lg:grid-cols-[220px_minmax(0,1fr)]">
        <section className="rounded-xl border border-line bg-panel p-5">
          <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-faint">Score</p>
          <p className="mt-2 font-mono text-6xl tabular-nums tracking-tight" style={{ color: tone }}>
            {formatScore(result.score)}
          </p>
          <p className="mt-1 text-xs text-mute">out of 100</p>
        </section>
        <section className="rounded-xl border border-line bg-panel p-5">
          <div className="flex flex-wrap items-center gap-3">
            <DirectiveBadge directive={guidance.directive} />
            <p className="text-xs text-faint">from guidance.directive</p>
          </div>
          <p className="mt-3 text-sm leading-relaxed text-paper">{guidance.message}</p>
          {guidance.next_steps?.length ? (
            <ol className="mt-4 space-y-1 text-sm text-mute">
              {guidance.next_steps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          ) : null}
        </section>
      </div>

      <section className="mt-4 rounded-xl border border-line bg-panel p-5">
        <div className="flex items-baseline justify-between gap-3">
          <h2 className="font-mono text-[11px] uppercase tracking-[0.16em] text-faint">Weak topics</h2>
          <p className="text-xs text-faint">Bar length is rank. The API sends names, not counts.</p>
        </div>
        {chart.length ? (
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chart} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
                <CartesianGrid stroke="#242c38" vertical={false} />
                <XAxis dataKey="topic" stroke="#8d96a6" tick={{ fill: "#8d96a6", fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis allowDecimals={false} stroke="#8d96a6" tick={{ fill: "#5d6676", fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip
                  cursor={{ fill: "rgba(77, 157, 224, 0.08)" }}
                  contentStyle={{ background: "#131922", border: "1px solid #242c38", borderRadius: 8, color: "#e8eaee" }}
                  formatter={(value) => [value, "priority"]}
                />
                <Bar dataKey="priority" fill="#4d9de0" radius={[4, 4, 0, 0]} maxBarSize={48} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="mt-4 text-sm text-mute">No weak topics on this attempt.</p>
        )}
      </section>

      <section className="mt-4 rounded-xl border border-line bg-panel p-5">
        <h2 className="font-mono text-[11px] uppercase tracking-[0.16em] text-faint">Mistakes</h2>
        {mistakes.length ? (
          <ul className="mt-3 divide-y divide-line">
            {mistakes.map((pattern) => {
              const parsed = parseMistake(pattern);
              return (
                <li key={pattern} className="flex flex-wrap items-baseline justify-between gap-2 py-3">
                  <span className="text-sm capitalize text-paper">{parsed.kind}</span>
                  <span className="font-mono text-xs text-mute">{parsed.skill || pattern}</span>
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="mt-3 text-sm text-mute">No mistake patterns were recorded.</p>
        )}
      </section>
    </div>
  );
}
