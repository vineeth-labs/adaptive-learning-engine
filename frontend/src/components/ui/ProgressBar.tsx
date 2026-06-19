interface ProgressBarProps {
  /** 0–100 */
  progress: number;
  colorClass?: string;
}

export function ProgressBar({
  progress,
  colorClass = "bg-indigo-600",
}: ProgressBarProps) {
  return (
    <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
      <div
        className={`${colorClass} h-2.5 rounded-full transition-all duration-1000 ease-out`}
        style={{ width: `${progress}%` }}
      />
    </div>
  );
}
