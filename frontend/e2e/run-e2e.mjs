import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const playwrightCli = fileURLToPath(
  new URL("../node_modules/@playwright/test/cli.js", import.meta.url),
);
const forwardedArguments = process.argv.slice(2);
const selectedTestFiles = forwardedArguments.filter((argument) =>
  /(?:^|[/\\])[^/\\]+\.spec\.[cm]?[jt]sx?$/.test(argument),
);
const releaseModes = selectedTestFiles.length
  ? selectedTestFiles.some((file) => file.includes("preview-release.spec."))
    ? ["preview"]
    : ["full"]
  : ["full", "preview"];

for (const releaseMode of releaseModes) {
  const projectRuns = forwardedArguments.some((argument) =>
    argument.startsWith("--project"),
  )
    ? [undefined]
    : releaseMode === "preview"
      ? ["desktop-chrome"]
      : ["desktop-chrome", "mobile-chrome"];

  for (const project of projectRuns) {
    const result = spawnSync(
      process.execPath,
      [
        playwrightCli,
        "test",
        ...forwardedArguments,
        ...(project ? [`--project=${project}`] : []),
      ],
      {
        env: { ...process.env, E2E_RELEASE_MODE: releaseMode },
        stdio: "inherit",
      },
    );

    if (result.error) throw result.error;
    if (result.status !== 0) process.exit(result.status ?? 1);
  }
}
