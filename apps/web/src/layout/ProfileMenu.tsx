import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import type { CurrentUser } from "../auth/types";
import { ProfileImage } from "../components/ProfileImage";

export function ProfileMenu({
  user,
  onLogout
}: {
  user: CurrentUser;
  onLogout: () => Promise<void>;
}): React.JSX.Element {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return undefined;
    const onPointerDown = (event: PointerEvent): void => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div className="relative justify-self-end" ref={rootRef}>
      <button
        className="rounded-full border-0 bg-transparent p-0 shadow-none ring-offset-2 transition hover:ring-4 hover:ring-indigo-100"
        ref={triggerRef}
        type="button"
        aria-label="Open profile menu"
        aria-expanded={open}
        aria-controls="profile-menu-panel"
        onClick={() => {
          setOpen((current) => !current);
        }}
      >
        <ProfileImage
          displayName={user.displayName}
          src={user.profilePictureUrl}
          decorative
        />
      </button>
      {open ? (
        <div className="absolute right-0 z-50 mt-3 grid min-w-56 gap-1 rounded-2xl border border-slate-200 bg-white p-2 shadow-2xl shadow-slate-900/15" id="profile-menu-panel">
          <p className="m-0 truncate border-b border-slate-100 px-3 py-2 text-sm font-bold text-slate-900">{user.displayName}</p>
          <Link
            className="flex min-h-11 items-center rounded-lg px-3 font-semibold text-slate-700 no-underline hover:bg-slate-100"
            to="/profile"
            onClick={() => {
              setOpen(false);
            }}
          >
            Profile
          </Link>
          <button className="flex min-h-11 items-center rounded-lg border-0 bg-transparent px-3 font-semibold text-rose-700 shadow-none hover:bg-rose-50" type="button" onClick={() => void onLogout()}>
            Logout
          </button>
        </div>
      ) : null}
    </div>
  );
}
