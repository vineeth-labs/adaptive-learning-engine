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
