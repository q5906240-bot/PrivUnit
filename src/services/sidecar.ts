import { Command } from "@tauri-apps/plugin-shell";
import { isTauri } from "@tauri-apps/api/core";
import { UI_TEXT, type Locale } from "../i18n";
import type { Candidate, FileAnalysis } from "../types";

const SIDECAR_NAME = "binaries/redactor-sidecar";

export interface AnalyzeInput {
  path: string;
  fileId: string;
  materialType: "social" | "other";
  personName: string;
  employerTerms: string[];
  locale?: Locale;
}

export interface ExportInput {
  sourcePath: string;
  outputPath: string;
  candidates: Candidate[];
  locale?: Locale;
}

export async function analyzeWithSidecar(input: AnalyzeInput): Promise<FileAnalysis> {
  if (!isTauri()) {
    return mockAnalysis(input);
  }

  const args = [
    "analyze",
    "--file",
    input.path,
    "--file-id",
    input.fileId,
    "--person-name",
    input.personName,
    "--material-type",
    input.materialType,
    ...input.employerTerms.flatMap((term) => ["--employer-term", term]),
  ];
  const fallback = UI_TEXT[input.locale ?? "zh-CN"].analysisFailed;
  const output = await executeSidecar(args, fallback);
  if (output.code !== 0) {
    throw new Error(sidecarErrorMessage(output.stderr, fallback));
  }
  return JSON.parse(output.stdout) as FileAnalysis;
}

export async function exportWithSidecar(input: ExportInput): Promise<string> {
  if (!isTauri()) {
    return input.outputPath;
  }

  const fallback = UI_TEXT[input.locale ?? "zh-CN"].exportFailed;
  const output = await executeSidecar(
    [
    "export-json",
    JSON.stringify({
      sourcePath: input.sourcePath,
      outputPath: input.outputPath,
      candidates: input.candidates,
    }),
    ],
    fallback,
  );
  if (output.code !== 0) {
    throw new Error(sidecarErrorMessage(output.stderr, fallback));
  }
  return (JSON.parse(output.stdout) as { outputPath: string }).outputPath;
}

async function executeSidecar(args: string[], fallback: string) {
  try {
    return await Command.sidecar(SIDECAR_NAME, args).execute();
  } catch (error) {
    throw new Error(sidecarErrorMessage(error, fallback));
  }
}

export function sidecarErrorMessage(error: unknown, fallback: string): string {
  if (typeof error === "string") {
    return parseSidecarErrorText(error) ?? error ?? fallback;
  }
  if (error instanceof Error) {
    return parseSidecarErrorText(error.message) ?? error.message ?? fallback;
  }
  return fallback;
}

function parseSidecarErrorText(text: string): string | null {
  const trimmed = text.trim();
  if (!trimmed) return null;
  try {
    const payload = JSON.parse(trimmed) as { error?: unknown };
    return typeof payload.error === "string" && payload.error.trim() ? payload.error : trimmed;
  } catch {
    return trimmed;
  }
}

function mockAnalysis(input: AnalyzeInput): FileAnalysis {
  return {
    fileId: input.fileId,
    sourcePath: input.path,
    fileType: input.path.toLowerCase().endsWith(".pdf") ? "pdf" : "image",
    pages: [{ index: 0, width: 840, height: 1188, imagePath: null }],
    candidates: [
      {
        fileId: input.fileId,
        pageIndex: 0,
        rectNormalized: { x: 0.12, y: 0.18, width: 0.24, height: 0.045 },
        category: "person_name",
        source: "rule",
        confidence: 0.94,
        status: "pending",
        color: "#2563eb",
        text: input.personName || (input.locale === "en" ? "Applicant name" : "本人姓名"),
      },
      {
        fileId: input.fileId,
        pageIndex: 0,
        rectNormalized: { x: 0.12, y: 0.28, width: 0.42, height: 0.045 },
        category: "identity_number",
        source: "rule",
        confidence: 0.98,
        status: "pending",
        color: "#dc2626",
        text: input.locale === "en" ? "ID number candidate" : "身份证号候选",
      },
    ],
  };
}
