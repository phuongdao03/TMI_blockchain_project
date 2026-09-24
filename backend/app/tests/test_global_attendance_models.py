from app.modules.hr.models import (
    AttendanceAssignment,
    AttendanceLocationEventType,
    AttendanceLocationEvidence,
    AttendanceLocationException,
    AttendanceLocationExceptionStatus,
    AttendanceLocationOutcome,
    AttendanceWorksite,
    AttendanceWorksitePolicy,
)


def test_global_attendance_models_expose_versioned_location_contract() -> None:
    assert AttendanceWorksite.__tablename__ == "attendance_worksites"
    assert AttendanceWorksitePolicy.__tablename__ == "attendance_worksite_policies"
    assert AttendanceAssignment.__tablename__ == "attendance_assignments"
    assert AttendanceLocationEvidence.__tablename__ == "attendance_location_evidence"
    assert AttendanceLocationException.__tablename__ == "attendance_location_exceptions"
    assert {
        AttendanceLocationEventType.CHECK_IN.value,
        AttendanceLocationEventType.CHECK_OUT.value,
    } == {"CHECK_IN", "CHECK_OUT"}
    assert AttendanceLocationOutcome.LOW_ACCURACY.value == "LOW_ACCURACY"
    assert AttendanceLocationExceptionStatus.PENDING.value == "PENDING"
    assert "attendance_id" in AttendanceLocationEvidence.__table__.c
    assert "effective_timezone" in AttendanceLocationEvidence.__table__.c
    assert "retention_until" in AttendanceLocationEvidence.__table__.c
    assert "location_purged_at" in AttendanceLocationEvidence.__table__.c
    assert AttendanceLocationEvidence.__table__.c.received_at.server_default is not None
    assert "location_evidence_id" in AttendanceLocationException.__table__.c
    assert "schedule_code" in AttendanceAssignment.__table__.c
    assert "holiday_calendar_code" in AttendanceAssignment.__table__.c
