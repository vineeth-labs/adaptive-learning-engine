import { ChevronRight, Play } from "lucide-react";

import type { ConceptNode } from "../../api/types";
import {
  categoryFromPath,
  masteryColorClass,
  masteryToStatus,
  pct,
  recentConcepts,
} from "../../lib/mastery";
import { ProgressBar } from "../ui/ProgressBar";
import { StatusBadge } from "../ui/StatusBadge";

export function ConceptDeepDive({ nodes }: { nodes: ConceptNode[] }) {
  const concepts = recentConcepts(nodes);

  return (
    <div className="lg:col-span-2 bg-white rounded-3xl p-6 shadow-sm border border-slate-200">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-bold text-slate-900">Concept Deep Dive</h3>
          <p className="text-sm text-slate-500">
            Your recent activity and areas needing attention
          </p>
        </div>
        <button className="text-sm font-medium text-indigo-600 hover:text-indigo-700 flex items-center">
          View Full Library <ChevronRight size={16} className="ml-1" />
        </button>
      </div>

      {concepts.length === 0 ? (
        <p className="text-sm text-slate-500 py-8 text-center">
          No assessed concepts yet — take an assessment to start building your map.
        </p>
      ) : (
        <div className="space-y-5">
          {concepts.map((concept) => {
            const score = pct(concept.mastery);
            return (
              <div
                key={concept.id}
                className="group p-4 border border-slate-100 rounded-2xl hover:border-indigo-100 hover:bg-slate-50 hover:shadow-sm transition-all"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-3 gap-2">
                  <div>
                    <div className="flex items-center space-x-2 mb-1">
                      <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                        {categoryFromPath(concept.path)}
                      </span>
                      <span className="w-1 h-1 rounded-full bg-slate-300" />
                      <StatusBadge status={masteryToStatus(concept.mastery)} />
                    </div>
                    <h4 className="text-base font-bold text-slate-900 group-hover:text-indigo-700 transition-colors">
                      {concept.name}
                    </h4>
                    {concept.misconceptions.length > 0 && (
                      <p className="text-xs text-red-500 mt-1">
                        ⚠ {concept.misconceptions[0]}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center space-x-4">
                    <div className="text-right hidden sm:block">
                      <span className="text-sm font-bold text-slate-900">
                        {score}%
                      </span>
                      <span className="text-xs text-slate-500 block">Mastery</span>
                    </div>
                    <button className="hidden group-hover:flex items-center justify-center w-8 h-8 rounded-full bg-indigo-100 text-indigo-600 transition-colors">
                      <Play size={14} className="ml-0.5 fill-current" />
                    </button>
                  </div>
                </div>

                <div className="flex items-center space-x-3">
                  <ProgressBar
                    progress={score}
                    colorClass={masteryColorClass(concept.mastery)}
                  />
                  <span className="text-xs font-bold text-slate-700 sm:hidden w-8">
                    {score}%
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
