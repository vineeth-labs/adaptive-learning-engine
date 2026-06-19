// TypeScript mirrors of the backend Pydantic schemas.
// Source of truth: backend/schemas/map.py and backend/schemas/recommendation.py.

export interface ConceptNode {
  id: string;
  domain_id: string;
  name: string;
  /** String form of the Postgres ltree path, e.g. "Java.Concurrency". */
  path: string;
  /** 0.0–1.0 */
  difficulty: number;
  metadata: Record<string, unknown>;
  /** Learner mastery belief, 0.0–1.0 (0 when no state exists yet). */
  mastery: number;
  evidence_count: number;
  misconceptions: string[];
  /** ISO timestamp, or null if never interacted with. */
  last_interaction_at: string | null;
}

export interface ConceptEdge {
  source_id: string;
  target_id: string;
  relation_type: "prerequisite";
}

export interface UserMapResponse {
  user_id: string;
  nodes: ConceptNode[];
  edges: ConceptEdge[];
}

// --- Assessment flow (backend/schemas/assessment.py) ---

export interface AssessmentQuestion {
  id: string;
  position: number;
  question_text: string;
  /** Target concept for this question (frontier assessments); null for legacy single-concept. */
  concept_id: string | null;
}

export interface TargetConcept {
  concept_id: string;
  concept_name: string;
}

/** Response of POST /assessments/next. */
export interface AssessmentNextResponse {
  assessment_id: string;
  user_id: string;
  status: string;
  target_concepts: TargetConcept[];
  questions: AssessmentQuestion[];
  created_at: string;
  message: string;
}

/** One answer in the submit payload. */
export interface QuestionResponse {
  question_id: string;
  response_text: string;
}

export interface AssessmentSubmitRequest {
  user_id: string;
  responses: QuestionResponse[];
}

export interface ConceptMasteryUpdate {
  concept_id: string;
  concept_name: string;
  /** Updated mastery belief, 0.0–1.0. */
  mastery_score: number;
  misconception: string | null;
}

/** Response of POST /assessments/{id}/submit. */
export interface AssessmentSubmitResponse {
  assessment_id: string;
  status: string;
  concept_results: ConceptMasteryUpdate[];
  /** Back-compat: seed (first) concept's mastery. */
  mastery_score: number;
  misconception: string | null;
  message: string;
}

export type ActionType = "assess" | "review" | "teach";

export interface RecommendationDetail {
  concept_id: string;
  concept_name: string;
  score: number;
  /** Weight breakdown: gap, review, centrality, fatigue. */
  score_breakdown: Record<string, number>;
}

export interface RecommendationResponse {
  action_type: ActionType;
  recommended_concepts: RecommendationDetail[];
  rationale: string;
  /** Context-specific details, e.g. scenario text or tutorial content. */
  payload: Record<string, unknown> | null;
}
