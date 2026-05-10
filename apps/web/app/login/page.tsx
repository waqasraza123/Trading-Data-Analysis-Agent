import { AuthCard } from "@/components/auth/AuthCard";

export default function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-10">
      <AuthCard mode="login" />
    </main>
  );
}
