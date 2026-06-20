import { describe, expect, it } from "vitest";
import { getExtension, validateFileLike } from "./files";

describe("file helpers", () => {
  it("normalizes ipg as jpg", () => {
    expect(getExtension("scan.ipg")).toBe("jpg");
  });

  it("allows only supported upload formats", () => {
    expect(validateFileLike("paper.pdf", 1024)).toBeNull();
    expect(validateFileLike("paper.docx", 1024)).toContain("仅允许上传");
  });

  it("rejects files larger than 4 MiB", () => {
    expect(validateFileLike("paper.png", 4 * 1024 * 1024 + 1)).toContain("不超过 4MiB");
  });

  it("returns English validation messages when requested", () => {
    expect(validateFileLike("paper.docx", 1024, "en")).toContain("Only PDF");
    expect(validateFileLike("paper.png", 4 * 1024 * 1024 + 1, "en")).toContain("4 MiB");
  });
});
