// Pure derivations over competency-map data. No React, no IO — easy to unit-test.

import type { ConceptNode } from "../api/types";

export type MasteryStatus =
  | "Mastered"
  | "Proficient"
  | "Learning"
  | "Needs Review";

/** Backend mastery is 0.0–1.0; render as an integer percent. */
export const pct = (mastery: number): number => Math.round(mastery * 100);

/** Status badge derived from mastery, mirroring the reference color thresholds. */
export function masteryToStatus(mastery: number): MasteryStatus {
  if (mastery >= 0.8) return "Mastered";
  if (mastery >= 0.6) return "Proficient";
  if (mastery >= 0.4) return "Learning";
  return "Needs Review";
}

const TITLE_CASE = (segment: string): string =>
  segment
    .split(/[_-]/)
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : w))
    .join(" ");

/**
 * Category for a concept = the path segment just below the domain root.
 * Paths look like "java.collections.arrays" — the first segment is the domain
 * root ("java"), so the meaningful category is the second segment.
 */
export function categoryFromPath(path: string): string {
  const segments = path.split(".").filter(Boolean);
  if (segments.length === 0) return "General";
  const raw = segments.length > 1 ? segments[1] : segments[0];
  return TITLE_CASE(raw);
}

export interface RadarDatum {
  subject: string;
  mastery: number; // 0–100 for the chart
  fullMark: 100;
}

/** Average mastery per category, as percentages, for the radar chart. */
export function toRadarData(nodes: ConceptNode[]): RadarDatum[] {
  const buckets = new Map<string, { sum: number; count: number }>();
  for (const node of nodes) {
    const key = categoryFromPath(node.path);
    const b = buckets.get(key) ?? { sum: 0, count: 0 };
    b.sum += node.mastery;
    b.count += 1;
    buckets.set(key, b);
  }
  return [...buckets.entries()].map(([subject, { sum, count }]) => ({
    subject,
    mastery: pct(sum / count),
    fullMark: 100 as const,
  }));
}

/** Mean mastery across all concepts, as a percent. */
export function overallReadiness(nodes: ConceptNode[]): number {
  if (nodes.length === 0) return 0;
  const mean = nodes.reduce((acc, n) => acc + n.mastery, 0) / nodes.length;
  return pct(mean);
}

/**
 * Concepts to surface in "recent activity / needs attention":
 * most-recently interacted first (nulls last), capped at `limit`.
 */
export function recentConcepts(nodes: ConceptNode[], limit = 5): ConceptNode[] {
  const ts = (n: ConceptNode) =>
    n.last_interaction_at ? Date.parse(n.last_interaction_at) : -Infinity;
  return [...nodes].sort((a, b) => ts(b) - ts(a)).slice(0, limit);
}

/** Tailwind bg class for a progress bar at a given mastery (0–1). */
export function masteryColorClass(mastery: number): string {
  if (mastery >= 0.8) return "bg-green-500";
  if (mastery >= 0.6) return "bg-blue-500";
  if (mastery >= 0.4) return "bg-yellow-500";
  return "bg-red-500";
}
