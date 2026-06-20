import {
  BookOpen,
  Brain,
  LayoutDashboard,
  Settings,
  Target,
  TrendingUp,
} from "lucide-react";

import { SidebarItem } from "../ui/SidebarItem";

export function Sidebar({ userName }: { userName: string }) {
  return (
    <aside className="hidden md:flex w-64 flex-col bg-white border-r border-slate-200 px-4 py-6 shadow-sm z-10">
      <div className="flex items-center space-x-3 px-2 mb-10">
        <div className="bg-indigo-600 p-2 rounded-lg">
          <Brain className="text-white w-6 h-6" />
        </div>
        <span className="text-xl font-bold text-slate-900 tracking-tight">
          MasteryApp
        </span>
      </div>

      <nav className="flex-1 space-y-2">
        <SidebarItem icon={LayoutDashboard} label="Dashboard" active />
        <SidebarItem icon={Target} label="My Path" />
        <SidebarItem icon={BookOpen} label="Concept Library" />
        <SidebarItem icon={TrendingUp} label="Analytics" />
      </nav>

      <div className="mt-auto border-t border-slate-100 pt-4">
        <SidebarItem icon={Settings} label="Settings" />
        <div className="flex items-center space-x-3 px-4 py-3 mt-2 rounded-xl bg-slate-50">
          <div className="w-8 h-8 rounded-full bg-indigo-200 flex items-center justify-center text-indigo-700 font-bold">
            {userName[0]}
          </div>
          <div>
            <p className="text-sm font-medium text-slate-900">{userName}</p>
            <p className="text-xs text-slate-500">Free Tier</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
