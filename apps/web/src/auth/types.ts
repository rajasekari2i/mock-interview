export type Role = "CANDIDATE" | "MANAGER" | "ADMIN";

interface UserBase {
  id: string;
  organizationId: string;
  displayName: string;
  email: string;
  profilePictureUrl: string | null;
}

export interface CandidateUser extends UserBase {
  role: "CANDIDATE";
  candidateProfileId: string;
}

export interface ManagerUser extends UserBase {
  role: "MANAGER";
}

export interface AdminUser extends UserBase {
  role: "ADMIN";
}

export type CurrentUser = CandidateUser | ManagerUser | AdminUser;

export interface CurrentUserResponse {
  user: CurrentUser;
  session: {
    absoluteExpiresAt: string;
    idleExpiresAt: string;
  };
}

export type ErrorCode =
  | "AUTHENTICATION_REQUIRED"
  | "SESSION_EXPIRED"
  | "SESSION_REVOKED"
  | "ACCESS_NOT_PROVISIONED"
  | "ACCOUNT_DISABLED"
  | "OAUTH_CANCELLED"
  | "OAUTH_PROVIDER_UNAVAILABLE"
  | "OAUTH_RESPONSE_INVALID"
  | "FORBIDDEN"
  | "CSRF_DENIED"
  | "IDENTITY_CONFLICT"
  | "CANDIDATE_PROFILE_CONFLICT"
  | "VALIDATION_ERROR"
  | "RESOURCE_NOT_FOUND";

export type RecoveryAction = "SIGN_IN_AGAIN" | "CONTACT_ADMIN" | "RETRY" | "GO_TO_ROLE_HOME";

export interface ErrorEnvelope {
  error: {
    code: ErrorCode;
    recovery: RecoveryAction;
    message: string;
    correlationId: string;
  };
}

export type AuthState =
  | { status: "loading" }
  | { status: "anonymous" }
  | { status: "authenticated"; current: CurrentUserResponse }
  | { status: "error"; error: ErrorEnvelope["error"] };
