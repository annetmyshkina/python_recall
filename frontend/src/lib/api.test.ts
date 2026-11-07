import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { server } from "../test/server";
import type { components } from "../types/api.generated";
import { ApiError, apiRequest } from "./api";

type CategoryPage = components["schemas"]["CategoryPage"];

async function expectApiError(
  request: Promise<unknown>,
  expected: { code: string; status: number },
) {
  try {
    await request;
    throw new Error("Expected the API request to fail");
  } catch (error) {
    expect(error).toBeInstanceOf(ApiError);
    if (!(error instanceof ApiError)) {
      throw error;
    }
    expect(error.code).toBe(expected.code);
    expect(error.status).toBe(expected.status);
  }
}

describe("apiRequest", () => {
  it("sends query parameters and returns JSON", async () => {
    server.use(
      http.get("http://localhost/api/v1/categories", ({ request }) => {
        const url = new URL(request.url);
        expect(url.searchParams.get("page")).toBe("2");
        expect(url.searchParams.getAll("tag")).toEqual(["python", "async"]);

        return HttpResponse.json({
          items: [],
          pagination: { page: 2, limit: 20, total: 0, pages: 0 },
        });
      }),
    );

    const result = await apiRequest<CategoryPage>("/categories", {
      query: { page: 2, tag: ["python", "async"], ignored: undefined },
    });

    expect(result.pagination.page).toBe(2);
  });

  it("supports successful responses without a body", async () => {
    server.use(
      http.delete("http://localhost/api/v1/categories/category-id", () => {
        return new HttpResponse(null, { status: 204 });
      }),
    );

    await expect(
      apiRequest<void>("/categories/category-id", { method: "DELETE" }),
    ).resolves.toBeUndefined();
  });

  it("keeps stable Problem Details fields", async () => {
    server.use(
      http.post("http://localhost/api/v1/categories", () => {
        return HttpResponse.json(
          {
            type: "urn:python-recall:error:duplicate-resource",
            title: "Resource already exists",
            status: 409,
            detail: "A category with this name already exists.",
            instance: "/api/v1/categories",
            code: "duplicate_resource",
            trace_id: "trace-id",
            errors: [],
          },
          {
            status: 409,
            headers: { "Content-Type": "application/problem+json" },
          },
        );
      }),
    );

    const request = apiRequest("/categories", {
      method: "POST",
      body: { name: "Python" },
    });

    await expectApiError(request, {
      code: "duplicate_resource",
      status: 409,
    });
  });

  it("normalizes network failures", async () => {
    server.use(
      http.get("http://localhost/api/v1/categories", () => {
        return HttpResponse.error();
      }),
    );

    await expectApiError(apiRequest("/categories"), {
      code: "network_error",
      status: 0,
    });
  });
});
