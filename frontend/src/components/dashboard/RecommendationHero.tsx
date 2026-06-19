import { BookOpen, Clock, Play, Target, Zap } from "lucide-react";

import type { RecommendationResponse } from "../../api/types";

const ACTION_VERB: Record<RecommendationResponse["action_type"], string> = {
  assess: "Start Assessment",
  review: "Review Concept",
  teach: "Start Lesson",
};

function payloadNumber(
  payload: Record<string, unknown> | null,
  key: string,
): number | undefined {
  const v = payload?.[key];
  return typeof v === "number" ? v : undefined;
}

function payloadString(
  payload: Record<string, unknown> | null,
  key: string,
): string | undefined {
  const v = payload?.[key];
  return typeof v === "string" ? v : undefined;
}

export function RecommendationHero({ rec }: { rec: RecommendationResponse }) {
  const top = rec.recommended_concepts[0];

  // Empty frontier: nothing learnable right now.
  if (!top) {
    return (
      <div className="mb-8 bg-slate-900 rounded-3xl shadow-xl border border-slate-800 p-8 md:p-10 text-white">
        <h2 className="text-2xl font-bold mb-2">You're all caught up</h2>
        <p className="text-slate-300 max-w-xl">{rec.rationale}</p>
      </div>
    );
  }

  // The recommendation schema carries no path; payload may carry session hints.
  const minutes = payloadNumber(rec.payload, "estimated_minutes");
  const questions = payloadNumber(rec.payload, "num_questions");
  const difficulty = payloadString(rec.payload, "difficulty");
  const domain = payloadString(rec.payload, "domain");

  return (
    <div className="mb-8 relative overflow-hidden bg-slate-900 rounded-3xl shadow-xl border border-slate-800 group">
      <div className="absolute inset-0 bg-gradient-to-br from-indigo-600/20 to-purple-800/40 z-0" />
      <div className="absolute -top-24 -right-24 w-64 h-64 bg-indigo-500/20 rounded-full blur-3xl z-0" />
      <div className="absolute -bottom-24 -left-24 w-64 h-64 bg-purple-500/20 rounded-full blur-3xl z-0" />

      <div className="relative z-10 p-8 md:p-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="flex-1 text-white">
          <div className="inline-flex items-center space-x-1.5 bg-white/10 backdrop-blur-md px-3 py-1.5 rounded-full text-xs font-semibold uppercase tracking-wider mb-4 border border-white/10">
            <Zap size={14} className="text-yellow-400" />
            <span>Up Next For You</span>
          </div>
          <h2 className="text-3xl md:text-4xl font-bold mb-2 text-white">
            {top.concept_name}
          </h2>
          <p className="text-slate-300 max-w-xl text-sm md:text-base">
            {domain && (
              <span className="font-medium text-indigo-300">{domain} • </span>
            )}
            {rec.rationale}
          </p>

          <div className="flex flex-wrap items-center gap-x-6 gap-y-2 mt-6">
            {minutes !== undefined && (
              <span className="flex items-center text-slate-300 text-sm">
                <Clock size={16} className="mr-1.5 opacity-70" />
                {minutes} mins
              </span>
            )}
            {questions !== undefined && (
              <span className="flex items-center text-slate-300 text-sm">
                <BookOpen size={16} className="mr-1.5 opacity-70" />
                {questions} Questions
              </span>
            )}
            {difficulty && (
              <span className="flex items-center text-slate-300 text-sm">
                <Target size={16} className="mr-1.5 opacity-70" />
                {difficulty}
              </span>
            )}
          </div>
        </div>

        <button className="w-full md:w-auto bg-white text-indigo-900 hover:bg-indigo-50 transition-colors px-8 py-4 rounded-2xl font-bold flex items-center justify-center space-x-2 shadow-lg shadow-white/10 group-hover:scale-105 duration-200">
          <Play size={20} className="fill-current" />
          <span>{ACTION_VERB[rec.action_type]}</span>
        </button>
      </div>
    </div>
  );
}
