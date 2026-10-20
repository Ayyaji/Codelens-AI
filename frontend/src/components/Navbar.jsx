import { NavLink, useNavigate } from "react-router-dom";
import { mocksActive } from "../api/client";
import { useSession } from "../session";

const LINKS = [
  { to: "/upload", label: "Upload" },
  { to: "/analysis", label: "Analysis" },
  { to: "/test", label: "Test" },
  { to: "/results", label: "Results" },
  { to: "/chat", label: "Guidance" },
];

export function Navbar() {
  const { session, logout } = useSession();
  const navigate = useNavigate();
  const mocked = mocksActive();

  function onLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <header className="sticky top-0 z-20 border-b border-line bg-ink/90 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center gap-4 px-4">
        <NavLink to="/upload" className="flex shrink-0 items-center gap-2 font-mono text-sm font-semibold tracking-tight">
          <span className="grid h-6 w-6 place-items-center rounded-md bg-hint text-[11px] font-bold text-ink">CL</span>
          CodeLens
        </NavLink>
        <nav className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto text-sm" aria-label="Primary">
          {LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                `rounded-md px-2.5 py-1.5 whitespace-nowrap transition ${
                  isActive ? "bg-panel text-paper" : "text-mute hover:text-paper"
                }`
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="flex shrink-0 items-center gap-3">
          {mocked ? (
            <span className="hidden font-mono text-[10px] uppercase tracking-[0.16em] text-full sm:inline">mocks</span>
          ) : null}
          <span className="max-w-[8rem] truncate font-mono text-xs text-mute" title={session.studentId}>
            {session.studentId}
          </span>
          <button type="button" onClick={onLogout} className="text-xs text-faint hover:text-paper">
            Log out
          </button>
        </div>
      </div>
    </header>
  );
}
