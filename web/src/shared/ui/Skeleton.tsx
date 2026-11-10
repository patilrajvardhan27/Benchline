type Variant = "row" | "stat" | "chart";

/** Placeholder block shown while data loads. Decorative, so it is hidden from screen readers. */
export function Skeleton({ variant, count = 1 }: { variant: Variant; count?: number }) {
  return (
    <>
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className={`skeleton skeleton--${variant}`} aria-hidden="true" />
      ))}
    </>
  );
}
