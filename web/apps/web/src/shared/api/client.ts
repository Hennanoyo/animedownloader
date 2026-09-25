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

export async function requestJson(
  path: string,
  init: RequestInit = {},
): Promise<unknown> {
  let response: Response;

  try {
    response = await fetch(apiBaseUrl + path, init);
  } catch (error) {
    if (error instanceof Error) {
      throw new Error("Network request failed: " + error.message, {
        cause: error,
      });
    }
    throw new Error("Network request failed");
  }

  if (!response.ok) {
    const responseBody = await response.text();
    const detail = extractErrorDetail(responseBody);
    throw new ApiRequestError(
      detail
        ? "API request failed with status " +
            response.status +
            ": " +
            detail
        : "API request failed with status " + response.status,
      response.status,
      responseBody,
    );
  }

  if (response.status === 204) {
    return undefined;
  }

  return response.json();
}

export function getJson(
  path: string,
  init?: Omit<RequestInit, "method" | "body">,
): Promise<unknown> {
  return requestJson(path, { ...init, method: "GET" });
}

export function postJson(
  path: string,
  body: unknown,
  init?: Omit<RequestInit, "method" | "body">,
): Promise<unknown> {
  return requestJson(path, {
    ...init,
    method: "POST",
    headers: jsonHeaders(init?.headers),
    body: JSON.stringify(body),
  });
}

export function patchJson(
  path: string,
  body: unknown,
  init?: Omit<RequestInit, "method" | "body">,
): Promise<unknown> {
  return requestJson(path, {
    ...init,
    method: "PATCH",
    headers: jsonHeaders(init?.headers),
    body: JSON.stringify(body),
  });
}

export async function deleteJson(
  path: string,
  init?: Omit<RequestInit, "method" | "body">,
): Promise<void> {
  await requestJson(path, { ...init, method: "DELETE" });
}

function jsonHeaders(headers?: HeadersInit): Headers {
  const result = new Headers(headers);
  if (!result.has("Content-Type")) {
    result.set("Content-Type", "application/json");
  }
  return result;
}

function formatFastApiLocation(value: unknown): string {
  if (!Array.isArray(value)) return "";

  const segments = value
    .filter(
      (segment): segment is string | number =>
        typeof segment === "string" || typeof segment === "number",
    )
    .map((segment) =>
      typeof segment === "number" ? "[" + (segment + 1) + "]" : segment,
    );

  let path = "";
  for (const segment of segments) {
    if (typeof segment === "number") {
      path += "[" + segment + "]";
    } else {
      path = path ? path + "." + segment : segment;
    }
  }
  return path;
}

function extractErrorDetail(responseBody: string): string | null {
  try {
    const payload: unknown = JSON.parse(responseBody);

    if (
      typeof payload === "object" &&
      payload !== null &&
      "detail" in payload
    ) {
      const detail = payload.detail;

      if (typeof detail === "string") {
        return detail;
      }

      if (Array.isArray(detail)) {
        const messages = detail.flatMap((issue) => {
          if (typeof issue !== "object" || issue === null) return [];

          const message =
            "msg" in issue && typeof issue.msg === "string"
              ? issue.msg
              : null;
          if (!message) return [];

          const location =
            "loc" in issue ? formatFastApiLocation(issue.loc) : "";

          return [location ? location + ": " + message : message];
        });

        return messages.length > 0 ? Array.from(new Set(messages)).join("; ") : null;
      }
    }
  } catch {
    return responseBody.trim() || null;
  }

  return responseBody.trim() || null;
}
