import { redirect } from "next/navigation";

/** Old URL kept for bookmarks; the page lives at /register. */
export default function SignUpPage() {
  redirect("/register");
}
