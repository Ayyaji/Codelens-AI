import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { analyseJd, generateTest } from "../api/client";
import { MatchMeter } from "../components/MatchMeter";
import { ErrorBanner, LoadingLine, PageHeader, btn, btnGhost } from "../components/ui";
import { matchFromSkills } from "../lib/format";
import { useSession } from "../session";

const LEVEL_TONE = {
  beginner: "text-ok border-ok/30",
  intermediate: "text-hint border-hint/30",
  advanced: "text-full border-full/30",
};

const TICKS = { beginner: 1, intermediate: 2, advanced: 3 };

export function AnalysisPage() {
  const { session, setAnalysis, setQuestions } = useSession();
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    if (!session.jdId || session.analysis) return undefined;
    let cancel = false;
    setLoading(true);
    setError("");
    analyseJd(session.jdId)
      .then((data) => {
        if (!cancel) setAnalysis(data);
      })
      .catch((err) => {
        if (!cancel) setError(err.message || "Could not analyse that job description.");
      })
      .finally(() => {
        if (!cancel) setLoading(false);
      });
    return () => {
      cancel = true;
    };
  }, [session.jdId, session.analysis, setAnalysis]);

  async function onGenerate() {
    setGenerating(true);
    setError("");
    try {
      const data = await generateTest(session.jdId);
      setQuestions(data.questions || []);
      navigate("/test");
    } catch (err) {
      setError(err.message || "Could not generate a test.");
    } finally {
      setGenerating(false);
    }
  }

  if (!session.jdId) {
    return (
      <div>
        <PageHeader kicker="02  Analysis" title="No posting yet" lede="Upload a job description first. The skills and roadmap are loaded from that id." />
        <Link to="/upload" className={btn}>
          Upload a posting
        </Link>
      </div>
    );
  }

  const analysis = session.analysis;
  const skills = analysis?.skills || [];
  const roadmap = [...(analysis?.roadmap || [])].sort((a, b) => a.order - b.order);

  return (
    <div>
      <PageHeader
        kicker="02  Analysis"
        title="What this role is asking for"
        lede={session.sourceLabel ? `${session.sourceLabel} · ${session.jdId}` : session.jdId}
        actions={
          <>
            {session.questions.length ? (
              <Link to="/test" className={btnGhost}>
                Continue test
              </Link>
            ) : null}
            <button type="button" className={btn} onClick={onGenerate} disabled={generating || loading || !analysis}>
              {generating ? "Generating…" : session.questions.length ? "New test" : "Generate test"}
            </button>
          </>
        }
      />
      <ErrorBanner message={error} />
      {loading ? <LoadingLine label="Reading the posting…" /> : null}
      {analysis ? (
        <div className="space-y-8">
          <MatchMeter value={matchFromSkills(skills)} />
          <section>
            <h2 className="font-mono text-[11px] uppercase tracking-[0.16em] text-faint">Skills</h2>
            <ul className="mt-3 grid gap-3 md:grid-cols-2">
              {skills.map((skill) => (
                <li key={skill.name} className="rounded-xl border border-line bg-panel p-4">
                  <div className="flex items-start justify-between gap-3">
                    <h3 className="text-base font-semibold">{skill.name}</h3>
                    <span className={`rounded-md border px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.12em] ${LEVEL_TONE[skill.level] || "text-mute border-line"}`}>
                      {skill.level}
                    </span>
                  </div>
                  <div className="mt-2 flex gap-1" aria-hidden="true">
                    {[1, 2, 3].map((tick) => (
                      <span
                        key={tick}
                        className={`h-1 w-6 rounded-full ${tick <= (TICKS[skill.level] || 2) ? "bg-hint" : "bg-line"}`}
                      />
                    ))}
                  </div>
                  <p className="mt-3 text-sm leading-relaxed text-mute">{skill.explanation}</p>
                </li>
              ))}
            </ul>
          </section>
          <section>
            <h2 className="font-mono text-[11px] uppercase tracking-[0.16em] text-faint">Roadmap</h2>
            <ol className="mt-3 space-y-2">
              {roadmap.map((item) => (
                <li key={`${item.order}-${item.skill}`} className="grid grid-cols-[auto_1fr] gap-4 rounded-xl border border-line bg-panel p-4">
                  <span className="font-mono text-sm text-hint">{String(item.order).padStart(2, "0")}</span>
                  <div>
                    <p className="text-sm font-semibold">{item.skill || "Step"}</p>
                    <p className="mt-1 text-sm text-paper">{item.goal}</p>
                    {item.practice ? <p className="mt-1 text-sm text-mute">Practice: {item.practice}</p> : null}
                  </div>
                </li>
              ))}
            </ol>
          </section>
        </div>
      ) : null}
    </div>
  );
}
