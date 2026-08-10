import { useEffect, useState } from "react";

function initials(displayName: string): string {
  return displayName
    .trim()
    .split(/\s+/u)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part.charAt(0).toLocaleUpperCase())
    .join("");
}

export function ProfileImage({
  displayName,
  src,
  decorative = false
}: {
  displayName: string;
  src: string | null;
  decorative?: boolean;
}): React.JSX.Element {
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    setFailed(false);
  }, [src]);

  if (src !== null && !failed) {
    return (
      <img
        className="grid size-11 place-items-center rounded-full border-2 border-white object-cover shadow-md"
        src={src}
        alt={decorative ? "" : `${displayName} profile picture`}
        referrerPolicy="no-referrer"
        onError={() => {
          setFailed(true);
        }}
      />
    );
  }
  const label = decorative ? undefined : `${displayName} profile placeholder`;
  const value = initials(displayName);
  return (
    <span className="grid size-11 place-items-center rounded-full border-2 border-white bg-indigo-600 text-sm font-extrabold text-white shadow-md" role={decorative ? undefined : "img"} aria-label={label}>
      {value || <span aria-hidden="true">●</span>}
    </span>
  );
}
