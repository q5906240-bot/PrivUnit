export const MAX_UPLOAD_BYTES = 4 * 1024 * 1024;
export const ALLOWED_EXTENSIONS = new Set(["pdf", "jpg", "jpeg", "png", "ipg"]);

export const REDACTION_COLORS = [
  "#2563eb",
  "#dc2626",
  "#059669",
  "#d97706",
  "#7c3aed",
  "#0f766e",
] as const;

export const DEFAULT_EXPORT_COLOR = REDACTION_COLORS[0];
