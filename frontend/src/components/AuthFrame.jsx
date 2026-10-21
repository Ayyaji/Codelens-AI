import { Link } from "react-router-dom";

export function AuthFrame({ children }) {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-line">
        <div className="mx-auto flex h-14 max-w-6xl items-center px-4">
          <Link to="/" className="flex items-center gap-2 font-mono text-sm font-semibold">
            <span className="grid h-6 w-6 place-items-center rounded-md bg-hint text-[11px] font-bold text-ink">CL</span>
            CodeLens
          </Link>
        </div>
      </header>
      <main className="mx-auto flex w-full max-w-lg flex-1 flex-col justify-center px-4 py-16">{children}</main>
    </div>
  );
}
