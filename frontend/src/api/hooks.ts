import { useQuery } from "@tanstack/react-query";

import { fetchCompetencyMap, fetchNextRecommendation } from "./client";
import { USE_MOCKS } from "./config";
import { MOCK_COMPETENCY_MAP, MOCK_RECOMMENDATION } from "./mocks";
import type { RecommendationResponse, UserMapResponse } from "./types";

// Small delay so loading states are exercised even in mock mode.
const withDelay = <T>(value: T, ms = 350): Promise<T> =>
  new Promise((resolve) => setTimeout(() => resolve(value), ms));

export function useCompetencyMap(userId: string) {
  return useQuery<UserMapResponse>({
    queryKey: ["competency-map", userId, USE_MOCKS],
    queryFn: () =>
      USE_MOCKS ? withDelay(MOCK_COMPETENCY_MAP) : fetchCompetencyMap(userId),
  });
}

export function useNextRecommendation(userId: string) {
  return useQuery<RecommendationResponse>({
    queryKey: ["recommendation", userId, USE_MOCKS],
    queryFn: () =>
      USE_MOCKS ? withDelay(MOCK_RECOMMENDATION) : fetchNextRecommendation(userId),
  });
}
