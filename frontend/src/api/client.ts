import { API_BASE_URL } from "./config";
import type { RecommendationResponse, UserMapResponse } from "./types";

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

export function fetchCompetencyMap(userId: string): Promise<UserMapResponse> {
  return get<UserMapResponse>(`/users/${userId}/competency-map`);
}

export function fetchNextRecommendation(
  userId: string,
): Promise<RecommendationResponse> {
  return get<RecommendationResponse>(`/users/${userId}/recommendations/next`);
}
