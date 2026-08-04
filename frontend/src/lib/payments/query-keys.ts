export const paymentKeys = {
  all: ["payments"] as const,
  detail: (orderId: string) => [...paymentKeys.all, orderId] as const,
};
