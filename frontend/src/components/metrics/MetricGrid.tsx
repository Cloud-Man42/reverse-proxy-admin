import { ReactNode } from "react";

interface MetricGridProps {
  children: ReactNode;
  columns?: 2 | 3 | 4 | 5;
}

const columnClasses = {
  2: "md:grid-cols-2",
  3: "md:grid-cols-3",
  4: "md:grid-cols-2 xl:grid-cols-4",
  5: "md:grid-cols-2 xl:grid-cols-5",
};

export function MetricGrid({ children, columns = 4 }: MetricGridProps) {
  return <div className={`grid gap-4 ${columnClasses[columns]}`}>{children}</div>;
}
