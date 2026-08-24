# Implementation plan: four roles and theme repair

1. Add a role-consolidation migration: create product roles, remap existing
   assignments and rebuild permission mappings. Verify upgrade/downgrade.
2. Replace role guards, staff-role options and workspace routing with the four
   product roles; give only Super Admin `blockchain.sign`.
3. Audit theme providers and global tokens, then convert the shared shells,
   controls and search surface to semantic tokens.
4. Run focused regression tests, typecheck and lint; inspect the affected
   pages in the local browser after the running dev server reloads.
