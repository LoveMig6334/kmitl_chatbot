/** The four B.Sc. programs of the Faculty of IT, KMITL. Ids must match the backend exactly. */
export const PROGRAMS = [
  { id: "AIT", en: "Artificial Intelligence Technology", th: "เทคโนโลยีปัญญาประดิษฐ์" },
  { id: "DSBA", en: "Data Science and Business Analytics", th: "วิทยาการข้อมูลและการวิเคราะห์เชิงธุรกิจ" },
  { id: "BIT", en: "Business IT (International)", th: "เทคโนโลยีสารสนเทศทางธุรกิจ (นานาชาติ)" },
  { id: "IT", en: "Information Technology", th: "เทคโนโลยีสารสนเทศ" },
] as const;

export type ProgramId = (typeof PROGRAMS)[number]["id"];
export const PROGRAM_IDS: readonly ProgramId[] = PROGRAMS.map((p) => p.id);
