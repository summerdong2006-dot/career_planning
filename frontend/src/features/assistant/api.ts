import { repairMojibakeValue } from "../../shared/encoding";
import { requestJson } from "../../shared/http";

import type { AssistantChatRequest, AssistantChatResponse } from "./types";

export async function chatWithAssistant(payload: AssistantChatRequest): Promise<AssistantChatResponse> {
  const result = await requestJson<AssistantChatResponse>("/api/v1/assistant/chat", {
    body: JSON.stringify(payload),
    method: "POST"
  });
  return repairMojibakeValue(result);
}
