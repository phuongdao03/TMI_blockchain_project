# Screenshot corrections and member chat redesign

User acceptance: natural Vietnamese word wrapping; direct attendance navigation;
home link reads “Xem quy trình”; usable GPS header actions; calmer member chat.

Implement in order: localized typography/grid repairs and navigation; compact
room entry rows; desktop room rail with focused conversation and mobile room
selector; browser checks at 390/768/1440 in both themes.

Preserve backend authorization, membership access checks, message pagination,
polling, editing, removal and failed-send recovery. Attendance entry can be
visible to reviewers without granting an employee profile or backend rights.
No invented online counts, unread counts or room access claims.

Acceptance: a long asset title wraps only between words; GPS actions retain
their label on one line; reviewer sees attendance directly; denied chat never
loads private messages; selecting rooms and sending/editing still work.

Implemented: verification facts use natural word wrapping; GPS actions occupy
the explicit third grid column and keep their labels on one line. Reviewer
attendance is a direct sidebar/mobile destination, while employee-only leave
and overtime retain their existing gating. The home action reads “Xem quy trình”.

Member room entry is now two compact rows rather than nested promotional cards.
The chat has a desktop room rail, compact mobile selectors, a bounded scrollable
conversation and a distinct composer. Room entry links jump to the conversation.
History, access checks, polling and edit/remove/send behavior are preserved.

Checks: 25 initial unit regressions and 28 final HR/chat/navigation checks passed;
four screenshot-repair browser cases passed, followed by six updated membership
access cases. The old membership screenshot test's >250px stacked-room width was
updated to verify the new compact controls retain 44px touch height. Lint has
zero errors/four pre-existing warnings; typecheck and production build passed.
Screenshots: `ux-evidence-2026-10-27/chat-redesign-*.png` (390/768/1440, both themes).
Browser data is synthetic. Physical devices and production were not changed.
