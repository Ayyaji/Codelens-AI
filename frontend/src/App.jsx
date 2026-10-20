import { Navigate, Route, Routes } from "react-router-dom";
import { Navbar } from "./components/Navbar";
import { AnalysisPage } from "./pages/AnalysisPage";
import { ChatPage } from "./pages/ChatPage";
import { LoginPage } from "./pages/LoginPage";
import { ResultsPage } from "./pages/ResultsPage";
import { TestPage } from "./pages/TestPage";
import { UploadPage } from "./pages/UploadPage";
import { useSession } from "./session";

function RequireAuth({ children }) {
  const { session } = useSession();
  if (!session.studentId) return <Navigate to="/login" replace />;
  return children;
}

function Shell({ children }) {
  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/upload"
        element={
          <RequireAuth>
            <Shell>
              <UploadPage />
            </Shell>
          </RequireAuth>
        }
      />
      <Route
        path="/analysis"
        element={
          <RequireAuth>
            <Shell>
              <AnalysisPage />
            </Shell>
          </RequireAuth>
        }
      />
      <Route
        path="/test"
        element={
          <RequireAuth>
            <Shell>
              <TestPage />
            </Shell>
          </RequireAuth>
        }
      />
      <Route
        path="/results"
        element={
          <RequireAuth>
            <Shell>
              <ResultsPage />
            </Shell>
          </RequireAuth>
        }
      />
      <Route
        path="/chat"
        element={
          <RequireAuth>
            <Shell>
              <ChatPage />
            </Shell>
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
