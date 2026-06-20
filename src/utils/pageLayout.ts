import type { PageAnalysis } from "../types";

export function pageAspectRatio(page?: Pick<PageAnalysis, "width" | "height"> | null): string {
  const width = Number(page?.width ?? 0);
  const height = Number(page?.height ?? 0);
  if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) {
    return "0.707";
  }
  return `${width} / ${height}`;
}
