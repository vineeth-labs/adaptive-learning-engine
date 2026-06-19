import { BookOpen, Brain, LayoutDashboard, Target, TrendingUp } from "lucide-react";

export function MobileHeader({ userName }: { userName: string }) {
  return (
    <div className="md:hidden flex items-center justify-between bg-white px-6 py-4 border-b border-slate-200 sticky top-0 z-20">
      <div className="flex items-center space-x-2">
        <Brain className="text-indigo-600 w-6 h-6" />
        <span className="text-lg font-bold text-slate-900">MasteryApp</span>
      </div>
      <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-700 font-bold">
        {userName[0]}
      </div>
    </div>
  );
}

export function MobileBottomNav() {
  return (
    <nav className="md:hidden fixed bottom-0 w-full bg-white border-t border-slate-200 flex items-center justify-around py-3 px-2 z-20">
      <button className="flex flex-col items-center text-indigo-600">
        <LayoutDashboard size={20} />
        <span className="text-[10px] font-medium mt-1">Home</span>
      </button>
      <button className="flex flex-col items-center text-slate-400">
        <Target size={20} />
        <span className="text-[10px] mt-1">My Path</span>
      </button>
      <button className="flex flex-col items-center text-slate-400">
        <BookOpen size={20} />
        <span className="text-[10px] mt-1">Library</span>
      </button>
      <button className="flex flex-col items-center text-slate-400">
        <TrendingUp size={20} />
        <span className="text-[10px] mt-1">Stats</span>
      </button>
    </nav>
  );
}
