export type MaterialType = "social" | "other";
export type CandidateStatus = "pending" | "approved" | "rejected";
export type CandidateSource = "ocr" | "vision" | "manual" | "rule";

export type Category =
  | "person_name"
  | "identity_number"
  | "employer_name"
  | "employer_logo"
  | "employer_address"
  | "department_name"
  | "phone_number"
  | "portrait"
  | "seal"
  | "manual";

export interface RectNormalized {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Candidate {
  fileId: string;
  pageIndex: number;
  rectNormalized: RectNormalized;
  category: Category;
  source: CandidateSource;
  confidence: number;
  status: CandidateStatus;
  color: string;
  text?: string | null;
}

export interface PageAnalysis {
  index: number;
  width: number;
  height: number;
  imagePath?: string | null;
}

export interface FileAnalysis {
  fileId: string;
  sourcePath: string;
  fileType: "pdf" | "image";
  pages: PageAnalysis[];
  candidates: Candidate[];
}

export interface LoadedFile {
  id: string;
  path: string;
  name: string;
  extension: string;
  size: number;
  analysis?: FileAnalysis;
}
