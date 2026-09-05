"use client";

import {
  QueryClient,
  QueryClientProvider,
  useQuery,
} from "@tanstack/react-query";
import { type ReactNode, useState } from "react";
import { usePathname } from "next/navigation";

import { authApi } from "@/lib/api/client";
import { wagmiConfig } from "@/lib/blockchain/wagmi-config";
import { WagmiProvider } from "wagmi";

const sessionlessPrefixes = [
  "/works",
  "/search",
  "/map",
  "/verify",
  "/voting",
  "/process",
  "/policies",
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
  "/verify-email",
  "/staff-invitation",
] as const;

function SessionBootstrap() {
  const pathname = usePathname();
  const publicPath =
    pathname === "/" ||
    sessionlessPrefixes.some(
      (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
    );
  useQuery({
    queryKey: ["auth", "me"],
    queryFn: authApi.currentUser,
    retry: false,
    staleTime: 60_000,
    enabled: !publicPath,
  });
  return null;
}

export function AppProviders({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  return (
    <WagmiProvider config={wagmiConfig}>
      <QueryClientProvider client={queryClient}>
        <SessionBootstrap />
        {children}
      </QueryClientProvider>
    </WagmiProvider>
  );
}
