import { requestJson } from "../../shared/http";

import type { MatchingRecommendResponse } from "./types";

type RecommendParams = {
  studentProfileId: number;
  topK: number;
};

export async function recommendJobs(params: RecommendParams): Promise<MatchingRecommendResponse> {
  return requestJson<MatchingRecommendResponse>("/api/v1/matching/recommend", {
    body: JSON.stringify({
      student_profile_id: params.studentProfileId,
      top_k: params.topK,
      persist: true
    }),
    method: "POST"
  });
}
