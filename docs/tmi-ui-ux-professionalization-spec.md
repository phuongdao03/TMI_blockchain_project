# Spec: TMI UI/UX professionalization

## Objective

Nâng cấp toàn bộ trải nghiệm TMI theo hướng dễ hiểu, nhất quán, accessible và
responsive mà không thay đổi nghiệp vụ, API, database hoặc cơ chế lưu file.
Blockchain chỉ dùng `THVProofRegistry` trên Polygon Mainnet tại
`0x4B7fFF9e719a55cA3792cF96fbb229611e505b5F` để lưu dấu vân tay số.

## Tech stack

- Next.js 16, React 19, TypeScript strict
- Tailwind CSS 4 và semantic CSS tokens trong `app/globals.css`
- TanStack Query cho server state
- Lucide React là bộ icon duy nhất
- Vitest, Testing Library, Playwright và axe-core

## Commands

- Format: `npm run format:check`
- Lint: `npm run lint`
- Typecheck: `npm run typecheck`
- Unit/integration: `npm test`
- Browser E2E: `npm --prefix frontend run test:e2e`
- Production build: `npm --prefix frontend run build`

## Project structure

- `frontend/src/components/ui`: primitives và state components dùng chung
- `frontend/src/components/layout`: shell, drawer, mobile navigation
- `frontend/src/components/blockchain`: signing flow và blockchain explanation
- `frontend/src/components/notifications`: notification panel/page
- `frontend/src/components/public`: public verification and landing experience
- `frontend/src/app/globals.css`: semantic design tokens and responsive layout
- `frontend/e2e`: cross-viewport and critical-flow tests

## Code style

```tsx
<StatusMessage
  icon={Clock3}
  title="Đang chờ mạng Polygon xác nhận"
  description="Bạn có thể rời trang; hệ thống vẫn tiếp tục kiểm tra giao dịch."
  tone="pending"
/>
```

- Dùng semantic HTML và semantic tokens; không hard-code màu cho state mới.
- Nội dung chính trước, chi tiết kỹ thuật đặt trong progressive disclosure.
- Mỗi interactive target tối thiểu 44px, luôn có focus-visible state.
- Motion 150–250ms, chỉ dùng opacity/transform và tôn trọng reduced motion.
- UTF-8 tiếng Việt chuẩn; không emoji, không `any` mới.

## Testing strategy

- Unit/component: state, focus, copy, explorer, notifications, light/dark.
- E2E: 320/375/390/768/1024/1440, no horizontal overflow, keyboard, mobile
  drawer, signing/error/confirmed flows.
- A transaction is never shown as confirmed without receipt, matching
  `ProofRecorded` event and required confirmations from the backend.
- Existing 104 browser journeys remain regression coverage.

## Boundaries

- Always: preserve routes/permissions/business behavior and storage semantics.
- Ask first: new dependency, API/database change, image asset purchase.
- Never: restore CertificateRegistry runtime, broadcast/deploy Mainnet, change
  roles, commit or deploy without explicit request.

## Success criteria

- Mobile navigation has four primary actions plus “Thêm”, safe-area support,
  focus trap and restoration, with blockchain discoverable for signers.
- `/blockchain` has a clear primary action, four-step progress, human-readable
  failures, transaction copy/explorer actions and mobile sticky action/status.
- Public verification explains blockchain in plain Vietnamese and hides raw
  identifiers under “Chi tiết nâng cao”.
- Dashboard, forms, notifications and public pages have useful loading, empty
  and error states without blank surfaces.
- Light/dark states meet WCAG AA and no browser-default hover color leaks.
- All mandatory commands pass.

## Approved assumptions

- The user-provided brief is the approved product specification.
- Existing backend response types remain the source of truth for confirmation.
- Lucide remains the single icon library to avoid dependency and bundle churn.
