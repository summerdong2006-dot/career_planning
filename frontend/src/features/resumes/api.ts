import { apiBaseUrl, getErrorMessage, requestJson } from "../../shared/http";
import { getAuthToken } from "../../shared/authStorage";

import type { ResumeDetail, ResumeExportFormat } from "./types";

type GenerateResumeParams = {
  studentProfileId: number;
  targetJob: string;
};

function parseFilename(contentDisposition: string | null, fallback: string): string {
  if (!contentDisposition) {
    return fallback;
  }

  const basicMatch = contentDisposition.match(/filename="?([^";]+)"?/i);
  return basicMatch?.[1] ?? fallback;
}

export async function generateResume(params: GenerateResumeParams): Promise<ResumeDetail> {
  return requestJson<ResumeDetail>("/api/v1/resumes/generate", {
    body: JSON.stringify({
      student_profile_id: params.studentProfileId,
      target_job: params.targetJob,
      style: "campus",
      persist: true
    }),
    method: "POST"
  });
}

export async function updateResume(resumeId: number, payload: { summary: string; skills: string[] }): Promise<ResumeDetail> {
  return requestJson<ResumeDetail>(`/api/v1/resumes/${resumeId}`, {
    body: JSON.stringify(payload),
    method: "PUT"
  });
}

export async function downloadResume(resumeId: number, format: ResumeExportFormat): Promise<{ blob: Blob; filename: string }> {
  const token = getAuthToken();
  const response = await fetch(`${apiBaseUrl}/api/v1/resumes/${resumeId}/export?format=${format}`, {
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    }
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, `Export failed with status ${response.status}`));
  }

  return {
    blob: await response.blob(),
    filename: parseFilename(response.headers.get("content-disposition"), `resume-${resumeId}.${format}`)
  };
}
