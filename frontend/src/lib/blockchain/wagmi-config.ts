import { createConfig, http } from "wagmi";
import { injected, walletConnect } from "wagmi/connectors";
import { polygon } from "wagmi/chains";

const walletConnectProjectId =
  process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID?.trim();

const connectors = [
  injected(),
  ...(walletConnectProjectId
    ? [
        walletConnect({
          projectId: walletConnectProjectId,
          showQrModal: true,
          metadata: {
            name: "Đề cử Tinh Hoa Việt",
            description: "Ký và xác minh hồ sơ trên Polygon.",
            url:
              process.env.NEXT_PUBLIC_APP_BASE_URL ??
              "https://decu.tinhhoaviet.org.vn",
            icons: [
              "https://decu.tinhhoaviet.org.vn/assets/brand/thv-brand-emblem.png",
            ],
          },
        }),
      ]
    : []),
] as const;

export const wagmiConfig = createConfig({
  chains: [polygon],
  connectors,
  multiInjectedProviderDiscovery: true,
  transports: { [polygon.id]: http() },
  ssr: true,
});

export const POLYGON_CHAIN_ID = polygon.id;
