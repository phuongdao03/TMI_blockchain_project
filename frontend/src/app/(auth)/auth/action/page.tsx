import type { Metadata } from "next";

import { FirebaseEmailAction } from "@/components/auth/firebase-email-action";

export const metadata: Metadata = { title: "Xác minh tài khoản" };

export default async function FirebaseEmailActionPage({
  searchParams,
}: {
  searchParams: Promise<{
    mode?: string | string[];
    oobCode?: string | string[];
  }>;
}) {
  const query = await searchParams;
  return (
    <FirebaseEmailAction
      mode={typeof query.mode === "string" ? query.mode : ""}
      oobCode={typeof query.oobCode === "string" ? query.oobCode : ""}
    />
  );
}
