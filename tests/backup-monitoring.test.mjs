import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), "utf8");

test("backup monitoring defines freshness alert and executable age check", async () => {
  const [alerts, checker, validator, recovery] = await Promise.all([
    read("infrastructure/monitoring/alert-policies.yaml"),
    read("infrastructure/scripts/check-backup-age.sh"),
    read("infrastructure/scripts/validate-backup.sh"),
    read("docs/runbooks/backup-and-restore.md"),
  ]);

  assert.match(alerts, /backup_freshness/);
  assert.match(alerts, /backup_newest_valid_age_seconds/);
  assert.match(checker, /validate-backup\.sh/);
  assert.match(checker, /max_age_hours/);
  assert.match(validator, /artifacts\":4/);
  assert.match(validator, /sha256sum --check --status/);
  assert.match(validator, /tar -tzf/);
  assert.match(recovery, /check-backup-age\.sh/);
  assert.match(recovery, /exit code 70/i);
});
