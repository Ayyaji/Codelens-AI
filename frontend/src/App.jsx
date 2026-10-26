import { Navigate, Route, Routes } from "react-router-dom";
import { Navbar } from "./components/Navbar";
import { ChatPage } from "./pages/ChatPage";
import { ActivityPage } from "./pages/ActivityPage";
import { AnalysisPage } from "./pages/AnalysisPage";
import { DashboardPage } from "./pages/DashboardPage";
import { KbPage } from "./pages/KbPage";
import { LoginPage } from "./pages/LoginPage";
import { MySpacePage } from "./pages/MySpacePage";
import { RegisterPage } from "./pages/RegisterPage";
import { ResultsPage } from "./pages/ResultsPage";
import { StudentDetailPage } from "./pages/StudentDetailPage";
import { ClassResultPage } from "./pages/ClassResultPage";
import { ClassTakePage } from "./pages/ClassTakePage";
import { ClassTestsPage } from "./pages/ClassTestsPage";
import { TeacherTestEditorPage } from "./pages/TeacherTestEditorPage";
import { TeacherTestResultsPage } from "./pages/TeacherTestResultsPage";
import { TeacherTestsPage } from "./pages/TeacherTestsPage";
import { TestPage } from "./pages/TestPage";
import { UploadPage } from "./pages/UploadPage";
import { homeFor, useSession } from "./session";

function BootScreen() {
  return (
    <div className="grid min-h-screen place-items-center">
      <p className="font-mono text-xs text-mute" role="status">
        Checking session…
      </p>
    </div>
  );
}

function Shell({ children }) {
  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
    </div>
  );
}

function HomeRedirect() {
  const { session } = useSession();
  if (!session.user) return <Navigate to="/login" replace />;
  return <Navigate to={homeFor(session.user)} replace />;
}

function GuestOnly({ children }) {
  const { session } = useSession();
  if (session.user) return <Navigate to={homeFor(session.user)} replace />;
  return children;
}

function RequireAuth({ role, children }) {
  const { session } = useSession();
  if (!session.user) return <Navigate to="/login" replace />;
  if (role && session.user.role !== role) return <Navigate to={homeFor(session.user)} replace />;
  return <Shell>{children}</Shell>;
}

export default function App() {
  const { ready } = useSession();
  if (!ready) return <BootScreen />;
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <GuestOnly>
            <LoginPage />
          </GuestOnly>
        }
      />
      <Route
        path="/register"
        element={
          <GuestOnly>
            <RegisterPage />
          </GuestOnly>
        }
      />
      <Route path="/" element={<HomeRedirect />} />
      <Route
        path="/space"
        element={
          <RequireAuth role="student">
            <MySpacePage />
          </RequireAuth>
        }
      />
      <Route
        path="/upload"
        element={
          <RequireAuth role="student">
            <UploadPage />
          </RequireAuth>
        }
      />
      <Route
        path="/analysis"
        element={
          <RequireAuth role="student">
            <AnalysisPage />
          </RequireAuth>
        }
      />
      <Route
        path="/test"
        element={
          <RequireAuth role="student">
            <TestPage />
          </RequireAuth>
        }
      />
      <Route
        path="/class-tests"
        element={
          <RequireAuth role="student">
            <ClassTestsPage />
          </RequireAuth>
        }
      />
      <Route
        path="/class-tests/:testId/results"
        element={
          <RequireAuth role="student">
            <ClassResultPage />
          </RequireAuth>
        }
      />
      <Route
        path="/class-tests/:testId"
        element={
          <RequireAuth role="student">
            <ClassTakePage />
          </RequireAuth>
        }
      />
      <Route
        path="/results"
        element={
          <RequireAuth role="student">
            <ResultsPage />
          </RequireAuth>
        }
      />
      <Route
        path="/chat/:chatId?"
        element={
          <RequireAuth role="student">
            <ChatPage />
          </RequireAuth>
        }
      />
      <Route
        path="/dashboard"
        element={
          <RequireAuth role="teacher">
            <DashboardPage />
          </RequireAuth>
        }
      />
      <Route
        path="/dashboard/activity"
        element={
          <RequireAuth role="teacher">
            <ActivityPage />
          </RequireAuth>
        }
      />
      <Route
        path="/dashboard/kb"
        element={
          <RequireAuth role="teacher">
            <KbPage />
          </RequireAuth>
        }
      />
      <Route
        path="/dashboard/tests"
        element={
          <RequireAuth role="teacher">
            <TeacherTestsPage />
          </RequireAuth>
        }
      />
      <Route
        path="/dashboard/tests/new"
        element={
          <RequireAuth role="teacher">
            <TeacherTestEditorPage />
          </RequireAuth>
        }
      />
      <Route
        path="/dashboard/tests/:testId/results"
        element={
          <RequireAuth role="teacher">
            <TeacherTestResultsPage />
          </RequireAuth>
        }
      />
      <Route
        path="/dashboard/tests/:testId"
        element={
          <RequireAuth role="teacher">
            <TeacherTestEditorPage />
          </RequireAuth>
        }
      />
      <Route
        path="/dashboard/students/:studentId"
        element={
          <RequireAuth role="teacher">
            <StudentDetailPage />
          </RequireAuth>
        }
      />
      <Route path="*" element={<HomeRedirect />} />
    </Routes>
  );
}
