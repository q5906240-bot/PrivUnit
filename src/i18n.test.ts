import { describe, expect, it } from "vitest";
import { UI_TEXT } from "./i18n";

describe("brand labels", () => {
  it("uses the PrivUnit product name in Chinese and English", () => {
    expect(UI_TEXT["zh-CN"].appName).toBe("私元处理");
    expect(UI_TEXT.en.appName).toBe("PrivUnit");
  });
});
