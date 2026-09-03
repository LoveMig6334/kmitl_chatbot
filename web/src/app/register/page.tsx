import { RegisterForm } from "@/components/auth/RegisterForm";
import { pageMetadata } from "@/i18n/server";

export const generateMetadata = () => pageMetadata("auth.register.pageTitle");

export default function RegisterPage() {
  return <RegisterForm />;
}
