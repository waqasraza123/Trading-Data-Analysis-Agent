import { AuthCard } from "@/components/auth/AuthCard";
import { getPublicEnv } from "@/config/env";
import { getCurrentIdentity } from "@/lib/api/auth";
import { redirect } from "next/navigation";
import Link from "next/link";

export default async function RegisterPage() {
  if (getPublicEnv().authMode === "session") {
    const identity = await getCurrentIdentity();
    if (identity.ok && identity.data.authenticated) {
      redirect("/command-center");
    }
  }
  return (
    <main className="landing-grid relative flex min-h-screen items-center justify-center overflow-hidden bg-[#050811] px-4 py-10">
      <div className="landing-glow pointer-events-none absolute inset-0" />
      <Link className="absolute left-5 top-5 z-10 text-sm font-semibold text-slate-400 transition hover:text-white" href="/">← Back to starter kit</Link>
      <div className="relative z-10"><AuthCard mode="register" /></div>
    </main>
  );
}
