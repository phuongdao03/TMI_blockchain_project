import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const playwrightCli = fileURLToPath(
  new URL("../node_modules/@playwright/test/cli.js", import.meta.url),
);
const forwardedArguments = process.argv.slice(2);

for (const releaseMode of ["full", "preview"]) {
  const result = spawnSync(
    process.execPath,
    [playwrightCli, "test", ...forwardedArguments],
    {
      env: { ...process.env, E2E_RELEASE_MODE: releaseMode },
      stdio: "inherit",
    },
  );

  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
}
