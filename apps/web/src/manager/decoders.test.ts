import { describe, expect, it } from "vitest";

import {
  decodeManagerCandidatePage,
  decodeManagerInterviewPage,
  decodeManagerJobDescriptionPage
} from "./decoders";

const page = {
  items: [
    {
      id: "jd-1",
      title: "Platform Engineer",
      sourceType: "UPLOAD",
      sourceFormat: "PDF",
      createdAt: "2026-08-10T09:00:00Z"
    }
  ],
  page: 1,
  pageSize: 25,
  totalItems: 1,
  totalPages: 1
};

describe("manager JD decoder", () => {
  it("accepts minimum pages and rejects malformed projections", () => {
    expect(decodeManagerJobDescriptionPage(page)).toEqual(page);
    for (const value of [
      null,
      { ...page, items: {} },
      { ...page, items: [{ ...page.items[0], sourceType: "SECRET" }] },
      { ...page, items: [{ ...page.items[0], sourceFormat: "EXE" }] },
      { ...page, items: [{ ...page.items[0], title: "" }] },
      { ...page, totalItems: -1 }
    ]) {
      expect(() => decodeManagerJobDescriptionPage(value)).toThrow();
    }
  });
});

describe("manager scheduling decoders", () => {
  it("accepts candidate and interview pages and rejects malformed nested data", () => {
    const candidate = { id: "candidate-1", displayName: "Ada", email: "ada@example.test" };
    const candidates = { items: [candidate], page: 1, pageSize: 25, totalItems: 1, totalPages: 1 };
    const interviews = {
      items: [{
        id: "interview-1",
        candidate,
        jobDescription: { id: "jd-1", title: "Engineer" },
        scheduledAt: "2026-08-11T09:00:00Z",
        status: "SCHEDULED"
      }],
      page: 1,
      pageSize: 25,
      totalItems: 1,
      totalPages: 1
    };
    expect(decodeManagerCandidatePage(candidates)).toEqual(candidates);
    expect(decodeManagerInterviewPage(interviews)).toEqual(interviews);
    expect(() => decodeManagerCandidatePage({ ...candidates, items: {} })).toThrow();
    expect(() => decodeManagerInterviewPage({ ...interviews, items: {} })).toThrow();
    expect(() => decodeManagerCandidatePage({
      ...candidates, items: [{ ...candidate, email: "" }]
    })).toThrow();
    for (const value of [
      { ...interviews, items: [{ ...interviews.items[0], status: "SECRET" }] },
      { ...interviews, items: [{ ...interviews.items[0], jobDescription: null }] }
    ]) expect(() => decodeManagerInterviewPage(value)).toThrow();
  });
});
