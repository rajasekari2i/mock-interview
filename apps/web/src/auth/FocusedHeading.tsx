import { useEffect, useRef } from "react";

export function FocusedHeading({ children }: { children: React.ReactNode }): React.JSX.Element {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => heading.current?.focus(), []);
  return (
    <h1 ref={heading} tabIndex={-1}>
      {children}
    </h1>
  );
}
