export function getApiBaseUrl(rawUrl: string | undefined): string {
  return (rawUrl ?? "http://localhost:8000").replace(/\/$/, "");
}

export const apiBaseUrl = getApiBaseUrl(import.meta.env.VITE_API_URL);
