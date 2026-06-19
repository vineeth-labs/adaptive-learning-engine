import { ArrowLeft, ArrowRight, Send } from "lucide-react";

import type { AssessmentQuestion, TargetConcept } from "../../api/types";

interface QuestionStepProps {
  question: AssessmentQuestion;
  /** 0-based index of this question. */
  index: number;
  total: number;
  /** Concept name for this question, resolved from target_concepts. */
  conceptName?: string;
  value: string;
  onChange: (text: string) => void;
  onBack: () => void;
  onNext: () => void;
  onSubmit: () => void;
  isSubmitting: boolean;
}

export function QuestionStep({
  question,
  index,
  total,
  conceptName,
  value,
  onChange,
  onBack,
  onNext,
  onSubmit,
  isSubmitting,
}: QuestionStepProps) {
  const isLast = index === total - 1;
  const isFirst = index === 0;
  const answered = value.trim().length > 0;

  return (
    <div className="bg-white rounded-3xl shadow-sm border border-slate-200 p-6 md:p-8">
      {/* progress */}
      <div className="mb-6">
        <div className="flex items-center justify-between text-sm mb-2">
          <span className="font-medium text-slate-500">
            Question {index + 1} of {total}
          </span>
          {conceptName && (
            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-100">
              {conceptName}
            </span>
          )}
        </div>
        <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
          <div
            className="bg-indigo-600 h-1.5 rounded-full transition-all duration-500"
            style={{ width: `${((index + 1) / total) * 100}%` }}
          />
        </div>
      </div>

      <p className="text-lg md:text-xl text-slate-800 leading-relaxed mb-5 whitespace-pre-wrap">
        {question.question_text}
      </p>

      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Type your answer here. Explain your reasoning — free-text answers are graded on understanding, not exact wording."
        rows={8}
        className="w-full rounded-2xl border border-slate-200 bg-slate-50 p-4 text-slate-800 text-sm md:text-base resize-y focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
      />

      <div className="flex items-center justify-between mt-6">
        <button
          onClick={onBack}
          disabled={isFirst || isSubmitting}
          className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl font-medium text-slate-600 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          <ArrowLeft size={18} />
          Back
        </button>

        {isLast ? (
          <button
            onClick={onSubmit}
            disabled={!answered || isSubmitting}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl font-bold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
          >
            <Send size={18} />
            {isSubmitting ? "Grading…" : "Submit Assessment"}
          </button>
        ) : (
          <button
            onClick={onNext}
            disabled={!answered}
            className="inline-flex items-center gap-1.5 px-6 py-3 rounded-xl font-bold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
          >
            Next
            <ArrowRight size={18} />
          </button>
        )}
      </div>
    </div>
  );
}

/** Tiny helper used by the orchestrator to label a question by its target concept. */
export function conceptNameFor(
  question: AssessmentQuestion,
  targets: TargetConcept[],
): string | undefined {
  return targets.find((t) => t.concept_id === question.concept_id)?.concept_name;
}
