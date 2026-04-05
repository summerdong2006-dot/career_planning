export type MatchDimensionScores = {
  base_requirement: number;
  skill: number;
  soft_skill: number;
  growth: number;
};

export type JobRequirementSnapshot = {
  must_have_skills: string[];
  certificates: string[];
  innovation_requirement: number;
  learning_requirement: number;
  stress_tolerance_requirement: number;
  communication_requirement: number;
  internship_requirement: number;
  promotion_path: string[];
};

export type StudentCapabilitySnapshot = {
  professional_skills: string[];
  certificates: string[];
  innovation_score: number;
  learning_score: number;
  stress_tolerance_score: number;
  communication_score: number;
  internship_score: number;
  completeness_score: number;
  competitiveness_score: number;
};

export type JobMatchResult = {
  match_id: number | null;
  job_id: number;
  job_profile_id: number;
  job_title: string;
  total_score: number;
  reason: string;
  gap_analysis: string[];
  evidence: string[];
  risk_flags: string[];
  dimension_scores: MatchDimensionScores;
  job_requirement_snapshot: JobRequirementSnapshot;
  student_capability_snapshot: StudentCapabilitySnapshot;
};

export type MatchingRecommendResponse = {
  student_profile_id: number;
  top_k: number;
  matches: JobMatchResult[];
};
