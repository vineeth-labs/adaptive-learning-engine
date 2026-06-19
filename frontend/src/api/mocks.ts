// Mock payloads shaped to the REAL API schema (backend/schemas).
// Used when VITE_USE_MOCKS !== "false" so the dashboard renders with no backend.
// Concept names/paths mirror backend/curriculum/programming/java.yaml.

import type { RecommendationResponse, UserMapResponse } from "./types";

const DOMAIN_ID = "11111111-1111-1111-1111-111111111111";
const USER_ID = "00000000-0000-0000-0000-000000000001";

const daysAgo = (n: number): string =>
  new Date(Date.now() - n * 24 * 60 * 60 * 1000).toISOString();

interface MockConcept {
  id: string;
  name: string;
  path: string;
  difficulty: number;
  mastery: number;
  evidence_count: number;
  misconceptions: string[];
  last_interaction_at: string | null;
}

const CONCEPTS: MockConcept[] = [
  { id: "c-arrays", name: "Arrays", path: "java.collections.arrays", difficulty: 0.25, mastery: 0.92, evidence_count: 6, misconceptions: [], last_interaction_at: daysAgo(1) },
  { id: "c-arraylist", name: "ArrayList", path: "java.collections.arraylist", difficulty: 0.3, mastery: 0.81, evidence_count: 4, misconceptions: [], last_interaction_at: daysAgo(2) },
  { id: "c-strings", name: "Strings", path: "java.collections.strings", difficulty: 0.2, mastery: 0.74, evidence_count: 3, misconceptions: [], last_interaction_at: daysAgo(5) },
  { id: "c-classes", name: "Classes", path: "java.oop.classes", difficulty: 0.3, mastery: 0.68, evidence_count: 4, misconceptions: [], last_interaction_at: daysAgo(3) },
  { id: "c-inheritance", name: "Inheritance", path: "java.oop.inheritance", difficulty: 0.45, mastery: 0.52, evidence_count: 3, misconceptions: ["Confuses overriding with overloading"], last_interaction_at: daysAgo(4) },
  { id: "c-polymorphism", name: "Polymorphism", path: "java.oop.polymorphism", difficulty: 0.5, mastery: 0.38, evidence_count: 2, misconceptions: ["Thinks static methods can be overridden"], last_interaction_at: daysAgo(7) },
  { id: "c-loops", name: "Loops", path: "java.control_flow.loops", difficulty: 0.15, mastery: 0.88, evidence_count: 5, misconceptions: [], last_interaction_at: daysAgo(9) },
  { id: "c-conditionals", name: "Conditional Statements", path: "java.control_flow.conditionals", difficulty: 0.15, mastery: 0.79, evidence_count: 3, misconceptions: [], last_interaction_at: daysAgo(11) },
  { id: "c-recursion", name: "Recursion", path: "java.functions.recursion", difficulty: 0.35, mastery: 0.41, evidence_count: 2, misconceptions: ["Missing base case reasoning"], last_interaction_at: daysAgo(6) },
  { id: "c-methods", name: "Methods", path: "java.functions.methods", difficulty: 0.2, mastery: 0.83, evidence_count: 4, misconceptions: [], last_interaction_at: daysAgo(12) },
  { id: "c-jvm", name: "JVM", path: "java.fundamentals.jvm", difficulty: 0.1, mastery: 0.6, evidence_count: 2, misconceptions: [], last_interaction_at: daysAgo(14) },
  { id: "c-concurrency", name: "Threads", path: "java.concurrency.threads", difficulty: 0.7, mastery: 0.18, evidence_count: 1, misconceptions: ["Confuses concurrency with parallelism"], last_interaction_at: daysAgo(20) },
];

export const MOCK_COMPETENCY_MAP: UserMapResponse = {
  user_id: USER_ID,
  nodes: CONCEPTS.map((c) => ({
    ...c,
    domain_id: DOMAIN_ID,
    metadata: {},
  })),
  edges: [
    { source_id: "c-classes", target_id: "c-inheritance", relation_type: "prerequisite" },
    { source_id: "c-inheritance", target_id: "c-polymorphism", relation_type: "prerequisite" },
    { source_id: "c-methods", target_id: "c-recursion", relation_type: "prerequisite" },
  ],
};

export const MOCK_RECOMMENDATION: RecommendationResponse = {
  action_type: "assess",
  recommended_concepts: [
    {
      concept_id: "c-polymorphism",
      concept_name: "Polymorphism",
      score: 0.86,
      score_breakdown: { gap: 0.45, review: 0.12, centrality: 0.22, fatigue: 0.07 },
    },
  ],
  rationale:
    "Your prerequisites (Classes, Inheritance) are in place, but Polymorphism mastery is still low and it unlocks several downstream OOP concepts — the highest-leverage next step.",
  payload: { estimated_minutes: 15, num_questions: 3, difficulty: "Intermediate" },
};
