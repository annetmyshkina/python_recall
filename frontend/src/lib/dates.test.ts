import { describe, expect, it } from "vitest";

import { formatDate, formatDateTime } from "./dates";

describe("date formatting", () => {
  it("returns a neutral placeholder for missing or invalid values", () => {
    expect(formatDate(null)).toBe("—");
    expect(formatDateTime("not-a-date")).toBe("—");
  });

  it("formats a valid instant for the browser locale", () => {
    const formatted = formatDate(new Date(2026, 10, 7, 10, 0));

    expect(formatted).toContain("2026");
    expect(formatted).toContain("7");
  });
});
