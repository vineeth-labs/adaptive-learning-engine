import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, Loader2, Sparkles } from "lucide-react";

import { useStartAssessment, useSubmitAssessment } from "../api/hooks";
import type { AssessmentSubmitResponse } from "../api/types";
import { AssessmentResults } from "../components/assessment/AssessmentResults";
import {
  QuestionStep,
  conceptNameFor,
} from "../components/assessment/QuestionStep";

interface AssessmentProps {
  userId: string;
  onExit: () => void;
}

export function Assessment({ userId, onExit }: AssessmentProps) {
  const start = useStartAssessment(userId);
  const submit = useSubmitAssessment(userId);

  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<AssessmentSubmitResponse | null>(null);

  // Kick off generation once on mount (guarded against StrictMode double-invoke).
  const startedRef = useRef(false);
  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    start.mutate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const assessment = start.data;
  const questions = useMemo(() => assessment?.questions ?? [], [assessment]);

  // --- Generating / loading ---
  if (start.isPending || (!start.isError && !assessment)) {
    return (
      <Shell onExit={onExit}>
        <CenteredCard>
          <Loader2 className="animate-spin text-indigo-500 mb-4" size={36} />
          <h2 className="text-xl font-bold text-slate-800 mb-1">
            Building your assessment…
          </h2>
          <p className="text-slate-500 text-sm max-w-sm text-center">
            Selecting a cluster of concepts at the edge of what you know and
            generating a scenario.
          </p>
        </CenteredCard>
      </Shell>
    );
  }

  // --- Generation error ---
  if (start.isError) {
    return (
      <Shell onExit={onExit}>
        <ErrorCard
          title="Couldn't start an assessment"
          message={(start.error as Error).message}
          onRetry={() => start.mutate()}
        />
      </Shell>
    );
  }

  // --- Empty frontier: nothing learnable right now ---
  if (assessment && (assessment.status === "empty" || questions.length === 0)) {
    return (
      <Shell onExit={onExit}>
        <CenteredCard>
          <Sparkles className="text-indigo-500 mb-4" size={36} />
          <h2 className="text-xl font-bold text-slate-800 mb-1">
            You're all caught up
          </h2>
          <p className="text-slate-500 text-sm max-w-sm text-center mb-6">
            {assessment.message ||
              "Everything reachable is mastered or blocked — no learnable frontier right now."}
          </p>
          <button
            onClick={onExit}
            className="px-6 py-3 rounded-xl font-bold text-white bg-slate-900 hover:bg-slate-800 transition-colors"
          >
            Back to Dashboard
          </button>
        </CenteredCard>
      </Shell>
    );
  }

  // --- Results ---
  if (result) {
    return (
      <Shell onExit={onExit}>
        <AssessmentResults result={result} onDone={onExit} />
      </Shell>
    );
  }

  // --- Question flow ---
  const current = questions[index];

  const handleSubmit = () => {
    if (!assessment) return;
    const responses = questions.map((q) => ({
      question_id: q.id,
      response_text: answers[q.id] ?? "",
    }));
    submit.mutate(
      {
        assessmentId: assessment.assessment_id,
        payload: { user_id: userId, responses },
      },
      { onSuccess: (data) => setResult(data) },
    );
  };

  return (
    <Shell onExit={onExit}>
      <QuestionStep
        question={current}
        index={index}
        total={questions.length}
        conceptName={conceptNameFor(current, assessment!.target_concepts)}
        value={answers[current.id] ?? ""}
        onChange={(text) =>
          setAnswers((prev) => ({ ...prev, [current.id]: text }))
        }
        onBack={() => setIndex((i) => Math.max(0, i - 1))}
        onNext={() => setIndex((i) => Math.min(questions.length - 1, i + 1))}
        onSubmit={handleSubmit}
        isSubmitting={submit.isPending}
      />
      {submit.isError && (
        <p className="mt-4 text-sm text-red-600">
          Submission failed: {(submit.error as Error).message}
        </p>
      )}
    </Shell>
  );
}

function Shell({
  children,
  onExit,
}: {
  children: React.ReactNode;
  onExit: () => void;
}) {
  return (
    <div className="max-w-3xl mx-auto px-6 py-8">
      <button
        onClick={onExit}
        className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-slate-800 mb-6 transition-colors"
      >
        <ArrowLeft size={16} />
        Back to Dashboard
      </button>
      {children}
    </div>
  );
}

function CenteredCard({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-3xl shadow-sm border border-slate-200 p-10 flex flex-col items-center justify-center min-h-[20rem]">
      {children}
    </div>
  );
}

function ErrorCard({
  title,
  message,
  onRetry,
}: {
  title: string;
  message: string;
  onRetry: () => void;
}) {
  return (
    <div className="rounded-3xl border border-red-200 bg-red-50 p-6">
      <h3 className="font-bold text-red-800">{title}</h3>
      <p className="text-sm text-red-600 mt-1 break-words">{message}</p>
      <button
        onClick={onRetry}
        className="mt-4 px-4 py-2 rounded-xl font-medium text-white bg-red-600 hover:bg-red-700 transition-colors"
      >
        Try again
      </button>
    </div>
  );
}
