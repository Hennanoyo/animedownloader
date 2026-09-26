import { z } from "zod";

export function formatZodIssues(issues: z.core.$ZodIssue[]): string {
  return issues
    .map((issue) => {
      const path = issue.path
        .map((segment) =>
          typeof segment === "number"
            ? "[" + (segment + 1) + "]"
            : String(segment),
        )
        .reduce((result, segment) => {
          if (segment.startsWith("[")) return result + segment;
          return result ? result + "." + segment : segment;
        }, "");

      return path ? path + ": " + issue.message : issue.message;
    })
    .join("; ");
}
