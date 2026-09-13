# Implementation plan

1. Source reuse
   - Add failing service/schema/UI tests for safe snapshot fields and no uploader.
   - Extend publication context/editor response and add quick-fill controls.
   - Keep submitted evidence as the only publication media source.
2. Video delivery and cover
   - Add failing media contract/worker/player tests.
   - Persist poster timestamp and adaptive streaming URL; retain optimized MP4 fallback.
   - Add source-image/frame selection and lazy responsive playback.
3. Certificate experience
   - Add tests for historical notification links, QR endpoint, inline verification, and no PDF action.
   - Implement authenticated QR and redesign detail around verifiable proof.
   - Remove the certificate download API/client surface while retaining internal issuance artifacts.
4. Voting retirement
   - Add a retirement contract test.
   - Remove voting pages/navigation/client APIs/backend router registration and voting schedules.
   - Preserve tables, migrations, and historical audit records.
5. Verification
   - Run focused tests after each slice, then backend tests, frontend unit tests, typecheck/lint/build, and E2E where the environment supports it.
   - Review the final diff for authorization, data leakage, migration safety, and unrelated files.
