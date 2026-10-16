# Navigation architecture specification

## Goal

Make public browsing the default experience, provide a canonical personal workspace at `/workspace`, and expose administrative navigation only to users whose server-issued roles or permissions allow it. Preserve active public URLs and keep authorization enforced by the backend.

## Behavior

- Public pages remain readable whether signed in or signed out. Keep existing routes such as `/`, `/works`, `/community`, `/process`, `/verify`, and `/guide`.
- Preserve the requested local destination through login, Google login, and registration. A login from a protected route returns to that route including its query. Reject external, protocol-relative, malformed, and fragment destinations.
- A login without an explicit destination opens `/workspace`, regardless of whether the user also has administrative roles. Admin access is an explicit navigation choice or direct `/admin` visit.
- Add `/workspace` as the canonical personal landing page; retain `/dashboard` for compatibility.
- Public navigation provides the public links and, when authenticated, a user menu with workspace, own community posts, notifications, account, logout, and permitted admin entry.
- Personal workspace navigation includes personal/work features and links back to the public website and community. Admin routes use an admin-focused navigation drawer with Website and Community links. Do not duplicate the same navigation in the header and sidebar.
- Mobile navigation provides Home, Nominations, Community, Personal, and More. Admin routes use their separate drawer and do not show admin modules in the bottom bar. Respect safe areas, touch targets, active state, and theme.
- Visibility is a convenience only. Backend authorization remains authoritative.

## Acceptance checks

- Guest can browse public routes and sees login/register links that retain the current public route.
- Protected direct links retain pathname and query through login; hostile `next` values fall back to `/workspace`.
- Direct login defaults to `/workspace`, including SUPER_ADMIN; explicit `/admin` remains reachable for authorized admins.
- Public, personal, and admin navigation expose the correct links for available roles/permissions.
- Mobile public/personal bottom navigation has the five requested destinations; admin pages use the admin drawer.
- Existing route URLs and authorization behavior remain compatible.
