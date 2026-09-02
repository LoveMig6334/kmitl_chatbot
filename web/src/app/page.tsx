import { redirect } from "next/navigation";
import { ThemeSync } from "@/components/ThemeSync";

export default function Home() {
  return (
    <>
      <ThemeSync />
      {redirect("/chat")}
    </>
  );
}
