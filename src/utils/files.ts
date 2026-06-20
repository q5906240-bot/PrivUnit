import { ALLOWED_EXTENSIONS, MAX_UPLOAD_BYTES } from "../constants";
import type { Locale } from "../i18n";

export function getExtension(pathOrName: string): string {
  const extension = pathOrName.split(".").pop()?.toLowerCase() ?? "";
  return extension === "ipg" ? "jpg" : extension;
}

export function validateFileLike(name: string, size: number, locale: Locale = "zh-CN"): string | null {
  const rawExtension = name.split(".").pop()?.toLowerCase() ?? "";
  if (!ALLOWED_EXTENSIONS.has(rawExtension)) {
    return locale === "en" ? "Only PDF, JPG, JPEG, and PNG files are allowed" : "仅允许上传 PDF、JPG、JPEG、PNG 格式文件";
  }
  if (size > MAX_UPLOAD_BYTES) {
    return locale === "en" ? "Each file must be 4 MiB or smaller" : "单个文件不超过 4MiB";
  }
  return null;
}

export function makeFileId(path: string, index: number): string {
  let hash = 0;
  for (const char of path) {
    hash = (hash << 5) - hash + char.charCodeAt(0);
    hash |= 0;
  }
  return `file-${index + 1}-${Math.abs(hash)}`;
}
