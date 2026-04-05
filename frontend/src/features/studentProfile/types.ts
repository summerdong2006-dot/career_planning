export type StudentProject = {
  name: string;
  role: string;
  description: string;
};

export type StudentInternship = {
  company: string;
  role: string;
  description: string;
};

export type StudentProfilePayload = {
  student_name: string;
  career_intention: string;
  skills: string[];
  projects: StudentProject[];
  internships: StudentInternship[];
  completeness_score: number;
  competitiveness_score: number;
  summary: string;
};

export type StudentProfileBuildResult = {
  student_id: string;
  profile_version: number;
  persisted: boolean;
  profile: StudentProfilePayload;
  record_refs: {
    profile_id: number | null;
    resume_id: number | null;
  };
  created_at: string | null;
  raw_profile_payload: Record<string, unknown>;
};
