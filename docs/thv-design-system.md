# THV Design System

## Brand foundation

Đề cử Tinh Hoa Việt sử dụng nhận diện đỏ–vàng trang trọng, hiện đại và gần gũi với văn hóa Việt. Huy hiệu tròn vàng–đỏ là dấu hiệu nhận diện chính; logo ngang dùng cho header, footer và email. Không dùng xanh olive làm màu thương hiệu hoặc logo cũ.

Brand assets được dùng từ `frontend/public/assets/brand/`:

- `thv-brand-wordmark.png`: logo ngang chính thức.
- `thv-brand-emblem.png`: huy hiệu cho favicon, app icon và sidebar thu gọn.

## Color tokens

| Purpose | Light | Dark |
|---|---|---|
| Primary | `#9D0000` | `#F6C515` |
| Primary strong | `#650000` | `#FFD83D` |
| Canvas | `#FFF9F3` | `#1A0B0B` |
| Surface | `#FFFFFF` | `#261111` |
| Surface raised | `#FFF4ED` | `#321717` |
| Text | `#241515` | `#FFF9F3` |
| Secondary text | `#6B5656` | `#E4C9C2` |
| Muted text | `#8D7474` | `#B58F85` |
| Border | `#EAD9D3` | `#4C2424` |
| Success | `#347A4A` | `#73B887` |
| Warning | `#A87324` | `#DBB66B` |
| Danger | `#B54343` | `#E08A8A` |
| Information | `#4B6E85` | `#83A9BE` |

Đỏ thương hiệu chỉ dùng cho CTA chính, tiêu đề hero, sidebar nội bộ và trạng thái active. Vàng dùng cho nhấn mạnh, icon và đường viền trang trọng. Gradient chỉ được dùng tiết chế cho nền hero hoặc header:

```css
linear-gradient(115deg, #650000 0%, #470000 100%)
```

Không dùng neon, tím, hiệu ứng Web3 hoặc gradient nhiều màu. Màu thành công/cảnh báo/lỗi giữ ngữ nghĩa riêng và không thay bằng đỏ–vàng thương hiệu.

## Typography

- Primary: `Be Vietnam Pro`.
- Fallback: `Inter`, system sans-serif.
- Display headings use tight tracking and a maximum two-line measure.
- Body copy uses comfortable line height and a maximum readable width of 68 characters.
- Technical identifiers use a mono font only where the identifier itself matters.

## Layout

- Mobile-first breakpoints: 360–430, 768, 1024, 1280, 1440, 1920 px.
- Public pages use a sticky header and a contained editorial canvas.
- Authenticated mobile pages use a compact header, scrollable content, and fixed bottom navigation.
- Authenticated desktop pages use sidebar, context header, and content; shells never nest.
- Standard content width is 1200–1320 px with 16/24/32 px responsive gutters.

## Shape and elevation

- Controls: 10–14 px radius.
- Content surfaces: 16–20 px radius when a container is necessary.
- Avoid card-per-paragraph layouts. Prefer sections, dividers, lists, timelines, and tables.
- Shadows are subtle and used only to establish layers.

## Interaction states

- One primary action per screen or section.
- Hover and focus must preserve text contrast.
- Focus ring: 3 px translucent primary outline with 2 px offset.
- Loading states preserve layout; empty states explain the next useful action.
- Reduced-motion preference disables decorative movement.

## Content voice

- Lead with outcomes and next steps.
- Use familiar Vietnamese; hide implementation details.
- Prefer “Hồ sơ đang được xem xét” over internal status codes.
- Prefer “Tài khoản nhân sự được cấp qua lời mời riêng” over role or authentication architecture.
- Blockchain information appears under “Thông tin xác minh” and expands only on request.

## Core components

- Brand mark and compact product signature.
- Public header and mobile menu.
- Desktop workspace sidebar.
- Mobile bottom navigation.
- Section heading, status badge, data row, timeline, table, empty state, notice, dialog, and toast.
- Search field, filter chips, pagination, form field, upload zone, and confirmation step.
