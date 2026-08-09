import { RoleNavigation } from "../navigation/RoleNavigation";
import { FocusedHeading } from "./FocusedHeading";

export function AdminHome(): React.JSX.Element {
  return (
    <>
      <RoleNavigation role="ADMIN" />
      <main>
        <FocusedHeading>Application administration</FocusedHeading>
        <p>Manage users and review application reports.</p>
      </main>
    </>
  );
}
