import Link from "next/link";

export function WorkspaceMissingState() {
  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-amber-950">
      <p className="text-sm font-semibold">No workspace selected</p>
      <p className="mt-1 text-xs leading-5">Open onboarding to create or select workspace context.</p>
      <Link className="mt-2 inline-flex text-xs font-semibold underline" href="/onboarding">
        Open onboarding
      </Link>
    </div>
  );
}
