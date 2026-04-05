import { apiBaseUrl, requestJson } from "../../shared/http";
import { repairMojibakeValue } from "../../shared/encoding";

import type { StudentProfileBuildResult } from "./types";

const studentProfilesBaseUrl = `${apiBaseUrl}/api/v1/student-profiles`;

type BuildStudentProfileParams = {
  studentId: string;
  resumeText: string;
  persist?: boolean;
};

export async function buildStudentProfile(params: BuildStudentProfileParams): Promise<StudentProfileBuildResult> {
  const result = await requestJson<StudentProfileBuildResult>(`${studentProfilesBaseUrl}/build`, {
    body: JSON.stringify({
      persist: params.persist ?? true,
      source: {
        student_id: params.studentId,
        resume_text: params.resumeText,
        manual_form: {},
        supplement_text: "",
        basic_info: {}
      }
    }),
    method: "POST"
  });
  return repairMojibakeValue(result);
}
