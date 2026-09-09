import { getApp, getApps, initializeApp } from "firebase/app";
import { connectAuthEmulator, getAuth } from "firebase/auth";

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
  appHostname: string | undefined,
  production: boolean,
): string | undefined {
  // Production serves Firebase's /__/auth helpers through the existing Next.js
  // reverse proxy. Keeping the helper on the application origin avoids the
  // third-party storage partition that breaks redirect sign-in on mobile Safari.
  if (
    production &&
    configuredDomain &&
    /^[a-z0-9-]+\.firebaseapp\.com$/i.test(configuredDomain) &&
    appHostname &&
    /^[a-z0-9.-]+$/i.test(appHostname)
  ) {
    return appHostname;
  }
  return configuredDomain;
}

function firebaseConfig() {
  return {
    ...configuredFirebase,
    authDomain: resolveFirebaseAuthDomain(
      configuredFirebase.authDomain,
      typeof window === "undefined" ? undefined : window.location.hostname,
      process.env.NODE_ENV === "production",
    ),
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
