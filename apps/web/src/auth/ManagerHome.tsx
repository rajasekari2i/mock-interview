import { RoleNavigation } from "../navigation/RoleNavigation";
import { FocusedHeading } from "./FocusedHeading";

export function ManagerHome(): React.JSX.Element {
  return (
    <>
      <RoleNavigation role="MANAGER" />
      <main>
        <FocusedHeading>Manager workspace</FocusedHeading>
        <p>Upload job descriptions</p>
      </main>
    </>
  );
}
