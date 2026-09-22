export function getApiBaseUrl(rawUrl: string | undefined): string {
  return (rawUrl ?? "http://localhost:8000").replace(/\/$/, "");
}

export async function fetchHealth(apiBaseUrl: string): Promise<string> {
  const response = await fetch(`${apiBaseUrl}/api/health`);

  if (!response.ok) {
    throw new Error(`Health request failed with status ${response.status}`);
  }

  const payload: unknown = await response.json();

  if (
    typeof payload !== "object" ||
    payload === null ||
    !("status" in payload) ||
    payload.status !== "ok"
  ) {
    throw new Error("Unexpected health response");
  }

  return "ok";
}
