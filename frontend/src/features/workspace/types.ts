import type { AuthUser } from "../auth/types";

export type StudentWorkspaceSummary = {
  profile_id: number;
  student_id: string;
  profile_version: number;
  summary: string;
  career_intention: string;
  ability_scores: Record<string, number>;
  completeness_score: number;
  competitiveness_score: number;
  updated_at: string | null;
};

export type ReportWorkspaceSummary = {
  report_id: number;
  student_profile_id: number;
  report_title: string;
  status: string;
  updated_at: string | null;
};

export type ResumeWorkspaceSummary = {
  resume_id: number;
  student_profile_id: number;
  target_job: string;
  style: string;
  created_at: string | null;
};

export type WorkspaceOverview = {
  user: AuthUser;
  student_profiles: StudentWorkspaceSummary[];
  reports: ReportWorkspaceSummary[];
  resumes: ResumeWorkspaceSummary[];
};
