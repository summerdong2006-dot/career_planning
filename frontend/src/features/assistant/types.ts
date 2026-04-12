export type AssistantMessageRole = "user" | "assistant";

export type AssistantMessage = {
  role: AssistantMessageRole;
  content: string;
};

export type AssistantPageContext = {
  page_name: string;
  page_label?: string;
  student_profile_id?: number;
  report_id?: number;
  resume_id?: number;
  notes?: string;
};

export type AssistantChatRequest = {
  messages: AssistantMessage[];
  context?: AssistantPageContext;
};

export type AssistantChatResponse = {
  reply: string;
  provider: string;
  model: string;
  used_context: boolean;
};
