import { ImageResponse } from "next/og";

import { isCertificateNumber } from "@/lib/verification/certificate-route";

export const alt = "Chứng thư xác lập tài sản số Tinh Hoa Việt";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function CertificateOpenGraphImage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const identifier = decodeURIComponent((await params).token);
  const number = isCertificateNumber(identifier)
    ? identifier.toUpperCase()
    : "CHỨNG THƯ SỐ";
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          padding: 34,
          background: "#3f090d",
          color: "#281a16",
        }}
      >
        <div
          style={{
            width: "100%",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            border: "8px double #9b7a35",
            padding: 54,
            background: "#f4ecd2",
          }}
        >
          <div
            style={{
              display: "flex",
              color: "#8b1118",
              fontSize: 24,
              letterSpacing: 6,
            }}
          >
            ĐỀ CỬ VÀ XÁC LẬP TINH HOA VIỆT
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", fontSize: 68, fontWeight: 800 }}>
              Chứng thư xác lập tài sản số
            </div>
            <div
              style={{
                display: "flex",
                marginTop: 28,
                color: "#8b1118",
                fontSize: 38,
                fontWeight: 700,
              }}
            >
              {number}
            </div>
          </div>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              borderTop: "2px solid #9b7a35",
              paddingTop: 24,
              fontSize: 22,
            }}
          >
            <span>Kiểm tra độc lập trên Polygon</span>
            <span>decu.tinhhoaviet.org.vn</span>
          </div>
        </div>
      </div>
    ),
    size,
  );
}
