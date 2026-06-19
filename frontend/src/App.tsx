import { MobileBottomNav, MobileHeader } from "./components/layout/MobileNav";
import { Sidebar } from "./components/layout/Sidebar";
import { Dashboard } from "./pages/Dashboard";

const USER_NAME = "Alex";

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col md:flex-row font-sans">
      <Sidebar userName={USER_NAME} />

      <main className="flex-1 h-screen overflow-y-auto pb-20 md:pb-0">
        <MobileHeader userName={USER_NAME} />
        <Dashboard />
      </main>

      <MobileBottomNav />
    </div>
  );
}
