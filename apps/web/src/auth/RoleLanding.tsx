import type { CurrentUser } from "./types";
import { AdminHome } from "./AdminHome";
import { CandidateHome } from "./CandidateHome";
import { ManagerHome } from "./ManagerHome";

export function RoleLanding({ user }: { user: CurrentUser }): React.JSX.Element {
  switch (user.role) {
    case "CANDIDATE":
      return <CandidateHome />;
    case "MANAGER":
      return <ManagerHome />;
    case "ADMIN":
      return <AdminHome />;
  }
}
