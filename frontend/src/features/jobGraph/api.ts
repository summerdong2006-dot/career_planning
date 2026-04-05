import { requestJson } from "../../shared/http";

import type { JobGraphOverviewResponse } from "./types";

export async function getJobGraphOverview(limit = 10): Promise<JobGraphOverviewResponse> {
  return requestJson<JobGraphOverviewResponse>(`/api/v1/job-graph/overview?limit=${limit}`);
}
