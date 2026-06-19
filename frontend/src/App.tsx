import { useState } from "react";

import { USER_ID } from "./api/config";
import { useStartAssessment } from "./api/hooks";
import { MobileBottomNav, MobileHeader } from "./components/layout/MobileNav";
import { Sidebar } from "./components/layout/Sidebar";
import { Assessment } from "./pages/Assessment";
import { Dashboard } from "./pages/Dashboard";

const USER_NAME = "Alex";

type View = "dashboard" | "assessment";

export default function App() {
  const [view, setView] = useState<View>("dashboard");
  // The assessment is started here, from the user's click, so the request fires
  // exactly once (event handlers don't double-invoke under StrictMode). The
  // Assessment view reads this mutation's state.
  const start = useStartAssessment(USER_ID);

  const handleStart = () => {
    start.reset();
    start.mutate();
    setView("assessment");
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col md:flex-row font-sans">
      <Sidebar userName={USER_NAME} />

      <main className="flex-1 h-screen overflow-y-auto pb-20 md:pb-0">
        <MobileHeader userName={USER_NAME} />
        {view === "assessment" ? (
          <Assessment
            userId={USER_ID}
            start={start}
            onExit={() => setView("dashboard")}
          />
        ) : (
          <Dashboard onStartAssessment={handleStart} />
        )}
      </main>

      <MobileBottomNav />
    </div>
  );
}
