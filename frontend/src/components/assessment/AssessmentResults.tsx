import { AlertTriangle, CheckCircle2, Home } from "lucide-react";

import type { AssessmentSubmitResponse } from "../../api/types";
import { masteryColorClass, masteryToStatus, pct } from "../../lib/mastery";
import { ProgressBar } from "../ui/ProgressBar";
import { StatusBadge } from "../ui/StatusBadge";

interface AssessmentResultsProps {
  result: AssessmentSubmitResponse;
  onDone: () => void;
}

export function AssessmentResults({ result, onDone }: AssessmentResultsProps) {
  return (
    <div className="bg-white rounded-3xl shadow-sm border border-slate-200 p-6 md:p-8">
      <div className="flex items-center gap-3 mb-1">
        <CheckCircle2 className="text-green-500" size={28} />
        <h2 className="text-2xl font-bold text-slate-900">Assessment complete</h2>
      </div>
      <p className="text-slate-500 mb-6">
        Your mastery has been updated. Here's how each concept was graded.
      </p>

      <div className="space-y-4">
        {result.concept_results.map((c) => (
          <div
            key={c.concept_id}
            className="rounded-2xl border border-slate-100 bg-slate-50 p-4"
          >
            <div className="flex items-center justify-between mb-2 gap-3">
              <span className="font-semibold text-slate-800">
                {c.concept_name}
              </span>
              <div className="flex items-center gap-3">
                <StatusBadge status={masteryToStatus(c.mastery_score)} />
                <span className="font-bold text-slate-900 tabular-nums w-10 text-right">
                  {pct(c.mastery_score)}%
                </span>
              </div>
            </div>
            <ProgressBar
              progress={pct(c.mastery_score)}
              colorClass={masteryColorClass(c.mastery_score)}
            />
            {c.misconception && (
              <div className="flex items-start gap-2 mt-3 text-sm text-amber-700 bg-amber-50 border border-amber-100 rounded-xl p-3">
                <AlertTriangle size={16} className="mt-0.5 shrink-0" />
                <span>{c.misconception}</span>
              </div>
            )}
          </div>
        ))}
      </div>

      <button
        onClick={onDone}
        className="mt-8 w-full md:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-bold text-white bg-slate-900 hover:bg-slate-800 transition-colors shadow-sm"
      >
        <Home size={18} />
        Back to Dashboard
      </button>
    </div>
  );
}
