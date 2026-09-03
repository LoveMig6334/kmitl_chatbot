import { Suspense } from "react";
import { LoginForm } from "@/components/auth/LoginForm";
import { pageMetadata } from "@/i18n/server";

export const generateMetadata = () => pageMetadata("auth.login.pageTitle");

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
