export type WorksiteInput = { code: string; name: string };

export type PolicyInput = {
  effectiveFrom: string;
  effectiveTo?: string | null;
  timezone: string;
  latitude: string;
  longitude: string;
  radiusMeters: number;
  maxAccuracyMeters: number;
};

export type AssignmentInput = {
  employeeId: string;
  worksiteId: string;
  effectiveFrom: string;
  effectiveTo?: string | null;
  scheduleCode: string;
  holidayCalendarCode: string;
};
