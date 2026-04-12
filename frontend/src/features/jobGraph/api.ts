import { requestJson } from "../../shared/http";
import { repairMojibakeValue } from "../../shared/encoding";

import type { JobGalleryListResponse, JobGraphOverviewResponse, JobPathExplorerResponse } from "./types";

export async function getJobGraphOverview(limit = 10): Promise<JobGraphOverviewResponse> {
  const result = await requestJson<JobGraphOverviewResponse>(`/api/v1/job-graph/overview?limit=${limit}`);
  return repairMojibakeValue(result);
}

export async function getJobGallery(q = "", limit = 18): Promise<JobGalleryListResponse> {
  const search = new URLSearchParams();
  if (q.trim()) {
    search.set("q", q.trim());
  }
  search.set("limit", String(limit));
  const result = await requestJson<JobGalleryListResponse>(`/api/v1/job-graph/gallery?${search.toString()}`);
  return repairMojibakeValue(result);
}

export async function getJobPathByJobId(jobId: number): Promise<JobPathExplorerResponse> {
  const result = await requestJson<JobPathExplorerResponse>(`/api/v1/job-graph/path?job_id=${jobId}`);
  return repairMojibakeValue(result);
}

export async function getJobPathByJobTitle(jobTitle: string): Promise<JobPathExplorerResponse> {
  const result = await requestJson<JobPathExplorerResponse>(`/api/v1/job-graph/path?job_title=${encodeURIComponent(jobTitle)}`);
  return repairMojibakeValue(result);
}

export async function getJobPathByStudentProfileId(studentProfileId: number): Promise<JobPathExplorerResponse> {
  const result = await requestJson<JobPathExplorerResponse>(`/api/v1/job-graph/path?student_profile_id=${studentProfileId}`);
  return repairMojibakeValue(result);
}
