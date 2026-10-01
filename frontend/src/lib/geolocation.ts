export type ForegroundLocationCapture = {
  latitude: number;
  longitude: number;
  accuracyMeters: number;
  clientCapturedAt: string;
};

type LocationCaptureFailureCode =
  | "LOCATION_INSECURE_CONTEXT"
  | "LOCATION_UNSUPPORTED"
  | "LOCATION_PERMISSION_DENIED"
  | "LOCATION_POLICY_BLOCKED"
  | "LOCATION_ACCESS_BLOCKED"
  | "LOCATION_TIMEOUT"
  | "LOCATION_UNAVAILABLE"
  | "LOCATION_INVALID";

export class LocationCaptureError extends Error {
  constructor(
    readonly code: LocationCaptureFailureCode,
    message: string,
  ) {
    super(message);
    this.name = "LocationCaptureError";
  }
}

function locationError(error: GeolocationPositionError): LocationCaptureError {
  switch (error.code) {
    case 1:
      return new LocationCaptureError(
        "LOCATION_PERMISSION_DENIED",
        "Trình duyệt hoặc thiết bị từ chối cung cấp vị trí. Kiểm tra quyền vị trí của website, quyền vị trí của trình duyệt trong hệ điều hành rồi thử lại.",
      );
    case 3:
      return new LocationCaptureError(
        "LOCATION_TIMEOUT",
        "Không lấy được vị trí kịp thời. Hãy kiểm tra GPS hoặc kết nối rồi thử lại.",
      );
    default:
      return new LocationCaptureError(
        "LOCATION_UNAVAILABLE",
        "Thiết bị chưa thể cung cấp vị trí. Hãy bật dịch vụ định vị rồi thử lại.",
      );
  }
}

function locationPolicyBlocked(): boolean {
  const policyDocument = document as Document & {
    permissionsPolicy?: { allowsFeature(feature: string): boolean };
    featurePolicy?: { allowsFeature(feature: string): boolean };
  };
  const policy =
    policyDocument.permissionsPolicy ?? policyDocument.featurePolicy;
  try {
    return policy?.allowsFeature("geolocation") === false;
  } catch {
    return false;
  }
}

async function locationPermissionState(): Promise<PermissionState | null> {
  try {
    return (
      (await navigator.permissions?.query({ name: "geolocation" }))?.state ??
      null
    );
  } catch {
    return null;
  }
}

function blockedLocationError(): LocationCaptureError {
  return new LocationCaptureError(
    "LOCATION_ACCESS_BLOCKED",
    "Quyền vị trí của website đã bật, nhưng trình duyệt hoặc thiết bị vẫn chặn lấy vị trí. Kiểm tra dịch vụ định vị của hệ điều hành và quyền vị trí của trình duyệt, rồi mở lại trang để thử.",
  );
}

function policyLocationError(): LocationCaptureError {
  return new LocationCaptureError(
    "LOCATION_POLICY_BLOCKED",
    "Trang hiện tại bị chính sách bảo mật chặn lấy vị trí. Hãy mở trực tiếp website chấm công hoặc liên hệ quản trị viên để kiểm tra cấu hình.",
  );
}

/** Captures one location only after an explicit attendance action. */
export async function captureForegroundLocation(): Promise<ForegroundLocationCapture> {
  if (typeof window === "undefined" || !window.isSecureContext) {
    throw new LocationCaptureError(
      "LOCATION_INSECURE_CONTEXT",
      "Chấm công bằng vị trí chỉ hoạt động trên kết nối bảo mật (HTTPS).",
    );
  }
  if (!navigator.geolocation) {
    throw new LocationCaptureError(
      "LOCATION_UNSUPPORTED",
      "Trình duyệt này không hỗ trợ lấy vị trí cho chấm công.",
    );
  }

  const readPosition = (enableHighAccuracy: boolean) =>
    new Promise<GeolocationPosition>((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject, {
        enableHighAccuracy,
        maximumAge: 0,
        timeout: 15_000,
      });
    });
  let position: GeolocationPosition;
  try {
    position = await readPosition(true);
  } catch (error) {
    const failure = error as GeolocationPositionError;
    if (failure.code === 1) {
      if (locationPolicyBlocked()) {
        throw policyLocationError();
      }
      const permissionState = await locationPermissionState();
      if (permissionState === "denied" || permissionState === "prompt") {
        throw locationError(failure);
      }
    }
    try {
      position = await readPosition(false);
    } catch (retryError) {
      const retryFailure = retryError as GeolocationPositionError;
      if (retryFailure.code === 1) {
        if (locationPolicyBlocked()) {
          throw policyLocationError();
        }
        if ((await locationPermissionState()) === "granted") {
          throw blockedLocationError();
        }
      }
      throw locationError(retryFailure);
    }
  }
  const { accuracy, latitude, longitude } = position.coords;
  const capturedAt = new Date(position.timestamp);
  if (
    !Number.isFinite(latitude) ||
    !Number.isFinite(longitude) ||
    !Number.isFinite(accuracy) ||
    accuracy <= 0 ||
    Number.isNaN(capturedAt.getTime())
  ) {
    throw new LocationCaptureError(
      "LOCATION_INVALID",
      "Dữ liệu vị trí chưa đủ chính xác. Hãy chờ GPS ổn định rồi thử lại.",
    );
  }
  return {
    latitude: Number(latitude.toFixed(6)),
    longitude: Number(longitude.toFixed(6)),
    accuracyMeters: Math.max(0.01, Number(accuracy.toFixed(2))),
    clientCapturedAt: capturedAt.toISOString(),
  };
}
