type E2EUser = {
  email: string;
  emailVerified: boolean;
  getIdToken(forceRefresh?: boolean): Promise<string>;
};

type E2EAuth = {
  currentUser: E2EUser | null;
};

const auth: E2EAuth = { currentUser: null };

function user(email: string, token: string, emailVerified = true): E2EUser {
  return { email, emailVerified, getIdToken: async () => token };
}

function authError(code: string): Error & { code: string } {
  return Object.assign(new Error(code), { code });
}

export class GoogleAuthProvider {}

export const TotpMultiFactorGenerator = {
  FACTOR_ID: "totp",
  assertionForEnrollment: (_secret: unknown, code: string) => ({ code }),
  assertionForSignIn: (_uid: string, code: string) => ({ code }),
  generateSecret: async () => ({ secretKey: "E2E-TOTP-SETUP-KEY" }),
};

export function getAuth(): E2EAuth {
  return auth;
}

export function connectAuthEmulator(): void {}

export async function createUserWithEmailAndPassword(
  target: E2EAuth,
  email: string,
): Promise<{ user: E2EUser }> {
  const created = user(email, "e2e-unverified-token", false);
  target.currentUser = created;
  return { user: created };
}

export async function sendEmailVerification(): Promise<void> {}

export async function sendPasswordResetEmail(
  _target: E2EAuth,
  email: string,
): Promise<void> {
  if (email === "failure@tmigroup.vn")
    throw authError("auth/too-many-requests");
}

export async function confirmPasswordReset(
  _target: E2EAuth,
  code: string,
): Promise<void> {
  if (code !== "e2e-valid-reset-code-123456789012") {
    throw authError("auth/expired-action-code");
  }
}

export async function signInWithEmailAndPassword(
  target: E2EAuth,
  email: string,
  password: string,
): Promise<{ user: E2EUser }> {
  if (password !== "correct horse battery staple") {
    throw authError("auth/invalid-credential");
  }
  if (email === "reviewer@tmigroup.vn") {
    throw authError("auth/multi-factor-auth-required");
  }
  const signedIn = user(
    email,
    email === "superadmin@tmigroup.vn"
      ? "e2e-super-admin-token"
      : email === "owner@tmigroup.vn"
        ? "e2e-admin-token"
        : "e2e-applicant-token",
  );
  target.currentUser = signedIn;
  return { user: signedIn };
}

export async function signInWithPopup(
  target: E2EAuth,
): Promise<{ user: E2EUser }> {
  const isInvitation = window.location.pathname.includes("staff-invitation");
  const signedIn = isInvitation
    ? user("reviewer@tmigroup.vn", "e2e-staff-invitation-token")
    : user("applicant@tmigroup.vn", "e2e-applicant-token");
  target.currentUser = signedIn;
  return { user: signedIn };
}

export function getMultiFactorResolver(target: E2EAuth) {
  return {
    hints: [{ factorId: "totp", uid: "e2e-totp-factor" }],
    async resolveSignIn(assertion: { code: string }) {
      if (assertion.code !== "654321")
        throw authError("auth/invalid-verification-code");
      const signedIn = user("reviewer@tmigroup.vn", "e2e-reviewer-mfa-token");
      target.currentUser = signedIn;
      return { user: signedIn };
    },
  };
}

export function multiFactor(target: E2EUser) {
  return {
    getSession: async () => ({ user: target.email }),
    async enroll(assertion: { code: string }) {
      if (assertion.code !== "654321")
        throw authError("auth/invalid-verification-code");
    },
  };
}

export async function signOut(target: E2EAuth): Promise<void> {
  target.currentUser = null;
}

export type MultiFactorError = Error & { code: string };
export type MultiFactorResolver = ReturnType<typeof getMultiFactorResolver>;
export type TotpSecret = { secretKey: string };
export type User = E2EUser;
