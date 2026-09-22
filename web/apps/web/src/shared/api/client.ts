import { apiBaseUrl } from "../config/env";

export async function getJson(path: string, init?: RequestInit): Promise<unknown> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    method: "GET",
  });

  if (!response.ok) {
    throw new Error(
      "API request failed with status " + String(response.status),
    );
  }

  return response.json();
}
