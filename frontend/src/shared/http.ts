import { getAuthToken } from "./authStorage";

const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();
const apiBaseUrl = (configuredApiBaseUrl || "http://localhost:8000").replace(/\/+$/, "");

async function getErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const errorPayload = (await response.json()) as {
      detail?: string;
      message?: string;
      details?: string[] | null;
    };
    if (Array.isArray(errorPayload.details) && errorPayload.details.length > 0) {
      return `${errorPayload.message ?? fallback}: ${errorPayload.details.join("; ")}`;
    }
    return errorPayload.detail ?? errorPayload.message ?? fallback;
  } catch {
    const text = await response.text();
    return text || fallback;
  }
}

export async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const token = getAuthToken();
  const targetUrl = url.startsWith("http") ? url : `${apiBaseUrl}${url.startsWith("/") ? url : `/${url}`}`;
  const response = await fetch(targetUrl, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {})
    }
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, `Request failed with status ${response.status}`));
  }

  return (await response.json()) as T;
}

export { apiBaseUrl, getErrorMessage };
