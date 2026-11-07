interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className = "h-5 w-full" }: SkeletonProps) {
  return (
    <span
      aria-hidden="true"
      className={`block animate-pulse rounded-lg bg-stone-200 ${className}`}
    />
  );
}
