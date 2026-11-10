import { useIsFetching } from "@tanstack/react-query";

/** Thin bar at the top of the page while any request is in flight. */
export function RouteProgress() {
  const fetching = useIsFetching();
  if (fetching === 0) return null;
  return <div className="route-progress" role="presentation" />;
}
