export const DEGREES = [
  { id: "bachelor", en: "Bachelor", th: "ปริญญาตรี" },
  { id: "master", en: "Master", th: "ปริญญาโท" },
  { id: "phd", en: "PhD", th: "ปริญญาเอก" },
  { id: "certificate", en: "Certificate", th: "ประกาศนียบัตร" },
] as const;

export const FACULTIES = [
  { id: "engineering", en: "Engineering", th: "วิศวกรรมศาสตร์" },
  { id: "it", en: "Information Technology", th: "เทคโนโลยีสารสนเทศ" },
  { id: "science", en: "Science", th: "วิทยาศาสตร์" },
  { id: "business", en: "Business Administration", th: "บริหารธุรกิจ" },
  { id: "medicine", en: "Medicine", th: "แพทยศาสตร์" },
  { id: "architecture", en: "Architecture", th: "สถาปัตยกรรมศาสตร์" },
  { id: "education", en: "Education", th: "ครุศาสตร์" },
] as const;

export type Locale = "th" | "en";

export const GHOST_PROMPTS = [
  "ask about course registration…",
  "what courses does Engineering offer?",
  "สอบถามรายวิชาของคณะวิศวกรรมศาสตร์",
  "how do I apply for a scholarship?",
];
