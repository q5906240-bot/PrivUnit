import { describe, expect, it } from "vitest";
import { pageAspectRatio } from "./pageLayout";

describe("page layout helpers", () => {
  it("uses real landscape page dimensions for preview aspect ratio", () => {
    expect(pageAspectRatio({ width: 1200, height: 800 })).toBe("1200 / 800");
  });

  it("falls back to portrait ratio before analysis is available", () => {
    expect(pageAspectRatio(null)).toBe("0.707");
  });
});
