import { ForgotPasswordForm } from "@/components/auth/ForgotPasswordForm";
import { pageMetadata } from "@/i18n/server";

export const generateMetadata = () => pageMetadata("auth.forgot.pageTitle");

export default function ForgotPasswordPage() {
  return <ForgotPasswordForm />;
}
