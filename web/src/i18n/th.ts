/**
 * Thai UI strings — the source of truth for the key set.
 * `en.ts` must define exactly the same keys (enforced by the type + a test).
 * Placeholders use {name}; see `translate()` in index.ts.
 */
export const th = {
  // brand
  "app.name": "IT KMITL Chatbot",
  "app.tagline": "ผู้ช่วยตอบคำถามหลักสูตร คณะเทคโนโลยีสารสนเทศ สจล.",
  "app.description":
    "ถามเรื่องหลักสูตรปริญญาตรีของคณะไอที สจล. (AIT, DSBA, BIT, IT) ได้เลย",

  // common
  "common.loading": "กำลังโหลด…",
  "common.cancel": "ยกเลิก",
  "common.close": "ปิด",
  "common.back": "ย้อนกลับ",
  "common.or": "หรือ",
  "common.retry": "ลองอีกครั้ง",
  "common.optional": "ไม่บังคับ",
  "common.showPassword": "แสดงรหัสผ่าน",
  "common.hidePassword": "ซ่อนรหัสผ่าน",
  "common.backToChat": "กลับไปหน้าแชท",
  "common.openMenu": "เปิดเมนู",

  // theme
  "theme.label": "ธีม",
  "theme.light": "สว่าง",
  "theme.dark": "มืด",
  "theme.system": "ตามระบบ",
  "theme.toggle": "สลับธีม",

  // locale
  "locale.label": "ภาษา",
  "locale.th": "ไทย",
  "locale.en": "English",
  "locale.toggle": "เปลี่ยนภาษา",

  // user menu
  "user.menu": "เมนูผู้ใช้",
  "user.signOut": "ออกจากระบบ",
  "user.signedInAs": "เข้าสู่ระบบในชื่อ",
  "user.guest": "ผู้เยี่ยมชม",
  "user.demoBadge": "โหมดสาธิต",
  "user.settings": "การตั้งค่า",

  // auth: shared
  "auth.email": "อีเมล",
  "auth.emailPlaceholder": "you@example.com",
  "auth.password": "รหัสผ่าน",
  "auth.passwordPlaceholder": "กรอกรหัสผ่าน",
  "auth.confirmPassword": "ยืนยันรหัสผ่าน",
  "auth.confirmPasswordPlaceholder": "กรอกรหัสผ่านอีกครั้ง",
  "auth.displayName": "ชื่อที่แสดง",
  "auth.displayNamePlaceholder": "ชื่อที่ให้เพื่อน ๆ เรียก",
  "auth.continueWithGoogle": "ดำเนินการต่อด้วย Google",
  "auth.demoNotice":
    "ยังไม่ได้ตั้งค่า Supabase — ระบบทำงานในโหมดสาธิต การเข้าสู่ระบบจะถูกจำลองในเบราว์เซอร์",
  "auth.legal": "เมื่อดำเนินการต่อ คุณยอมรับว่านี่คือระบบสาธิตสำหรับการแข่งขัน",

  // auth: login
  "auth.login.title": "ยินดีต้อนรับกลับมา",
  "auth.login.subtitle": "เข้าสู่ระบบเพื่อถามเรื่องหลักสูตรต่อจากที่ค้างไว้",
  "auth.login.submit": "เข้าสู่ระบบ",
  "auth.login.submitting": "กำลังเข้าสู่ระบบ…",
  "auth.login.forgot": "ลืมรหัสผ่าน?",
  "auth.login.noAccount": "ยังไม่มีบัญชี?",
  "auth.login.registerLink": "สมัครสมาชิก",
  "auth.login.pageTitle": "เข้าสู่ระบบ",

  // auth: register
  "auth.register.title": "สร้างบัญชีใหม่",
  "auth.register.subtitle": "ใช้เวลาไม่ถึงนาที แล้วเริ่มถามได้ทันที",
  "auth.register.submit": "สมัครสมาชิก",
  "auth.register.submitting": "กำลังสร้างบัญชี…",
  "auth.register.haveAccount": "มีบัญชีอยู่แล้ว?",
  "auth.register.loginLink": "เข้าสู่ระบบ",
  "auth.register.pageTitle": "สมัครสมาชิก",
  "auth.register.checkEmailTitle": "ตรวจสอบอีเมลของคุณ",
  "auth.register.checkEmailBody":
    "เราส่งลิงก์ยืนยันไปที่ {email} แล้ว กดลิงก์ในอีเมลเพื่อเปิดใช้งานบัญชี จากนั้นกลับมาเข้าสู่ระบบ",
  "auth.register.goToLogin": "ไปหน้าเข้าสู่ระบบ",

  // auth: password requirements
  "auth.pw.title": "รหัสผ่านต้องมี",
  "auth.pw.minLength": "อย่างน้อย 8 ตัวอักษร",
  "auth.pw.letter": "ตัวอักษร (a-z หรือ ก-ฮ) อย่างน้อย 1 ตัว",
  "auth.pw.number": "ตัวเลขอย่างน้อย 1 ตัว",
  "auth.pw.strength.weak": "คาดเดาง่าย",
  "auth.pw.strength.fair": "ปานกลาง",
  "auth.pw.strength.strong": "รัดกุม",

  // auth: forgot password
  "auth.forgot.title": "ลืมรหัสผ่าน",
  "auth.forgot.subtitle": "กรอกอีเมล แล้วเราจะส่งลิงก์สำหรับตั้งรหัสผ่านใหม่ให้",
  "auth.forgot.submit": "ส่งลิงก์ตั้งรหัสผ่านใหม่",
  "auth.forgot.submitting": "กำลังส่ง…",
  "auth.forgot.sentTitle": "ส่งอีเมลแล้ว",
  "auth.forgot.sentBody":
    "หากมีบัญชีที่ใช้อีเมล {email} เราได้ส่งลิงก์ตั้งรหัสผ่านใหม่ไปให้แล้ว ลิงก์จะหมดอายุภายในหนึ่งชั่วโมง",
  "auth.forgot.backToLogin": "กลับไปหน้าเข้าสู่ระบบ",
  "auth.forgot.pageTitle": "ลืมรหัสผ่าน",

  // auth: update password
  "auth.update.title": "ตั้งรหัสผ่านใหม่",
  "auth.update.subtitle": "เลือกรหัสผ่านใหม่สำหรับบัญชีของคุณ",
  "auth.update.newPassword": "รหัสผ่านใหม่",
  "auth.update.submit": "บันทึกรหัสผ่านใหม่",
  "auth.update.submitting": "กำลังบันทึก…",
  "auth.update.successTitle": "เปลี่ยนรหัสผ่านแล้ว",
  "auth.update.successBody": "รหัสผ่านใหม่ใช้งานได้แล้ว กำลังพาคุณไปหน้าแชท…",
  "auth.update.noSessionTitle": "ลิงก์ไม่ถูกต้องหรือหมดอายุ",
  "auth.update.noSessionBody":
    "กรุณาขอลิงก์ตั้งรหัสผ่านใหม่อีกครั้ง แล้วเปิดลิงก์จากอีเมลภายในหนึ่งชั่วโมง",
  "auth.update.requestAgain": "ขอลิงก์ใหม่",
  "auth.update.pageTitle": "ตั้งรหัสผ่านใหม่",

  // validation (inline, per field)
  "validation.required": "กรุณากรอกช่องนี้",
  "validation.emailInvalid": "รูปแบบอีเมลไม่ถูกต้อง",
  "validation.passwordTooShort": "รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร",
  "validation.passwordMismatch": "รหัสผ่านทั้งสองช่องไม่ตรงกัน",
  "validation.displayNameTooShort": "ชื่อที่แสดงต้องมีอย่างน้อย 2 ตัวอักษร",
  "validation.displayNameTooLong": "ชื่อที่แสดงต้องไม่เกิน 40 ตัวอักษร",

  // auth errors (mapped from Supabase error codes — raw messages are never shown)
  "authError.invalid_credentials": "อีเมลหรือรหัสผ่านไม่ถูกต้อง",
  "authError.email_not_confirmed":
    "อีเมลนี้ยังไม่ได้ยืนยัน กรุณากดลิงก์ยืนยันในอีเมลก่อนเข้าสู่ระบบ",
  "authError.rate_limited": "มีการลองหลายครั้งเกินไป กรุณารอสักครู่แล้วลองใหม่",
  "authError.network": "เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ กรุณาตรวจสอบอินเทอร์เน็ตแล้วลองใหม่",
  "authError.user_exists": "อีเมลนี้มีบัญชีอยู่แล้ว ลองเข้าสู่ระบบแทน",
  "authError.weak_password": "รหัสผ่านนี้เดาง่ายเกินไป กรุณาเลือกรหัสผ่านที่ซับซ้อนขึ้น",
  "authError.same_password": "รหัสผ่านใหม่ต้องต่างจากรหัสผ่านเดิม",
  "authError.session_expired": "เซสชันหมดอายุ กรุณาเข้าสู่ระบบอีกครั้ง",
  "authError.oauth_failed": "เข้าสู่ระบบด้วย Google ไม่สำเร็จ กรุณาลองใหม่",
  "authError.link_invalid": "ลิงก์นี้ใช้ไม่ได้แล้ว (หมดอายุหรือถูกใช้ไปแล้ว) กรุณาขอลิงก์ตั้งรหัสผ่านใหม่อีกครั้ง",
  "authError.confirm_link_used":
    "ลิงก์ยืนยันถูกใช้ไปแล้วหรือถูกเปิดในเบราว์เซอร์อื่น บัญชีของคุณน่าจะยืนยันแล้ว ลองเข้าสู่ระบบได้เลย",
  "authError.provider_disabled": "ระบบยังไม่เปิดให้เข้าสู่ระบบด้วยวิธีนี้",
  "authError.unknown": "เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง",

  // toasts
  "toast.region": "การแจ้งเตือน",
  "toast.signedOut": "ออกจากระบบแล้ว",
  "toast.signedIn": "เข้าสู่ระบบสำเร็จ",
  "toast.accountCreated": "สร้างบัญชีสำเร็จ",
  "toast.passwordUpdated": "เปลี่ยนรหัสผ่านเรียบร้อย",
} as const;

export type MessageKey = keyof typeof th;
export type Dictionary = Record<MessageKey, string>;
