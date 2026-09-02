export const DEGREES = [
  { id: "bachelor", en: "Bachelor", th: "ปริญญาตรี" },
  { id: "master", en: "Master", th: "ปริญญาโท" },
  { id: "phd", en: "PhD", th: "ปริญญาเอก" },
  { id: "certificate", en: "Certificate", th: "ประกาศนียบัตร" },
] as const;

/** The four B.Sc. programs of the Faculty of IT, KMITL. Ids must match the backend exactly. */
export const PROGRAMS = [
  { id: "AIT", en: "Artificial Intelligence Technology", th: "เทคโนโลยีปัญญาประดิษฐ์" },
  { id: "DSBA", en: "Data Science and Business Analytics", th: "วิทยาการข้อมูลและการวิเคราะห์เชิงธุรกิจ" },
  { id: "BIT", en: "Business IT (International)", th: "เทคโนโลยีสารสนเทศทางธุรกิจ (นานาชาติ)" },
  { id: "IT", en: "Information Technology", th: "เทคโนโลยีสารสนเทศ" },
] as const;

export type ProgramId = (typeof PROGRAMS)[number]["id"];
export const PROGRAM_IDS: readonly ProgramId[] = PROGRAMS.map((p) => p.id);

/** Scope chips + profile dropdown still import this name; it now lists programs. */
export const FACULTIES = PROGRAMS;

export type Locale = "th" | "en";

export const GHOST_PROMPTS = [
  "AIT เรียนกี่หน่วยกิต…",
  "DSBA กับ IT ต่างกันอย่างไร",
  "หลักสูตร BIT สอนเป็นภาษาอะไร",
  "ปี 1 ของ IT เรียนวิชาอะไรบ้าง",
  "what courses does AIT teach in year 1?",
];
