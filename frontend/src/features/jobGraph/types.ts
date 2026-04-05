export type JobGraphNode = {
  job_id: number | string;
  job_profile_id: number | null;
  job_title: string;
  job_level: string;
};

export type JobGraphEdge = {
  source_job_id: number | string;
  target_job_id: number | string;
  type: string;
  weight: number;
};

export type RepresentativeJobCard = {
  job_id: number;
  job_profile_id: number;
  job_title: string;
  job_level: string;
  summary: string;
  must_have_skills: string[];
  certificates: string[];
  promotion_path: string[];
  career_paths: string[][];
};

export type JobGraphOverviewResponse = {
  representative_jobs: RepresentativeJobCard[];
  graph: {
    nodes: JobGraphNode[];
    edges: JobGraphEdge[];
  };
};
