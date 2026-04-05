import { useEffect, useState } from "react";

type LoginRoute = {
  name: "login";
};

type DashboardRoute = {
  name: "dashboard";
};

type StudentProfileRoute = {
  name: "student-profile";
};

type ReportGenerateRoute = {
  name: "report-generate";
  studentProfileId?: number;
};

type ReportDetailRoute = {
  name: "report-detail";
  reportId: number;
};

type JobRecommendationRoute = {
  name: "job-recommendation";
  studentProfileId?: number;
};

type ResumeGenerateRoute = {
  name: "resume-generate";
  studentProfileId?: number;
};

type JobGraphRoute = {
  name: "job-graph";
};

export type AppRoute =
  | LoginRoute
  | DashboardRoute
  | StudentProfileRoute
  | ReportGenerateRoute
  | ReportDetailRoute
  | JobRecommendationRoute
  | ResumeGenerateRoute
  | JobGraphRoute;

function parseStudentProfileId(search: string): number | undefined {
  const value = new URLSearchParams(search).get("studentProfileId");
  const parsed = Number(value);

  if (!value || !Number.isInteger(parsed) || parsed <= 0) {
    return undefined;
  }

  return parsed;
}

function buildPathWithStudentProfile(path: string, studentProfileId?: number): string {
  if (!studentProfileId) {
    return path;
  }

  const search = new URLSearchParams({ studentProfileId: String(studentProfileId) });
  return `${path}?${search.toString()}`;
}

function parseRoute(pathname: string, search: string): AppRoute {
  const normalizedPath = pathname.replace(/\/+$/, "") || "/";
  const studentProfileId = parseStudentProfileId(search);
  const detailMatch = normalizedPath.match(/^\/reports\/(\d+)$/);

  if (normalizedPath === "/login") {
    return { name: "login" };
  }

  if (normalizedPath === "/" || normalizedPath === "/dashboard") {
    return { name: "dashboard" };
  }

  if (detailMatch) {
    return {
      name: "report-detail",
      reportId: Number(detailMatch[1])
    };
  }

  if (normalizedPath === "/reports") {
    return {
      name: "report-generate",
      studentProfileId
    };
  }

  if (normalizedPath === "/recommendations") {
    return {
      name: "job-recommendation",
      studentProfileId
    };
  }

  if (normalizedPath === "/resumes") {
    return {
      name: "resume-generate",
      studentProfileId
    };
  }

  if (normalizedPath === "/job-graph") {
    return { name: "job-graph" };
  }

  if (normalizedPath === "/profiles/new") {
    return { name: "student-profile" };
  }

  return { name: "dashboard" };
}

export function buildLoginPath(): string {
  return "/login";
}

export function buildDashboardPath(): string {
  return "/dashboard";
}

export function buildStudentProfilePath(): string {
  return "/profiles/new";
}

export function buildReportPath(reportId: number): string {
  return `/reports/${reportId}`;
}

export function buildReportGeneratePath(studentProfileId?: number): string {
  return buildPathWithStudentProfile("/reports", studentProfileId);
}

export function buildJobRecommendationPath(studentProfileId?: number): string {
  return buildPathWithStudentProfile("/recommendations", studentProfileId);
}

export function buildResumeGeneratePath(studentProfileId?: number): string {
  return buildPathWithStudentProfile("/resumes", studentProfileId);
}

export function buildJobGraphPath(): string {
  return "/job-graph";
}

export function useAppRouter() {
  const [route, setRoute] = useState<AppRoute>(() => parseRoute(window.location.pathname, window.location.search));

  useEffect(() => {
    const handlePopState = () => {
      setRoute(parseRoute(window.location.pathname, window.location.search));
    };

    window.addEventListener("popstate", handlePopState);
    return () => {
      window.removeEventListener("popstate", handlePopState);
    };
  }, []);

  const navigate = (path: string) => {
    const currentPath = `${window.location.pathname}${window.location.search}`;

    if (currentPath === path) {
      setRoute(parseRoute(window.location.pathname, window.location.search));
      return;
    }

    window.history.pushState({}, "", path);
    setRoute(parseRoute(window.location.pathname, window.location.search));
  };

  return {
    route,
    navigate
  };
}
