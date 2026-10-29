export const notificationKeys = {
  unread: (userId?: string) =>
    ["notifications", "unread-count", userId] as const,
  recent: (userId?: string) => ["notifications", "recent", userId] as const,
  list: (userId: string | undefined, page: number, unreadOnly: boolean) =>
    ["notifications", "list", userId, page, unreadOnly] as const,
};
