import { describe, expect, it } from "vitest";

import { decodeCandidateInterviewPage } from "./decoders";

const response = {
  items: [
    {
      id: "interview-1",
      jobDescription: { id: "jd-1", title: "Platform Engineer" },
      scheduledAt: "2026-08-11T09:00:00Z",
      status: "SCHEDULED"
    }
  ],
  page: 1,
  pageSize: 25,
  totalItems: 1,
  totalPages: 1
};

describe("candidate interview decoder", () => {
  it("accepts the minimum projection and rejects malformed data", () => {
    expect(decodeCandidateInterviewPage(response)).toEqual(response);
    for (const value of [
      null,
      { ...response, items: {} },
      { ...response, items: [{ ...response.items[0], status: "SECRET" }] },
      { ...response, items: [{ ...response.items[0], jobDescription: { id: "jd-1" } }] },
      { ...response, page: 0 },
      { ...response, page: "one" },
      { ...response, totalItems: -1 },
      { ...response, totalPages: "one" }
    ]) {
      expect(() => decodeCandidateInterviewPage(value)).toThrow();
    }
  });
});
