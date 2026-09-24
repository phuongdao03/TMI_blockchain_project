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
        "Bạn đã từ chối quyền vị trí. Hãy cho phép vị trí rồi thử lại.",
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

  const position = await new Promise<GeolocationPosition>((resolve, reject) => {
    navigator.geolocation.getCurrentPosition(resolve, reject, {
      enableHighAccuracy: true,
      maximumAge: 0,
      timeout: 15_000,
    });
  }).catch((error: GeolocationPositionError) => {
    throw locationError(error);
  });
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
