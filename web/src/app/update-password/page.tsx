import { UpdatePasswordForm } from "@/components/auth/UpdatePasswordForm";
import { pageMetadata } from "@/i18n/server";

export const generateMetadata = () => pageMetadata("auth.update.pageTitle");

export default function UpdatePasswordPage() {
  return <UpdatePasswordForm />;
}
