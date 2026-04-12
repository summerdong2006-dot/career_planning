export type AuthUser = {
  id: number;
  email: string;
  display_name: string;
  created_at: string | null;
};

export type AuthSessionResponse = {
  token: string;
  user: AuthUser;
};

export type AuthProfileUpdatePayload = {
  email?: string;
  displayName?: string;
  currentPassword?: string;
  newPassword?: string;
};
