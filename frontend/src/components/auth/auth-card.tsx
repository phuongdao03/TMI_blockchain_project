import Link from "next/link";
import type { ReactNode } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
} from "@/components/ui/card";

interface AuthCardProps {
  title: string;
  description: string;
  children: ReactNode;
  footer: ReactNode;
}

export function AuthCard({
  title,
  description,
  children,
  footer,
}: AuthCardProps) {
  return (
    <Card className="auth-card rounded-xl backdrop-blur-sm">
      <CardHeader className="px-6 pt-7 pb-5 text-left sm:px-8 sm:pt-8">
        <p className="auth-card-kicker font-mono text-[0.62rem] font-medium tracking-[0.14em] uppercase">
          Đề cử Tinh Hoa Việt
        </p>
        <h1 className="auth-card-title mt-3 text-3xl font-semibold tracking-[-0.03em]">
          {title}
        </h1>
        <CardDescription className="auth-card-description max-w-sm">
          {description}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6 px-6 pb-7 sm:px-8 sm:pb-8">
        {children}
        <p className="auth-card-footer border-t pt-6 text-center text-sm">
          {footer}
        </p>
      </CardContent>
    </Card>
  );
}

export function AuthLink({
  href,
  children,
}: {
  href: string;
  children: ReactNode;
}) {
  return (
    <Link
      className="auth-link font-semibold underline-offset-4 hover:underline"
      href={href}
    >
      {children}
    </Link>
  );
}
