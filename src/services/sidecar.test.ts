import { describe, expect, it } from "vitest";
import { sidecarErrorMessage } from "./sidecar";

describe("sidecar error handling", () => {
  it("shows JSON stderr error messages from the Python sidecar", () => {
    expect(sidecarErrorMessage('{"error":"文件格式不支持"}', "分析失败")).toBe("文件格式不支持");
  });

  it("shows Tauri shell permission errors instead of a generic fallback", () => {
    expect(sidecarErrorMessage("not allowed to execute sidecar", "分析失败")).toBe("not allowed to execute sidecar");
  });
});
