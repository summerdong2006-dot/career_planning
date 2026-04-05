import { getAuthToken } from "../../shared/authStorage";
import { repairMojibakeValue } from "../../shared/encoding";
import { apiBaseUrl, getErrorMessage, requestJson } from "../../shared/http";

import type { CareerReportDetail, DemoExportFormat, ReportSectionPutRequest } from "./types";

const reportsBaseUrl = `${apiBaseUrl}/api/v1/reports`;

type GenerateReportParams = {
  studentProfileId: number;
  topK: number;
  reportTitle?: string;
};

type ExportResult = {
  blob: Blob;
  filename: string;
};

function parseFilename(contentDisposition: string | null, fallback: string): string {
  if (!contentDisposition) {
    return fallback;
  }

  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1]);
  }

  const basicMatch = contentDisposition.match(/filename="?([^";]+)"?/i);
  return basicMatch?.[1] ?? fallback;
}

export async function generateReport(params: GenerateReportParams): Promise<CareerReportDetail> {
  const result = await requestJson<CareerReportDetail>(`${reportsBaseUrl}/generate`, {
    body: JSON.stringify({
      persist: true,
      persist_matches: true,
      report_title: params.reportTitle,
      student_profile_id: params.studentProfileId,
      top_k: params.topK
    }),
    method: "POST"
  });
  return repairMojibakeValue(result);
}

export async function getReportDetail(reportId: number): Promise<CareerReportDetail> {
  const result = await requestJson<CareerReportDetail>(`${reportsBaseUrl}/${reportId}`);
  return repairMojibakeValue(result);
}

export async function getLatestReport(studentProfileId: number): Promise<CareerReportDetail> {
  const result = await requestJson<CareerReportDetail>(`${reportsBaseUrl}/student/${studentProfileId}/latest`);
  return repairMojibakeValue(result);
}

export async function updateReportSection(
  reportId: number,
  sectionKey: string,
  payload: ReportSectionPutRequest
): Promise<CareerReportDetail> {
  const result = await requestJson<CareerReportDetail>(`${reportsBaseUrl}/${reportId}/sections/${sectionKey}`, {
    body: JSON.stringify(payload),
    method: "PUT"
  });
  return repairMojibakeValue(result);
}

export async function downloadReport(reportId: number, format: DemoExportFormat): Promise<ExportResult> {
  const token = getAuthToken();
  const response = await fetch(`${reportsBaseUrl}/${reportId}/export?format=${format}`, {
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    }
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, `Export failed with status ${response.status}`));
  }

  return {
    blob: await response.blob(),
    filename: parseFilename(response.headers.get("content-disposition"), `career-report-${reportId}.${format}`)
  };
}
