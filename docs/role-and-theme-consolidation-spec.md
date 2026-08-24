# Spec: four roles and reliable THV themes

## Objective

Replace the fragmented staff-role experience with four product roles while
preserving the underlying dossier workflow:

| Product role | Code | Scope |
| --- | --- | --- |
| Người xem | `VIEWER` | Browse published works and vote. |
| Người dùng | `USER` | Create, submit and track their own dossiers. |
| Người kiểm duyệt | `MODERATOR` | Review, request amendments and decide dossiers. |
| Super Admin | `SUPER_ADMIN` | System administration, staff access and the sole THV blockchain signer. |

Legacy roles are migrated to the closest product role. `SUPER_ADMIN` retains
all capabilities and receives `blockchain.sign`; no separate blockchain-admin
role is required. The signer still needs the one verified active wallet and
the on-chain `ISSUER_ROLE`.

Theme switching must use semantic CSS tokens only. Light and dark states must
keep text, fields, panels, navigation and footers legible without changing
content or permissions.

## Commands

```powershell
cd backend; python -m pytest app/tests/test_role_consolidation.py -q
cd frontend; npx.cmd tsc --noEmit --incremental false; npm.cmd run lint
```

## Boundaries

- Always: retain audit history, enforce server-side permissions and test the
  migration both directions on SQLite.
- Ask first: deploy a contract, grant a real chain role or transact on a live
  network.
- Never: store a wallet private key, reveal secrets or expose internal roles
  in the public UI.

## Acceptance criteria

- Only `VIEWER`, `USER`, `MODERATOR` and `SUPER_ADMIN` are assignable product
  roles after migration.
- Super Admin is authorized for blockchain signing; all other product roles
  are denied.
- Existing user-role assignments migrate deterministically and staff screens
  offer only the four product roles.
- Theme tokens provide accessible foreground, surface, border and control
  colors in both modes; no page relies on hard-coded light text/background
  combinations.
- Typecheck, lint and focused backend/frontend tests pass.
