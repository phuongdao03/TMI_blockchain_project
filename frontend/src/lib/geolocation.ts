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
        "Chưa được cấp quyền vị trí cho lần lấy này. Kiểm tra quyền vị trí của website và thiết bị rồi thử lại.",
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
    if (failure.code === 1) throw locationError(failure);
    try {
      position = await readPosition(false);
    } catch (retryError) {
      throw locationError(retryError as GeolocationPositionError);
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
    latitude,
    longitude,
    accuracyMeters: accuracy,
    clientCapturedAt: capturedAt.toISOString(),
  };
}
