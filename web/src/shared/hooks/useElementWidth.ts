import { type RefObject, useEffect, useState } from "react";

const FALLBACK = 720; // used until measured, and where ResizeObserver does not exist (tests)

/** Width of an element in pixels, kept up to date as the window or layout changes. */
export function useElementWidth(ref: RefObject<Element | null>): number {
  const [width, setWidth] = useState(FALLBACK);
  useEffect(() => {
    const element = ref.current;
    if (!element || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(([entry]) => {
      if (entry) setWidth(Math.round(entry.contentRect.width));
    });
    observer.observe(element);
    return () => { observer.disconnect(); };
  }, [ref]);
  return width;
}
