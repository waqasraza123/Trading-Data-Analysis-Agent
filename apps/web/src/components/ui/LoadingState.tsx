import { Skeleton } from "./Skeleton";
import { Card } from "./Card";

type LoadingStateProps = {
  title?: string;
  rows?: number;
  className?: string;
};

export function LoadingState({ title = "Loading workspace state", rows = 3, className }: LoadingStateProps) {
  return (
    <Card className={className}>
      <Skeleton className="h-4 w-44" />
      <p className="sr-only">{title}</p>
      <div className="mt-5 grid gap-3">
        {Array.from({ length: rows }).map((_, index) => (
          <Skeleton key={index} className="h-16" />
        ))}
      </div>
    </Card>
  );
}
