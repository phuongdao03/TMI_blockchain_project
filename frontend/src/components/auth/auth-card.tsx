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
    <Card className="rounded-lg border-white/8 bg-[#1c1b1b] shadow-[0_20px_40px_rgb(0_0_0/0.4)]">
      <CardHeader className="px-6 pt-8 pb-5 text-center sm:px-9 sm:pt-10">
        <p className="font-mono text-[0.62rem] font-medium tracking-[0.14em] text-[#ffb4aa] uppercase">
          TMI Certificate
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-[-0.02em] text-[#e5e2e1] sm:text-4xl">
          {title}
        </h1>
        <CardDescription className="mx-auto max-w-sm text-[#ad8883]">
          {description}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6 px-6 pb-8 sm:px-9 sm:pb-10">
        {children}
        <p className="border-t border-white/8 pt-6 text-center text-sm text-[#929090]">
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
      className="font-semibold text-[#ffb4aa] underline-offset-4 hover:text-[#ffdb3c] hover:underline"
      href={href}
    >
      {children}
    </Link>
  );
}
