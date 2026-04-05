import { requestJson } from "../../shared/http";

import type { WorkspaceOverview } from "./types";

export async function getWorkspaceOverview(): Promise<WorkspaceOverview> {
  return requestJson<WorkspaceOverview>("/api/v1/portal/workspace");
}
