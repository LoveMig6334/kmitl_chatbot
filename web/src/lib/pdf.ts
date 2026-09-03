import path from "node:path";
import type { ProgramId } from "./constants";

/** Curriculum PDF per program (files in PDF_DIR, default ../data/raw — gitignored). */
export const PDF_FILES: Record<ProgramId, string> = {
  AIT: "AIT.pdf",
  DSBA: "DSBA.pdf",
  BIT: "IT_inter2565.pdf",
  IT: "IT2565.pdf",
};

export function pdfDir() {
  return process.env.PDF_DIR || path.resolve(process.cwd(), "../data/raw");
}
