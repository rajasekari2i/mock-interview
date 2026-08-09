import { RoleNavigation } from "../navigation/RoleNavigation";
import { FocusedHeading } from "./FocusedHeading";

export function CandidateHome(): React.JSX.Element {
  return (
    <>
      <RoleNavigation role="CANDIDATE" />
      <main>
        <FocusedHeading>Your allocated interviews</FocusedHeading>
        <p>No interviews have been allocated yet.</p>
      </main>
    </>
  );
}
