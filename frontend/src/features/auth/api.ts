import { requestJson } from "../../shared/http";

import type { AuthSessionResponse, AuthUser } from "./types";

type AuthPayload = {
  email: string;
  password: string;
};

type RegisterPayload = AuthPayload & {
  displayName: string;
};

export async function registerAccount(payload: RegisterPayload): Promise<AuthSessionResponse> {
  return requestJson<AuthSessionResponse>("/api/v1/auth/register", {
    body: JSON.stringify({
      email: payload.email,
      display_name: payload.displayName,
      password: payload.password
    }),
    method: "POST"
  });
}

export async function loginAccount(payload: AuthPayload): Promise<AuthSessionResponse> {
  return requestJson<AuthSessionResponse>("/api/v1/auth/login", {
    body: JSON.stringify(payload),
    method: "POST"
  });
}

export async function getCurrentUser(): Promise<AuthUser> {
  return requestJson<AuthUser>("/api/v1/auth/me");
}

export async function logoutAccount(): Promise<void> {
  await requestJson<{ ok: boolean }>("/api/v1/auth/logout", {
    method: "POST"
  });
}
