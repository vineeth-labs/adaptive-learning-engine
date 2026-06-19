import type { MasteryStatus } from "../../lib/mastery";

const STYLES: Record<MasteryStatus, string> = {
  Mastered: "bg-green-100 text-green-700 border-green-200",
  Proficient: "bg-blue-100 text-blue-700 border-blue-200",
  Learning: "bg-yellow-100 text-yellow-700 border-yellow-200",
  "Needs Review": "bg-red-100 text-red-700 border-red-200",
};

export function StatusBadge({ status }: { status: MasteryStatus }) {
  return (
    <span
      className={`px-2.5 py-1 rounded-full text-xs font-medium border ${STYLES[status]}`}
    >
      {status}
    </span>
  );
}
