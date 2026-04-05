export type ResumeBasicInfo = {
  student_name: string;
  student_id: string;
  school: string;
  major: string;
  education: string;
  grade: string;
};

export type ResumeJobIntention = {
  target_job: string;
  target_city: string;
  style: string;
};

export type ResumeEducationEntry = {
  school: string;
  major: string;
  education: string;
  grade: string;
  highlights: string[];
};

export type ResumeProjectEntry = {
  name: string;
  role: string;
  highlights: string[];
  tech_stack: string[];
};

export type ResumeInternshipEntry = {
  company: string;
  role: string;
  duration: string;
  highlights: string[];
};

export type ResumeContent = {
  basic_info: ResumeBasicInfo;
  job_intention: ResumeJobIntention;
  summary: string;
  education: ResumeEducationEntry[];
  skills: string[];
  projects: ResumeProjectEntry[];
  internships: ResumeInternshipEntry[];
  extras: string[];
};

export type ResumeDetail = {
  resume_id: number;
  student_profile_id: number;
  student_id: string;
  target_job: string;
  style: string;
  content: ResumeContent;
  markdown_content: string;
  html_content: string;
  created_at: string | null;
};

export type ResumeExportFormat = "markdown" | "html" | "json";
