import Link from "next/link";

export function OnboardingErrorState({ message }: { message: string }) {
  return (
    <section className="rounded-lg border border-rose-200 bg-rose-50 p-5 text-rose-950">
      <p className="text-sm font-semibold">Onboarding status unavailable</p>
      <p className="mt-2 text-sm leading-6">{message}</p>
      <Link className="mt-4 inline-flex rounded-md border border-rose-300 px-4 py-2 text-sm font-semibold" href="/setup">
        Open setup wizard
      </Link>
    </section>
  );
}
