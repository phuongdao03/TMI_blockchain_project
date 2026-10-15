# Attendance assignment end dates (2026-10)

## Incident and operator flow

- The employee assignment for `CNS-03` at `SG-SILVERSTAR` started on 2026-10-01 without an end date. A second assignment starting on 2026-10-15 therefore overlaps. The GPS policy shown in the incident ended on 2026-10-10, which independently blocks check-in after that date.
- In **Điểm chấm công**, select the employee. The panel now lists that employee's assignments across all worksites. End the old assignment on 2026-10-14 with a reason, then create the new assignment from 2026-10-15. Ensure the new worksite has a GPS policy effective on that day. For continued work at the old site, create a new GPS policy version covering current dates.
- Deleting an assignment means ending its effective period. The row and attendance history stay intact. Worksites use active/inactive status; GPS policy versions remain in history.

## Contract and safeguards

- `PATCH /api/v1/admin/hr/attendance-assignments/{id}` accepts `effectiveTo` and `reason` (10–500 characters). It requires Super Admin and CSRF protection, returns the updated assignment, and audits before/after values plus reason.
- A date before the assignment start, one that excludes recorded attendance, or one that overlaps another assignment is rejected. No schema migration is required.
- Backend service and HTTP contract tests cover the move, history preservation, overlap rejection and input validation. Frontend test covers finding an assignment at another worksite and submitting its end date.
