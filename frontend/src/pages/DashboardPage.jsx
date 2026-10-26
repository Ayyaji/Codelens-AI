import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getOverview, listStudents } from "../api/client";
import { ActivityFeed } from "../components/ActivityFeed";
import { ErrorBanner, LoadingLine, PageHeader, field } from "../components/ui";
import { formatScore, formatWhen } from "../lib/format";

const DIRECTIVES = [
  { key: "full", label: "FULL", fill: "#e8a33d" },
  { key: "hint", label: "HINT", fill: "#4d9de0" },
  { key: "gentle", label: "GENTLE", fill: "#8b7fd1" },
  { key: "break", label: "BREAK", fill: "#e15b6a" },
];

const tooltipStyle = {
  contentStyle: { background: "#131922", border: "1px solid #242c38", borderRadius: 8, color: "#e8eaee" },
  cursor: { fill: "rgba(77, 157, 224, 0.08)" },
};

function tone(score) {
  if (score == null) return "#8d96a6";
  if (score < 50) return "#e15b6a";
  if (score < 75) return "#e8a33d";
  return "#3cbe8c";
}

function Stat({ label, value, hint, to }) {
  const body = (
    <article className="h-full rounded-xl border border-line bg-panel px-4 py-4">
      <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-faint">{label}</p>
      <p className="mt-2 font-mono text-3xl tabular-nums text-paper">{value}</p>
      {hint ? <p className="mt-1 text-xs text-mute">{hint}</p> : null}
    </article>
  );
  if (!to) return body;
  return (
    <Link to={to} className="block h-full rounded-xl focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hint">
      {body}
    </Link>
  );
}

export function DashboardPage() {
  const navigate = useNavigate();
  const [overview, setOverview] = useState(null);
  const [students, setStudents] = useState([]);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancel = false;
    Promise.all([getOverview(), listStudents()])
      .then(([nextOverview, nextStudents]) => {
        if (cancel) return;
        setOverview(nextOverview);
        setStudents(nextStudents);
      })
      .catch((err) => {
        if (!cancel) setError(err.message || "Could not load the dashboard.");
      })
      .finally(() => {
        if (!cancel) setLoading(false);
      });
    return () => {
      cancel = true;
    };
  }, []);

  const directiveData = useMemo(
    () =>
      DIRECTIVES.map((item) => ({
        ...item,
        count: overview?.directive_counts?.[item.key] ?? 0,
      })),
    [overview],
  );

  const scoreData = useMemo(
    () =>
      students
        .filter((student) => student.avg_score != null)
        .map((student) => ({
          id: student.id,
          name: student.name.split(" ")[0] || student.name,
          score: student.avg_score,
          fill: tone(student.avg_score),
        })),
    [students],
  );

  const needle = query.trim().toLowerCase();
  const shown = students.filter((student) => {
    if (!needle) return true;
    return student.name.toLowerCase().includes(needle) || student.email.toLowerCase().includes(needle);
  });

  return (
    <div>
      <PageHeader
        kicker="Dashboard"
        title="How the cohort is doing"
        lede="Counts come from GET /teacher/overview. The student list is everyone with role student. Search runs in the browser."
      />
      <ErrorBanner message={error} />
      {loading ? <LoadingLine label="Loading the overview…" /> : null}
      {overview ? (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Stat label="Students" value={overview.total_students} hint="Accounts with role student" />
          <Stat label="Active today" value={overview.active_today} hint="Any activity since UTC midnight" />
          <Stat label="Average score" value={formatScore(overview.avg_score)} hint="Mean of every submission" />
          <Stat label="Pending notes" value={overview.pending_kb} hint="Waiting for review" to="/dashboard/kb" />
        </div>
      ) : null}

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <section className="rounded-xl border border-line bg-panel p-5">
          <h2 className="font-mono text-[11px] uppercase tracking-[0.16em] text-faint">Directives</h2>
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={directiveData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="#242c38" vertical={false} />
                <XAxis dataKey="label" stroke="#8d96a6" tick={{ fill: "#8d96a6", fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis allowDecimals={false} stroke="#8d96a6" tick={{ fill: "#5d6676", fontSize: 11 }} axisLine={false} tickLine={false} width={28} />
                <Tooltip {...tooltipStyle} formatter={(value) => [value, "count"]} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {directiveData.map((entry) => (
                    <Cell key={entry.key} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <ul className="mt-3 grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
            {directiveData.map((entry) => (
              <li key={entry.key} className="flex items-center justify-between gap-2 rounded-md border border-line px-2 py-1">
                <span className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full" style={{ background: entry.fill }} />
                  {entry.label}
                </span>
                <span className="font-mono text-paper">{entry.count}</span>
              </li>
            ))}
          </ul>
        </section>
        <section className="rounded-xl border border-line bg-panel p-5">
          <h2 className="font-mono text-[11px] uppercase tracking-[0.16em] text-faint">Average score by student</h2>
          {scoreData.length ? (
            <div className="mt-4 h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={scoreData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid stroke="#242c38" vertical={false} />
                  <XAxis dataKey="name" stroke="#8d96a6" tick={{ fill: "#8d96a6", fontSize: 12 }} axisLine={false} tickLine={false} />
                  <YAxis domain={[0, 100]} stroke="#8d96a6" tick={{ fill: "#5d6676", fontSize: 11 }} axisLine={false} tickLine={false} width={28} />
                  <Tooltip {...tooltipStyle} formatter={(value) => [value, "average"]} />
                  <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                    {scoreData.map((entry) => (
                      <Cell key={entry.id} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="mt-8 text-sm text-faint">No submissions yet.</p>
          )}
        </section>
      </div>

      <section className="mt-8">
        <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
          <h2 className="font-mono text-[11px] uppercase tracking-[0.16em] text-faint">Students</h2>
          <label className="w-full max-w-xs text-xs text-mute" htmlFor="student-search">
            Search
            <input
              id="student-search"
              className={`${field} mt-1`}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Name or email"
            />
          </label>
        </div>
        <p className="mb-2 text-xs text-faint">
          Showing {shown.length} of {students.length}
        </p>
        <div className="overflow-x-auto rounded-xl border border-line">
          <table className="w-full min-w-[40rem] text-left text-sm">
            <thead className="bg-panel text-[11px] uppercase tracking-[0.14em] text-faint">
              <tr>
                <th scope="col" className="px-4 py-3 font-medium">Name</th>
                <th scope="col" className="px-4 py-3 font-medium">Last active</th>
                <th scope="col" className="px-4 py-3 font-medium">Average</th>
                <th scope="col" className="px-4 py-3 font-medium">Weak topics</th>
                <th scope="col" className="px-4 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((student) => (
                <tr
                  key={student.id}
                  className="cursor-pointer border-t border-line hover:bg-panel"
                  onClick={() => navigate(`/dashboard/students/${encodeURIComponent(student.id)}`)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") navigate(`/dashboard/students/${encodeURIComponent(student.id)}`);
                  }}
                  tabIndex={0}
                >
                  <td className="px-4 py-3">
                    <span className="block font-medium text-paper">{student.name}</span>
                    <span className="block font-mono text-[11px] text-faint">{student.email}</span>
                  </td>
                  <td className="px-4 py-3 text-mute">{formatWhen(student.last_active)}</td>
                  <td className="px-4 py-3 font-mono text-paper">{formatScore(student.avg_score)}</td>
                  <td className="px-4 py-3 text-mute">{student.weak_topics.length ? student.weak_topics.join(", ") : "—"}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-md border px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.12em] ${
                        student.disabled ? "border-break/40 text-break" : "border-ok/40 text-ok"
                      }`}
                    >
                      {student.disabled ? "Disabled" : "Active"}
                    </span>
                  </td>
                </tr>
              ))}
              {!shown.length ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-sm text-faint">
                    No students match that search.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mt-8">
        <div className="mb-3 flex items-baseline justify-between gap-3">
          <h2 className="font-mono text-[11px] uppercase tracking-[0.16em] text-faint">Activity</h2>
          <Link to="/dashboard/activity" className="text-xs text-hint hover:underline">
            Open the feed
          </Link>
        </div>
        <ActivityFeed limit={8} />
      </section>
    </div>
  );
}
