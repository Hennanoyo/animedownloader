import { apiBaseUrl } from "../config/env";

export class ApiRequestError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly responseBody: string,
  ) {
    super(message);
    this.name = "ApiRequestError";
  }
}

export async function getJson(path: string, init?: RequestInit): Promise<unknown> {
  let response: Response;

  try {
    response = await fetch(`${apiBaseUrl}${path}`, {
      ...init,
      method: "GET",
    });
  } catch (error) {
    if (error instanceof Error) {
      throw new Error(`Network request failed: ${error.message}`, { cause: error });
    }
    throw new Error("Network request failed");
  }

  if (!response.ok) {
    const responseBody = await response.text();
    const detail = extractErrorDetail(responseBody);
    throw new ApiRequestError(
      detail
        ? `API request failed with status ${response.status}: ${detail}`
        : `API request failed with status ${response.status}`,
      response.status,
      responseBody,
    );
  }

  return response.json();
}

function extractErrorDetail(responseBody: string): string | null {
  try {
    const payload: unknown = JSON.parse(responseBody);

    if (
      typeof payload === "object" &&
      payload !== null &&
      "detail" in payload &&
      typeof payload.detail === "string"
    ) {
      return payload.detail;
    }
  } catch {
    return responseBody.trim() || null;
  }

  return null;
}
