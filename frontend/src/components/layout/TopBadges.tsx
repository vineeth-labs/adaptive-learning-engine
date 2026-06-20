import { Award, Zap } from "lucide-react";

// TODO: Level and streak have no backend source yet (no gamification model).
// Rendered as static placeholders to preserve the reference design.
const PLACEHOLDER_LEVEL = 12;
const PLACEHOLDER_STREAK_DAYS = 4;

export function TopBadges() {
  return (
    <div className="flex space-x-3">
      <div className="bg-white px-4 py-2 rounded-xl border border-slate-200 shadow-sm flex items-center">
        <Award className="text-amber-500 mr-2" size={18} />
        <span className="font-medium text-slate-800">Lvl {PLACEHOLDER_LEVEL}</span>
      </div>
      <div className="bg-white px-4 py-2 rounded-xl border border-slate-200 shadow-sm flex items-center">
        <Zap className="text-yellow-500 mr-2" size={18} />
        <span className="font-medium text-slate-800">
          {PLACEHOLDER_STREAK_DAYS} Day Streak
        </span>
      </div>
    </div>
  );
}
