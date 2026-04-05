export type ExportFormat = "markdown" | "html" | "json" | "pdf";
export type DemoExportFormat = Exclude<ExportFormat, "markdown">;

export type ReportActionItem = {
  action_id: string;
  title: string;
  description: string;
  timeline: string;
  priority: string;
  success_metric: string;
  related_gap: string;
};

export type ReportEditorSection = {
  section_key: string;
  title: string;
  content: string;
};

export type CareerRecommendation = {
  match_id: number | null;
  job_id: number;
  job_profile_id: number;
  job_title: string;
  category: string;
  total_score: number;
  recommendation_reason: string;
  matched_skills: string[];
  missing_skills: string[];
  gap_analysis: string[];
  risk_flags: string[];
};

export type CareerReportSection = {
  key: string;
  title: string;
  content: string;
};

export type ReportMeta = {
  student_id: string;
  target_job: string;
  generated_at: string;
};

export type ReportCompletenessCheck = {
  score: number;
  is_complete: boolean;
  missing_sections: string[];
  warnings: string[];
};

export type ReportSectionPutRequest = {
  title?: string;
  content?: string;
};

export type CareerReportDetail = {
  report_id: number;
  student_profile_id: number;
  report_version: number;
  report_title: string;
  status: string;
  markdown_content: string;
  html_content: string;
  created_at: string | null;
  updated_at: string | null;
  completeness_check: ReportCompletenessCheck;
  content: {
    meta: ReportMeta;
    sections: CareerReportSection[];
  };
  recommendations: CareerRecommendation[];
  suggested_actions: ReportActionItem[];
  editor_state: {
    report_title: string;
    sections: ReportEditorSection[];
    supported_export_formats: ExportFormat[];
  };
};
