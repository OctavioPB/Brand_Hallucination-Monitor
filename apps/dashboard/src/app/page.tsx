import { redirect } from "next/navigation";

// Root "/" redirects to login
export default function RootPage() {
  redirect("/login");
}
