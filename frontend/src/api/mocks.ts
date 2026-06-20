// Mock payloads shaped to the REAL API schema (backend/schemas).
// Used when VITE_USE_MOCKS !== "false" so the dashboard renders with no backend.
// Concept names/paths mirror backend/curriculum/programming/java.yaml.

import type {
  AssessmentNextResponse,
  AssessmentSubmitRequest,
  AssessmentSubmitResponse,
  RecommendationResponse,
  UserMapResponse,
} from "./types";

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

// A frontier cluster of 2 related, low-mastery concepts (mirrors POST /assessments/next).
export const MOCK_ASSESSMENT: AssessmentNextResponse = {
  assessment_id: "a0000000-0000-0000-0000-0000000000aa",
  user_id: USER_ID,
  status: "generated",
  target_concepts: [
    { concept_id: "c-polymorphism", concept_name: "Polymorphism" },
    { concept_id: "c-recursion", concept_name: "Recursion" },
  ],
  questions: [
    {
      id: "q-1",
      position: 1,
      concept_id: "c-polymorphism",
      question_text:
        "You have an Animal base class and Dog and Cat subclasses that each override a speak() method. Explain what happens at runtime when you call speak() on an Animal reference that points to a Dog object, and why. What would change if speak() were a static method?",
    },
    {
      id: "q-2",
      position: 2,
      concept_id: "c-recursion",
      question_text:
        "Write a recursive method to compute the factorial of a non-negative integer n. Identify the base case and the recursive case, and explain what would happen if the base case were missing.",
    },
  ],
  created_at: new Date().toISOString(),
  message: "Frontier assessment over 2 related concept(s).",
};

/**
 * Deterministic mock grader: rewards longer, more substantive answers so the flow
 * feels responsive without a backend. Real grading is the LLM diagnostic evaluator.
 */
export function mockSubmitAssessment(
  payload: AssessmentSubmitRequest,
): AssessmentSubmitResponse {
  const byConcept: Record<string, { name: string; len: number }> = {
    "q-1": { name: "Polymorphism", len: 0 },
    "q-2": { name: "Recursion", len: 0 },
  };
  const conceptIdFor: Record<string, string> = {
    "q-1": "c-polymorphism",
    "q-2": "c-recursion",
  };

  for (const r of payload.responses) {
    if (byConcept[r.question_id]) {
      byConcept[r.question_id].len = r.response_text.trim().length;
    }
  }

  const concept_results = Object.entries(byConcept).map(([qid, { name, len }]) => {
    // Map answer length to a 0.3–0.95 mastery, clamped.
    const score = Math.min(0.95, Math.max(0.3, 0.3 + len / 300));
    return {
      concept_id: conceptIdFor[qid],
      concept_name: name,
      mastery_score: Math.round(score * 100) / 100,
      misconception:
        len < 40 ? "Answer was too brief to demonstrate understanding." : null,
    };
  });

  const seed = concept_results[0];
  return {
    assessment_id: MOCK_ASSESSMENT.assessment_id,
    status: "evaluated",
    concept_results,
    mastery_score: seed.mastery_score,
    misconception: seed.misconception,
    message: "Assessment submitted and evaluated successfully.",
  };
}
