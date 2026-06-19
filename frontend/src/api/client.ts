import { API_BASE_URL } from "./config";
import type {
  AssessmentNextResponse,
  AssessmentSubmitRequest,
  AssessmentSubmitResponse,
  RecommendationResponse,
  UserMapResponse,
} from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function get<T>(path: string): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      headers: { Accept: "application/json" },
    });
  } catch (err) {
    throw new ApiError(
      `Cannot reach the API at ${API_BASE_URL}. Is the backend running? (${String(err)})`,
      0,
    );
  }
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(
      `GET ${path} failed: ${res.status} ${res.statusText} ${body}`.trim(),
      res.status,
    );
  }
  return (await res.json()) as T;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body),
    });
  } catch (err) {
    throw new ApiError(
      `Cannot reach the API at ${API_BASE_URL}. Is the backend running? (${String(err)})`,
      0,
    );
  }
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(
      `POST ${path} failed: ${res.status} ${res.statusText} ${body}`.trim(),
      res.status,
    );
  }
  return (await res.json()) as T;
}

export function fetchCompetencyMap(userId: string): Promise<UserMapResponse> {
  return get<UserMapResponse>(`/users/${userId}/competency-map`);
}

export function fetchNextRecommendation(
  userId: string,
): Promise<RecommendationResponse> {
  return get<RecommendationResponse>(`/users/${userId}/recommendations/next`);
}

/** Auto-select a frontier cluster and generate the next diagnostic assessment. */
export function startNextAssessment(
  userId: string,
): Promise<AssessmentNextResponse> {
  return post<AssessmentNextResponse>(`/assessments/next`, { user_id: userId });
}

/** Submit free-text answers; the backend grades each concept and updates mastery. */
export function submitAssessment(
  assessmentId: string,
  payload: AssessmentSubmitRequest,
): Promise<AssessmentSubmitResponse> {
  return post<AssessmentSubmitResponse>(
    `/assessments/${assessmentId}/submit`,
    payload,
  );
}
