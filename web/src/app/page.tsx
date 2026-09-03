import { LandingPage } from "@/components/landing/LandingPage";
import { pageMetadata } from "@/i18n/server";

export const generateMetadata = () => pageMetadata("landing.pageTitle");

export default function Home() {
  return <LandingPage />;
}
