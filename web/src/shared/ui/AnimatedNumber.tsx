import { useCountUp } from "../hooks/useCountUp";
import { formatInt } from "../format/format";

/** Counts up on mount. The final value is what assistive technology reads. */
export function AnimatedNumber({ value }: { value: number }) {
  const shown = useCountUp(value);
  return (
    <>
      <span aria-hidden="true">{formatInt(shown)}</span>
      <span className="visually-hidden">{formatInt(value)}</span>
    </>
  );
}
