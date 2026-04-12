const AVATAR_KEY_PREFIX = "career_planning_avatar:";

export function getStoredAvatar(userId: number): string | null {
  return window.localStorage.getItem(`${AVATAR_KEY_PREFIX}${userId}`);
}

export function setStoredAvatar(userId: number, dataUrl: string): void {
  window.localStorage.setItem(`${AVATAR_KEY_PREFIX}${userId}`, dataUrl);
}

export function clearStoredAvatar(userId: number): void {
  window.localStorage.removeItem(`${AVATAR_KEY_PREFIX}${userId}`);
}
