import type {
  CurrentUser,
  CurrentUserResponse,
  ErrorCode,
  ErrorEnvelope,
  RecoveryAction,
  Role
} from "./types";

const roles = new Set<Role>(["CANDIDATE", "MANAGER", "ADMIN"]);
const errorCodes = new Set<ErrorCode>([
  "AUTHENTICATION_REQUIRED",
  "SESSION_EXPIRED",
  "SESSION_REVOKED",
  "ACCESS_NOT_PROVISIONED",
  "ACCOUNT_DISABLED",
  "OAUTH_CANCELLED",
  "OAUTH_PROVIDER_UNAVAILABLE",
  "OAUTH_RESPONSE_INVALID",
  "FORBIDDEN",
  "CSRF_DENIED",
  "IDENTITY_CONFLICT",
  "CANDIDATE_PROFILE_CONFLICT",
  "VALIDATION_ERROR",
  "RESOURCE_NOT_FOUND"
]);
const recoveries = new Set<RecoveryAction>([
  "SIGN_IN_AGAIN",
  "CONTACT_ADMIN",
  "RETRY",
  "GO_TO_ROLE_HOME"
]);

function record(value: unknown): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error("Expected an object response");
  }
  return value as Record<string, unknown>;
}

function string(value: unknown, field: string): string {
  if (typeof value !== "string" || value.length === 0) {
    throw new Error(`Expected ${field}`);
  }
  return value;
}

function decodeUser(value: unknown): CurrentUser {
  const input = record(value);
  const roleValue = string(input.role, "role");
  if (!roles.has(roleValue as Role)) throw new Error("Unknown role");
  const shared = {
    id: string(input.id, "id"),
    organizationId: string(input.organizationId, "organizationId"),
    displayName: string(input.displayName, "displayName")
  };
  if (roleValue === "CANDIDATE") {
    return {
      ...shared,
      role: "CANDIDATE",
      candidateProfileId: string(input.candidateProfileId, "candidateProfileId")
    };
  }
  if (roleValue === "MANAGER") return { ...shared, role: "MANAGER" };
  return { ...shared, role: "ADMIN" };
}

export function decodeCurrentUserResponse(value: unknown): CurrentUserResponse {
  const input = record(value);
  const session = record(input.session);
  return {
    user: decodeUser(input.user),
    session: {
      absoluteExpiresAt: string(session.absoluteExpiresAt, "absoluteExpiresAt"),
      idleExpiresAt: string(session.idleExpiresAt, "idleExpiresAt")
    }
  };
}

export function decodeErrorEnvelope(value: unknown): ErrorEnvelope {
  const error = record(record(value).error);
  const code = string(error.code, "code");
  const recovery = string(error.recovery, "recovery");
  if (!errorCodes.has(code as ErrorCode) || !recoveries.has(recovery as RecoveryAction)) {
    throw new Error("Unknown authentication error contract");
  }
  return {
    error: {
      code: code as ErrorCode,
      recovery: recovery as RecoveryAction,
      message: string(error.message, "message"),
      correlationId: string(error.correlationId, "correlationId")
    }
  };
}

const callbackErrors: Partial<
  Record<ErrorCode, { recovery: RecoveryAction; message: string }>
> = {
  ACCESS_NOT_PROVISIONED: {
    recovery: "CONTACT_ADMIN",
    message: "Access is unavailable. Contact your administrator."
  },
  ACCOUNT_DISABLED: {
    recovery: "CONTACT_ADMIN",
    message: "Access is unavailable. Contact your administrator."
  },
  IDENTITY_CONFLICT: {
    recovery: "CONTACT_ADMIN",
    message: "Access is unavailable. Contact your administrator."
  },
  CANDIDATE_PROFILE_CONFLICT: {
    recovery: "CONTACT_ADMIN",
    message: "Candidate access requires administrator review."
  },
  OAUTH_CANCELLED: {
    recovery: "RETRY",
    message: "Google sign-in was not completed. Try again."
  },
  OAUTH_PROVIDER_UNAVAILABLE: {
    recovery: "RETRY",
    message: "Google sign-in is temporarily unavailable. Try again."
  },
  OAUTH_RESPONSE_INVALID: {
    recovery: "RETRY",
    message: "Google sign-in could not be verified. Try again."
  }
};

export function decodeCallbackError(search: string): ErrorEnvelope["error"] | null {
  const parameters = new URLSearchParams(search);
  const code = parameters.get("code");
  const correlationId = parameters.get("correlation_id");
  if (code === null || correlationId === null || correlationId.length === 0) return null;
  const definition = callbackErrors[code as ErrorCode];
  if (definition === undefined) return null;
  return { code: code as ErrorCode, correlationId, ...definition };
}
