import { getApp, getApps, initializeApp } from "firebase/app";
import { connectAuthEmulator, getAuth, type Auth } from "firebase/auth";

const configuredFirebase = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

let emulatorConnected = false;

export function resolveFirebaseAuthDomain(
  configuredDomain: string | undefined,
): string | undefined {
  if (process.env.NEXT_PUBLIC_FIREBASE_SAME_ORIGIN_AUTH === "true") {
    const appUrl = process.env.NEXT_PUBLIC_APP_BASE_URL;
    if (appUrl) return new URL(appUrl).hostname;
  }
  return configuredDomain;
}

function firebaseConfig() {
  return {
    ...configuredFirebase,
    authDomain: resolveFirebaseAuthDomain(configuredFirebase.authDomain),
  };
}

export function firebaseConfigured(): boolean {
  return Boolean(
    configuredFirebase.apiKey &&
      configuredFirebase.authDomain &&
      configuredFirebase.projectId &&
      configuredFirebase.appId,
  );
}

export function getFirebaseAuth() {
  if (!firebaseConfigured()) {
    throw new Error("FIREBASE_CLIENT_NOT_CONFIGURED");
  }
  const app = getApps().length > 0 ? getApp() : initializeApp(firebaseConfig());
  const auth = getAuth(app);
  const emulatorUrl = process.env.NEXT_PUBLIC_FIREBASE_AUTH_EMULATOR_URL;
  if (
    emulatorUrl &&
    process.env.NODE_ENV !== "production" &&
    !emulatorConnected
  ) {
    connectAuthEmulator(auth, emulatorUrl, { disableWarnings: true });
    emulatorConnected = true;
  }
  return auth;
}

export async function prepareGooglePopup(): Promise<void> {
  const auth = getFirebaseAuth();
  await auth.authStateReady();
  // Firebase otherwise initializes this iframe after the user's first tap.
  // Safari can expire the tap's popup permission before window.open runs.
  const resolver = (
    auth as Auth & {
      _popupRedirectResolver?: { _initialize(auth: Auth): Promise<unknown> };
    }
  )._popupRedirectResolver;
  if (resolver) await resolver._initialize(auth);
}
