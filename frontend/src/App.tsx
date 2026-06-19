import { useState } from "react";

import { USER_ID } from "./api/config";
import { MobileBottomNav, MobileHeader } from "./components/layout/MobileNav";
import { Sidebar } from "./components/layout/Sidebar";
import { Assessment } from "./pages/Assessment";
import { Dashboard } from "./pages/Dashboard";

const USER_NAME = "Alex";

type View = "dashboard" | "assessment";

export default function App() {
  const [view, setView] = useState<View>("dashboard");

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col md:flex-row font-sans">
      <Sidebar userName={USER_NAME} />

      <main className="flex-1 h-screen overflow-y-auto pb-20 md:pb-0">
        <MobileHeader userName={USER_NAME} />
        {view === "assessment" ? (
          <Assessment
            userId={USER_ID}
            onExit={() => setView("dashboard")}
          />
        ) : (
          <Dashboard onStartAssessment={() => setView("assessment")} />
        )}
      </main>

      <MobileBottomNav />
    </div>
  );
}
