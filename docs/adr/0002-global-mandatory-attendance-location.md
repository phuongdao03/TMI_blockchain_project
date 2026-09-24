---
status: accepted
---

# Require location evidence for every global attendance event

## Context

The HRMS serves employees in multiple countries and locations. Every employee
must provide location evidence when recording attendance. A browser location
sample is useful evidence, but it cannot prove physical presence or prevent
location spoofing on its own.

## Decision

Require one foreground location sample for every check-in and check-out. Do not
perform background tracking. Worksites, IANA time zones, schedules, holiday
calendars and location policies are effective-dated and may vary per employee.
The server derives all geographic outcomes from coordinates and reported
accuracy; browser results are evidence, never unquestioned proof.

When location policy fails, the system does not silently mark normal attendance.
It creates `PENDING` attendance plus a separate immutable-evidence exception;
the record is non-payable until an audited Super Admin approves or rejects it.
Approval never overwrites the original GPS outcome. A rejection produces
`REJECTED` attendance. The timezone identifier of a worksite is locked once it
has an attendance assignment; relocation requires a new worksite and an
effective-dated reassignment, while the IANA database handles DST changes.
Exact location evidence is sensitive personal data and is restricted to the
affected employee and authorized Super Administrators. It is retained for 24
calendar months after the server receives it, then a scheduled worker purges
the exact latitude and longitude from both immutable evidence and legacy
attendance copies. Status, workday and non-location audit history remain.

The first administrator map uses Leaflet with a configurable OpenStreetMap
tile URL. It visualises the existing centre-and-radius circle policy; the
server, not the browser map, is the only geofence decision-maker. Public OSM
tiles are not a production SLA and deployment must comply with the selected
tile provider's terms and privacy review.

## Consequences

- Attendance remains unsuitable for automatic payroll until the approved
  calculation, leave and overtime rules are complete.
- UTC remains the storage standard, while workday determination moves to an
  effective employee/worksite IANA timezone.
- A migration, API contract, browser permission handling, privacy safeguards,
  admin worksite management and controlled VPS tests are required.
- Geolocation may be inaccurate or spoofed. The product needs quality rules,
  transparent failure reasons and an exception workflow rather than claiming
  absolute physical-presence verification.
