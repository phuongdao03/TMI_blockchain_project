import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CertificateOrbit } from "@/components/visual/certificate-orbit";

describe("CertificateOrbit", () => {
  it("presents the TMI evidence register as one accessible visual", () => {
    render(<CertificateOrbit />);

    expect(
      screen.getByRole("img", {
        name: "Hồ sơ đề cử minh họa",
      }),
    ).toBeDefined();
    expect(screen.getByText("DẤU VÂN TAY DỮ LIỆU")).toBeDefined();
    expect(screen.getByText("Sẵn sàng xác minh")).toBeDefined();
  });
});
