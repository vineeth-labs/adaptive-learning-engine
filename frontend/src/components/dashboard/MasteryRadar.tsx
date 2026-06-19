import { TrendingUp } from "lucide-react";
import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

import type { ConceptNode } from "../../api/types";
import { overallReadiness, toRadarData } from "../../lib/mastery";

export function MasteryRadar({
  nodes,
  targetRole,
}: {
  nodes: ConceptNode[];
  targetRole: string;
}) {
  const data = toRadarData(nodes);
  const readiness = overallReadiness(nodes);

  return (
    <div className="lg:col-span-1 bg-white rounded-3xl p-6 shadow-sm border border-slate-200 flex flex-col">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-lg font-bold text-slate-900">Domain Mastery</h3>
      </div>
      <p className="text-sm text-slate-500 mb-6">
        Your calibration against {targetRole}
      </p>

      <div className="flex-1 w-full min-h-[250px] relative">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="70%" data={data}>
            <PolarGrid stroke="#e2e8f0" />
            <PolarAngleAxis
              dataKey="subject"
              tick={{ fill: "#64748b", fontSize: 12, fontWeight: 500 }}
            />
            <PolarRadiusAxis
              angle={30}
              domain={[0, 100]}
              tick={false}
              axisLine={false}
            />
            <Radar
              name="Mastery"
              dataKey="mastery"
              stroke="#4f46e5"
              strokeWidth={2}
              fill="#6366f1"
              fillOpacity={0.3}
            />
            <Tooltip
              contentStyle={{
                borderRadius: "12px",
                border: "none",
                boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
              }}
              itemStyle={{ color: "#4f46e5", fontWeight: "bold" }}
              formatter={(value: number) => [`${value}%`, "Mastery"]}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-4 p-4 bg-indigo-50 rounded-2xl flex items-start space-x-3">
        <div className="mt-0.5">
          <TrendingUp size={18} className="text-indigo-600" />
        </div>
        <div>
          <p className="text-sm font-medium text-slate-900">
            Overall Readiness: {readiness}%
          </p>
          <p className="text-xs text-slate-500 mt-1">
            Averaged across {data.length} domain
            {data.length === 1 ? "" : "s"} from your assessed concepts.
          </p>
        </div>
      </div>
    </div>
  );
}
