import { describe, expect, it, vi } from "vitest";

import {
  createManualJobDescription,
  fetchManagerJobDescriptions,
  uploadJobDescription
} from "./api";

const item = {
  id: "jd-1",
  title: "Platform Engineer",
  sourceType: "MANUAL",
  sourceFormat: null,
  createdAt: "2026-08-10T09:00:00Z"
};

describe("manager JD API", () => {
  it("decodes list, manual, and multipart responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn<typeof fetch>()
        .mockResolvedValueOnce(
          Response.json({ items: [item], page: 1, pageSize: 25, totalItems: 1, totalPages: 1 })
        )
        .mockResolvedValueOnce(Response.json(item))
        .mockResolvedValueOnce(
          Response.json({ ...item, sourceType: "UPLOAD", sourceFormat: "TXT" })
        )
    );
    expect((await fetchManagerJobDescriptions()).items).toHaveLength(1);
    expect((await createManualJobDescription("Title", "Content")).sourceType).toBe("MANUAL");
    expect(
      (await uploadJobDescription("Title", new File(["text"], "role.txt"))).sourceFormat
    ).toBe("TXT");
    expect(vi.mocked(fetch).mock.calls[2]?.[1]?.body).toBeInstanceOf(FormData);
  });

  it("fails closed on unsuccessful responses", async () => {
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 500 })));
    await expect(fetchManagerJobDescriptions()).rejects.toThrow("Request failed");
  });
});
