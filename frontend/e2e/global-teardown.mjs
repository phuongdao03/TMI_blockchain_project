export default async function globalTeardown() {
  if (process.env.E2E_EXTERNAL_SERVERS === "1") return;

  const mockPort = process.env.E2E_MOCK_PORT ?? "4010";
  try {
    await fetch(`http://127.0.0.1:${mockPort}/api/e2e/shutdown`, {
      method: "POST",
      signal: AbortSignal.timeout(2_000),
    });
  } catch {
    // The mock may already have stopped after a startup or test failure.
  }
}
