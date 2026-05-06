export function OnboardingSkeleton() {
  return (
    <div className="space-y-4">
      <div className="h-32 animate-pulse rounded-lg bg-slate-100" />
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
        <div className="space-y-4">
          <div className="h-36 animate-pulse rounded-lg bg-slate-100" />
          <div className="h-96 animate-pulse rounded-lg bg-slate-100" />
        </div>
        <div className="h-72 animate-pulse rounded-lg bg-slate-100" />
      </div>
    </div>
  );
}
