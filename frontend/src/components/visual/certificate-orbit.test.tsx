import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CertificateOrbit } from "@/components/visual/certificate-orbit";

describe("CertificateOrbit", () => {
  it("presents the TMI evidence register as one accessible visual", () => {
    render(<CertificateOrbit />);

    expect(
      screen.getByRole("img", {
        name: "Sổ bằng chứng số TMI",
      }),
    ).toBeDefined();
    expect(screen.getByText("DẤU VÂN TAY DỮ LIỆU")).toBeDefined();
    expect(screen.getByText("Sẵn sàng xác minh")).toBeDefined();
  });
});
