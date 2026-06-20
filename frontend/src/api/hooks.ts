import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  fetchCompetencyMap,
  fetchNextRecommendation,
  startNextAssessment,
  submitAssessment,
} from "./client";
import { USE_MOCKS } from "./config";
import {
  MOCK_ASSESSMENT,
  MOCK_COMPETENCY_MAP,
  MOCK_RECOMMENDATION,
  mockSubmitAssessment,
} from "./mocks";
import type {
  AssessmentNextResponse,
  AssessmentSubmitRequest,
  AssessmentSubmitResponse,
  RecommendationResponse,
  UserMapResponse,
} from "./types";

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

/** Start (generate) the next frontier assessment for the user. */
export function useStartAssessment(userId: string) {
  return useMutation<AssessmentNextResponse>({
    mutationFn: () =>
      USE_MOCKS ? withDelay(MOCK_ASSESSMENT, 500) : startNextAssessment(userId),
  });
}

/**
 * Submit answers and grade them. On success we invalidate the competency map and
 * recommendation so the dashboard reflects the updated mastery.
 */
export function useSubmitAssessment(userId: string) {
  const queryClient = useQueryClient();
  return useMutation<
    AssessmentSubmitResponse,
    Error,
    { assessmentId: string; payload: AssessmentSubmitRequest }
  >({
    mutationFn: ({ assessmentId, payload }) =>
      USE_MOCKS
        ? withDelay(mockSubmitAssessment(payload), 600)
        : submitAssessment(assessmentId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["competency-map", userId] });
      queryClient.invalidateQueries({ queryKey: ["recommendation", userId] });
    },
  });
}
