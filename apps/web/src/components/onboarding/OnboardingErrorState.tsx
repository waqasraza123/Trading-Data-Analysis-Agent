import Link from "next/link";
import { cn } from "@/lib/ui/cn";
import { motionCardClass } from "@/lib/ui/motion";

export function OnboardingErrorState({ message }: { message: string }) {
  return (
    <section
      className={cn(
        "rounded-lg border border-rose-200 bg-rose-50 p-5 text-rose-950",
        motionCardClass,
      )}
    >
      <p className="text-sm font-semibold">Onboarding status unavailable</p>
      <p className="mt-2 text-sm leading-6">{message}</p>
      <Link
        className={cn("mt-4 inline-flex rounded-md border border-rose-300 px-4 py-2 text-sm font-semibold", motionCardClass)}
        href="/setup"
      >
        Open setup wizard
      </Link>
    </section>
  );
}
